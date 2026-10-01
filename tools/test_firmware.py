"""Host-side protocol/state tests; does not validate the physical circuit."""
import importlib.util
import sys
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
    def __init__(self, *args, **kwargs): pass
    def write(self, data):
        events.append(('spi', data))
        if self.fail: raise OSError('injected SPI fault')

sys.modules['machine'] = types.SimpleNamespace(Pin=Pin, SPI=SPI)
time.sleep_us = lambda _: None
path = Path(__file__).resolve().parents[1]/'pcb/analog_matrix_4x4_rev_d/firmware/main.py'
spec = importlib.util.spec_from_file_location('matrix_firmware', path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
assert m.encode(0, 0) == b'\x00\x00\x00'
assert m.encode(3, 65535) == b'\x03\xff\xff'
assert m.encode(2, 32768) == b'\x02\x80\x00'
b = m.Matrix()
assert not b.armed and b.run.value() == b.enable.value() == 0
assert sum(e[0] == 'spi' for e in events) == 20
assert all(p.value() == 1 for p in b.cs)
a = [[0.0]*4 for _ in range(4)]
a[0][0], a[3][3] = 1, -1
b.set_matrix(a)
assert b.codes[0][0] == b.codes[3][3] == 64187  # Initial 1.021 gain estimate.
assert b.signs == 1 << 15
events.clear()
bad = [[0]*4 for _ in range(4)];bad[2][1] = 1.1
try: b.set_matrix(bad)
except ValueError: pass
else: raise AssertionError('out-of-range matrix accepted')
assert not events, 'invalid matrix changed hardware'
bad[2][1] = float('nan')
try: b.set_matrix(bad)
except ValueError: pass
else: raise AssertionError('NaN accepted')
assert not events
b.arm();events.clear()
b.set_matrix(a)
assert events[0] == ('pin', 14, 0)
assert events[1] == ('pin', 13, 0)
assert events[-1] == ('pin', 14, 1)
bits = [e[2] for e in events if e[:2] == ('pin', 10)]
assert bits == [1] + [0]*15, 'shift-register bit order incorrect'
b.set_trim([32000, 32768, 33000, 32768])
assert b.trim[0] == 32000
b.raw(2, 1, 65535, True)
assert b.signs == 1 << 9 and sum(map(sum,b.codes)) == 65535
b.set_calibration([[1.039]*4 for _ in range(4)], [[1.041]*4 for _ in range(4)])
assert b.calibrated and not b.armed and not b.raw_mode
assert sum(map(sum,b.codes)) == 0
b.arm()
b.spi.fail = True
try: b.set_matrix(a)
except OSError: pass
else: raise AssertionError('fault not propagated')
assert not b.armed and b.run.value() == b.enable.value() == 0
assert all(p.value() == 1 for p in b.cs)
print('PASS: packing, startup mute, mapping, sign bit order, invalid inputs, blanking, trim, calibration raw mode, SPI fault mute')
