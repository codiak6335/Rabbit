import os
import threading
import time


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_EMULATOR = os.getenv('RABBIT_EMULATOR', '').lower() in ('1', 'true', 'yes', 'on')


def project_path(path):
    return os.path.join(BASE_DIR, path.lstrip('/'))


def patch_time_module():
    if not hasattr(time, 'ticks_ms'):
        time.ticks_ms = lambda: int(time.monotonic() * 1000)
    if not hasattr(time, 'ticks_diff'):
        time.ticks_diff = lambda current, start: current - start
    if not hasattr(time, 'sleep_ms'):
        time.sleep_ms = lambda value: time.sleep(value / 1000.0)


class EmulatorState:
    def __init__(self):
        self._lock = threading.Lock()
        self.strip = []
        self.display = []
        self.audio_events = []

    def update_strip(self, pixels):
        with self._lock:
            self.strip = [list(pixel) for pixel in pixels]

    def update_display(self, lines):
        with self._lock:
            self.display = list(lines)

    def add_audio_event(self, label):
        with self._lock:
            self.audio_events.append({'event': label, 'ticks_ms': time.ticks_ms()})
            self.audio_events = self.audio_events[-10:]

    def snapshot(self):
        with self._lock:
            lit_pixels = []
            for index, pixel in enumerate(self.strip):
                if any(pixel):
                    lit_pixels.append({'index': index, 'rgb': list(pixel)})
            return {
                'pixelCount': len(self.strip),
                'litPixels': lit_pixels,
                'displayLines': list(self.display),
                'audioEvents': list(self.audio_events),
            }


EMULATOR_STATE = EmulatorState()


class FakePin:
    OUT = 1

    def __init__(self, pin, mode=None):
        self.pin = pin
        self.mode = mode
        self._value = 0

    def value(self, new_value=None):
        if new_value is None:
            return self._value
        self._value = new_value

    def __call__(self, new_value=None):
        return self.value(new_value)


class FakeSPI:
    def __init__(self, *args, **kwargs):
        pass

    def write(self, data):
        return len(data)


class FakeMachineModule:
    Pin = FakePin
    SPI = FakeSPI

    @staticmethod
    def unique_id():
        return b'RABBIT01'

    @staticmethod
    def reset():
        raise SystemExit('Emulated reset requested')


class FakeNeoPixel:
    def __init__(self, pin, count, timing=1):
        self.pin = pin
        self.count = count
        self.timing = timing
        self._pixels = [(0, 0, 0)] * count
        EMULATOR_STATE.update_strip(self._pixels)

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            values = [tuple(item) for item in value]
            pixels = list(self._pixels)
            pixels[index] = values
            self._pixels = pixels
        else:
            pixels = list(self._pixels)
            pixels[index] = tuple(value)
            self._pixels = pixels

    def __getitem__(self, index):
        return self._pixels[index]

    def fill(self, value):
        self._pixels = [tuple(value)] * self.count

    def write(self):
        EMULATOR_STATE.update_strip(self._pixels)


class FakeNeoPixelModule:
    NeoPixel = FakeNeoPixel


class FakeWLAN:
    def __init__(self, interface):
        self.interface = interface
        self._active = False
        self._connected = False
        self._essid = None

    def active(self, value=None):
        if value is None:
            return self._active
        self._active = value

    def disconnect(self):
        self._connected = False

    def config(self, essid=None, password=None):
        self._essid = essid

    def connect(self, ssid, password):
        self._connected = True
        self._essid = ssid

    def isconnected(self):
        return self._connected

    def ifconfig(self):
        host = '127.0.0.1' if IS_EMULATOR else '0.0.0.0'
        return (host, '255.0.0.0', host, host)


class FakeNetworkModule:
    AP_IF = 1
    STA_IF = 2

    @staticmethod
    def WLAN(interface):
        return FakeWLAN(interface)


def get_machine_module():
    if IS_EMULATOR:
        return FakeMachineModule()
    import machine
    return machine


def get_neopixel_module():
    if IS_EMULATOR:
        return FakeNeoPixelModule()
    import neopixel
    return neopixel


def get_network_module():
    if IS_EMULATOR:
        return FakeNetworkModule()
    import network
    return network
