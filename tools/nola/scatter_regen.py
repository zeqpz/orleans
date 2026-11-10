"""The two scatters split into pieces that can move on their own (owner, 2026-11-09: "split up and animate the FS and
XFS, we want their idle animation to stand out more").

Each scatter was one flat sticker bent by a three-bone chain: its letters could only lean and squash together. Here
every piece of it is drawn on its own canvas by the image model, from the whole sticker as the reference - each
letter, the crystal ball, its smoke and the beads of FS; each letter, the skull in his top hat, his hands and the
flames of XFS - complete where another piece used to cover it, then laid back over the sticker (SIFT + RANSAC, as
tools/nola/doc_regen.py does for Doc) so every piece sits exactly where it was.

  gen [ID[:part],..]   art/nola-src/scatter_regen/<ID>_<part>_raw.png, one OpenRouter call each (the key never printed)
  fit [ID,..]          -> art/nola-src/scatter_parts/<ID>/<part>.png + pieces.json: each piece's box on the 1000 px icon, its
                          pivot (where it turns and squashes about) and its depth order, for blender/symparts.py
                          (pieces that are several separate shapes - the flames, the two hands - are cut into one
                          part a shape); and _sheet.png, the sticker against the pieces put back together
  finish [ID,..]       the pieces at rest become the symbol's still picture everywhere else: icons/<ID>.png (the
                          first sticker kept as <ID>_v1.png - fit always reads that one), icons/<ID>_glow.png (the
                          halo of the new outline, as prep_icons.py makes it) and frontend/assets/flat/<ID>.webp
usage: python tools/nola/scatter_regen.py gen|fit|finish [names]"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import orimg
import doc_regen as DR

ROOT = os.path.dirname(os.path.dirname(HERE))
ICONS = os.path.join(ROOT, "art", "nola-src", "icons")
WORK = os.path.join(ROOT, "art", "nola-src", "scatter_regen")
PARTS = os.path.join(ROOT, "art", "nola-src", "scatter_parts")
HEAD = ("The attached image is a sticker-style slot-machine symbol made of several pieces. Redraw ONLY ONE piece of "
        "it, by itself, exactly as it appears in the image: the same shapes, the same colours and glossy highlights, "
        "the same dark outline, the SAME SIZE, the same angle and the SAME POSITION on the canvas - as if every other "
        "piece had been erased around it. Where another piece covers part of it, COMPLETE it (draw the whole piece). ")
TAIL = (" Keep a thick cream-white sticker border all the way round the piece, as the sticker has. Same cartoon style: "
        "bold dark outlines, flat glossy cel colours, crisp clean high-resolution linework. Transparent background. "
        "Nothing else in the picture: no other letters or objects, no text, no shadow, no glow.")
# piece: (prompt, where it turns about - x, y as shares of its own box, depth order back to front, split into shapes)
SPEC = {
    "BS": {
        "smoke": ("The piece: the curling GREEN SMOKE plume that rises behind and above the crystal ball - only the "
                  "smoke, complete down to where it starts.", (.5, 1.0), 0, False),
        "beads": ("The piece: the MARDI GRAS BEAD NECKLACE - the strand of round purple and green beads that drapes "
                  "down the left side of the letters - only the beads.", (.75, .0), 1, False),
        "f": ("The piece: the big gold bubble LETTER F only (glossy yellow-gold), the whole letter with no beads on it.",
              (.5, 1.0), 2, False),
        "s": ("The piece: the big gold bubble LETTER S only (glossy yellow-gold), the whole letter.", (.5, 1.0), 3, False),
        "ball": ("The piece: the CRYSTAL BALL only - the purple faceted gem ball sitting in its little gold crown "
                 "setting with the green jewel - with no smoke.", (.5, 1.0), 4, False),
    },
    "ES": {
        "flames": ("The piece: the GREEN FLAMES only - the tongues of green ghostly fire that rise behind the letters "
                   "and the skull - each tongue complete down to its root.", (.5, 1.0), 0, True),
        "skull": ("The piece: the SKULL in his little black top hat only (purple hat band, crossbones badge, purple "
                  "feather) - the whole skull with its jaw and grinning teeth, complete below where the letters hid "
                  "it; NO hands.", (.5, 1.0), 1, False),
        "x": ("The piece: the slimy green dripping LETTER X only, with its own drips.", (.5, 1.0), 2, False),
        "f": ("The piece: the slimy green dripping LETTER F only, with its own drips.", (.5, 1.0), 3, False),
        "s": ("The piece: the slimy green dripping LETTER S only, with its own drips.", (.5, 1.0), 4, False),
        "hands": ("The piece: the skull's two bony SKELETON HANDS only - the fingers curled over as if gripping the "
                  "top edge of something - just the two hands, apart from each other.", (.5, 1.0), 5, True),
    },
}


def first(sid):
    """The sticker the pieces were drawn from (finish replaces icons/<ID>.png with the pieces at rest)."""
    v1 = os.path.join(ICONS, sid + "_v1.png")
    return v1 if os.path.exists(v1) else os.path.join(ICONS, sid + ".png")


def ref(sid):
    os.makedirs(WORK, exist_ok=True)
    p = os.path.join(WORK, f"{sid}_ref.png")
    if not os.path.exists(p):
        Image.open(first(sid)).convert("RGBA").resize((1024, 1024), Image.LANCZOS).save(p)
    return p


def gen(job):
    sid, part = job
    try:
        _, cost = orimg.generate(os.path.join(WORK, f"{sid}_{part}_raw.png"), HEAD + SPEC[sid][part][0] + TAIL,
                                 aspect="1:1", refs=[ref(sid)])
        return f"OK {sid} {part} {cost}"
    except RuntimeError as e:
        return f"FAIL {sid} {part} {e}"


# Where a piece goes when its drawing cannot be matched to the sticker by its features (the model draws each piece
# big, filling its canvas, and redraws smoke and fire to its own plan): its ink's box on the 1000 px icon
BOX = {
    "BS": {"f": (62, 272, 520, 945), "s": (432, 348, 905, 912), "ball": (590, 135, 842, 400),
           "smoke": (512, 58, 932, 420), "beads": (62, 292, 285, 770)},
    "ES": {"flames1": (45, 185, 215, 0), "flames2": (485, 255, 665, 0), "flames3": (730, 165, 955, 0), "hands1": (106, 383, 214, 474), "hands2": (383, 391, 474, 499),
           "skull": (175, 62, 560, 470), "x": (60, 420, 400, 890), "f": (395, 400, 660, 900), "s": (640, 380, 945, 930)},
}
ALWAYS_BOX = {("BS", "smoke"), ("BS", "beads"), ("ES", "flames"), ("ES", "hands")}   # redrawn to a new plan: never matched
# the fire: the model draws one W of three tongues on a shared root; it is cut at the two troughs and each tongue
# goes where the sticker has one - (left, top, right): as wide as that, its tip at that height, its root running
# down behind the letters and fading out there (FADE: from, to)
TOP = ("flames1", "flames2", "flames3")
FADE = (455, 560)
RIM = 27                                                   # px: the sticker's cream border round the whole symbol
CREAM = (252, 234, 210)


def strip_border(im):
    """The model gives every piece its own cream sticker border. Take it off (the border is put back round the whole
    symbol, behind all the pieces, so it follows them as one outline): the cream that can be reached from outside
    the piece without crossing its dark outline."""
    a = im[..., 3] > 128
    ring = a & ~ndimage.binary_erosion(a, iterations=10)
    if ring.sum() < 50:
        return im
    col = np.median(im[..., :3][ring], axis=0)
    if col.min() < 170:                                    # no cream border on this one
        return im
    cream = a & (np.abs(im[..., :3] - col).sum(axis=2) < 110) & (im[..., :3].min(axis=2) > 150)
    lab, n = ndimage.label(cream)
    edge = ndimage.binary_dilation(~a, iterations=3) & cream
    hit = np.unique(lab[edge])
    gone = np.isin(lab, hit[hit > 0])
    gone = ndimage.binary_dilation(gone, iterations=2) & ~ndimage.binary_erosion(a & ~gone, iterations=2)
    keep = a & ~gone
    keep = ndimage.binary_opening(keep, iterations=2)
    soft = ndimage.gaussian_filter(keep.astype(np.float32), .8)
    out = im.copy()
    out[..., 3] = np.minimum(im[..., 3], 255 * np.clip(soft * 1.6 - .3, 0, 1))
    return out


def tongues(raw):
    """The W of fire cut into its three tongues, at the two troughs between them (left to right)."""
    a = raw[..., 3] > 128
    xs = np.nonzero(a.any(axis=0))[0]
    x0, x1 = xs.min(), xs.max()
    top = np.where(a.any(axis=0), a.argmax(axis=0), 0).astype(np.float32)
    top = ndimage.uniform_filter1d(top, 21)
    cand = [x for x in range(x0 + (x1 - x0) // 6, x1 - (x1 - x0) // 6)
            if top[x] == top[max(x0, x - 70):x + 71].max()]
    cuts = []
    for x in sorted(cand, key=lambda x: -top[x]):          # the two deepest, apart
        if all(abs(x - c) > (x1 - x0) // 5 for c in cuts):
            cuts.append(x)
        if len(cuts) == 2:
            break
    cuts = [x0 - 1] + sorted(cuts) + [x1 + 1]
    out = []
    for k in range(3):
        piece = raw.copy()
        piece[:, :max(0, cuts[k] - 2), 3] = 0
        piece[:, cuts[k + 1] + 2:, 3] = 0
        out.append((f"flames{k + 1}", piece))
    return out


def place(raw, lay, box, force):
    """raw px -> icon px, 2x3: by its features where they match well, else its ink's box laid on `box`."""
    M, n_good, n_in = (None, 0, 0) if force else DR.similar(raw, lay)
    if M is not None and n_in >= 14 and .2 < float(np.hypot(M[0][0], M[1][0])) < 2:
        return np.float32(M), f"sift {n_in}/{n_good}"
    ys, xs = np.nonzero(raw[..., 3] > 128)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    u0, v0, u1, v1 = box
    if v1 == 0:                                            # (left, top, right): by its width, its tip at the top
        k = (u1 - u0) / (x1 - x0)
        return np.float32([[k, 0, (u0 + u1) / 2 - k * (x0 + x1) / 2], [0, k, v0 - k * y0]]), "top"
    k = min((u1 - u0) / (x1 - x0), (v1 - v0) / (y1 - y0))
    return np.float32([[k, 0, (u0 + u1) / 2 - k * (x0 + x1) / 2], [0, k, (v0 + v1) / 2 - k * (y0 + y1) / 2]]), "box"


def warp(raw, M, W, H):
    pm = raw.copy()
    pm[..., :3] *= pm[..., 3:4] / 255.
    big = cv2.warpAffine(pm, M * 2, (W * 2, H * 2), flags=cv2.INTER_AREA if np.hypot(M[0, 0], M[1, 0]) < .3 else cv2.INTER_CUBIC,
                         borderValue=(0, 0, 0, 0))
    full = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    al = full[..., 3:4].clip(0, 255)
    full[..., :3] = np.where(al > 1, full[..., :3] * 255. / np.maximum(al, 1), 0)
    return full.clip(0, 255)


def fit(sid):
    """Each raw piece, its border off, onto the sticker (1000 px), cropped to its ink; its rim (the cream border it
    throws, to sit behind everything); pieces.json; the sheet."""
    icon = DR.rgba(first(sid))
    H, W = icon.shape[:2]
    out_dir = os.path.join(PARTS, sid)
    os.makedirs(out_dir, exist_ok=True)
    for old in os.listdir(out_dir):
        os.remove(os.path.join(out_dir, old))
    pieces, layers = [], []
    for part, (_, pivot, order, split) in sorted(SPEC[sid].items(), key=lambda kv: kv[1][2]):
        rp = os.path.join(WORK, f"{sid}_{part}_raw.png")
        if not os.path.exists(rp):
            print(sid, part, "no raw picture")
            continue
        raw = strip_border(DR.tidy(DR.rgba(rp)))
        shapes = [(part, raw)]
        if part == "flames":
            shapes = tongues(raw)
        elif split:                                            # one part a separate shape, left to right
            lab, n = ndimage.label(raw[..., 3] > 128)
            sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
            keep = [i + 1 for i, sz in enumerate(sizes) if sz > 2500]
            keep.sort(key=lambda i: ndimage.center_of_mass(lab == i)[1])
            shapes = []
            for k, i in enumerate(keep):
                m = ndimage.binary_dilation(lab == i, iterations=4)
                piece = raw.copy()
                piece[..., 3] = np.where(m, piece[..., 3], 0)
                shapes.append((f"{part}{k + 1}", piece))
        for name, im in shapes:
            # (the sticker at the drawing's own size, for the match)
            lay = cv2.resize(icon, (im.shape[1], im.shape[0]), interpolation=cv2.INTER_AREA)
            M, how = place(im, lay, [v * im.shape[1] / W for v in BOX[sid].get(name, BOX[sid].get(part))], (sid, part) in ALWAYS_BOX)
            M = M * (W / im.shape[1])
            full = warp(im, M, W, H)
            if name in TOP:                                    # its root fades out behind the letters
                yy = np.arange(H, dtype=np.float32)[:, None]
                full[..., 3] *= np.clip((FADE[1] - yy) / (FADE[1] - FADE[0]), 0, 1)
            ys, xs = np.nonzero(full[..., 3] > 8)
            x0, y0, x1, y1 = max(0, xs.min() - 4), max(0, ys.min() - 4), min(W, xs.max() + 5), min(H, ys.max() + 5)
            print(f"{sid} {name:8s} {how:14s} scale {np.hypot(M[0, 0], M[1, 0]):.3f}  ink {x0},{y0} - {x1},{y1}", flush=True)
            Image.fromarray(full[y0:y1, x0:x1].astype(np.uint8), "RGBA").save(os.path.join(out_dir, name + ".png"))
            # its rim: the cream border, RIM px out from its ink
            d = ndimage.distance_transform_edt(full[..., 3] < 128)
            ra = np.clip(RIM + .5 - d, 0, 1)
            rys, rxs = np.nonzero(ra > 0)
            r0, s0, r1, s1 = max(0, rxs.min() - 2), max(0, rys.min() - 2), min(W, rxs.max() + 3), min(H, rys.max() + 3)
            rim = np.zeros((s1 - s0, r1 - r0, 4), np.uint8)
            rim[..., :3] = CREAM
            rim[..., 3] = (ra[s0:s1, r0:r1] * 255).astype(np.uint8)
            Image.fromarray(rim, "RGBA").save(os.path.join(out_dir, name + "_rim.png"))
            pieces.append({"name": name, "of": part, "box": [int(x0), int(y0), int(x1 - x0), int(y1 - y0)],
                           "rim": [int(r0), int(s0), int(r1 - r0), int(s1 - s0)],
                           "pivot": [round(float(x0 + pivot[0] * (x1 - x0)), 1), round(float(y0 + pivot[1] * (y1 - y0)), 1)],
                           "order": order})
            layers.append((full, ra))
    json.dump({"size": [W, H], "pieces": pieces}, open(os.path.join(out_dir, "pieces.json"), "w"), indent=1)
    # the sheet: the sticker, and the pieces put back together on their rims
    can = np.zeros((H, W, 4), np.float32)
    for _, ra in layers:
        can[..., :3] = np.where(ra[..., None] > 0, CREAM, can[..., :3])
        can[..., 3] = np.maximum(can[..., 3], ra * 255)
    for im, _ in layers:
        a = im[..., 3:4] / 255.
        can[..., :3] = can[..., :3] * (1 - a) + im[..., :3] * a
        can[..., 3:4] = np.maximum(can[..., 3:4], im[..., 3:4])
    Image.fromarray(can.clip(0, 255).astype(np.uint8), "RGBA").save(os.path.join(out_dir, "_rest.png"))
    sh = Image.new("RGB", (W * 2, H), (70, 60, 110))
    for k, im in enumerate((icon, can)):
        t = Image.fromarray(im.clip(0, 255).astype(np.uint8), "RGBA")
        bg = Image.new("RGBA", (W, H), (70, 60, 110, 255))
        bg.alpha_composite(t)
        sh.paste(bg.convert("RGB"), (k * W, 0))
    sh.save(os.path.join(WORK, f"{sid}_sheet.png"))
    print(sid, "pieces", [p["name"] for p in pieces])


STARS = {"BS": [(380, 225, 170), (892, 602, 130), (466, 862, 150), (150, 262, 110)]}   # the still keeps its gold stars


def finish(sid):
    from PIL import ImageFilter
    import shutil
    cur, v1 = os.path.join(ICONS, sid + ".png"), os.path.join(ICONS, sid + "_v1.png")
    if not os.path.exists(v1):
        shutil.copyfile(cur, v1)
    out = Image.open(os.path.join(PARTS, sid, "_rest.png")).convert("RGBA")
    out.save(cur)
    a = Image.new("L", (1200, 1200), 0)                       # (the halo: exactly as tools/nola/prep_icons.py makes it)
    a.paste(out.getchannel("A").point(lambda v: 255 if v > 100 else 0), (100, 100))
    a = a.resize((300, 300), Image.BILINEAR).filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(7))
    a = a.resize((1200, 1200), Image.BICUBIC)
    Image.merge("RGBA", (Image.new("L", a.size, 255),) * 3 + (a,)).save(os.path.join(ICONS, sid + "_glow.png"))
    still = out.copy()
    for x, y, size in STARS.get(sid, []):
        st = Image.open(os.path.join(ROOT, "art", "nola-src", "fx", "sparkle.png")).convert("RGBA")
        st = st.resize((size, round(size * st.size[1] / st.size[0])), Image.LANCZOS)
        still.alpha_composite(st, (x - st.size[0] // 2, y - st.size[1] // 2))
    f = still.convert("RGBa").resize((800, 800), Image.LANCZOS).convert("RGBA")
    f.save(os.path.join(ROOT, "frontend", "assets", "flat", sid + ".webp"), "WEBP", quality=92, alpha_quality=100, method=6)
    print(sid, "icon, glow and still written")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    names = sys.argv[2].split(",") if len(sys.argv) > 2 else list(SPEC)
    if cmd == "gen":
        jobs = []
        for n in names:
            sid, _, part = n.partition(":")
            jobs += [(sid, part)] if part else [(sid, p) for p in SPEC[sid]]
        for sid in {j[0] for j in jobs}:
            ref(sid)                                           # (made once, before the calls share it)
        with ThreadPoolExecutor(8) as ex:
            for r in ex.map(gen, jobs):
                print(r, flush=True)
    elif cmd == "fit":
        for sid in names:
            fit(sid)
    elif cmd == "finish":
        for sid in names:
            finish(sid)
    else:
        print(__doc__)
