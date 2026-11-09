"""Export the animated background for the game (frontend/assets/bg/ + frontend/assets/bonus_wall.webp):
  bonus_wall.webp         the static plate (lights off, no moon, stars or smoke), Real-ESRGAN x4 -> 3840 x 2160
  bg/<layer>.webp         each light layer (art/nola-src/bglayers, additive, on black) at 4K scale
  bg/mist_a|b|c.webp      tileable green fog bands (fractal noise, made here; the game scrolls them)
  bg/scene.json           layer boxes (0..1 of the painting), kinds, colours, and 170 star positions sampled
                          from the sky (size, brightness, twinkle speed, colour) - the game draws the stars live
usage: python tools/nola/bg_export.py [plate,layers,mist,stars]"""
import json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import upscale4k

SRC = os.path.join(ROOT, "art", "nola-src", "bglayers")
ASSETS = os.path.join(ROOT, "frontend", "assets")
OUT = os.path.join(ASSETS, "bg")
FULL = (3840, 2160)


def plate():
    im = Image.open(os.path.join(SRC, "plate_aligned.png")).convert("RGBA")
    out = upscale4k.up4(im, FULL).convert("RGB")
    out.save(os.path.join(ROOT, "art", "nola-src", "4k", "bg_plate.png"))
    out.save(os.path.join(ASSETS, "bonus_wall.webp"), "WEBP", quality=90, method=6)
    print("plate -> bonus_wall.webp", out.size)


def layers(meta):
    k = FULL[0] / meta["size"][0]
    for l in meta["layers"]:
        im = Image.open(os.path.join(SRC, l["name"] + ".png")).convert("RGBA")
        x, y, w, h = l["px"]
        size = (max(1, round(w * k)), max(1, round(h * k)))
        up = feather(upscale4k.up4(im, size).convert("RGB"))   # on black: additive light, black adds nothing
        up.save(os.path.join(OUT, l["name"] + ".webp"), "WEBP", quality=88, method=6)
    print("layers", len(meta["layers"]))


FEATHER = 28        # px (4K) over which every light layer fades to black at its box's edges


def feather(im):
    """Fade a light layer to black at its edges: light cut off by its box drew a faint rectangle on the street
    (render QA 2026-11-09: lamp_far's right edge, the candle's and the fleur sign's tops)."""
    a = np.asarray(im).astype(np.float32)
    h, w = a.shape[:2]
    f = min(FEATHER, w // 4, h // 4) or 1
    ramp = lambda n: np.clip(np.minimum(np.arange(n), np.arange(n)[::-1]) / f, 0, 1)
    k = np.outer(ramp(h), ramp(w))
    k = k * k * (3 - 2 * k)
    return Image.fromarray((a * k[..., None]).round().clip(0, 255).astype(np.uint8), "RGB")


def refeather(meta):
    """feather the exported layers in place (no new upscale)"""
    for l in meta["layers"]:
        p = os.path.join(OUT, l["name"] + ".webp")
        feather(Image.open(p).convert("RGB")).save(p, "WEBP", quality=88, method=6)
    print("feathered", len(meta["layers"]))


def fbm(w, h, seed, octaves=6, base=4):
    """Fractal value noise, tileable in x (period w) and smooth in y."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        gx, gy = base * 2 ** o, max(2, base * 2 ** o * h // w + 1)
        g = rng.random((gy + 1, gx)).astype(np.float32)
        xs = np.linspace(0, gx, w, endpoint=False)
        ys = np.linspace(0, gy, h)
        x0 = np.floor(xs).astype(int); fx = xs - x0; x1 = (x0 + 1) % gx
        y0 = np.minimum(np.floor(ys).astype(int), gy - 1); fy = ys - y0; y1 = y0 + 1
        sx = fx * fx * (3 - 2 * fx); sy = (fy * fy * (3 - 2 * fy))[:, None]
        a = g[y0][:, x0] * (1 - sx) + g[y0][:, x1] * sx
        b = g[y1][:, x0] * (1 - sx) + g[y1][:, x1] * sx
        out += amp * (a * (1 - sy) + b * sy)
        tot += amp
        amp *= .5
    return out / tot


def mist():
    W, H = 2048, 512
    for name, seed, col, dens in (("mist_a", 7, (124, 255, 120), .62), ("mist_b", 19, (150, 230, 170), .5),
                                  ("mist_c", 31, (170, 140, 230), .38)):
        n = fbm(W, H, seed)
        n = np.clip((n - .38) / .4, 0, 1) ** 1.6                    # wisps, not a flat sheet
        yy = np.linspace(0, 1, H)[:, None]
        band = np.clip(np.sin(np.pi * yy) ** 1.3, 0, 1)                # soft top and bottom: no hard band edges
        a = (n * band * dens * 255).astype(np.uint8)
        rgb = np.zeros((H, W, 3), np.uint8); rgb[:] = col
        Image.fromarray(np.dstack([rgb, a]), "RGBA").save(os.path.join(OUT, name + ".webp"), "WEBP", quality=82,
                                                          alpha_quality=80, method=6)
    print("mist x3")


def stars(meta):
    sky = np.asarray(Image.open(os.path.join(SRC, "sky_mask.png"))) > 128
    H, W = sky.shape
    from scipy import ndimage
    inner = ndimage.binary_erosion(sky, iterations=6)
    # keep stars off the moon and its halo
    moon = next((l for l in meta["layers"] if l["kind"] == "moon"), None)
    yy, xx = np.mgrid[0:H, 0:W]
    if moon:
        x, y, w, h = moon["px"]
        inner &= np.hypot(xx - (x + w / 2), yy - (y + h / 2)) > max(w, h) * .62
    ys, xs = np.nonzero(inner)
    rng = np.random.default_rng(1803)
    out = []
    # fewer stars low in the sky (city glow), more high up
    wts = (1.15 - ys / H) ** 2
    pick = rng.choice(len(xs), size=min(170, len(xs)), replace=False, p=wts / wts.sum())
    for i in pick:
        big = rng.random() < .12
        out.append({"x": round(float(xs[i]) / W, 4), "y": round(float(ys[i]) / H, 4),
                    "r": round(float(rng.uniform(1.4, 2.4) if big else rng.uniform(.6, 1.3)), 2),
                    "b": round(float(rng.uniform(.75, 1) if big else rng.uniform(.35, .8)), 2),
                    "s": round(float(rng.uniform(.4, 1.6)), 2),            # twinkle speed
                    "p": round(float(rng.uniform(0, 6.28)), 2),
                    "c": ["#ffffff", "#fff4dc", "#dfe8ff", "#e8dcff"][int(rng.integers(0, 4))],
                    "cross": bool(big)})
    return out


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    what = sys.argv[1].split(",") if len(sys.argv) > 1 else ["plate", "layers", "mist", "stars"]
    meta = json.load(open(os.path.join(SRC, "layers.json")))
    if "plate" in what:
        plate()
    if "layers" in what:
        layers(meta)
    if "feather" in what:
        refeather(meta)
    if "mist" in what:
        mist()
    if "stars" in what or not os.path.exists(os.path.join(OUT, "scene.json")):
        scene = {"size": meta["size"], "layers": [{k: l[k] for k in ("name", "kind", "box", "hue")} for l in meta["layers"]],
                 "stars": stars(meta)}
        json.dump(scene, open(os.path.join(OUT, "scene.json"), "w"), separators=(",", ":"))
        print("scene.json", len(scene["layers"]), "layers", len(scene["stars"]), "stars")
