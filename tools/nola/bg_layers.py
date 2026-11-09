"""Split the lit Bourbon Street painting (art/nola-src/bg_v1.png) into a static plate + animated light layers.
The plate (bg_plate_v1.png) is the same painting redrawn with every light off; it is ECC-aligned to the lit one and
light = max(0, lit - plate) per channel, an ADDITIVE layer (the game draws it with plus-lighter: black adds nothing).
Light pixels are grouped into lamps / signs (each flickers on its own), the moon (its own layer, halo breathes),
the street's reflections (shimmer); stars and green smoke are dropped (the game draws them live: twinkling stars,
drifting fog). -> art/nola-src/bglayers/*.png at 1536 x 864 + layers.json (boxes in 0..1 of the painting).
usage: python tools/nola/bg_layers.py"""
import json, os
import cv2
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "art", "nola-src")
OUT = os.path.join(SRC, "bglayers")


# hand-placed in the 1536 x 864 painting: name, kind, box (x0 y0 x1 y1), green allowed
REGIONS = [
    ("lamp_big", "lamp", (0, 30, 120, 240), False),
    ("lamp_a", "lamp", (470, 388, 552, 480), False),
    ("lamp_b", "lamp", (598, 442, 666, 504), False),
    ("lamp_c", "lamp", (696, 460, 748, 518), False),
    ("lamp_far", "lamp", (745, 470, 965, 560), False),
    ("lamp_d", "lamp", (972, 424, 1044, 506), False),
    ("lamp_e", "lamp", (1136, 406, 1202, 472), False),
    ("candle", "lamp", (1490, 488, 1536, 575), False),
    ("neon_fleur", "neon", (112, 238, 224, 416), False),
    ("neon_trumpet", "neon", (400, 270, 552, 372), False),
    ("neon_sax", "neon", (1070, 222, 1158, 366), True),
    ("neon_skull", "neon", (1398, 26, 1536, 230), False),
]


def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32)


def main():
    os.makedirs(OUT, exist_ok=True)
    lit, plate = load(os.path.join(SRC, "bg_v1.png")), load(os.path.join(SRC, "bg_plate_v1.png"))
    H, W = lit.shape[:2]
    if plate.shape != lit.shape:
        plate = cv2.resize(plate, (W, H), interpolation=cv2.INTER_CUBIC)
    g = lambda a: cv2.GaussianBlur(a.mean(-1), (0, 0), 1.5).astype(np.float32)
    warp = np.eye(2, 3, dtype=np.float32)
    try:
        _, warp = cv2.findTransformECC(g(lit), g(plate), warp, cv2.MOTION_AFFINE,
                                       (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
    except cv2.error as e:
        print("ECC failed", e)
    plate = cv2.warpAffine(plate, warp, (W, H), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    print("plate warp", np.round(warp, 4).tolist())
    Image.fromarray(plate.clip(0, 255).astype(np.uint8)).save(os.path.join(OUT, "plate_aligned.png"))
    d = np.maximum(lit - plate, 0)
    lum = d.max(-1)
    r, gg, b = d[..., 0], d[..., 1], d[..., 2]
    # the sky: what lies above the rooftops in the plate (dark, navy, joined to the top edge)
    pl = plate
    skyish = (pl.mean(-1) < 95) & (pl[..., 2] > pl[..., 0])
    lab, n = ndimage.label(skyish)
    top = set(np.unique(lab[0])) - {0}
    sky = np.isin(lab, list(top))
    sky = ndimage.binary_closing(sky, iterations=4)
    Image.fromarray((sky * 255).astype(np.uint8)).save(os.path.join(OUT, "sky_mask.png"))
    strong = ndimage.binary_opening(lum > 34, iterations=1)
    green = (gg > r * 1.25) & (gg > b * 1.1)
    # the moon: the big bright blob high in the middle of the sky
    blob, nb = ndimage.label(ndimage.binary_dilation(strong & sky & ~green, iterations=3))
    moon = np.zeros_like(strong)
    if nb:
        sizes = ndimage.sum(np.ones_like(blob), blob, range(1, nb + 1))
        k = int(np.argmax(sizes)) + 1
        moon = blob == k
    yy, xx = np.mgrid[0:H, 0:W]
    layers = []

    def save(name, mask, grow, kind, allow_green=False):
        m = mask & strong & (allow_green | ~green)
        m = ndimage.binary_dilation(m, iterations=grow)
        soft = cv2.GaussianBlur(m.astype(np.float32), (0, 0), max(1, grow * .6)) * mask
        lay = d * soft[..., None]
        ys, xs = np.nonzero(soft > .01)
        if not len(xs):
            print("empty", name)
            return
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        Image.fromarray(lay[y0:y1, x0:x1].clip(0, 255).astype(np.uint8)).save(os.path.join(OUT, name + ".png"))
        c = lit[y0:y1, x0:x1][m[y0:y1, x0:x1]]
        layers.append({"name": name, "kind": kind, "box": [x0 / W, y0 / H, (x1 - x0) / W, (y1 - y0) / H],
                       "px": [int(x0), int(y0), int(x1 - x0), int(y1 - y0)],
                       "hue": [int(v) for v in (c.mean(0) if len(c) else [255, 220, 150])]})

    def rect(x0, y0, x1, y1):
        m = np.zeros((H, W), bool)
        m[max(0, y0):min(H, y1), max(0, x0):min(W, x1)] = True
        return m

    save("moon", moon, 8, "moon")
    for name, kind, box, green_ok in REGIONS:
        save(name, rect(*box), 5 if kind != "neon" else 4, kind, green_ok)
    # the reflections: every lit pixel on the street and the pavements left over
    taken = np.zeros((H, W), bool)
    for _, _, box, _ in REGIONS:
        taken |= rect(*box)
    save("street", (yy > H * .68) & ~taken & ~sky, 3, "street")
    json.dump({"size": [W, H], "layers": layers}, open(os.path.join(OUT, "layers.json"), "w"), indent=1)
    print(len(layers), "layers:", ", ".join(f"{l['name']}@{l['px'][:2]}" for l in layers))
    # QA: plate + every layer added back should be the lit painting, less the stars and the green smoke
    back = plate.copy()
    for l in layers:
        x, y, w, h = l["px"]
        back[y:y + h, x:x + w] += np.asarray(Image.open(os.path.join(OUT, l["name"] + ".png"))).astype(np.float32)
    Image.fromarray(back.clip(0, 255).astype(np.uint8)).save(os.path.join(OUT, "_recomposed.png"))


if __name__ == "__main__":
    main()
