from emulator import runtime_state

MONO_VLSB = 0
RGB565 = 1


class FrameBuffer:
    def __init__(self, buffer, width, height, format):
        self.buffer = buffer
        self.width = int(width)
        self.height = int(height)
        self.format = format
        runtime_state.init_display(self.width, self.height)

    def fill(self, color):
        runtime_state.display_fill(color)

    def text(self, text, x, y, color):
        runtime_state.display_text(text, x, y, color)
