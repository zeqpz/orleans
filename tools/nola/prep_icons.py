"""Lay the 4K symbol masters (art/nola-src/4k/<ID>.png) out for Blender and the game:
  art/nola-src/icons/<ID>.png        1000x1000, the art's longer side 940 px, centred (what Blender maps to 10 units)
  art/nola-src/icons/<ID>_glow.png   a soft halo of the silhouette (white, alpha = blurred grown silhouette)
  art/blender/parts/<ID>/parts.json  {"size": [1000, 1000]} - the icon size pack_frames.py reads
  frontend/assets/flat/<ID>.webp     the still icon (400 px; BS / ES 800 px)
usage: python tools/fall/prep_icons.py [ID,ID..]"""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IDS = "H1 H2 H3 H4 H5 H6 H7 L1 L2 L3 L4 L5 L6 L7 L8 L9 L10 M BS ES".split()
SIDE, ART = 1000, 940


def layout(sid):
    im = Image.open(os.path.join(ROOT, "art", "nola-src", "4k", sid + ".png")).convert("RGBA")
    x0, y0, x1, y1 = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    im = im.crop((x0, y0, x1, y1))
    k = ART / max(im.size)
    im = im.convert("RGBa").resize((round(im.size[0] * k), round(im.size[1] * k)), Image.LANCZOS).convert("RGBA")
    out = Image.new("RGBA", (SIDE, SIDE), (0, 0, 0, 0))
    out.alpha_composite(im, ((SIDE - im.size[0]) // 2, (SIDE - im.size[1]) // 2))
    d = os.path.join(ROOT, "art", "nola-src", "icons")
    os.makedirs(d, exist_ok=True)
    out.save(os.path.join(d, sid + ".png"))
    # the halo canvas is 1200 px (12 units) so its soft edge never meets the square's border on a wide icon
    a = Image.new("L", (1200, 1200), 0)
    a.paste(out.getchannel("A").point(lambda v: 255 if v > 100 else 0), (100, 100))
    a = a.resize((300, 300), Image.BILINEAR).filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(7))
    a = a.resize((1200, 1200), Image.BICUBIC)
    glow = Image.merge("RGBA", (Image.new("L", a.size, 255),) * 3 + (a,))
    glow.save(os.path.join(d, sid + "_glow.png"))
    pd = os.path.join(ROOT, "art", "blender", "parts", sid)
    os.makedirs(pd, exist_ok=True)
    json.dump({"size": [SIDE, SIDE]}, open(os.path.join(pd, "parts.json"), "w"))
    flat = 800 if sid in ("BS", "ES") else 400
    f = out.convert("RGBa").resize((flat, flat), Image.LANCZOS).convert("RGBA")
    f.save(os.path.join(ROOT, "frontend", "assets", "flat", sid + ".webp"), "WEBP", quality=92, alpha_quality=100,
           method=6)
    return sid


if __name__ == "__main__":
    ids = sys.argv[1].split(",") if len(sys.argv) > 1 else IDS
    for s in ids:
        print(layout(s), end=" ", flush=True)
    print()
