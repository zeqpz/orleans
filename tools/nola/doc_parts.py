"""Cut Doc (the voodoo showman) into the layered parts of his rig -> art/nola-src/doc_parts/ (4K, 2731 x 4096 canvas):

  back to front:  coat_back  the dark coat panel seen between his legs (painted on behind the legs)
                  leg_r      his left leg (the viewer's right): trouser, spat and shoe, the thigh painted up under the coat
                  leg_l      his right leg (the viewer's left)
                  cane       the skull-topped cane (behind his right hand, so the fingers wrap the knob)
                  head       face, ears, braid and neck (behind the collar; the neck runs on down under it, and a scalp
                             is painted under the hat so a tipped hat shows a head, not a hole)
                  body       torso, vest, cravat, collar, the front coat tails, and a cap of each sleeve at the shoulder
                             (the arm sits over it, so a raised arm never opens a gap at the seam)
                  hat        the top hat, its band, bone and feather
                  arm_r      his left arm (viewer's right): sleeve, ruffled cuff and the open, spread hand
                  arm_l      his right arm (viewer's left): sleeve, cuff and the hand on the skull knob
                  wisp       the green magic smoke over the open palm
  face_<name>.png  each reaction face (art/nola-src/doc/body_<name>.png) cut to the head: only the pixels that differ
                   from the neutral face, feathered, so a face swap is a small patch over the head layer
  parts.json       every part's box (4K px) and order, the drawing size, the joints (1024 x 1536 art px)
  _debug.png       the parts tinted over the drawing, to check the cuts

Masks are worked out on the 1024 x 1536 drawing (art/nola-src/clean/doc_v1.png) where the coordinates below were
read off zoomed grids, then scaled up and applied to the 4K plates (art/nola-src/doc/body_neutral.png, cane.png,
wisp.png - already 4K through tools/nola/upscale4k.py). Hidden areas (under the coat tails, behind the legs, under the
hat, under the collar) are filled by inpainting from their own part, so they only need to read as cloth/skin/hair when
a joint opens them a little.
usage: python tools/nola/doc_parts.py"""
import json, os
import cv2
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, "art", "nola-src")
PLATES = os.path.join(SRC, "doc")
OUT = os.path.join(SRC, "doc_parts")
W1, H1 = 1024, 1536
K = 4096 / 1536                                   # 1k drawing px -> 4K plate px

ORDER = ["coat_back", "leg_r", "leg_l", "cane", "head", "body", "hat", "arm_r", "arm_l", "wisp"]

# ---- the cuts (1k drawing px) ----
SHOULDER_L = ((366, 374), (399, 468), (401, 492))  # the seam where his right sleeve meets the coat (viewer's left), to the gap
SHOULDER_R = ((618, 388), (597, 500), (594, 512))  # and where his left sleeve meets it (viewer's right)
HAND_L, HAND_R = (250, 700), (720, 620)           # a pixel on each arm, to pick its piece after the cut
CAP_L, CAP_R = ((390, 425), 34), ((606, 440), 36)  # the sleeve caps the body keeps at each shoulder: centre, radius
# the face and neck (inside the hat's brim, down to the collar) - the head part; everything above it that is opaque
# and above BRIM_Y is the hat
HEAD_POLY = [(440, 162), (556, 162), (557, 212), (571, 227), (586, 262), (582, 330), (548, 352), (532, 358),
             (520, 372), (472, 372), (455, 356), (428, 330), (422, 262), (426, 214), (437, 206)]
BRIM_Y = 236                                      # nothing of the hat hangs lower than this
NECK = (468, 524, 340, 372)                       # the neck: x0 x1 y0 y1 (it runs on down to NECK_HIDE under the collar)
NECK_HIDE = 410
SCALP = ((497, 178), (66, 30))                    # the scalp painted under the hat: centre, radii
# the legs: trouser, spat and shoe, each to the crotch (the hidden thigh under the coat is filled)
LEG_L = [(452, 652), (508, 668), (506, 760), (486, 900), (462, 1050), (430, 1250), (412, 1395), (414, 1500),
         (296, 1505), (300, 1470), (340, 1400), (346, 1250), (372, 1050), (402, 880), (420, 760)]
LEG_R = [(512, 668), (568, 652), (600, 760), (614, 880), (640, 1050), (676, 1250), (700, 1395), (760, 1470),
         (768, 1505), (628, 1505), (612, 1400), (594, 1250), (566, 1050), (540, 900), (518, 760)]
# the coat's back panel between the legs (its ragged hem included)
COAT_BACK = [(440, 680), (584, 680), (590, 760), (578, 905), (560, 1010), (530, 1000), (512, 960), (494, 1000),
             (464, 1010), (440, 905), (430, 760)]

JOINTS = {   # art px, for the rig (tools/nola/blender/doc_rig.py reads these)
    "root": (512, 1500), "hips": (512, 690), "spine": (512, 600), "chest": (512, 470), "neck": (500, 372),
    "head": (498, 300), "hat": (488, 172), "shoulder_l": (392, 428), "elbow_l": (312, 652), "wrist_l": (236, 724),
    "knob": (186, 834), "cane_tip": (186, 1500), "shoulder_r": (606, 440), "elbow_r": (684, 652),
    "wrist_r": (792, 548), "palm": (850, 462), "hip_l": (470, 700), "knee_l": (420, 1060), "ankle_l": (372, 1420),
    "toe_l": (318, 1490), "hip_r": (552, 700), "knee_r": (600, 1060), "ankle_r": (648, 1420), "toe_r": (720, 1490),
}


def rgba(p):
    return np.asarray(Image.open(p).convert("RGBA")).astype(np.float32)


def poly_mask(pts, shape, scale=1.0):
    m = np.zeros(shape, np.uint8)
    cv2.fillPoly(m, [np.round(np.array(pts, np.float32) * scale).astype(np.int32)], 1)
    return m.astype(bool)


def cut_line(mask, *pts, width=4):
    m = mask.astype(np.uint8).copy()
    for a, b in zip(pts, pts[1:]):
        cv2.line(m, tuple(map(int, a)), tuple(map(int, b)), 0, width)
    return m.astype(bool)


def piece_at(mask, p):
    lab, _ = ndimage.label(mask)
    v = lab[p[1], p[0]]
    if not v:
        raise SystemExit(f"no piece at {p}")
    return lab == v


def side_of(shape, a, b):
    """True on the far side (x greater) of the line a-b, extended."""
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W]
    (ax, ay), (bx, by) = a, b
    return (bx - ax) * (yy - ay) - (by - ay) * (xx - ax) < 0


def masks_1k(art, cane1k, wisp1k):
    """Every part's mask on the 1k drawing (bool), plus each part's 'paint' area (where it must have pixels even
    though another part covers them: the hidden thigh, the panel behind the legs, the neck under the collar)."""
    H, W = art.shape[:2]
    op = art[..., 3] > 8
    yy, xx = np.mgrid[0:H, 0:W]
    cane = cane1k > 8
    wisp = wisp1k > 8
    rest = op & ~cane & ~wisp
    # arms: cut each sleeve from the coat at its shoulder seam and take the piece with the hand in it
    arm_l = piece_at(cut_line(rest & (xx < 430) & (yy > 360) & (yy < 900), *SHOULDER_L), HAND_L)
    arm_l &= ~side_of((H, W), *SHOULDER_L[:2]) | (yy > SHOULDER_L[1][1])
    arm_r = piece_at(cut_line(rest & (xx > 585) & (yy > 360) & (yy < 760), *SHOULDER_R), HAND_R)
    arm_r &= side_of((H, W), *SHOULDER_R[:2]) | (yy > SHOULDER_R[1][1])
    rest &= ~arm_l & ~arm_r
    # head + hat
    headp = poly_mask(HEAD_POLY, (H, W))
    head = rest & headp
    hat = rest & ~headp & (yy < BRIM_Y) & (xx > 360) & (xx < 680)
    rest &= ~head & ~hat
    # legs and the back panel: trouser pixels inside each leg's outline; they are a near-grey, the coat is purple
    r, g, b = art[..., 0], art[..., 1], art[..., 2]
    purple = (r - g > 14) & (b - g > 10)
    legl_p, legr_p = poly_mask(LEG_L, (H, W)), poly_mask(LEG_R, (H, W))
    back_p = poly_mask(COAT_BACK, (H, W))
    leg_l = rest & legl_p & ~purple & (yy > 650)
    leg_r = rest & legr_p & ~purple & (yy > 650)
    for m in (leg_l, leg_r):                       # the ink lines between trouser and coat go with the trouser
        m[:] = ndimage.binary_closing(m, iterations=2) & rest
    # only the trouser seen below the coat's hem and between the tails belongs to the leg; a stray grey fleck
    # inside a coat tail does not
    leg_l &= ndimage.binary_opening(leg_l, iterations=1)
    leg_r &= ndimage.binary_opening(leg_r, iterations=1)
    # spats and shoes: everything under the trouser hems is foot (the cane is its own part already)
    leg_l = piece_at(leg_l, (370, 1300)) | (rest & (yy > 1376) & (xx < 512))
    leg_r = piece_at(leg_r, (650, 1300)) | (rest & (yy > 1376) & (xx >= 512))
    coat_back = rest & back_p & ~leg_l & ~leg_r & purple & (yy > 690)
    coat_back = ndimage.binary_opening(coat_back, iterations=1)
    body = rest & ~leg_l & ~leg_r & ~coat_back
    # what each must paint although it is covered
    # only what another part really covers is painted: the thigh under the coat, the panel behind the legs
    coat = ndimage.binary_dilation(body | coat_back, iterations=3)
    paint = {
        "leg_l": legl_p & coat & (yy < 1400),
        "leg_r": legr_p & coat & (yy < 1400),
        "coat_back": back_p & ndimage.binary_dilation(leg_l | leg_r, iterations=3),
        "head": ((xx >= NECK[0]) & (xx < NECK[1]) & (yy >= NECK[2]) & (yy < NECK_HIDE))
                | (((xx - SCALP[0][0]) / SCALP[1][0]) ** 2 + ((yy - SCALP[0][1]) / SCALP[1][1]) ** 2 <= 1),
    }
    caps = {}
    for nm, ((cx, cy), rad), arm in (("l", CAP_L, arm_l), ("r", CAP_R, arm_r)):
        caps[nm] = arm & (((xx - cx) ** 2 + (yy - cy) ** 2) <= rad * rad)
    parts = {"coat_back": coat_back, "leg_r": leg_r, "leg_l": leg_l, "head": head, "body": body, "hat": hat,
             "arm_r": arm_r, "arm_l": arm_l}
    # stray islands (a skull eye left out of the cane, a fleck between masks) go to the part round them
    lab, n = ndimage.label(op & ~cane & ~wisp)
    for nm in list(parts):
        pl, k = ndimage.label(parts[nm])
        if k <= 1:
            continue
        sizes = ndimage.sum(np.ones_like(pl), pl, range(1, k + 1))
        for i, sz in enumerate(sizes, 1):
            if sz >= .2 * sizes.max() or sz > 400:
                continue
            isl = pl == i
            ring = ndimage.binary_dilation(isl, iterations=2) & ~isl
            votes = {o: int((parts[o] & ring).sum()) for o in parts if o != nm}
            votes["cane"] = int((cane & ring).sum())
            best = max(votes, key=votes.get)
            if votes[best] == 0:
                continue
            parts[nm] &= ~isl
            if best == "cane":
                cane = cane | isl
            else:
                parts[best] |= isl
    coat_back, leg_r, leg_l, head, body, hat, arm_r, arm_l = (parts[k] for k in
        ("coat_back", "leg_r", "leg_l", "head", "body", "hat", "arm_r", "arm_l"))
    body |= caps["l"] | caps["r"]                  # the body keeps the sleeve's cap under each shoulder
    return {"coat_back": coat_back, "leg_r": leg_r, "leg_l": leg_l, "cane": cane, "head": head, "body": body,
            "hat": hat, "arm_r": arm_r, "arm_l": arm_l, "wisp": wisp}, paint


def up_mask(m, shape4k, feather=1.2):
    f = cv2.resize(m.astype(np.float32), (shape4k[1], shape4k[0]), interpolation=cv2.INTER_LINEAR)
    if feather:
        f = cv2.GaussianBlur(f, (0, 0), feather)
    return np.clip((f - .5) * 2.2 + .5, 0, 1)


def fill_hidden(layer, paint4k, own4k, colour=None):
    """Paint the hidden area of a part: inpaint its RGB from its own pixels (on a quarter-size copy, then scaled up)
    and give it full alpha, under the pixels it already has."""
    H, W = layer.shape[:2]
    need = paint4k & ~(layer[..., 3] > 250)
    if not need.any():
        return layer
    s = 4
    small = cv2.resize(layer[..., :3], (W // s, H // s), interpolation=cv2.INTER_AREA).astype(np.uint8)
    have = cv2.resize(own4k.astype(np.uint8), (W // s, H // s), interpolation=cv2.INTER_NEAREST).astype(bool)
    hole = (~have).astype(np.uint8)
    if colour is not None:
        small[~have] = colour
    filled = cv2.inpaint(small, hole, 9, cv2.INPAINT_TELEA)
    big = cv2.resize(filled, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    a = layer[..., 3:4] / 255.
    soft = cv2.GaussianBlur(need.astype(np.float32), (0, 0), 2)[..., None]
    out = layer.copy()
    out[..., :3] = layer[..., :3] * a + big * (1 - a) * (soft > 0) + layer[..., :3] * (1 - a) * (soft <= 0)
    out[..., 3] = np.maximum(layer[..., 3], soft[..., 0] * 255)
    return out


def main(quick=False):
    os.makedirs(OUT, exist_ok=True)
    art = rgba(os.path.join(SRC, "clean", "doc_v1.png"))
    neutral = rgba(os.path.join(PLATES, "body_neutral.png"))
    cane4 = rgba(os.path.join(PLATES, "cane.png"))
    wisp4 = rgba(os.path.join(PLATES, "wisp.png"))
    H4, W4 = neutral.shape[:2]
    small = lambda a: cv2.resize(a[..., 3], (W1, H1), interpolation=cv2.INTER_AREA)
    m1, paint1 = masks_1k(art, small(cane4), small(wisp4))
    full = neutral.copy()                          # the whole figure, cane and wisp included, at 4K
    for extra in (cane4, wisp4):
        a = extra[..., 3:4] / 255.
        full[..., :3] = full[..., :3] * (1 - a) + extra[..., :3] * a
        full[..., 3] = np.maximum(full[..., 3], extra[..., 3])
    meta = {"size": [W4, H4], "art": [W1, H1], "scale": K, "order": ORDER, "joints": JOINTS, "parts": {}}
    dbg = np.zeros((H1, W1, 3), np.float32)
    tints = {"coat_back": (120, 60, 160), "leg_r": (60, 160, 220), "leg_l": (60, 220, 160), "cane": (200, 200, 200),
             "head": (230, 160, 90), "body": (170, 60, 200), "hat": (240, 240, 60), "arm_r": (240, 90, 90),
             "arm_l": (90, 120, 240), "wisp": (90, 255, 90)}
    for nm in ORDER:
        dbg[m1[nm]] = np.array(tints[nm]) * .8 + 30
    if quick:                                      # --quick: just the debug picture of the cuts
        base = art[..., :3] * (art[..., 3:4] / 255.) * .35 + 40
        Image.fromarray(np.where((dbg.sum(-1) > 0)[..., None], dbg, base).clip(0, 255).astype(np.uint8)).save(
            os.path.join(OUT, "_debug.png"))
        return
    for nm in ORDER:
        m = m1[nm]
        src = cane4 if nm == "cane" else wisp4 if nm == "wisp" else full
        if nm in ("cane", "wisp"):
            lay = src.copy()
        else:
            lay = src.copy()
            lay[..., 3] *= up_mask(m, (H4, W4))
        if nm in paint1:
            p4 = cv2.resize(paint1[nm].astype(np.uint8), (W4, H4), interpolation=cv2.INTER_NEAREST).astype(bool)
            if nm == "head":                       # the scalp: short dark hair under the hat, inked round its top
                (cx, cy), (rx, ry) = SCALP
                dome = np.zeros((H4, W4), np.uint8)
                cv2.ellipse(dome, (int(cx * K), int(cy * K)), (int(rx * K), int(ry * K)), 0, 180, 360, 1, -1)
                cv2.rectangle(dome, (int((cx - rx) * K), int(cy * K)), (int((cx + rx) * K), int((cy + 14) * K)), 1, -1)
                dome = dome.astype(bool)
                under = dome & (lay[..., 3] < 250)          # never over the face's own pixels
                ring = dome & ~ndimage.binary_erosion(dome, iterations=7)
                a = lay[..., 3:4] / 255.
                hair = np.where(ring[..., None], np.float32([8, 6, 8]), np.float32([30, 20, 24]))
                lay[..., :3] = np.where(under[..., None], lay[..., :3] * a + hair * (1 - a), lay[..., :3])
                lay[..., 3] = np.where(under, 255, lay[..., 3])
                p4 &= ~dome                             # the neck below is inpainted; the dome is done
            own = lay[..., 3] > 200
            lay = fill_hidden(lay, p4, own)
        ys, xs = np.nonzero(lay[..., 3] > 2)
        x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
        pad = 8
        x0, y0, x1, y1 = max(0, x0 - pad), max(0, y0 - pad), min(W4, x1 + pad), min(H4, y1 + pad)
        crop = lay[y0:y1, x0:x1].clip(0, 255).astype(np.uint8)
        Image.fromarray(crop).save(os.path.join(OUT, nm + ".png"))
        meta["parts"][nm] = {"box": [x0, y0, x1 - x0, y1 - y0]}
        print(nm, "box", meta["parts"][nm]["box"], "px", int(m.sum()), flush=True)
    # faces: each reaction's head, only where it differs from the neutral (feathered), boxed
    faces = json.load(open(os.path.join(PLATES, "meta.json")))["faces"]
    hp4 = up_mask(poly_mask(HEAD_POLY, (H1, W1)), (H4, W4), 2)
    meta["faces"] = {}
    for f in faces:
        if f == "neutral":
            continue
        im = rgba(os.path.join(PLATES, f"body_{f}.png"))
        diff = (np.abs(im[..., :3] - neutral[..., :3]).max(-1) > 10) & (hp4 > .5)
        diff = ndimage.binary_dilation(diff, iterations=10)
        diff = ndimage.binary_fill_holes(diff)
        a = cv2.GaussianBlur(diff.astype(np.float32), (0, 0), 5) * hp4
        lay = im.copy()
        lay[..., 3] = im[..., 3] * a
        ys, xs = np.nonzero(lay[..., 3] > 2)
        if not len(xs):
            continue
        x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
        Image.fromarray(lay[y0:y1, x0:x1].clip(0, 255).astype(np.uint8)).save(os.path.join(OUT, f"face_{f}.png"))
        meta["faces"][f] = {"box": [x0, y0, x1 - x0, y1 - y0]}
        print("face", f, meta["faces"][f]["box"], flush=True)
    json.dump(meta, open(os.path.join(OUT, "parts.json"), "w"), indent=1)
    base = art[..., :3] * (art[..., 3:4] / 255.) * .35 + 40
    shown = np.where((dbg.sum(-1) > 0)[..., None], dbg, base)
    Image.fromarray(shown.clip(0, 255).astype(np.uint8)).save(os.path.join(OUT, "_debug.png"))


if __name__ == "__main__":
    import sys
    main("--quick" in sys.argv)
