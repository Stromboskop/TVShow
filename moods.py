# Carrousel des humeurs ; lance par main.py (run(display, stop))
from array import array
import framebuf
import math
import time


W, H = 320, 240
FRAME_MS = 50
MOOD_MS = 1900
THICK = 3

# Coordinates below come from the original 144x79 robot screen and are scaled to full screen.
S = 2.5
CX, CY = 160, 120


def rgb(r, g, b):
    color = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return ((color & 0xFF) << 8) | (color >> 8)


NAVY = rgb(28, 20, 55)
CYAN = rgb(61, 232, 239)
WHITE = rgb(255, 255, 255)
fb = framebuf.FrameBuffer(bytearray(W * H * 2), W, H, framebuf.RGB565)


def tx(x):
    return int(CX + (x - 160) * S)


def ty(y):
    return int(CY + (y - 155) * S)


def thick_line(x0, y0, x1, y1, color):
    half = THICK // 2
    for d in range(-half, half + 1):
        fb.line(x0 + d, y0, x1 + d, y1, color)
        fb.line(x0, y0 + d, x1, y1 + d, color)


def line(points, color):
    pts = [(tx(x), ty(y)) for x, y in points]
    for i in range(len(pts) - 1):
        thick_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], color)


def ellipse(x, y, rx, ry, color):
    fb.ellipse(tx(x), ty(y), int(rx * S), int(ry * S), color, True)


def filled_poly(points, color):
    coords = array("h")
    for x, y in points:
        coords.append(tx(x))
        coords.append(ty(y))
    fb.poly(0, 0, coords, color, True)


def rect(x, y, w, h, color):
    fb.fill_rect(tx(x), ty(y), int(w * S), int(h * S), color)


def draw_smile(cx=160, cy=172, width=22):
    line(((cx - width // 2, cy), (cx - width // 4, cy + 4),
          (cx, cy + 5), (cx + width // 4, cy + 4),
          (cx + width // 2, cy)), WHITE)


def draw_frown(cx=160, cy=174, width=23):
    line(((cx - width // 2, cy + 4), (cx - width // 4, cy),
          (cx, cy - 2), (cx + width // 4, cy),
          (cx + width // 2, cy + 4)), WHITE)


def draw_heart(cx, cy, size):
    ellipse(cx - size // 2, cy - size // 4, size // 2, size // 2, CYAN)
    ellipse(cx + size // 2, cy - size // 4, size // 2, size // 2, CYAN)
    filled_poly(((cx - size, cy - size // 6),
                 (cx + size, cy - size // 6),
                 (cx, cy + size)), CYAN)


def draw_mood(mood, phase):
    fb.fill(NAVY)
    pulse = int(2 * math.sin(phase * 5))

    if mood == 0:  # Happy
        ellipse(132, 146 + pulse, 9, 10, CYAN)
        ellipse(188, 146 + pulse, 9, 10, CYAN)
        draw_smile()
    elif mood == 1:  # Sad
        ellipse(132, 147, 9, 10, CYAN)
        ellipse(188, 147, 9, 10, CYAN)
        draw_frown(cy=175 + int(2 * math.sin(phase * 4)))
    elif mood == 2:  # Delighted / surprised
        ellipse(132, 147, 9, 10, CYAN)
        ellipse(188, 147, 9, 10, CYAN)
        ellipse(160, 174, 12, 9 + int(2 * (1 + math.sin(phase * 6))), WHITE)
    elif mood == 3:  # Thinking
        for i in range(4):
            radius = 4 + (1 if int(phase * 5) % 4 == i else 0)
            ellipse(132 + i * 19, 155, radius, radius, CYAN)
    elif mood == 4:  # Wink
        ellipse(132, 146, 9, 10, CYAN)
        line(((181, 149), (188, 143), (195, 149)), CYAN)
        draw_smile(cy=174)
    elif mood == 5:  # In love
        draw_heart(132, 147, 11)
        draw_heart(188, 147, 11)
        draw_smile(cy=174)
    elif mood == 6:  # Angry
        ellipse(132, 151, 10, 7, CYAN)
        ellipse(188, 151, 10, 7, CYAN)
        line(((121, 137), (133, 141), (143, 145)), CYAN)
        line(((177, 145), (187, 141), (199, 137)), CYAN)
        rect(149, 174, 22, 3, WHITE)
    elif mood == 7:  # Kiss
        line(((122, 147), (128, 151), (136, 151), (142, 147)), CYAN)
        line(((178, 147), (184, 151), (192, 151), (198, 147)), CYAN)
        ellipse(160, 174, 7, 8, CYAN)
    else:  # Dizzy
        for cx in (132, 188):
            line(((cx - 8, 139), (cx + 8, 155)), CYAN)
            line(((cx + 8, 139), (cx - 8, 155)), CYAN)
        ellipse(160, 174, 8, 10, WHITE)


def run(display, stop):
    start = time.ticks_ms()
    while not stop():
        now = time.ticks_ms()
        elapsed = time.ticks_diff(now, start)
        mood = (elapsed // MOOD_MS) % 9
        phase = (elapsed % MOOD_MS) / 1000
        draw_mood(mood, phase)
        display.blit(fb, 0, 0, W, H)
        time.sleep_ms(FRAME_MS)
