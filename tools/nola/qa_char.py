"""QA Doc's Blender renders (art/blender/chars/scarecrow/renders/<clip>/####.png):
art/blender/chars/scarecrow/qa/<clip>_sheet.jpg (every 4th frame on the farm-sky colour) and a report: the idle's
loop seam, each one-shot's first/last frame vs the idle's first, alpha on the frame edge.
usage: python tools/fall/qa_char.py [clip,..]"""
import glob, json, os, sys
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
C = os.path.join(ROOT, "art", "blender", "chars", "doc")
BG = (34, 22, 56)


def load(f):
    return np.asarray(Image.open(f).convert("RGBA").resize((180, 270))).astype(np.float32)


meta = json.load(open(os.path.join(C, "renders", "meta.json")))
clips = sys.argv[1].split(",") if len(sys.argv) > 1 else list(meta["clips"])
os.makedirs(os.path.join(C, "qa"), exist_ok=True)
rest = load(sorted(glob.glob(os.path.join(C, "renders", "idle", "*.png")))[0])
for c in clips:
    fs = sorted(glob.glob(os.path.join(C, "renders", c, "*.png")))
    first, last = load(fs[0]), load(fs[-1])
    edge = 0
    for f in fs[::3]:
        a = np.asarray(Image.open(f))[..., 3]
        edge = max(edge, int(a[0].max()), int(a[-1].max()), int(a[:, 0].max()), int(a[:, -1].max()))
    if meta["clips"][c]["loop"]:
        print(f"{c}: {len(fs)} f, seam {np.abs(last - first).mean():.2f} vs step {np.abs(load(fs[1]) - first).mean():.2f}, edge {edge}")
    else:
        print(f"{c}: {len(fs)} f, first vs rest {np.abs(first - rest).mean():.2f}, last vs rest {np.abs(last - rest).mean():.2f}, edge {edge}")
    pick = fs[::4]
    S = (160, 240)
    cols = 10
    sheet = Image.new("RGB", (S[0] * cols, S[1] * ((len(pick) + cols - 1) // cols)), BG)
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(pick):
        im = Image.open(f).convert("RGBA").resize(S, Image.LANCZOS)
        bg = Image.new("RGBA", S, BG + (255,))
        bg.alpha_composite(im)
        sheet.paste(bg.convert("RGB"), ((i % cols) * S[0], (i // cols) * S[1]))
        d.text(((i % cols) * S[0] + 3, (i // cols) * S[1] + 2), str(fs.index(f)), fill=(255, 255, 255))
    sheet.save(os.path.join(C, "qa", f"{c}_sheet.jpg"), quality=85)
