"""Voodoo on Bourbon: the 4K pass. Every generated picture goes to a 4K master in art/nola-src/4k/:
  symbols   art/nola-src/<ID>_v1.png -> clean_alpha -> Real-ESRGAN x4 (anime) -> 4096 x 4096
  bg        art/nola-src/bg_v1.png   -> Real-ESRGAN x4 -> 3840 x 2160 (also frontend/assets/bonus_wall.webp)
  doc       the character and his faces -> clean_alpha -> x4 -> 4096 tall
  ui        art/nola-src/ui/<name>.png -> x4 (long edge 4096+)
The masters are what Blender textures from and what tools/nola/gen_ui.py fits the game's UI from.
usage: python tools/nola/upscale4k.py [sym|bg|doc|ui|all] [name,..]
Runs with the art venv (smukiez-slot/.venv); needs ../.tools/realesrgan (see tools/hires/README.md)."""
import os, sys
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools", "hires"))
sys.path.insert(0, HERE)
import upscale as H          # bleed, esrgan, resize_premul, tidy_alpha
import clean_alpha

SRC = os.path.join(ROOT, "art", "nola-src")
OUT = os.path.join(SRC, "4k")
IDS = "H1 H2 H3 H4 H5 H6 H7 L1 L2 L3 L4 L5 L6 L7 L8 L9 L10 M BS ES".split()


def up4(im, size=None, long_edge=None, model=H.A):
    """x4: colour through Real-ESRGAN on the bled RGB (opaque), alpha through the same model as its own grey
    picture (the model's alpha path leaves stair-stepped, grey-fringed edges; as a grey image it keeps the
    silhouette smooth), then a gentle contrast on the alpha's ramp so the edge stays a 1-2 px antialias."""
    im = im.convert("RGBA")
    a = im.getchannel("A")
    rgb = H.bleed(im).convert("RGB").convert("RGBA")
    up = H.esrgan(rgb, model).convert("RGB")
    if a.getextrema() != (255, 255):
        ua = H.esrgan(Image.merge("RGBA", (a, a, a, Image.new("L", a.size, 255))), model).getchannel("R")
        ua = ua.point(lambda v: 0 if v < 10 else 255 if v > 245 else round((v - 10) * 255 / 235))
        up = up.convert("RGBA")
        up.putalpha(ua)
    else:
        up = up.convert("RGBA")
    if long_edge:
        k = long_edge / max(up.size)
        size = (round(up.width * k), round(up.height * k))
    if size and size != up.size:
        up = H.resize_premul(up, size)
    return H.tidy_alpha(up)


def sym(sid):
    os.makedirs(os.path.join(SRC, "clean"), exist_ok=True)
    clean = os.path.join(SRC, "clean", sid + ".png")
    clean_alpha.clean(os.path.join(SRC, sid + "_v1.png"), clean)
    up4(Image.open(clean).convert("RGBA"), (4096, 4096)).save(os.path.join(OUT, sid + ".png"))
    return sid


def bg(_=None):
    im = Image.open(os.path.join(SRC, "bg_v1.png")).convert("RGBA")
    out = up4(im, (3840, 2160), model="realesrgan-x4plus-anime").convert("RGB")
    out.save(os.path.join(OUT, "bg.png"))
    out.save(os.path.join(ROOT, "frontend", "assets", "bonus_wall.webp"), "WEBP", quality=90, method=6)
    return "bg"


def doc(name="doc_v1"):
    """The character (doc_v1) or a face plate (faces/<name>)."""
    src = os.path.join(SRC, name + ".png")
    clean = os.path.join(SRC, "clean", os.path.basename(name) + ".png")
    os.makedirs(os.path.dirname(clean), exist_ok=True)
    clean_alpha.clean(src, clean)
    dst = os.path.join(OUT, name.replace("_v1", "") + ".png")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    up4(Image.open(clean).convert("RGBA"), long_edge=4096).save(dst)
    return name


def ui(name):
    im = Image.open(os.path.join(SRC, "ui", name + ".png")).convert("RGBA")
    os.makedirs(os.path.join(OUT, "ui"), exist_ok=True)
    up4(im, long_edge=max(4096, 4 * max(im.size))).save(os.path.join(OUT, "ui", name + ".png"))
    return name


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    only = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    os.makedirs(OUT, exist_ok=True)
    jobs = []
    if what in ("sym", "all"):
        jobs += [(sym, s) for s in (only or IDS)]
    if what in ("bg", "all"):
        jobs.append((bg, None))
    if what in ("doc", "all"):
        jobs += [(doc, n) for n in (only or ["doc_v1"])]
    if what in ("ui", "all"):
        names = only or sorted(os.path.splitext(f)[0] for f in os.listdir(os.path.join(SRC, "ui")) if f.endswith(".png"))
        jobs += [(ui, n) for n in names]
    # the GPU does one Real-ESRGAN at a time well; two threads keep it fed while the CPU cleans the next
    with ThreadPoolExecutor(2) as ex:
        for r in ex.map(lambda j: j[0](j[1]), jobs):
            print("4k", r, flush=True)
