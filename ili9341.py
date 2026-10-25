# Pilote ILI9341 minimal (320x240 paysage) pour MicroPython
import time
import framebuf

BLACK = 0x0000


def color565(r, g, b):
    c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return c


WHITE = color565(255, 255, 255)


class ILI9341:
    WIDTH = 320
    HEIGHT = 240

    def __init__(self, spi, dc, cs, rst, bl=None):
        self.spi, self.dc, self.cs, self.rst = spi, dc, cs, rst
        self.cs(1)
        if bl is not None:
            bl.value(1)
        self.rst(0)
        time.sleep_ms(50)
        self.rst(1)
        time.sleep_ms(120)
        for cmd, data in (
            (0x01, b""),
            (0xCF, b"\x00\xC1\x30"),
            (0xED, b"\x64\x03\x12\x81"),
            (0xE8, b"\x85\x00\x78"),
            (0xCB, b"\x39\x2C\x00\x34\x02"),
            (0xF7, b"\x20"),
            (0xEA, b"\x00\x00"),
            (0xC0, b"\x23"),
            (0xC1, b"\x10"),
            (0xC5, b"\x3E\x28"),
            (0xC7, b"\x86"),
            (0x36, b"\x28"),  # paysage, ordre BGR
            (0x3A, b"\x55"),
            (0xB1, b"\x00\x18"),
            (0xB6, b"\x08\x82\x27"),
            (0x26, b"\x01"),
        ):
            self._w(cmd, data)
            if cmd == 0x01:
                time.sleep_ms(150)
        self._w(0x11)
        time.sleep_ms(120)
        self._w(0x29)

    def _w(self, cmd, data=None):
        self.cs(0)
        self.dc(0)
        self.spi.write(bytes([cmd]))
        if data:
            self.dc(1)
            self.spi.write(data)
        self.cs(1)

    def _window(self, x0, y0, x1, y1):
        self._w(0x2A, bytes([x0 >> 8, x0 & 255, x1 >> 8, x1 & 255]))
        self._w(0x2B, bytes([y0 >> 8, y0 & 255, y1 >> 8, y1 & 255]))
        self.cs(0)
        self.dc(0)
        self.spi.write(b"\x2C")
        self.dc(1)

    def blit(self, buf, x, y, w, h):
        """Envoie un tampon RGB565 big-endian."""
        self._window(x, y, x + w - 1, y + h - 1)
        self.spi.write(buf)
        self.cs(1)

    def fill_rect(self, x, y, w, h, color):
        if w <= 0 or h <= 0:
            return
        line = bytes([color >> 8, color & 255]) * w
        self._window(x, y, x + w - 1, y + h - 1)
        for _ in range(h):
            self.spi.write(line)
        self.cs(1)

    def fill(self, color):
        self.fill_rect(0, 0, self.WIDTH, self.HEIGHT, color)

    def text(self, x, y, s, fg=WHITE, bg=BLACK, scale=2):
        """Texte ASCII (police 8x8 integree) agrandi par 'scale'."""
        s = s[: (self.WIDTH - x) // (8 * scale)]
        if not s:
            return
        w = 8 * len(s)
        mono = framebuf.FrameBuffer(bytearray(len(s) * 8), w, 8, framebuf.MONO_HLSB)
        mono.text(s, 0, 0, 1)
        fb = bytes([fg >> 8, fg & 255])
        bb = bytes([bg >> 8, bg & 255])
        pw = w * scale
        self._window(x, y, x + pw - 1, y + 8 * scale - 1)
        for row in range(8):
            line = bytearray()
            for col in range(w):
                line += (fb if mono.pixel(col, row) else bb) * scale
            for _ in range(scale):
                self.spi.write(line)
        self.cs(1)
