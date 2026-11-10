"""Doc redrawn piece by piece at a higher quality (owner, 2026-11-09: "regenerate our character with openrouter as
well in a better quality"), for the live rig.

The first Doc was ONE 1024 x 1536 drawing, enlarged four times by Real-ESRGAN and cut up: his head was 140 px wide
before the enlargement, his hands smaller, and whatever one piece hid of another (the skull under the hat, the
shoulder inside the coat, the thigh under the tails) was smeared in by OpenCV. Here every piece of the rig is drawn
on its OWN canvas by the image model, from the old piece as its layout and the whole figure as its style: the head
alone fills 1024 x 1536 (five times the detail), and the model draws the hidden parts as real drawing - his hair
under the hat, the hat's whole brim, a round cap on each shoulder, the trousers up to the waist.

  gen  [part,..]   art/nola-src/doc_regen/<part>_layout.png (the old piece on the canvas the model is given) and
                   <part>_raw.png (what it drew), one call each (OpenRouter, the key never printed)
  faces [name,..]  the seven reaction faces, each the new head redrawn with only its expression changed
  fit              each raw piece laid over its old one (ECC), cleaned, scaled to the plates' 4K scale ->
                   art/nola-src/doc_parts/ (<part>.png, face_<name>.png, parts.json), the old set kept in
                   doc_parts_v1/; pieces not redrawn (coat_back, wisp) are carried over
  sheet            art/nola-src/doc_regen/_sheet.png: old against new, to look at
usage: python tools/nola/doc_regen.py gen|faces|fit|sheet [names]"""
import json, os, shutil, sys
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import orimg

ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, "art", "nola-src")
OLD = os.path.join(SRC, "doc_parts_v1")           # the first cut (made by doc_parts.py), kept as the layout
NEW = os.path.join(SRC, "doc_parts")
WORK = os.path.join(SRC, "doc_regen")
FULL = os.path.join(SRC, "4k", "doc.png")
CANVAS = {"2:3": (1024, 1536), "3:2": (1536, 1024), "1:1": (1024, 1024)}
MARGIN = .07

STYLE = ("STYLE - match image 1 exactly: a modern adult-animation TV cartoon cel (Rick and Morty-like): confident even "
         "black ink outlines of the same weight as in image 2, flat solid colour fills with ONE hard-edged darker shade "
         "tone, a thin warm ORANGE rim light along the edges that face the viewer's left and a thin GREEN rim light "
         "along the edges that face the viewer's right. Crisp, sharp, clean vector-quality linework at high resolution: "
         "no blur, no smudges, no fuzzy or ragged edges, no painterly texture, no gradients, no photo-realism. "
         "Transparent background. Draw ONLY this one piece: no other body parts, no other characters, no text, no "
         "ground, no shadow, no border.")
HEADER = ("Image 1 is the whole character (a tall thin cartoon voodoo showman) for style and colour. Image 2 is ONE "
          "piece of him, cut out of a low-resolution enlargement so it can be animated as a puppet; it is soft and "
          "smeared. REDRAW image 2 cleanly at high quality: the same piece, the same shapes, the same pose and angle, "
          "the SAME SIZE AND POSITION on the canvas (it must lie exactly over image 2), the same colours. ")
PARTS = {
    "head": ("2:3", "The piece: his HEAD AND NECK ONLY, WITHOUT his hat. The same long narrow brown face, the same "
             "expression: a wide sly grin with one gold tooth, big round white eyes with small dot pupils, heavy black "
             "eyebrows, a thin curled pencil moustache, the ear and black sideburn on the viewer's right. Image 2 still "
             "has scraps of the hat on top of the head (a black dome, a strip of purple band, a bit of bone): REMOVE "
             "them and draw the whole top of his head that the hat used to hide - a smooth rounded skull covered in "
             "short flat black hair with a neat hairline across the forehead. At the bottom, replace the blurry patch: "
             "draw the neck running straight on down, plain brown, with the two small white shirt-collar points at its "
             "sides, ending in a flat cut."),
    "hat": ("3:2", "The piece: his TOP HAT ONLY, exactly as it is in image 2 (which is cropped from the figure just "
            "under the hat's brim): a tall battered black stovepipe hat with a little white tear in the crown, a small "
            "stitched X, a purple band, a bone charm and a black crow feather with a green sheen tucked into the band, "
            "and its brim - a thin, slightly curved black brim seen from the FRONT at eye level, drooping a little at "
            "both ends, exactly the shape it has in image 2. We do NOT see under the brim or into the hat: no oval "
            "opening, no underside. If a sliver of brown forehead shows under the brim in image 2, do not draw it: "
            "finish the brim's lower edge as one clean inked curve. No head, no face, no hair."),
    "body": ("2:3", "The piece: his TORSO AND TAILCOAT ONLY, with NO head, NO arms or hands and NO legs: the plum-purple "
             "tailcoat with wide lapels and two long split tails with ragged pointed hems, the black-and-violet striped "
             "waistcoat with gold buttons and a gold watch chain, the ruffled cream cravat with a green oval gem brooch, "
             "the open collar at the top (an empty dark neck hole, no neck). Each SHOULDER ends in a smooth ROUNDED cap "
             "of purple coat cloth where the sleeve was taken off (no stump of an arm hanging from it). The gap between "
             "the two coat tails, below the waistcoat, stays EMPTY and transparent exactly as in image 2 (the legs are "
             "another piece)."),
    "arm_r": ("3:2", "The piece: ONE ARM ONLY, the arm on the viewer's right: the purple coat sleeve, bent at the elbow "
              "exactly as in image 2, with its green rim light, a gold cuff button and a cream lace ruffle at the "
              "wrist, and the big long-fingered brown hand held open, palm up (a thumb and three long fingers, exactly "
              "posed as in image 2). The sleeve was cut off at the shoulder: COMPLETE its top end as a smooth rounded "
              "shoulder (a full round cap of purple cloth, slightly bigger than the sleeve is wide). The hand is EMPTY: "
              "no smoke, no flame, nothing in it."),
    "arm_l": ("2:3", "The piece: ONE ARM ONLY, the arm on the viewer's left: the purple coat sleeve with its orange rim "
              "light, slightly bent exactly as in image 2, a gold cuff button and a cream lace ruffle at the wrist, and "
              "the big brown hand with its long fingers draped downward as if resting on the knob of a cane - keep the "
              "empty gap between the fingers and the thumb exactly as in image 2 (the cane is another piece: do NOT draw "
              "a cane or a skull). The sleeve was cut off at the shoulder: COMPLETE its top end as a smooth rounded "
              "shoulder (a full round cap of purple cloth, slightly bigger than the sleeve is wide)."),
    "leg_l": ("2:3", "The piece: ONE LEG ONLY, the leg on the viewer's left: a long narrow black pinstriped trouser leg, "
              "angled exactly as in image 2, a white spat with small buttons and a long pointed black shoe pointing to "
              "the viewer's left. The top of the leg in image 2 is a blurry smear (the coat used to hide it): REPLACE it "
              "- draw the whole thigh as clean pinstriped trouser right up to a flat top edge at the hip."),
    "leg_r": ("2:3", "The piece: ONE LEG ONLY, the leg on the viewer's right: a long narrow black pinstriped trouser "
              "leg, angled exactly as in image 2, a white spat with small buttons and a long pointed black shoe pointing "
              "to the viewer's right. The top of the leg in image 2 is a blurry smear (the coat used to hide it): REPLACE "
              "it - draw the whole thigh as clean pinstriped trouser right up to a flat top edge at the hip."),
    "cane": ("2:3", "The piece: his WALKING CANE ONLY, standing upright exactly as in image 2: a slim black lacquered "
             "shaft with a gold ferrule at the bottom tip, a gold collar under the knob, and the knob itself - a small "
             "silver human skull with purple gem eyes. No hand on it."),
}
FACES = {
    "blink": "both eyes fully CLOSED in a slow smug blink (curved closed eyelid lines), the same sly grin with the gold tooth",
    "laugh": "a big villainous LAUGH: mouth wide open showing teeth and the gold tooth, eyes squeezed into happy crescents, eyebrows up",
    "smug": "a smug sly SMIRK to one side, one eyebrow raised high, eyes half-lidded and scheming",
    "cheer": "ecstatic and amazed: a huge toothy grin with the gold tooth, eyes wide open with tiny glowing green dot pupils, eyebrows raised high",
    "shock": "SHOCKED: eyes popped wide open and bulging, tiny pupils, mouth a small round O, eyebrows raised high, moustache ends sprung up",
    "sad": "SULKING and annoyed: droopy half-closed eyes looking down to the side, mouth a wobbly frown, moustache drooping",
    "wink": "a cheeky WINK: the eye on the viewer's left closed in a curved line, the other eye open, a confident lopsided grin with the gold tooth",
}


def rgba(p):
    return np.asarray(Image.open(p).convert("RGBA")).astype(np.float32)


HAT_BOX = (372, 0, 684, 207)                       # art px: the hat on the first drawing, down to its brim's lower edge
K = 4096 / 1536.0                                 # plate px per art px


def layout(part):
    """The old piece on the model's canvas: where it sits (scale s canvas px per plate px, offset), and the picture."""
    meta = json.load(open(os.path.join(OLD, "parts.json")))
    if part == "hat":                                 # the whole hat, off the first drawing (the old cut gave the
        x0, y0, x1, y1 = [round(v * K) for v in HAT_BOX]   # middle of its brim to the head)
        im = Image.open(FULL).convert("RGBA").crop((x0, y0, x1, y1))
        meta["parts"]["hat"] = {"box": [x0, y0, x1 - x0, y1 - y0]}
    else:
        im = Image.open(os.path.join(OLD, part + ".png")).convert("RGBA")
    cw, ch = CANVAS[PARTS[part][0]]
    s = min(cw * (1 - 2 * MARGIN) / im.width, ch * (1 - 2 * MARGIN) / im.height)
    w, h = round(im.width * s), round(im.height * s)
    ox, oy = (cw - w) // 2, (ch - h) // 2
    can = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    can.paste(im.resize((w, h), Image.LANCZOS), (ox, oy))
    return can, {"s": s, "ox": ox, "oy": oy, "box": meta["parts"][part]["box"], "canvas": [cw, ch]}


def full_ref():
    p = os.path.join(WORK, "_full.png")
    if not os.path.exists(p):
        im = Image.open(FULL).convert("RGBA")
        im.resize((1024, round(1024 * im.height / im.width)), Image.LANCZOS).save(p)
    return p


def gen(part):
    os.makedirs(WORK, exist_ok=True)
    can, info = layout(part)
    lp = os.path.join(WORK, part + "_layout.png")
    can.save(lp)
    json.dump(info, open(os.path.join(WORK, part + "_layout.json"), "w"))
    try:
        _, cost = orimg.generate(os.path.join(WORK, part + "_raw.png"), HEADER + PARTS[part][1] + " " + STYLE,
                                 aspect=PARTS[part][0], refs=[full_ref(), lp])
        return f"OK {part} {cost}"
    except RuntimeError as e:
        return f"FAIL {part} {e}"


def face(name):
    src = os.path.join(WORK, "head_raw.png")           # the new head, as the model drew it
    p = (f"Redraw the attached image EXACTLY - the same cartoon man's head and neck, the same long narrow face, the "
         f"same short black hair, the same curled pencil moustache, the same outlines, the same colours, the same "
         f"position and size on the canvas, transparent background - changing ONLY the facial expression (eyes, "
         f"eyebrows, mouth) to: {FACES[name]}. Crisp clean cartoon linework, flat cel shading, no other changes, no "
         f"other characters, no text.")
    try:
        _, cost = orimg.generate(os.path.join(WORK, f"face_{name}_raw.png"), p, aspect="2:3", refs=[src])
        return f"OK face {name} {cost}"
    except RuntimeError as e:
        return f"FAIL face {name} {e}"


def over(im, bg=128.0):
    """Grey of an RGBA picture laid on a flat grey (uint8), for matching."""
    a = im[..., 3:4] / 255.
    return ((im[..., :3] * a + bg * (1 - a)) @ np.float32([.3, .59, .11])).clip(0, 255).astype(np.uint8)


def similar(raw, lay):
    """The similarity (scale, turn, shift) taking the model's drawing onto the old piece on the same canvas: SIFT
    features matched, RANSAC. 2x3, raw px -> layout px."""
    sift = cv2.SIFT_create(nfeatures=6000, contrastThreshold=.02)
    g0, g1 = over(raw), over(lay)
    k0, d0 = sift.detectAndCompute(g0, (raw[..., 3] > 40).astype(np.uint8) * 255)
    k1, d1 = sift.detectAndCompute(g1, (lay[..., 3] > 40).astype(np.uint8) * 255)
    if d0 is None or d1 is None or len(k0) < 8 or len(k1) < 8:
        return None, 0, 0
    bf = cv2.BFMatcher(cv2.NORM_L2)
    good = [m for m, n in bf.knnMatch(d0, d1, k=2) if m.distance < .8 * n.distance]
    if len(good) < 8:
        return None, len(good), 0
    src = np.float32([k0[m.queryIdx].pt for m in good])
    dst = np.float32([k1[m.trainIdx].pt for m in good])
    M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=6, maxIters=8000, confidence=.999)
    n_in = int(inl.sum()) if inl is not None else 0
    return M, len(good), n_in


def bbox_fit(raw, lay):
    """The fallback: lay the drawing's bounding box on the old piece's."""
    def bb(a):
        ys, xs = np.nonzero(a[..., 3] > 60)
        return xs.min(), ys.min(), xs.max(), ys.max()
    x0, y0, x1, y1 = bb(raw)
    u0, v0, u1, v1 = bb(lay)
    k = (v1 - v0) / (y1 - y0) if (y1 - y0) > 2 * (x1 - x0) else ((u1 - u0) / (x1 - x0) + (v1 - v0) / (y1 - y0)) / 2   # a tall piece: by its ends
    return np.float32([[k, 0, (u0 + u1) / 2 - k * (x0 + x1) / 2], [0, k, (v0 + v1) / 2 - k * (y0 + y1) / 2]])


# Where the fit must hold: the old piece is only trusted inside this window of its canvas (fractions), because the
# model was asked to CHANGE the rest (the scraps of hat on the head, the bitten brim, the smeared thigh)
TRUST = {"head": (0, .2, 1, .78)}
# pinstripes all look alike and a cane is a line: these are laid box on box (their ends are what matter)
BBOX = ("leg_l", "leg_r", "cane")
# a leg's two ends, art px: the middle of its flat top (inside the hips) and of its trouser hem over the spat. The
# model draws each leg at its own slant: it is sheared (never turned: the sole stays flat) until both ends sit here
LEG_ENDS = {"leg_l": ((480, 652), (372, 1384)), "leg_r": ((540, 652), (650, 1384))}
NECK_HOLE = (500, 366)                            # art px: inside the collar, where the model painted a dark hole
# a piece the model drew to a different plan gets a hand-set fit on top of the automatic one: (scale, dx, dy) in
# layout-canvas px, about the canvas's middle
NUDGE = {}


def tidy(im):
    """The model's transparent pictures carry a faint haze round the ink: only what is on or right by the solid
    drawing keeps its alpha."""
    a = im[..., 3]
    near = ndimage.binary_dilation(a > 128, iterations=3)
    im[..., 3] = np.where(near, a, 0)
    return im


def fit_part(part):
    raw = rgba(os.path.join(WORK, part + "_raw.png"))
    lay_im, info = layout(part)
    lay = np.asarray(lay_im).astype(np.float32)
    cw, ch = info["canvas"]
    if raw.shape[1] != cw:
        raw = cv2.resize(raw, (cw, ch), interpolation=cv2.INTER_AREA)
    raw = tidy(raw)
    trusted = lay.copy()
    if part in TRUST:
        x0, y0, x1, y1 = TRUST[part]
        keep = np.zeros(lay.shape[:2], bool)
        keep[int(y0 * ch):int(y1 * ch), int(x0 * cw):int(x1 * cw)] = True
        trusted[~keep, 3] = 0
    M, n_good, n_in = (None, 0, 0) if part in BBOX else similar(raw, trusted)
    how = f"sift {n_in}/{n_good}"
    if M is None or n_in < 12 or not (.4 < float(np.hypot(M[0][0], M[1][0])) < 2.5):
        M, how = bbox_fit(raw, trusted), f"bbox (sift {n_in}/{n_good})"
    M = np.float32(M)
    if part in NUDGE:
        k, dx, dy = NUDGE[part]
        c = np.float32([cw / 2, ch / 2])
        M[:, :2] *= k
        M[:, 2] = (M[:, 2] - c) * k + c + np.float32([dx, dy])
    scale = float(np.hypot(M[0, 0], M[1, 0]))
    turn = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
    # raw px -> plate px: through the layout canvas, off its offset, over its scale, onto the old box
    s, ox, oy = info["s"], info["ox"], info["oy"]
    bx, by = info["box"][:2]
    P = np.float32([[M[0, 0] / s, M[0, 1] / s, (M[0, 2] - ox) / s + bx], [M[1, 0] / s, M[1, 1] / s, (M[1, 2] - oy) / s + by]])
    ys, xs = np.nonzero(raw[..., 3] > 8)
    if part in LEG_ENDS:
        (tx, ty), (ax, ay) = [(x * K, y * K) for x, y in LEG_ENDS[part]]
        solid = raw[..., 3] > 128

        def mid_at(yp):                                # the leg's middle on the plate row yp, as fitted so far
            yr = int(round((yp - P[1, 2]) / P[1, 1]))
            row = np.nonzero(solid[max(0, min(solid.shape[0] - 1, yr))])[0]
            return (row.min() + row.max()) / 2 * P[0, 0] + P[0, 2]
        top_y = ys.min() * P[1, 1] + P[1, 2]
        x_top, x_ank = mid_at(top_y + 6 * K), mid_at(ay)
        b = ((tx - x_top) - (ax - x_ank)) / ((top_y + 6 * K) - ay)      # shear: px sideways per px up the leg
        a = (ax - x_ank) - b * ay
        P = np.float32([[P[0, 0] + b * P[1, 0], P[0, 1] + b * P[1, 1], P[0, 2] + b * P[1, 2] + a], P[1]])
        how += f"  sheared {b:+.3f}"
    corners = np.float32([[xs.min(), ys.min(), 1], [xs.max(), ys.min(), 1], [xs.min(), ys.max(), 1], [xs.max(), ys.max(), 1]])
    pc = corners @ P.T
    pad = 8
    x0, y0 = int(np.floor(pc[:, 0].min())) - pad, int(np.floor(pc[:, 1].min())) - pad
    x1, y1 = int(np.ceil(pc[:, 0].max())) + pad, int(np.ceil(pc[:, 1].max())) + pad
    W, H = x1 - x0, y1 - y0
    json.dump({"P": P.tolist(), "canvas": [cw, ch]}, open(os.path.join(WORK, part + "_fit.json"), "w"))
    SS = 2                                             # drawn at twice the plate's size, then averaged down
    Q = P.copy()
    Q[:, 2] -= [x0, y0]
    Q *= SS
    pm = raw.copy()
    pm[..., :3] *= pm[..., 3:4] / 255.                  # premultiplied: no dark fringe from the transparent px
    big = cv2.warpAffine(pm, Q, (W * SS, H * SS), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0, 0))
    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    al = out[..., 3:4].clip(0, 255)
    out[..., :3] = np.where(al > 1, out[..., :3] * 255. / np.maximum(al, 1), 0)
    out = out.clip(0, 255)
    if part == "body":                                 # the neck shows through the collar: the dark hole goes
        hx, hy = int(NECK_HOLE[0] * K - x0), int(NECK_HOLE[1] * K - y0)
        dark = (out[..., :3].max(-1) < 78) & (out[..., 3] > 40)
        yy, xx = np.mgrid[0:H, 0:W]
        win = (abs(xx - hx) < 40 * K) & (yy > hy - 30 * K) & (yy < hy + 34 * K)
        blob = ndimage.binary_opening(dark & win, iterations=7)       # the hole, without the ink lines that touch it
        lab, _ = ndimage.label(blob)
        if lab[hy, hx]:
            hole = ndimage.binary_dilation(lab == lab[hy, hx], iterations=9) & dark & win
            soft = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 1.2)
            out[..., 3] *= 1 - soft
            how += f"  neck hole {int(hole.sum())} px"
    note = f"{how}  scale {scale:.3f} turn {turn:+.2f} deg  drawn at {1 / (scale / s):.2f} px per plate px"
    return out, [x0, y0, W, H], info["box"], note


def fit(names):
    meta = json.load(open(os.path.join(OLD, "parts.json")))
    np_ = os.path.join(NEW, "parts.json")
    out_meta = json.load(open(np_)) if os.path.exists(np_) else json.loads(json.dumps(meta))
    for part in names:
        if not os.path.exists(os.path.join(WORK, part + "_raw.png")):
            continue
        out, box, obox, note = fit_part(part)
        Image.fromarray(out.astype(np.uint8), "RGBA").save(os.path.join(NEW, part + ".png"))
        out_meta["parts"][part] = {"box": box}
        print(f"{part:6s} box {box} (was {obox})  {note}", flush=True)
    json.dump(out_meta, open(np_, "w"), indent=1)


def to_plate(im, P, pad=8):
    """A canvas picture (float RGBA) through P onto the plate: the crop round its ink, and that crop's box."""
    ys, xs = np.nonzero(im[..., 3] > 8)
    corners = np.float32([[xs.min(), ys.min(), 1], [xs.max(), ys.min(), 1], [xs.min(), ys.max(), 1], [xs.max(), ys.max(), 1]])
    pc = corners @ P.T
    x0, y0 = int(np.floor(pc[:, 0].min())) - pad, int(np.floor(pc[:, 1].min())) - pad
    x1, y1 = int(np.ceil(pc[:, 0].max())) + pad, int(np.ceil(pc[:, 1].max())) + pad
    W, H = x1 - x0, y1 - y0
    Q = P.copy()
    Q[:, 2] -= [x0, y0]
    Q *= 2
    pm = im.copy()
    pm[..., :3] *= pm[..., 3:4] / 255.
    big = cv2.warpAffine(pm, Q, (W * 2, H * 2), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0, 0))
    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    al = out[..., 3:4].clip(0, 255)
    out[..., :3] = np.where(al > 1, out[..., :3] * 255. / np.maximum(al, 1), 0)
    return out.clip(0, 255), [x0, y0, W, H]


def fit_faces(names):
    """Each reaction: the model's redraw of the head laid back over the head it was made from (ECC) and put on the
    plate with the head's own fit - a whole head each (face_<name>.png), shown instead of the neutral one."""
    head = tidy(rgba(os.path.join(WORK, "head_raw.png")))
    info = json.load(open(os.path.join(WORK, "head_fit.json")))
    P = np.float32(info["P"])
    g_head = over(head).astype(np.float32)
    np_ = os.path.join(NEW, "parts.json")
    meta = json.load(open(np_))
    meta["faces"] = {}
    for f in names:
        fp = os.path.join(WORK, f"face_{f}_raw.png")
        if not os.path.exists(fp):
            continue
        im = tidy(rgba(fp))
        if im.shape[:2] != head.shape[:2]:
            im = cv2.resize(im, (head.shape[1], head.shape[0]), interpolation=cv2.INTER_AREA)
        warp = np.eye(2, 3, dtype=np.float32)
        try:                                          # a redraw sits a pixel or two off: lay it back on the head
            _, warp = cv2.findTransformECC(g_head, over(im).astype(np.float32), warp, cv2.MOTION_EUCLIDEAN,
                                           (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-6), None, 5)
        except cv2.error:
            pass
        im = cv2.warpAffine(im, warp, (head.shape[1], head.shape[0]), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                            borderValue=(0, 0, 0, 0))
        # the whole head is kept, not a patch over the neutral one: a closed eye is smaller than the open eye that
        # bulges past his cheek, and a patch left a sliver of the open eye showing beside it. The game shows one head
        # at a time.
        lay = im
        diff = np.abs(over(im).astype(np.float32) - g_head) > 40
        out, box = to_plate(lay, P)
        Image.fromarray(out.astype(np.uint8), "RGBA").save(os.path.join(NEW, f"face_{f}.png"))
        meta["faces"][f] = {"box": box}
        print(f"face {f:6s} box {box}  shift {warp[0, 2]:+.1f},{warp[1, 2]:+.1f} px  changed {100 * diff.mean():.1f}% of the canvas", flush=True)
    json.dump(meta, open(np_, "w"), indent=1)


def figure(d, skip=("wisp",)):
    """The whole figure put together from a set's pieces, on the 4K plate."""
    meta = json.load(open(os.path.join(d, "parts.json")))
    Wp, Hp = meta["size"]
    can = Image.new("RGBA", (Wp, Hp), (0, 0, 0, 0))
    for nm in meta["order"]:
        if nm in skip:
            continue
        im = Image.open(os.path.join(d, nm + ".png")).convert("RGBA")
        x, y = meta["parts"][nm]["box"][:2]
        tmp = Image.new("RGBA", (Wp, Hp), (0, 0, 0, 0))
        tmp.paste(im, (x, y))
        can = Image.alpha_composite(can, tmp)
    return can


def sheet(scale=.42):
    """Old against new, side by side, to look at."""
    a, b = figure(OLD), figure(NEW)
    w, h = round(a.width * scale), round(a.height * scale)
    sh = Image.new("RGB", (w * 2, h), (70, 100, 80))
    for k, im in enumerate((a, b)):
        bg = Image.new("RGBA", im.size, (70, 100, 80, 255))
        bg.alpha_composite(im)
        sh.paste(bg.convert("RGB").resize((w, h), Image.LANCZOS), (k * w, 0))
    sh.save(os.path.join(WORK, "_sheet.png"))
    b.save(os.path.join(WORK, "_figure.png"))
    print("sheet", sh.size)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    names = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    if cmd == "gen":
        if not os.path.isdir(OLD):
            shutil.copytree(NEW, OLD)
        with ThreadPoolExecutor(8) as ex:
            for r in ex.map(gen, names or list(PARTS)):
                print(r, flush=True)
    elif cmd == "faces":
        with ThreadPoolExecutor(7) as ex:
            for r in ex.map(face, names or list(FACES)):
                print(r, flush=True)
    elif cmd == "fit":
        fit(names or list(PARTS))
        sheet()
    elif cmd == "fitfaces":
        fit_faces(names or list(FACES))
    elif cmd == "sheet":
        sheet()
    else:
        print(__doc__)
