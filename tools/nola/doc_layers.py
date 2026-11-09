"""Cut the voodoo showman (Doc) into what Blender animates -> art/nola-src/doc/ (4K: 2731 x 4096):
  body_<face>.png   the figure without the cane and the palm wisp, one per face (neutral + art/nola-src/faces/*),
                    each face aligned on the hat and outline and pasted only where it changed (feathered)
  cane.png          the skull-topped cane (rigid; it sits BEHIND the body, so the fingers wrap round its knob)
  wisp.png          the green magic smoke over his palm (Blender flickers and re-shapes it)
  meta.json         {"size": [W, H], "base": [1024, 1536], "faces": [...]}
Coordinates below are in the 1024 x 1536 drawing (art/nola-src/doc_v1.png); the plates come out 4x via
tools/nola/upscale4k.py's Real-ESRGAN pass and are resized to 4096 tall.
usage: python tools/nola/doc_layers.py"""
import glob, json, os, sys
import cv2
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import upscale4k

ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, "art", "nola-src")
OUT = os.path.join(SRC, "doc")
TMP = os.path.join(SRC, "doc_1k")
HEAD_BOX = (240, 0, 760, 520)            # where head_crop.png was cut from the drawing
SHAFT = (158, 872, 216, 1510)            # the cane's shaft, x0 y0 x1 y1
KNOB = ((186, 834), (41, 55))            # the skull knob + gold collar: centre, radii
WISP = (785, 205, 910, 445)              # the green smoke over the open palm
FULL = (2731, 4096)


def rgba(p):
    return np.asarray(Image.open(p).convert("RGBA")).astype(np.float32)


def grey(a):
    return ((a[..., :3] @ np.array([.3, .59, .11], np.float32)) * (a[..., 3] / 255.)).astype(np.float32)


def align(moving, fixed, mask=None):
    warp = np.eye(2, 3, dtype=np.float32)
    try:
        _, warp = cv2.findTransformECC(fixed, moving, warp, cv2.MOTION_AFFINE,
                                       (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), mask, 5)
    except cv2.error:
        pass
    return warp


def warp_rgba(a, warp, size):
    return cv2.warpAffine(a, warp, size, flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderValue=(0, 0, 0, 0))


def skin(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (r > g + 8) & (g > b) & (r > 50) & (r < 215) & ((r - b) > 30)


def cane_mask(a):
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    shaft = np.zeros((H, W), bool)
    x0, y0, x1, y1 = SHAFT
    shaft[y0:y1, x0:x1] = True
    (cx, cy), (rx, ry) = KNOB
    knob = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
    # the fingers over the knob stay on the body, with their ink line (a few px round the skin); everything else
    # in the knob's oval - silver, gold, its outline, its rim light - is cane
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    sk = (r > g + 14) & (g > b + 4) & (r > 70) & (r < 210) & ((r - b) > .3 * r) & (a[..., 3] > 128)
    sk = ndimage.binary_opening(sk, iterations=1)
    keep = ndimage.binary_dilation(sk, iterations=3) | ((a[..., :3].min(-1) > 200) & (yy < 800))
    m = ((shaft & (yy > 858)) | (knob & ~keep)) & (a[..., 3] > 0)
    return m


def wisp_mask(a):
    H, W = a.shape[:2]
    x0, y0, x1, y1 = WISP
    m = np.zeros((H, W), bool)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    green = (g > r + 25) & (g > b + 15) & (a[..., 3] > 8)
    m[y0:y1, x0:x1] = green[y0:y1, x0:x1]
    return ndimage.binary_dilation(m, iterations=2) & (a[..., 3] > 0) & ~skin(a)


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    art = rgba(os.path.join(SRC, "clean", "doc_v1.png"))
    H, W = art.shape[:2]
    cm, wm = cane_mask(art), wisp_mask(art)
    for name, m in (("cane", cm), ("wisp", wm)):
        lay = art.copy()
        lay[~m, 3] = 0
        Image.fromarray(lay.clip(0, 255).astype(np.uint8)).save(os.path.join(TMP, name + ".png"))
    body = art.copy()
    body[cm | wm, 3] = 0
    faces = {"neutral": body}
    x0, y0, x1, y1 = HEAD_BOX
    hs = x1 - x0
    head = cv2.resize(body[y0:y1, x0:x1], (1024, 1024), interpolation=cv2.INTER_CUBIC)
    face_zone = np.zeros((1024, 1024), np.float32)
    cv2.ellipse(face_zone, (455, 530), (215, 185), 0, 0, 360, 1, -1)    # brows, eyes, nose, moustache, mouth, chin
    for p in sorted(glob.glob(os.path.join(SRC, "faces", "*.png"))):
        name = os.path.splitext(os.path.basename(p))[0]
        f = rgba(p)
        fw = align(grey(f), grey(head), (face_zone < .5).astype(np.uint8))   # on the hat + collar, not the face
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
        faces[name] = out
        print("face", name, "warp", np.round(fw, 3).tolist(), "changed px", int(changed.sum()), flush=True)
    for name, im in faces.items():
        Image.fromarray(im.clip(0, 255).astype(np.uint8)).save(os.path.join(TMP, f"body_{name}.png"))
    # 4K: every plate through the same Real-ESRGAN pass as the rest of the art, then exactly FULL
    names = [f"body_{n}" for n in faces] + ["cane", "wisp"]
    for n in names:
        im = Image.open(os.path.join(TMP, n + ".png")).convert("RGBA")
        upscale4k.up4(im, FULL).save(os.path.join(OUT, n + ".png"))
        print("4k", n, flush=True)
    json.dump({"size": list(FULL), "base": [W, H], "faces": list(faces)}, open(os.path.join(OUT, "meta.json"), "w"),
              indent=1)


if __name__ == "__main__":
    main()
