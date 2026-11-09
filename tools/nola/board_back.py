"""The board's opaque backing, cut to the iron frame (frontend/assets/frame.webp) so it fits it exactly:
the frame's opening is flood-filled from its centre through every see-through pixel it can reach - the gaps between
the fence spikes, the curls of the lace - up to the solid iron, grown 4 px so it runs under the metal, and the velvet
(art/nola-src/4k/ui/board_bg.png) is painted into that shape with a soft dark shadow baked in where it meets the iron.
-> frontend/assets/board_back.webp, the same size as frame.webp; the page draws it in the frame's own box (#paintback).
usage: python tools/nola/board_back.py"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
A = os.path.join(ROOT, "frontend", "assets")
frame = Image.open(os.path.join(A, "frame.webp")).convert("RGBA")
W, H = frame.size
al = np.asarray(frame.getchannel("A"))
clear = al < 110
lab, _ = ndimage.label(clear)
hole = lab == lab[H // 2, W // 2]                       # the opening and everything open to it
if hole[0].any() or hole[-1].any() or hole[:, 0].any() or hole[:, -1].any():
    raise SystemExit("the opening leaks to the frame's edge: the iron is not closed")
hole = ndimage.binary_fill_holes(hole)
shape = ndimage.binary_dilation(hole, iterations=4)     # tucks under the iron all round
ys, xs = np.nonzero(shape)
x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
tex = Image.open(os.path.join(ROOT, "art", "nola-src", "4k", "ui", "board_bg.png")).convert("RGB")
tex = np.asarray(tex.resize((x1 - x0, y1 - y0), Image.LANCZOS)).astype(np.float32)
# the shadow: how far each pixel is from the iron, darkening the last ~30 px into it
d = ndimage.distance_transform_edt(hole)[y0:y1, x0:x1]
shade = .32 + .68 * np.clip(d / 34.0, 0, 1) ** .8
rgb = np.zeros((H, W, 3), np.float32)
rgb[y0:y1, x0:x1] = tex * shade[..., None]
alpha = np.zeros((H, W), np.uint8)
alpha[shape] = 255
soft = ndimage.gaussian_filter(alpha.astype(np.float32), 1.0)   # an antialiased edge (it is under the iron anyway)
out = Image.fromarray(np.dstack([rgb.clip(0, 255).astype(np.uint8), soft.clip(0, 255).astype(np.uint8)]), "RGBA")
out.save(os.path.join(A, "board_back.webp"), "WEBP", quality=88, alpha_quality=90, method=6)
print("board_back.webp", (W, H), "opening box", (int(x0), int(y0), int(x1), int(y1)), "fill", round(shape.mean(), 3))
