from emulator import runtime_state


class I8080:
    def __init__(self, **kwargs):
        self.options = kwargs


class ST7789:
    def __init__(self, interface, **kwargs):
        self.interface = interface
        self.options = kwargs

    def reset(self):
        pass

    def init(self):
        pass

    def invert_color(self, enabled):
        pass

    def swap_xy(self, enabled):
        pass

    def mirror(self, horizontal, vertical):
        pass

    def set_gap(self, x, y):
        pass

    def bitmap(self, x, y, width, height, buffer):
        runtime_state.mark_display_show()

    def backlight_on(self):
        pass

    @staticmethod
    def color565(red, green, blue):
        return ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)
