# pyright: reportMissingImports=false
# Animation de demarrage (intro.bin genere par make_intro.py) ; lance par main.py (run(display, stop))
import struct
import time

import micropython


@micropython.viper
def _expand(src, pal, dst, n: int):
    """Palette 8 bits -> RGB565 big-endian, chaque pixel double horizontalement."""
    s = ptr8(src)
    p = ptr8(pal)
    d = ptr8(dst)
    o = 0
    for i in range(n):
        k = int(s[i]) * 2
        hi = int(p[k])
        lo = int(p[k + 1])
        d[o] = hi
        d[o + 1] = lo
        d[o + 2] = hi
        d[o + 3] = lo
        o += 4


def run(display, stop=None, path="intro.bin", loops=1):
    with open(path, "rb") as f:
        w, h, count, delay = struct.unpack("<HHHH", f.read(8))
        pal = f.read(512)
        base = f.tell()
        x0 = (display.WIDTH - 2 * w) // 2
        y0 = (display.HEIGHT - 2 * h) // 2
        row = bytearray(w)
        out = bytearray(4 * w)
        display.fill(0)
        for _ in range(loops):
            f.seek(base)
            for _ in range(count):
                started = time.ticks_ms()
                display._window(x0, y0, x0 + 2 * w - 1, y0 + 2 * h - 1)
                for _ in range(h):
                    f.readinto(row)
                    _expand(row, pal, out, w)
                    display.spi.write(out)
                    display.spi.write(out)
                display.cs(1)
                if stop is not None and stop():
                    return
                wait = delay - time.ticks_diff(time.ticks_ms(), started)
                if wait > 0:
                    time.sleep_ms(wait)
