import os
# import logo
import time

import framebuf
from machine import Pin, SPI

# noinspection PyUnresolvedReferences
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
    print('ST7789 not available')


# noinspection PyPep8Naming
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
        """Initialize display"""
        self.rst(1)
        time.sleep(0.001)
        self.rst(0)
        time.sleep(0.01)
        self.rst(1)

        self.write_cmd(0xAE)  # turn off OLED display*/

        self.write_cmd(0x04)  # turn off OLED display*/

        self.write_cmd(0x10)  # turn off OLED display*/

        self.write_cmd(0x40)  # set lower column address*/
        self.write_cmd(0x81)  # set higher column address*/
        self.write_cmd(0x80)  # --set start line address  Set Mapping RAM Display Start Line (0x00~0x3F, SSD1305_CMD)
        self.write_cmd(0xA1)  # --set contrast control register
        self.write_cmd(0xA6)  # Set SEG Output Current Brightness
        self.write_cmd(0xA8)  # --Set SEG/Column Mapping
        self.write_cmd(0x1F)  # Set COM/Row Scan Direction
        self.write_cmd(0xC8)  # --set normal display
        self.write_cmd(0xD3)  # --set multiplex ratio(1 to 64)
        self.write_cmd(0x00)  # --1/64 duty
        self.write_cmd(0xD5)  # -set display offset	Shift Mapping RAM Counter (0x00~0x3F)
        self.write_cmd(0xF0)  # -not offset
        self.write_cmd(0xD8)  # --set display clock divide ratio/oscillator frequency
        self.write_cmd(0x05)  # --set divide ratio, Set Clock as 100 Frames/Sec
        self.write_cmd(0xD9)  # --set pre-charge period
        self.write_cmd(0xC2)  # Set Pre-Charge as 15 Clocks & Discharge as 1 Clock
        self.write_cmd(0xDA)  # --set com pins hardware configuration
        self.write_cmd(0x12)
        self.write_cmd(0xDB)  # set vcomh
        self.write_cmd(0x08)  # Set VCOM Deselect Level
        self.write_cmd(0xAF)  # -Set Page Addressing Mode (0x00/0x01/0x02)

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
    _display = None
    if os.uname().machine == 'Raspberry Pi Pico W with RP2040':
        _display = Oled29()
    else:
        _display = ST7789()
    print(_display)
    return _display


if __name__ == "__main__":

    # display = ST7789()
    display = Oled29()
    display.fill(0)
    display.show()
    display.text("128 x 32 Pixels", 1, 2, display.white)
    display.text("Pico-OLED-2.23", 1, 12, display.white)
    display.text("SSD1503", 1, 22, display.white)
    display.show()
