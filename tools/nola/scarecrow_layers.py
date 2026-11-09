"""Cut the drunk scarecrow into what Blender animates (art/nola-src/scare/):
  pole.png          the bare T-pole and its grass (art/nola-src/pole_plate.png, aligned to the drawing)
  body_<face>.png   the scarecrow without the pole, one per face (neutral + art/nola-src/faces/*), the face
                    redrawn on the same head so the texture swaps cleanly
  meta.json         sizes, the face list
The body keeps every pixel that is not plain pole wood: a pixel inside the pole that matches the plate's wood
(colour within TOL) goes to the pole layer, everything else is the scarecrow (cloth, straw, ropes, the jug, the crow).
usage: python tools/fall/scarecrow_layers.py"""
import glob, json, os
import cv2
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "art", "nola-src")
OUT = os.path.join(SRC, "scare")
TOL = 34
HEAD_BOX = (200, 90, 720, 610)
CROW_X, CROW_Y = 760, 418           # the crow: everything right of x and above y (it perches on the crossbar)          # where head_crop.png was cut from the drawing (x0, y0, x1, y1)


def rgba(p):
    return np.asarray(Image.open(p).convert("RGBA")).astype(np.float32)


def align(moving, fixed, mask=None, mode=cv2.MOTION_AFFINE):
    """ECC-align moving onto fixed (grey, float32) -> the 2x3 warp."""
    warp = np.eye(2, 3, dtype=np.float32)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6)
    try:
        _, warp = cv2.findTransformECC(fixed, moving, warp, mode, crit, mask, 5)
    except cv2.error:
        pass
    return warp


def grey(a):
    g = (a[..., :3] @ np.array([.3, .59, .11], np.float32)) * (a[..., 3] / 255.)
    return g.astype(np.float32)


def warp_rgba(a, warp, size):
    return cv2.warpAffine(a, warp, size, flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderValue=(0, 0, 0, 0))


def main():
    os.makedirs(OUT, exist_ok=True)
    art = rgba(os.path.join(SRC, "clean", "scarecrow.png"))
    H, W = art.shape[:2]
    plate = rgba(os.path.join(SRC, "pole_plate.png"))
    # align the plate to the drawing on the post's top and the crossbar's ends (the parts both show)
    m = np.zeros((H, W), np.uint8)
    m[:150, 430:620] = 1
    m[380:480, 0:230] = 1
    m[380:480, 880:W] = 1
    warp = align(grey(plate), grey(art), m, cv2.MOTION_TRANSLATION)
    plate = warp_rgba(plate, warp, (W, H))
    print("pole warp", np.round(warp, 3).tolist())
    # the body: the scarecrow redrawn without the pole (art/nola-src/body_plate_c.png), aligned on his outline
    body = rgba(os.path.join(SRC, "body_plate_c.png"))
    bw = align(grey(body), grey(art), (art[..., 3] > 128).astype(np.uint8), cv2.MOTION_AFFINE)
    body = warp_rgba(body, bw, (W, H))
    print("body warp", np.round(bw, 4).tolist())
    Image.fromarray(plate.clip(0, 255).astype(np.uint8)).save(os.path.join(OUT, "pole.png"))
    faces = ["neutral"]
    Image.fromarray(body.clip(0, 255).astype(np.uint8)).save(os.path.join(OUT, "body_neutral.png"))
    # faces: align each redrawn head onto the drawing's head, paste only what changed (feathered)
    x0, y0, x1, y1 = HEAD_BOX
    hs = x1 - x0
    head = cv2.resize(body[y0:y1, x0:x1], (1024, 1024), interpolation=cv2.INTER_CUBIC)
    face_zone = np.zeros((1024, 1024), np.float32)
    cv2.ellipse(face_zone, (560, 560), (250, 230), -8, 0, 360, 1, -1)   # the burlap face, under the hat brim
    for p in sorted(glob.glob(os.path.join(SRC, "faces", "*.png"))):
        name = os.path.splitext(os.path.basename(p))[0]
        f = rgba(p)
        fw = align(grey(f), grey(head), (face_zone < .5).astype(np.uint8))   # align on the hat + outline, not the face
        f = warp_rgba(f, fw, (1024, 1024))
        changed = (np.abs(f[..., :3] - head[..., :3]).max(-1) > 28) & (face_zone > 0)
        changed = ndimage.binary_closing(changed, iterations=6)
        changed = ndimage.binary_dilation(changed, iterations=10)
        changed = ndimage.binary_fill_holes(changed)
        a = cv2.GaussianBlur(changed.astype(np.float32), (0, 0), 6) * face_zone
        a = cv2.GaussianBlur(a, (0, 0), 3)
        small_f = cv2.resize(f, (hs, hs), interpolation=cv2.INTER_AREA)
        small_a = cv2.resize(a, (hs, hs), interpolation=cv2.INTER_AREA)[..., None]
        out = body.copy()
        reg = out[y0:y1, x0:x1]
        reg[..., :3] = reg[..., :3] * (1 - small_a) + small_f[..., :3] * small_a
        reg[..., 3] = np.maximum(reg[..., 3], small_f[..., 3] * small_a[..., 0])
        Image.fromarray(out.clip(0, 255).astype(np.uint8)).save(os.path.join(OUT, f"body_{name}.png"))
        faces.append(name)
        print("face", name, "warp", np.round(fw, 3).tolist(), "changed px", int(changed.sum()))
    # the crow is its own rigid layer (it hops and flies off the bar): cut it out of every body texture
    crow = None
    for name in faces:
        path = os.path.join(OUT, f"body_{name}.png")
        im = rgba(path)
        zone = np.zeros((H, W), bool)
        zone[:CROW_Y, CROW_X:] = True
        if crow is None:
            crow = np.zeros_like(im)
            crow[zone] = im[zone]
            Image.fromarray(crow.clip(0, 255).astype(np.uint8)).save(os.path.join(OUT, "crow.png"))
        im[zone, 3] = 0
        Image.fromarray(im.clip(0, 255).astype(np.uint8)).save(path)
    json.dump({"size": [W, H], "faces": faces}, open(os.path.join(OUT, "meta.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
