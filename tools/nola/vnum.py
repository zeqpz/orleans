"""The voodoo multiplier glyphs and border (Multi values on potions and cells): art/nola-src/ui/vnum.png (a 4x3 sheet:
x 0 1 2 / 3 4 5 6 / 7 8 9 .) and vborder.png -> Real-ESRGAN x2 -> frontend/assets/vnum/<g>.webp (256 px tall, each glyph
cropped to its ink, sitting on a shared baseline) and assets/vnum/border.webp, plus assets/vnum/glyphs.css (one class
per glyph with its aspect ratio). The page writes values through vNum() (index.html).
usage: python tools/nola/vnum.py"""
import os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import upscale4k

ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, "art", "nola-src", "ui")
OUT = os.path.join(ROOT, "frontend", "assets", "vnum")
os.makedirs(OUT, exist_ok=True)
NAMES = ["x", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "dot"]
sheet = upscale4k.up4(Image.open(os.path.join(SRC, "vnum.png")).convert("RGBA"), long_edge=2048)
W, H = sheet.size
cw, ch = W / 4, H / 3
TALL = 256
cells = []
for i, n in enumerate(NAMES):
    c = sheet.crop((round((i % 4) * cw), round((i // 4) * ch), round((i % 4 + 1) * cw), round((i // 4 + 1) * ch)))
    a = np.asarray(c.getchannel("A"))
    ys, xs = np.nonzero(a > 20)
    cells.append((n, c, xs.min(), xs.max() + 1, ys.min(), ys.max() + 1))
# one scale for all: the digits' tallest ink -> TALL px; the x and the dot keep their place on the baseline
dig = [e[5] - e[4] for e in cells if e[0].isdigit()]
k = TALL / max(dig)
base = int(np.median([e[5] for e in cells if e[0].isdigit()]))
top = min(e[4] for e in cells if e[0].isdigit())
css = []
for n, c, x0, x1, y0, y1 in cells:
    g = c.crop((x0, top, x1, max(base, y1)))
    g = g.resize((max(1, round(g.width * k)), max(1, round(g.height * k))), Image.LANCZOS)
    g.save(os.path.join(OUT, n + ".webp"), "WEBP", quality=92, alpha_quality=100, method=6)
    css.append(f'.vg.g-{n} {{ background-image: url("{n}.webp"); aspect-ratio: {g.width} / {g.height}; }}')
border = upscale4k.up4(Image.open(os.path.join(SRC, "vborder.png")).convert("RGBA"), long_edge=1024)
bb = border.getchannel("A").getbbox()
border.crop(bb).save(os.path.join(OUT, "border.webp"), "WEBP", quality=90, alpha_quality=100, method=6)
open(os.path.join(OUT, "glyphs.css"), "w").write("/* tools/nola/vnum.py */\n" + "\n".join(css) + "\n")
print("glyphs", len(NAMES), "k", round(k, 3), "border", border.crop(bb).size)
