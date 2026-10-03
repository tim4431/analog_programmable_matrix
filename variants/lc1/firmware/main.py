"""LC1 only: Pico, four DAC7811 chains, MCP4728 trim; USB JSON lines.

Apply analog power before USB. Outputs start muted. Factory gains are estimates.
Do not install this firmware on Revision D; its DAC protocol is different.
"""
from machine import Pin, SPI, I2C
import json
import math
import sys
import time


def code12(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 4095:
        raise ValueError("code must be an integer in 0..4095")
    return value


def checked_matrix(values, gains=False):
    if not isinstance(values, list) or len(values) != 4:
        raise ValueError("expected four rows")
    result = []
    for row in values:
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError("expected four columns")
        out = []
        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("matrix entries must be numbers")
            value = float(value)
            if not math.isfinite(value) or (not gains and abs(value) > 1):
                raise ValueError("matrix entries must be finite and within -1..1")
            if gains and not .9 <= value <= 1.2:
                raise ValueError("measured full-code magnitude must be 0.9..1.2")
            out.append(value)
        result.append(out)
    return result


def encode_row(codes):
    if not isinstance(codes, list) or len(codes) != 4:
        raise ValueError("expected four row codes")
    # DAC7811 command 0001 loads and updates. Farthest column first.
    words = [0x1000 | code12(c) for c in reversed(codes)]
    return bytes(v for word in words for v in (word >> 8, word & 255))


def encode_trim(channel, code):
    if isinstance(channel, bool) or not isinstance(channel, int) or not 0 <= channel < 4:
        raise ValueError("channel must be 0..3")
    code12(code)
    # Volatile multi-write: UDAC=0, internal 2.048 V, normal mode, gain=1.
    return bytes((0x40 | (channel << 1), 0x80 | (code >> 8), code & 255))


class Matrix:
    def __init__(self):
        self.run = Pin(14, Pin.OUT, value=0)
        self.cs = [Pin(n, Pin.OUT, value=1) for n in (4, 5, 6, 7)]
        self.sd = Pin(10, Pin.OUT, value=0)
        self.sc = Pin(11, Pin.OUT, value=0)
        self.sl = Pin(12, Pin.OUT, value=0)
        # Mode 2 captures on falling edges and supplies the trailing rising
        # edge before SYNC rises, as required when using SDO daisy chains.
        self.spi = SPI(0, baudrate=1_000_000, polarity=1, phase=0,
                       bits=8, firstbit=SPI.MSB, sck=Pin(2), mosi=Pin(3))
        self.i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100_000)
        self.armed = False
        self.program_valid = False
        self.calibrated = False
        self.positive = [[1.0687] * 4 for _ in range(4)]
        self.negative = [[1.0687] * 4 for _ in range(4)]
        self.trim = [2500] * 4
        self.matrix = [[0.0] * 4 for _ in range(4)]
        self.codes = [[0] * 4 for _ in range(4)]
        self.signs = 0
        self.raw_mode = False
        self.load_warning = None
        try:
            with open("calibration_lc1.json") as stream:
                cfg = json.load(stream)
            if cfg.get("revision") != "LC1":
                raise ValueError("calibration belongs to a different hardware revision")
            positive = checked_matrix(cfg["positive"], True)
            negative = checked_matrix(cfg["negative"], True)
            trim = self._trim_codes(cfg["trim"])
            self.positive, self.negative, self.trim = positive, negative, trim
            self.calibrated = bool(cfg.get("calibrated", False))
        except OSError:
            self.load_warning = "No LC1 calibration file; using approximate gains"
        except (ValueError, KeyError, TypeError) as exc:
            self.load_warning = "Invalid LC1 calibration; using approximate gains: " + str(exc)
        time.sleep_us(500_000)
        self._program(self.codes, self.signs, self.trim)

    @staticmethod
    def _trim_codes(values):
        if not isinstance(values, list) or len(values) != 4:
            raise ValueError("expected four trim codes")
        return [code12(x) for x in values]

    def mute(self):
        self.run.value(0)
        self.armed = False

    def _write_row(self, row, codes):
        payload = encode_row(codes)
        self.cs[row].value(0)
        try:
            self.spi.write(payload)
        finally:
            self.cs[row].value(1)

    def _write_trim(self, channel, code):
        payload = encode_trim(channel, code)
        if self.i2c.writeto(0x60, payload) != len(payload):
            raise OSError("MCP4728 did not acknowledge every byte")

    def _signs(self, bits):
        self.sl.value(0)
        for bit in range(15, -1, -1):
            self.sc.value(0)
            self.sd.value((bits >> bit) & 1)
            time.sleep_us(1)
            self.sc.value(1)
            time.sleep_us(1)
        self.sc.value(0)
        self.sl.value(1)
        time.sleep_us(1)
        self.sl.value(0)

    def _program(self, codes, signs, trim):
        resume = self.armed
        self.run.value(0)
        self.program_valid = False
        time.sleep_us(20)
        try:
            self._signs(signs)
            for row in range(4):
                self._write_row(row, codes[row])
            for channel in range(4):
                self._write_trim(channel, trim[channel])
            time.sleep_us(2000)  # Settle the 100 us offset filters.
            self.codes = [row[:] for row in codes]
            self.signs = signs
            self.program_valid = True
            if resume:
                self.run.value(1)
        except Exception:
            self.mute()
            raise

    def set_matrix(self, matrix):
        values = checked_matrix(matrix)
        codes = [[0] * 4 for _ in range(4)]
        signs = 0
        for i in range(4):
            for j in range(4):
                value = values[i][j]
                gain = self.negative[i][j] if value < 0 else self.positive[i][j]
                code = int(abs(value) / gain * 4095 + .5)
                if code > 4095:
                    raise ValueError("requested coefficient exceeds calibrated range")
                codes[i][j] = code
                if value < 0:
                    signs |= 1 << (4*i+j)
        self._program(codes, signs, self.trim)
        self.matrix = values
        self.raw_mode = False

    def set_trim(self, values):
        values = self._trim_codes(values)
        self._program(self.codes, self.signs, values)
        self.trim = values

    def set_calibration(self, positive, negative):
        pos, neg = checked_matrix(positive, True), checked_matrix(negative, True)
        self.mute()
        self.positive, self.negative = pos, neg
        self.calibrated = True
        self.load_warning = None
        self.set_matrix([[0.0]*4 for _ in range(4)] if self.raw_mode else self.matrix)

    def raw(self, row, column, code, negative=False):
        if any(isinstance(x, bool) or not isinstance(x, int) or not 0 <= x < 4
               for x in (row, column)):
            raise ValueError("row and column must be 0..3")
        if not isinstance(negative, bool):
            raise ValueError("negative must be true or false")
        code12(code)
        codes = [[0] * 4 for _ in range(4)]
        codes[row][column] = code
        self._program(codes, (1 << (4*row+column)) if negative else 0, self.trim)
        self.matrix = [[0.0]*4 for _ in range(4)]
        gain = self.negative[row][column] if negative else self.positive[row][column]
        self.matrix[row][column] = (-1 if negative else 1)*code/4095*gain
        self.raw_mode = True

    def arm(self):
        if not self.program_valid:
            raise ValueError("programming failed; send SET successfully before ARM")
        self.run.value(1)
        self.armed = True

    def status(self):
        return dict(revision="LC1", coefficient_bits=12, program_valid=self.program_valid,
                    armed=self.armed, calibrated=self.calibrated,
                    matrix=self.matrix, codes=self.codes, signs=self.signs,
                    trim=self.trim, raw_mode=self.raw_mode, warning=self.load_warning)

    def command(self, obj):
        if not isinstance(obj, dict):
            raise ValueError("expected JSON object")
        cmd = obj.get("cmd")
        if cmd == "set": self.set_matrix(obj["matrix"])
        elif cmd == "mute": self.mute()
        elif cmd == "arm": self.arm()
        elif cmd == "trim": self.set_trim(obj["codes"])
        elif cmd == "calibration": self.set_calibration(obj["positive"], obj["negative"])
        elif cmd == "raw": self.raw(obj["row"], obj["column"], obj["code"], obj.get("negative", False))
        elif cmd == "save":
            self.mute()
            with open("calibration_lc1.json", "w") as stream:
                json.dump(dict(revision="LC1", positive=self.positive, negative=self.negative,
                               trim=self.trim, calibrated=self.calibrated), stream)
        elif cmd != "status": raise ValueError("unknown command")
        return self.status()


def serve():
    board = Matrix()
    print(json.dumps(dict(ready=True, **board.status())))
    try:
        for line in sys.stdin:
            try:
                print(json.dumps(dict(ok=True, **board.command(json.loads(line)))))
            except Exception as exc:
                board.mute()
                print(json.dumps(dict(ok=False, error=str(exc), armed=False)))
    finally:
        board.mute()


if __name__ == "__main__":
    serve()
