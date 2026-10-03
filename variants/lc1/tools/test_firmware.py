"""Host-side checks of protocol framing, blanking and fault recovery."""
import importlib.util
import json
import os
import sys
import tempfile
import time
import types
from pathlib import Path

events = []


class Pin:
    OUT = 1

    def __init__(self, n, mode=None, value=0):
        self.n, self.v = n, value

    def value(self, value=None):
        if value is not None:
            self.v = value
            events.append(('pin', self.n, value))
        return self.v


class SPI:
    MSB = 0
    fail = False

    def __init__(self, *args, **kwargs):
        # DAC7811: falling-edge capture, then trailing rising edge before SYNC.
        assert kwargs['phase'] == 0 and kwargs['polarity'] == 1

    def write(self, payload):
        events.append(('spi', payload))
        if self.fail:
            raise OSError('injected SPI fault')


class I2C:
    fail = False
    short = False

    def __init__(self, *args, **kwargs):
        assert kwargs['sda'].n == 0 and kwargs['scl'].n == 1

    def writeto(self, address, payload):
        events.append(('i2c', address, payload))
        if self.fail:
            raise OSError('injected I2C fault')
        return len(payload) - int(self.short)


sys.modules['machine'] = types.SimpleNamespace(Pin=Pin, SPI=SPI, I2C=I2C)
time.sleep_us = lambda delay: events.append(('delay', delay))
path = Path(__file__).resolve().parents[1]/'firmware/main.py'
spec = importlib.util.spec_from_file_location('lc1_firmware', path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def rejects(fn, exception=ValueError):
    try:
        fn()
    except exception:
        return
    raise AssertionError('invalid operation accepted')


with tempfile.TemporaryDirectory() as directory:
    previous = os.getcwd()
    os.chdir(directory)
    try:
        # Known frames from DAC7811 table 1 and MCP4728 figure 5-8.
        assert m.encode_row([0, 1, 2048, 4095]) == bytes.fromhex('1fff 1800 1001 1000')
        assert m.encode_trim(0, 2500) == bytes.fromhex('40 89 c4')
        assert m.encode_trim(3, 4095) == bytes.fromhex('46 8f ff')
        for invalid in [-1, 4096, True, 1.1]:
            rejects(lambda: m.code12(invalid))
        # A file intended for the old board must never be read.
        Path('calibration.json').write_text('{"trim":[65535,65535,65535,65535]}')
        b = m.Matrix()
        assert not b.armed and b.run.value() == 0 and b.program_valid
        assert b.trim == [2500]*4 and b.status()['revision'] == 'LC1'
        assert len([e for e in events if e[0] == 'spi']) == 4
        assert len([e for e in events if e[0] == 'i2c']) == 4
        assert all(p.value() == 1 for p in b.cs)
        matrix = [[0.0]*4 for _ in range(4)]
        matrix[0][0], matrix[3][3] = 1, -1
        b.arm()
        events.clear()
        b.set_matrix(matrix)
        assert b.signs == 1 << 15
        assert b.codes[0][0] == b.codes[3][3] == 3832
        assert events[0] == ('pin', 14, 0) and events[-1] == ('pin', 14, 1)
        assert events[-2] == ('delay', 2000)
        assert [e[2] for e in events if e[:2] == ('pin', 10)] == [1] + [0]*15
        events.clear()
        bad = [[0.0]*4 for _ in range(4)]
        for value in [1.1, float('nan'), float('inf'), True]:
            bad[1][2] = value
            rejects(lambda: b.set_matrix(bad))
            assert not events, 'invalid matrix changed hardware'
        for bus, mode in [('spi', 'fail'), ('i2c', 'fail'), ('i2c', 'short')]:
            b.arm()
            setattr(getattr(b, bus), mode, True)
            rejects(lambda: b.set_matrix(matrix), OSError)
            assert not b.armed and not b.program_valid and b.run.value() == 0
            assert all(p.value() == 1 for p in b.cs)
            rejects(b.arm)
            setattr(getattr(b, bus), mode, False)
            b.set_matrix(matrix)
            assert b.program_valid and not b.armed
        b.raw(2, 1, 4095, True)
        assert b.signs == 1 << 9 and sum(map(sum, b.codes)) == 4095
        b.set_calibration([[1.07]*4 for _ in range(4)], [[1.08]*4 for _ in range(4)])
        assert b.calibrated and not b.armed and not b.raw_mode
        assert sum(map(sum, b.codes)) == 0
        b.set_trim([2400, 2500, 2600, 2500])
        b.command({'cmd': 'save'})
        cfg = json.loads(Path('calibration_lc1.json').read_text())
        assert cfg['revision'] == 'LC1' and cfg['trim'][0] == 2400
        cfg['revision'] = 'D'
        Path('calibration_lc1.json').write_text(json.dumps(cfg))
        b2 = m.Matrix()
        assert not b2.calibrated and b2.trim == [2500]*4
        assert 'different hardware revision' in b2.load_warning
    finally:
        os.chdir(previous)

print('PASS: row-chain order, SPI mode, trim reference/configuration, startup mute, sign order, '
      'invalid inputs, 2 ms blanking, raw calibration, revision separation, SPI/I2C faults, re-arm guard')
