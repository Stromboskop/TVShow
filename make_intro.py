# A lancer sur le PC (pas sur le Pico) : python make_intro.py
# Convertit IMG_7433.gif en intro.bin (images 8 bits a palette globale, affichees x2 par intro.py).
# Format : <HHHH largeur, hauteur, nb images, delai ms> + palette RGB565 (256 x 2 octets) + images.
import os
import struct

from PIL import Image

SRC = "IMG_7433.gif"
DST = "intro.bin"
W, H = 160, 120   # affiche x2 = 320 x 240
STEP = 2          # garde 1 image sur STEP (taille du fichier)

here = os.path.dirname(os.path.abspath(__file__))
gif = Image.open(os.path.join(here, SRC))
delay = gif.info.get("duration", 100) * STEP

frames = []
for i in range(gif.n_frames):
    if i % STEP:
        continue
    gif.seek(i)
    rgba = gif.convert("RGBA")
    bg = Image.new("RGB", rgba.size, (0, 0, 0))
    bg.paste(rgba, mask=rgba.split()[3])
    frames.append(bg.resize((W, H), Image.LANCZOS))

# Palette commune a toutes les images (evite le scintillement des couleurs)
mosaic = Image.new("RGB", (W, H * len(frames)))
for i, f in enumerate(frames):
    mosaic.paste(f, (0, i * H))
pal_img = mosaic.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
flat = pal_img.getpalette()[:768]
flat += [0] * (768 - len(flat))

with open(os.path.join(here, DST), "wb") as out:
    out.write(struct.pack("<HHHH", W, H, len(frames), delay))
    for k in range(256):
        r, g, b = flat[3 * k:3 * k + 3]
        out.write(struct.pack(">H", ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)))
    for f in frames:
        q = f.quantize(palette=pal_img, dither=Image.Dither.NONE)
        out.write(q.tobytes())

print(DST, len(frames), "images", W, "x", H, os.path.getsize(os.path.join(here, DST)), "octets")
