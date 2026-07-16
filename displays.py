import os
import time

from runtime_support import EMULATOR_STATE, IS_EMULATOR, get_machine_module


machine = get_machine_module()

try:
    import framebuf
except ImportError:
    framebuf = None


class EmulatedDisplay:
    def __init__(self):
        self.white = 1
        self.black = 0
        self._lines = {}

    def fill(self, color):
        if color == self.black:
            self._lines = {}

    def text(self, text, x, y, color):
        self._lines[int(y)] = text

    def show(self):
        ordered = [self._lines[key] for key in sorted(self._lines)]
        EMULATOR_STATE.update_display(ordered)


if not IS_EMULATOR and framebuf is not None:
    from machine import Pin, SPI

    try:
        import lcd

        class ST7789:
            def __init__(self):
                self.i8080 = lcd.I8080(data=(Pin(39), Pin(40), Pin(41), Pin(42), Pin(45), Pin(46), Pin(47), Pin(48)),
                                       command=Pin(7),
                                       write=Pin(8),
                                       read=Pin(9),
                                       cs=Pin(6),
                                       pclk=2 * 1000 * 1000,
                                       width=320,
                                       height=170,
                                       swap_color_bytes=False,
                                       cmd_bits=8,
                                       param_bits=8)

                self.st = lcd.ST7789(self.i8080, reset=Pin(5), backlight=Pin(38))

                self.st.reset()
                self.st.init()
                self.st.invert_color(True)
                self.st.swap_xy(True)
                self.st.mirror(False, True)
                self.st.set_gap(0, 35)

                self.buf = bytearray(320 * 170 * 2)
                self.framebuf = framebuf.FrameBuffer(self.buf, 320, 170, framebuf.RGB565)
                self.st.bitmap(0, 0, 320, 170, self.buf)
                self.st.backlight_on()

                self.white = self.st.color565(255, 255, 255)
                self.black = self.st.color565(0, 0, 0)

            def show(self):
                self.st.bitmap(0, 0, 320, 170, self.buf)

            def text(self, text, x, y, color):
                self.framebuf.text(text, x, y, color)

            def fill(self, color):
                self.framebuf.fill(color)

    except ImportError:
        ST7789 = None

    class Oled29(framebuf.FrameBuffer):
        def __init__(self):
            DC = 8
            RST = 12
            MOSI = 11
            SCK = 10
            CS = 9

            self.width = 128
            self.height = 32

            self.cs = Pin(CS, Pin.OUT)
            self.rst = Pin(RST, Pin.OUT)

            self.cs(1)
            self.spi = SPI(1)
            self.spi = SPI(1, 1000_000)
            self.spi = SPI(1, 10000_000, polarity=0, phase=0, sck=Pin(SCK), mosi=Pin(MOSI), miso=None)
            self.dc = Pin(DC, Pin.OUT)
            self.dc(1)
            self.buffer = bytearray(self.height * self.width // 8)
            super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
            self.init_display()

            self.white = 0xffff
            self.black = 0x0000

        def write_cmd(self, cmd):
            self.cs(1)
            self.dc(0)
            self.cs(0)
            self.spi.write(bytearray([cmd]))
            self.cs(1)

        def write_data(self, buf):
            self.cs(1)
            self.dc(1)
            self.cs(0)
            self.spi.write(bytearray([buf]))
            self.cs(1)

        def init_display(self):
            self.rst(1)
            time.sleep(0.001)
            self.rst(0)
            time.sleep(0.01)
            self.rst(1)

            self.write_cmd(0xAE)
            self.write_cmd(0x04)
            self.write_cmd(0x10)
            self.write_cmd(0x40)
            self.write_cmd(0x81)
            self.write_cmd(0x80)
            self.write_cmd(0xA1)
            self.write_cmd(0xA6)
            self.write_cmd(0xA8)
            self.write_cmd(0x1F)
            self.write_cmd(0xC8)
            self.write_cmd(0xD3)
            self.write_cmd(0x00)
            self.write_cmd(0xD5)
            self.write_cmd(0xF0)
            self.write_cmd(0xD8)
            self.write_cmd(0x05)
            self.write_cmd(0xD9)
            self.write_cmd(0xC2)
            self.write_cmd(0xDA)
            self.write_cmd(0x12)
            self.write_cmd(0xDB)
            self.write_cmd(0x08)
            self.write_cmd(0xAF)

        def show(self):
            for page in range(0, 4):
                self.write_cmd(0xb0 + page)
                self.write_cmd(0x04)
                self.write_cmd(0x10)
                self.dc(1)
                for num in range(0, 128):
                    self.write_data(self.buffer[page * 128 + num])

        def text(self, txt, x, y, color):
            super().text(txt, x, y, color)

        def fill(self, color):
            super().fill(color)


def get_display():
    if IS_EMULATOR or framebuf is None:
        display = EmulatedDisplay()
        print(display)
        return display

    m = os.uname().machine
    print(m)
    if 'Raspberry Pi Pico' in m:
        display = Oled29()
    else:
        display = ST7789()
    print(display)
    return display


if __name__ == "__main__":
    display = get_display()
    display.fill(0)
    display.show()
    display.text("128 x 32 Pixels", 1, 2, display.white)
    display.text("Pico-OLED-2.23", 1, 12, display.white)
    display.text("SSD1503", 1, 22, display.white)
    display.show()
