"""The potion (M) in a colour per Multi value tier: hue-shifted copies of its packed Blender frames and its flat icon,
only the green liquid, smoke and bubbles recoloured (hue 65-165 deg, saturated) - its glass, cork, label, beads and
outline stay as drawn. Writes frontend/assets/sym/<density>/M<n>_<clip>.webp, flat/M<n>.webp and adds M2..M5 to
sym/manifest.json (same boxes and frame counts as M). The game picks the tier from the value (potionId in index.html):
  M  x1.25-2 green   M2 up to x5 sapphire   M3 up to x20 violet   M4 up to x100 gold   M5 above x100 blood red
usage: python tools/nola/potion_tiers.py   (after tools/blender/pack_frames.py)"""
import copy, glob, json, os
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYM = os.path.join(ROOT, "frontend", "assets", "sym")
FLAT = os.path.join(ROOT, "frontend", "assets", "flat")
TIERS = {"M2": 212, "M3": 278, "M4": 42, "M5": 356}      # target hue (deg) for the liquid's middle green (~115)
GAIN = {"M2": 1.0, "M3": 1.0, "M4": 1.04, "M5": .9}        # a touch brighter for gold, a touch deeper for blood
SAT = {"M2": 1.05, "M3": 1.05, "M4": 1.35, "M5": 1.55}      # the pale greens would come out pastel in gold and red


def shift(im, hue, gain, sat=1.0):
    a = np.asarray(im.convert("RGBA")).astype(np.float32) / 255
    rgb, al = a[..., :3], a[..., 3:]
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn + 1e-6
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.where(mx == r, (g - b) / d % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    s = np.where(mx > 0, d / (mx + 1e-6), 0)
    v = mx
    m = (h > 65) & (h < 165) & (s > .28) & (v > .12)
    nh = (hue + (h - 115)) % 360
    nv = np.clip(v * gain, 0, 1)
    s = np.where(m, np.clip(s * sat, 0, 1), s)
    c = nv * s
    x = c * (1 - np.abs((nh / 60) % 2 - 1))
    z = np.zeros_like(c)
    sec = (nh // 60).astype(int)
    tab = [(c, x, z), (x, c, z), (z, c, x), (z, x, c), (x, z, c), (c, z, x)]
    out = np.zeros_like(rgb)
    for i, (R, G, B) in enumerate(tab):
        k = sec == i
        out[k] = np.stack([R[k], G[k], B[k]], -1)
    out += (nv - c)[..., None]
    rgb2 = np.where(m[..., None], out, rgb)
    return Image.fromarray((np.dstack([rgb2, al]) * 255).clip(0, 255).astype(np.uint8), "RGBA")


man = json.load(open(os.path.join(SYM, "manifest.json")))
n = 0
for d in ["d%d" % round(x * 10) for x in man["densities"]]:
    for f in glob.glob(os.path.join(SYM, d, "M_*.webp")):
        clip = os.path.basename(f)[2:-5]
        im = Image.open(f)
        for t, hue in TIERS.items():
            shift(im, hue, GAIN[t], SAT[t]).save(os.path.join(SYM, d, f"{t}_{clip}.webp"), "WEBP", quality=90, alpha_quality=95, method=4)
            n += 1
flat = Image.open(os.path.join(FLAT, "M.webp"))
for t, hue in TIERS.items():
    shift(flat, hue, GAIN[t], SAT[t]).save(os.path.join(FLAT, t + ".webp"), "WEBP", quality=92, alpha_quality=100, method=6)
    man["symbols"][t] = copy.deepcopy(man["symbols"]["M"])
json.dump(man, open(os.path.join(SYM, "manifest.json"), "w"), separators=(",", ":"))
print("sheets", n, "flat", len(TIERS), "densities", man["densities"])
