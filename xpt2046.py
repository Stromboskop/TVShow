# Lecture tactile XPT2046 minimale
class XPT2046:
    def __init__(self, spi, cs, irq, width=320, height=240,
                 xmin=200, xmax=3900, ymin=200, ymax=3900, swap=True,
                 touch_baud=1_000_000, lcd_baud=40_000_000):
        self.spi, self.cs, self.irq = spi, cs, irq
        self.w, self.h = width, height
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax
        self.swap = swap
        self.touch_baud, self.lcd_baud = touch_baud, lcd_baud
        self.cs(1)

    def _read(self, cmd):
        buf = bytearray(3)
        self.cs(0)
        self.spi.write_readinto(bytes([cmd, 0, 0]), buf)
        self.cs(1)
        return ((buf[1] << 8) | buf[2]) >> 3

    def touched(self):
        return self.irq.value() == 0

    def get_xy(self):
        """Retourne (x, y) en pixels, ou None s'il n'y a pas d'appui."""
        if not self.touched():
            return None
        # Bus partage avec l'ecran : vitesse reduite pendant la lecture tactile
        self.spi.init(baudrate=self.touch_baud)
        try:
            xs = sorted(self._read(0xD0) for _ in range(5))[2]
            ys = sorted(self._read(0x90) for _ in range(5))[2]
        finally:
            self.spi.init(baudrate=self.lcd_baud)
        if self.swap:
            xs, ys = ys, xs
        x = (xs - self.xmin) * self.w // (self.xmax - self.xmin)
        y = (ys - self.ymin) * self.h // (self.ymax - self.ymin)
        return max(0, min(self.w - 1, x)), max(0, min(self.h - 1, y))
