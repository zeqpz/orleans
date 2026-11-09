"""QA a fall symbol's Blender renders (art/blender/renders/<ID>/<clip>/####.png):
  art/blender/qa/<ID>/<clip>_sheet.jpg   every 2nd frame on the board's dark colour
  art/blender/qa/<ID>/zoom.jpg           2x crops of the icon's centre on the frames that move most
  report.txt                             idle loop seam (last frame -> first), each one-shot's first and last
                                         frame vs the idle's first (they must hand over on the rest pose), and
                                         alpha touching the frame edge (an effect cut off by the sprite box)
usage: python tools/fall/qa_sym.py <ID,ID..|all>"""
import glob, os, sys
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REN = os.path.join(ROOT, "art", "blender", "renders")
QA = os.path.join(ROOT, "art", "blender", "qa")
BG = (46, 34, 40)
ALL = "H1 H2 H3 H4 H5 H6 H7 L1 L2 L3 L4 L5 L6 L7 L8 L9 L10 M BS ES".split()


def load(f):
    return np.asarray(Image.open(f).convert("RGBA")).astype(np.float32)


def diff(a, b):
    return float(np.abs(a - b).mean())


def on_bg(im):
    bg = Image.new("RGBA", im.size, BG + (255,))
    bg.alpha_composite(im)
    return bg.convert("RGB")


def qa(sid):
    out = os.path.join(QA, sid)
    os.makedirs(out, exist_ok=True)
    rep = []
    clips = {c: sorted(glob.glob(os.path.join(REN, sid, c, "*.png"))) for c in ("idle", "land", "hit", "multi")}
    rest = load(clips["idle"][0])
    rep.append(f"idle seam (last->first) {diff(load(clips['idle'][-1]), rest):.2f}   "
               f"(neighbouring frames ~ {diff(load(clips['idle'][1]), rest):.2f})")
    for c in ("land", "hit", "multi"):
        rep.append(f"{c}: first vs rest {diff(load(clips[c][0]), rest):.2f}  last vs rest "
                   f"{diff(load(clips[c][-1]), rest):.2f}")
    for c, fs in clips.items():
        edge = 0
        for f in fs:
            a = load(f)[..., 3]
            edge = max(edge, a[0].max(), a[-1].max(), a[:, 0].max(), a[:, -1].max())
        rep.append(f"{c}: {len(fs)} frames, max alpha on the frame edge {edge:.0f}")
        pick = fs[::2]
        S = 192
        cols = 8
        rows = (len(pick) + cols - 1) // cols
        sheet = Image.new("RGB", (S * cols, S * rows), BG)
        d = ImageDraw.Draw(sheet)
        for i, f in enumerate(pick):
            im = on_bg(Image.open(f).convert("RGBA")).resize((S, S), Image.LANCZOS)
            sheet.paste(im, ((i % cols) * S, (i // cols) * S))
            d.text(((i % cols) * S + 3, (i // cols) * S + 2), str(fs.index(f)), fill=(255, 255, 255))
        sheet.save(os.path.join(out, f"{c}_sheet.jpg"), quality=86)
    # zoom: the two frames of hit and multi that differ most from rest, centre crop at 2x
    tiles = []
    for c in ("hit", "multi", "land"):
        ds = [(diff(load(f), rest), f) for f in clips[c]]
        for _, f in sorted(ds, reverse=True)[:2]:
            im = on_bg(Image.open(f).convert("RGBA")).crop((96, 96, 416, 416)).resize((480, 480), Image.LANCZOS)
            tiles.append(im)
    z = Image.new("RGB", (480 * 3, 480 * 2), BG)
    for i, t in enumerate(tiles):
        z.paste(t, ((i // 2) * 480, (i % 2) * 480))
    z.save(os.path.join(out, "zoom.jpg"), quality=88)
    open(os.path.join(out, "report.txt"), "w").write("\n".join(rep) + "\n")
    return sid + "\n  " + "\n  ".join(rep)


if __name__ == "__main__":
    ids = ALL if sys.argv[1] == "all" else sys.argv[1].split(",")
    for s in ids:
        print(qa(s))
