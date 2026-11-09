"""QA of Doc's rig renders (art/blender/chars/doc_rig/renders/<clip>/, from tools/nola/blender/doc_rig.py render):
  holes   new see-through gaps inside his silhouette that the rest pose does not have (a seam opening at a shoulder,
          the collar, a knee, under the hat) - the area of the biggest, per clip and frame
  feet    the soles' lowest row on every frame (planted = it never moves, except on a toe tap)
  edges   any opaque pixel on the render's border (something swung out of the frame)
  loop    the idle's last frame against its first (a loop that closes)
  zoom    a contact sheet per clip: each clip's 3 most-moved frames, cropped at every joint and enlarged, to look at
usage: python tools/nola/qa_doc_rig.py   -> art/blender/chars/doc_rig/qa/<clip>.png + a report"""
import glob, json, os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REN = os.path.join(ROOT, "art", "blender", "chars", "doc_rig", "renders")
RIG = os.path.join(ROOT, "art", "blender", "chars", "doc_rig", "rig")
OUT = os.path.join(ROOT, "art", "blender", "chars", "doc_rig", "qa")
S = 1080 / 17.6 / 100                  # render px per art px (ortho 17.6 units over 1080 px)
CY = 768 + 30                          # the art y at the render's centre (the camera sits 0.3 units low)
# each joint crop rides its bone (through the exported rig's per-frame transforms), so it stays on the joint
JOINTS = {"shoulder L": ((392, 428), "upper_l"), "elbow L": ((312, 652), "fore_l"), "cane hand": ((200, 800), "hand_l"),
          "shoulder R": ((606, 440), "upper_r"), "elbow R": ((684, 652), "fore_r"), "open hand": ((880, 450), "hand_r"),
          "neck": ((500, 372), "neck"), "hat": ((490, 150), "hat"), "hips": ((512, 700), "hips"),
          "tail L": ((380, 980), "tail_l2"), "tail R": ((650, 980), "tail_r2"), "knee L": ((414, 1060), "shin_l"),
          "knee R": ((606, 1060), "shin_r"), "foot L": ((330, 1460), "foot_l"), "foot R": ((690, 1460), "foot_r")}
SEAM = 3000                            # a new enclosed gap smaller than this (render px) is a seam opening; bigger
                                       # ones are background closed in by a limb (the arm, the cane and a leg)
R = 70                                 # half-size of a joint crop, art px


def rp(x, y, W=800, H=1080):
    return (x - 512) * S + W / 2, (y - CY) * S + H / 2


def load(p):
    return np.asarray(Image.open(p).convert("RGBA")).astype(np.float32)


def holes(alpha):
    m = alpha > 128
    return ndimage.binary_fill_holes(m) & ~m


def main():
    os.makedirs(OUT, exist_ok=True)
    clips = sorted(d for d in os.listdir(REN) if os.path.isdir(os.path.join(REN, d)))
    rest = load(sorted(glob.glob(os.path.join(REN, "idle", "*.png")))[0])
    rest_holes = ndimage.binary_dilation(holes(rest[..., 3]), iterations=3)
    rig = json.load(open(os.path.join(RIG, "rig.json")))
    B = len(rig["bones"])
    report = []
    for c in clips:
        fs = sorted(glob.glob(os.path.join(REN, c, "*.png")))
        frames = [load(f) for f in fs]
        worst_hole, worst_at, soles, edge, moved = 0, -1, [], 0, []
        for i, a in enumerate(frames):
            al = a[..., 3]
            h = holes(al) & ~rest_holes
            lab, n = ndimage.label(h)
            if n:
                sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
                seams = sizes[sizes < SEAM]
                big = int(seams.max()) if len(seams) else 0
                if big > worst_hole:
                    worst_hole, worst_at = big, i
            rows = np.nonzero((al > 128).any(1))[0]
            soles.append(int(rows[-1]) if len(rows) else -1)
            edge = max(edge, int((al[0] > 8).sum() + (al[-1] > 8).sum() + (al[:, 0] > 8).sum() + (al[:, -1] > 8).sum()))
            moved.append(float(np.abs(a - frames[0]).mean()))
        line = (f"{c:13s} frames {len(fs):3d}  biggest seam gap {worst_hole:4d}px (frame {worst_at})  "
                f"soles {min(soles)}..{max(soles)}  border px {edge}")
        if c == "idle":
            line += f"  loop close {np.abs(frames[-1] - frames[0]).mean():.2f} (a step {np.abs(frames[1] - frames[0]).mean():.2f})"
        report.append(line)
        # the zoom sheet: the 3 most-moved frames (and the rest frame), every joint
        pick = [0] + sorted(np.argsort(moved)[-3:].tolist())
        cell = 2 * R * S * 2.2
        cw = int(cell)
        sheet = Image.new("RGB", (cw * len(JOINTS), cw * len(pick) + 18), (30, 30, 36))
        d = ImageDraw.Draw(sheet)
        for j, nm in enumerate(JOINTS):
            d.text((j * cw + 4, 2), nm, fill=(255, 255, 255))
        M = np.fromfile(os.path.join(RIG, c + ".bin"), np.float32).reshape(-1, B, 6)
        for r_, i in enumerate(pick):
            im = Image.fromarray(frames[i].astype(np.uint8))
            bg = Image.new("RGBA", im.size, (70, 110, 80, 255))
            bg.alpha_composite(im)
            for j, (nm, ((x0, y0), bn)) in enumerate(JOINTS.items()):
                a, b, cc, dd, tx, ty = M[min(i, len(M) - 1), rig["bones"].index(bn)]
                cx, cy = rp(a * x0 + cc * y0 + tx, b * x0 + dd * y0 + ty)
                box = (int(cx - R * S), int(cy - R * S), int(cx + R * S), int(cy + R * S))
                sheet.paste(bg.crop(box).convert("RGB").resize((cw, cw), Image.LANCZOS), (j * cw, 18 + r_ * cw))
            d.text((2, 18 + r_ * cw + 2), f"f{i}", fill=(255, 255, 0))
        sheet.save(os.path.join(OUT, f"{c}.png"))
    print("\n".join(report))


if __name__ == "__main__":
    main()
