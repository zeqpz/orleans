"""Doc's motion, checked from the numbers the game plays (art/blender/chars/doc_rig/rig/: every bone's transform on
every frame), not from pictures: what stiffness and pops look like in the data.
  speed / accel   for a set of points on him (hat, nose, palm, flame, fingertip, cane hand, cane tip, coat hems,
                  hips): the fastest each moves, and the hardest it is ever jerked (px per frame, per frame^2). A POP
                  is one frame whose acceleration stands far out of its neighbours'.
  seam            the idle's loop: the step across the seam against the steps either side (a loop that closes)
  ends            how far each point is from the rest pose on a clip's first and last frame (one-shots start and
                  end ON it, but for enter's first and exit's last)
  feet            the soles: how far they leave the ground line and how far they slide while planted
  alive           how much of a clip any point holds dead still for (a figure that stops looks cut out)
usage: python tools/nola/qa_doc_motion.py [clip,..]"""
import json, os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RIG = os.path.join(ROOT, "art", "blender", "chars", "doc_rig", "rig")
POINTS = {   # name: (bone, rest point in art px)
    "hat top": ("hat", (486, 20)), "nose": ("face", (462, 262)), "chin": ("head", (470, 356)),
    "chest": ("chest", (512, 430)), "hips": ("hips", (512, 690)),
    "shoulder L": ("clav_l", (392, 428)), "shoulder R": ("clav_r", (606, 440)),
    "palm": ("hand_r", (852, 446)), "flame": ("orb", (852, 446)), "fingertip": ("f1_r2", (936, 364)),
    "cane hand": ("hand_l", (236, 724)), "cane tip": ("cane", (186, 1500)),
    "hem L": ("tail_l4", (345, 1112)), "hem R": ("tail_r4", (702, 1122)), "feather": ("feather2", (648, 54)),
}
SOLES = {"ball L": ("foot_l", (268, 1502)), "ball R": ("foot_r", (792, 1502)), "heel L": ("foot_l", (404, 1502)),
         "heel R": ("foot_r", (638, 1502))}
HOVER = (0, -58)     # the flame's bone carries its hover: its rest is this far off its anchor
POP = 4.0            # a frame's acceleration this many times its neighbourhood's (and over 6 px/f^2) is a pop
# accents that are meant to hit: a cane rapped on the pavement, a hat landing back on his head, the spring out of a
# crouch, a catch. A pop within 2 frames of one of these is the animation, not a fault.
MEANT = {"win": (5, 50, 66), "big_win": (8, 14, 44, 80, 104, 108), "cane_twirl": (66,), "hat_tip": (10, 53),
         "enter": (18, 38), "lose": (63, 70)}


def track(M, bones, bone, pt):
    m = M[:, bones.index(bone)]
    x, y = pt
    return np.stack([m[:, 0] * x + m[:, 2] * y + m[:, 4], m[:, 1] * x + m[:, 3] * y + m[:, 5]], 1)


def main():
    rig = json.load(open(os.path.join(RIG, "rig.json")))
    bones = rig["bones"]
    B = len(bones)
    want = sys.argv[1].split(",") if len(sys.argv) > 1 else list(rig["clips"])
    bad = 0
    for c in want:
        C = rig["clips"][c]
        M = np.fromfile(os.path.join(RIG, c + ".bin"), np.float32).reshape(-1, B, 6)
        n, loop = len(M), C["loop"]
        print(f"\n== {c}: {n} frames{' (loop)' if loop else ''}")
        rows, pops, still = [], [], []
        for nm, (bone, pt) in POINTS.items():
            p = track(M, bones, bone, pt)
            q = np.concatenate([p[-2:], p, p[:2]]) if loop else p
            v = np.diff(q, axis=0)
            a = np.diff(v, axis=0)
            sp, ac = np.hypot(*v.T), np.hypot(*a.T)
            # a pop: acceleration far above the frames round it
            k = 5
            pad = np.pad(ac, k, mode="edge")
            hood = np.array([np.median(np.r_[pad[i:i + k], pad[i + k + 1:i + 2 * k + 1]]) for i in range(len(ac))])
            hit = np.nonzero((ac > POP * (hood + .25)) & (ac > 6.0))[0]
            off = 0 if loop else 1
            for i in hit:
                fr = int(i + off - (1 if loop else 0)) % n
                if not any(abs(fr - m) <= 2 for m in MEANT.get(c, ())):
                    pops.append((nm, fr, float(ac[i]), float(hood[i])))
            rows.append((nm, sp.max(), int(sp.argmax()), ac.max(), int(ac.argmax())))
            still.append((nm, float((sp < .02).mean())))
        for nm, vmax, vi, amax, ai in rows:
            print(f"   {nm:11s} top speed {vmax:6.1f} px/f (f{vi:3d})   hardest jerk {amax:6.2f} px/f2 (f{ai:3d})")
        if pops:
            bad += len(pops)
            print("   POPS:", "; ".join(f"{nm} f{i} {a:.1f} (round it {h:.1f})" for nm, i, a, h in pops[:14]))
        dead = [(nm, s) for nm, s in still if s > .25 and nm not in ("cane tip", "cane hand")]
        if dead:
            print("   holds still:", ", ".join(f"{nm} {100 * s:.0f}% of the clip" for nm, s in dead))
        # the ends: distance from the rest pose
        ends = []
        for nm, (bone, pt) in POINTS.items():
            p = track(M, bones, bone, pt)
            rest = np.float32(pt) + (HOVER if nm == "flame" else (0, 0))
            ends.append((float(np.hypot(*(p[0] - rest))), float(np.hypot(*(p[-1] - rest)))))
        e0, e1 = max(e[0] for e in ends), max(e[1] for e in ends)
        note = ""
        if not loop and c != "enter" and e0 > .6:
            note += "  START OFF REST"; bad += 1
        if not loop and c != "exit" and e1 > .6:
            note += "  END OFF REST"; bad += 1
        print(f"   ends: first frame {e0:.2f} px from rest, last {e1:.2f} px{note}")
        # the feet
        for nm, (bone, pt) in SOLES.items():
            p = track(M, bones, bone, pt)
            up = pt[1] - p[:, 1]
            planted = up < .6
            slide = float(np.abs(p[planted, 0] - pt[0]).max()) if planted.any() else 0.0
            sink = float(-up.min())
            flag = ""
            if slide > 1.5 or sink > 1.5:
                flag = "  <-- SLIDES / SINKS"; bad += 1
            if nm.startswith("ball") or flag:
                print(f"   {nm}: lifts {up.max():5.1f} px at most, sinks {max(0, sink):.2f}, slides {slide:.2f} px while planted{flag}")
    print(f"\n{bad} problem(s)" if bad else "\nno pops, clean ends, feet planted")


if __name__ == "__main__":
    main()
