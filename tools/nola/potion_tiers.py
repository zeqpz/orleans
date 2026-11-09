"""The potion (M) in a colour per Multi value tier: hue-shifted copies of its Blender renders and its flat icon, only the
green liquid, smoke, bubbles and their bloom recoloured - its glass, cork, label, beads and outline stay as drawn.
  M  x1.25-2 green   M2 up to x5 sapphire   M3 up to x20 violet   M4 up to x100 gold   M5 above x100 blood red
The game picks the tier from the value (potionId in index.html).

2026-11-09 (render QA): the tiers were recoloured from M's packed (lossy) sheets with a hard on/off hue mask, which
left 175-268 stray specks a frame, a half-recoloured teal neck and a blotchy cork where the steam crossed it. Now:
  - the source is M's lossless PNG renders (art/blender/renders/M/<clip>/), written as renders of their own
    (art/blender/renders/M2..M5/) and packed by tools/blender/pack_frames.py like every other symbol (one encode);
  - the mask is soft: hue feathered in over 62-80 deg and out over 140-158 (the teal glass, ~165+, is left alone),
    saturation and value feathered too, and the whole mask smoothed a touch so no lone pixel flips colour.
usage: python tools/nola/potion_tiers.py   (after tools/nola/blender/symanim.py has rendered M)"""
import copy, glob, json, os, shutil, subprocess, sys
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REN = os.path.join(ROOT, "art", "blender", "renders")
PARTS = os.path.join(ROOT, "art", "blender", "parts")
SYM = os.path.join(ROOT, "frontend", "assets", "sym")
FLAT = os.path.join(ROOT, "frontend", "assets", "flat")
TIERS = {"M2": 212, "M3": 278, "M4": 42, "M5": 356}      # target hue (deg) for the liquid's middle green (~115)
GAIN = {"M2": 1.0, "M3": 1.0, "M4": 1.04, "M5": .9}        # a touch brighter for gold, a touch deeper for blood
SAT = {"M2": 1.05, "M3": 1.05, "M4": 1.35, "M5": 1.55}      # the pale greens would come out pastel in gold and red


def ramp(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def shift(im, hue, gain, sat=1.0):
    a = np.asarray(im.convert("RGBA")).astype(np.float32) / 255
    rgb, al = a[..., :3], a[..., 3:]
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn + 1e-6
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.where(mx == r, (g - b) / d % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    s = np.where(mx > 0, d / (mx + 1e-6), 0)
    v = mx
    w = ramp(h, 62, 80) * (1 - ramp(h, 140, 158)) * ramp(s, .2, .36) * ramp(v, .08, .16)
    w = ndimage.gaussian_filter(w, .8)                     # no lone pixel flips colour
    nh = (hue + (h - 115)) % 360
    nv = np.clip(v * gain, 0, 1)
    s2 = np.clip(s * sat, 0, 1)
    c = nv * s2
    x = c * (1 - np.abs((nh / 60) % 2 - 1))
    z = np.zeros_like(c)
    sec = (nh // 60).astype(int) % 6
    tab = [(c, x, z), (x, c, z), (z, c, x), (z, x, c), (x, z, c), (c, z, x)]
    out = np.zeros_like(rgb)
    for i, (R, G, B) in enumerate(tab):
        k = sec == i
        out[k] = np.stack([R[k], G[k], B[k]], -1)
    out += (nv - c)[..., None]
    rgb2 = rgb * (1 - w[..., None]) + out * w[..., None]
    return Image.fromarray((np.dstack([rgb2, al]) * 255).round().clip(0, 255).astype(np.uint8), "RGBA")


def main():
    src = os.path.join(REN, "M")
    clips = sorted(c for c in os.listdir(src) if os.path.isdir(os.path.join(src, c)))
    for t, hue in TIERS.items():
        dst = os.path.join(REN, t)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        for c in clips:
            os.makedirs(os.path.join(dst, c))
            for f in sorted(glob.glob(os.path.join(src, c, "*.png"))):
                shift(Image.open(f), hue, GAIN[t], SAT[t]).save(os.path.join(dst, c, os.path.basename(f)))
        os.makedirs(os.path.join(PARTS, t), exist_ok=True)   # pack_frames reads the icon's size from here
        shutil.copyfile(os.path.join(PARTS, "M", "parts.json"), os.path.join(PARTS, t, "parts.json"))
        print("rendered", t, flush=True)
    # pack them like any symbol (same densities as the rest)
    man = json.load(open(os.path.join(SYM, "manifest.json")))
    dens = ",".join(str(x) for x in man["densities"])
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "blender", "pack_frames.py"), ",".join(TIERS), dens], check=True)
    flat = Image.open(os.path.join(FLAT, "M.webp"))
    for t, hue in TIERS.items():
        shift(flat, hue, GAIN[t], SAT[t]).save(os.path.join(FLAT, t + ".webp"), "WEBP", quality=92, alpha_quality=100, method=6)
    print("flat", len(TIERS))


if __name__ == "__main__":
    main()
