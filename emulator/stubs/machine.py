class Pin:
    OUT = 1
    IN = 0

    def __init__(self, number, mode=None):
        self.number = number
        self.mode = mode
        self._value = 0

    def __call__(self, value=None):
        return self.value(value)

    def value(self, value=None):
        if value is not None:
            self._value = int(bool(value))
        return self._value


class SPI:
    def __init__(self, bus, baudrate=None, **kwargs):
        self.bus = bus
        self.baudrate = baudrate
        self.options = kwargs

    def write(self, data):
        return len(data)


def unique_id():
    return b"\x52\x41\x42\x42\x49\x54"


def reset():
    print("[emulator] machine.reset() requested")
