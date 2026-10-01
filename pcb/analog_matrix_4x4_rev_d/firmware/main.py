"""4x4 matrix Rev A2, Raspberry Pi Pico / MicroPython.

USB serial JSON lines. Power the analog rails before Pico; outputs start muted.
Factory gains below are estimates. Measure BOTH signs at the installed 50 ohm load.
The MCU programs static analog gains; it never samples the signal path.
"""
from machine import Pin, SPI
import time
import math
import json
import sys


def delay_us(us):
    time.sleep_us(us)


def code16(x):
    if isinstance(x, bool) or not isinstance(x, int) or not 0 <= x <= 65535:
        raise ValueError("code must be an integer in 0..65535")
    return x


def checked_matrix(values, gains=False):
    if not isinstance(values, list) or len(values) != 4:
        raise ValueError("expected four rows")
    result = []
    for row in values:
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError("expected four columns")
        out = []
        for x in row:
            if isinstance(x, bool) or not isinstance(x, (int, float)):
                raise ValueError("matrix entries must be numbers")
            x = float(x)
            if not math.isfinite(x) or (not gains and abs(x) > 1):
                raise ValueError("matrix entries must be finite and within -1..1")
            if gains and not .9 <= x <= 1.2:
                raise ValueError("measured full-code magnitude must be 0.9..1.2")
            out.append(x)
        result.append(out)
    return result


def encode(channel, code):
    if not isinstance(channel, int) or not 0 <= channel < 4:
        raise ValueError("channel must be 0..3")
    value = (channel << 16) | code16(code)
    # AD5544 uses the last 18 bits received before CS rises.
    return bytes((value >> 16, (value >> 8) & 255, value & 255))


class Matrix:
    def __init__(self):
        self.run = Pin(14, Pin.OUT, value=0)
        self.enable = Pin(13, Pin.OUT, value=0)
        self.reset = Pin(9, Pin.OUT, value=0)
        self.ldac = Pin(8, Pin.OUT, value=1)
        self.cs = [Pin(n, Pin.OUT, value=1) for n in (4, 5, 6, 7, 15)]
        self.sd = Pin(10, Pin.OUT, value=0)
        self.sc = Pin(11, Pin.OUT, value=0)
        self.sl = Pin(12, Pin.OUT, value=0)
        self.spi = SPI(0, baudrate=1_000_000, polarity=0, phase=0,
                       bits=8, firstbit=SPI.MSB, sck=Pin(2), mosi=Pin(3))
        self.armed = False
        self.calibrated = False
        self.positive = [[1.021] * 4 for _ in range(4)]
        self.negative = [[1.021] * 4 for _ in range(4)]
        self.trim = [32768] * 4
        self.matrix = [[0.0] * 4 for _ in range(4)]
        self.codes = [[0] * 4 for _ in range(4)]
        self.signs = 0
        self.raw_mode = False
        self.load_warning = None
        try:
            with open("calibration.json") as f:
                cfg = json.load(f)
            pos = checked_matrix(cfg["positive"], gains=True)
            neg = checked_matrix(cfg["negative"], gains=True)
            trim = self._trim_codes(cfg["trim"])
            self.positive, self.negative, self.trim = pos, neg, trim
            self.calibrated = bool(cfg.get("calibrated", False))
        except OSError:
            self.load_warning = "No calibration file; using approximate gains"
        except (ValueError, KeyError, TypeError) as exc:
            self.load_warning = "Invalid calibration file; using approximate gains: " + str(exc)
        delay_us(500_000)
        self.reset.value(1)
        self._program(self.codes, self.signs, self.trim)

    @staticmethod
    def _trim_codes(values):
        if not isinstance(values, list) or len(values) != 4:
            raise ValueError("expected four trim codes")
        return [code16(x) for x in values]

    def mute(self):
        self.run.value(0)
        self.enable.value(0)
        self.armed = False

    def _write(self, chip, channel, code):
        payload = encode(channel, code)
        self.cs[chip].value(0)
        try:
            self.spi.write(payload)
        finally:
            self.cs[chip].value(1)

    def _latch(self):
        self.ldac.value(0)
        delay_us(2)
        self.ldac.value(1)

    def _signs(self, bits):
        # Highest bit first: final first-chip QA=bit0, second-chip QA=bit8.
        self.sl.value(0)
        for bit in range(15, -1, -1):
            self.sc.value(0)
            self.sd.value((bits >> bit) & 1)
            delay_us(1)
            self.sc.value(1)
            delay_us(1)
        self.sc.value(0)
        self.sl.value(1)
        delay_us(1)
        self.sl.value(0)

    def _program(self, codes, signs, trim):
        resume = self.armed
        self.run.value(0)
        delay_us(20)
        self.enable.value(0)
        try:
            self._signs(signs)
            for i in range(4):
                for j in range(4):
                    self._write(i, j, codes[i][j])
            for i in range(4):
                self._write(4, i, trim[i])
            self._latch()
            delay_us(50)
            if resume:
                self.enable.value(1)
                delay_us(50)
                self.run.value(1)
        except Exception:
            self.mute()
            raise
        self.codes = [row[:] for row in codes]
        self.signs = signs

    def set_matrix(self, matrix):
        values = checked_matrix(matrix)
        codes = [[0] * 4 for _ in range(4)]
        signs = 0
        for i in range(4):
            for j in range(4):
                x = values[i][j]
                gain = self.negative[i][j] if x < 0 else self.positive[i][j]
                d = int(abs(x) / gain * 65535 + .5)
                if d > 65535:
                    raise ValueError("requested coefficient exceeds calibrated range")
                codes[i][j] = d
                if x < 0:
                    signs |= 1 << (4*i+j)
        self._program(codes, signs, self.trim)
        self.matrix = values
        self.raw_mode = False

    def set_trim(self, values):
        values = self._trim_codes(values)
        self._program(self.codes, self.signs, values)
        self.trim = values

    def set_calibration(self, positive, negative):
        # Only change calibration while muted; existing raw codes remain until SET.
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
        code16(code)
        codes = [[0]*4 for _ in range(4)]
        codes[row][column] = code
        self._program(codes, (1 << (4*row+column)) if negative else 0, self.trim)
        self.matrix = [[0.0]*4 for _ in range(4)]
        self.matrix[row][column] = (-1 if negative else 1)*code/65535 * (
            self.negative[row][column] if negative else self.positive[row][column])
        self.raw_mode = True

    def arm(self):
        self.enable.value(1)
        delay_us(50)
        self.run.value(1)
        self.armed = True

    def status(self):
        return dict(armed=self.armed, calibrated=self.calibrated,
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
            self.mute()  # Flash writing is performed only with outputs muted.
            with open("calibration.json", "w") as f:
                json.dump(dict(positive=self.positive, negative=self.negative,
                               trim=self.trim, calibrated=self.calibrated), f)
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
