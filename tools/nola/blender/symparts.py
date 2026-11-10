"""The two scatters, FS and XFS, animated piece by piece (owner, 2026-11-09: "split up and animate the FS and XFS, we want
their idle animation to stand out more").

Every other symbol is one sticker bent by a chain of three bones (symanim.py). These two are rigs of separate pieces
(tools/nola/scatter_regen.py draws and places them): FS is its two gold letters, the crystal ball on the S, the green
smoke behind the ball and a strand of beads hung on the F; XFS is its three slime letters, the skull in his top hat
behind them, his two hands on the X and three tongues of green fire. Each piece has its own short chain of bones, so
the letters hop one after another, the ball bobs and jumps off its letter, the beads swing, the smoke and the fire
waver all the time and the skull ducks and peeks. The cream sticker border is not on any piece: every piece throws
its own border shape onto a layer BEHIND all the pieces, so the border follows them as one outline round the lot.

Same four clips on the same timeline as symanim.py (idle 72 f loop, land 24, hit 46, multi 42; every one-shot
starts and ends on the idle's first frame), same camera, glow and effect sprites; rendered to the same place, so
tools/blender/pack_frames.py packs them like any other symbol.

  blender.exe -b --factory-startup --python tools/nola/blender/symparts.py -- <BS|ES> [build,render,preview] [clips]
-> art/blender/symbols/<ID>.blend, art/blender/renders/<ID>/<clip>/####.png  (preview: every 5th frame, _preview/)"""
import json, math, os, random, sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import symanim as SA

PARTS = os.path.join(SA.ROOT, "art", "nola-src", "scatter_parts")
FPS, CLIPS, START, HALF = SA.FPS, SA.CLIPS, SA.START, SA.HALF
TAU = 2 * math.pi

# piece -> (links in its chain, the bone it rides on (None: the root), which way it grows from its pivot (+1 up,
#           -1 hangs down), its pivot as shares of its own box (x, y down)); listed back to front
RIG = {
    "BS": {"smoke": (3, "ball_0", 1, (.45, 1.0)), "f": (2, None, 1, (.5, 1.0)), "beads": (3, "f_1", -1, (.62, .0)),
           "s": (2, None, 1, (.5, 1.0)), "ball": (1, "s_1", 1, (.5, 1.0))},
    "ES": {"flames1": (3, None, 1, (.5, 1.0)), "flames2": (3, None, 1, (.5, 1.0)), "flames3": (3, None, 1, (.5, 1.0)),
           "skull": (2, None, 1, (.5, 1.0)), "x": (2, None, 1, (.5, 1.0)), "f": (2, None, 1, (.5, 1.0)),
           "s": (2, None, 1, (.5, 1.0)), "hands1": (1, "x_1", -1, (.5, .0)), "hands2": (1, "x_1", -1, (.5, .0))},
}
GLOW0 = .2                                                  # the halo at rest (symanim.base_glow)


# ---------------------------------------------------------------- the rig

def u(px, py):
    """Icon px -> picture units (x right, z up; the icon's centre at 0)."""
    return (px - 500) / 100.0, (500 - py) / 100.0


def build_rig(sid):
    spec = json.load(open(os.path.join(PARTS, sid, "pieces.json")))
    by = {p["name"]: p for p in spec["pieces"]}
    arm_d = bpy.data.armatures.new("rig")
    arm = bpy.data.objects.new("rig", arm_d)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_d.edit_bones
    root = eb.new("root")
    root.head, root.tail = (0, 0, -HALF), (0, 0, -HALF + 1.0)
    span = {}                                                # piece -> (pivot x, pivot z, far z)
    for name, (links, parent, grow, piv) in RIG[sid].items():
        x, y, w, h = by[name]["box"]
        px, pz = u(x + piv[0] * w, y + piv[1] * h)
        far = u(0, y if grow > 0 else y + h)[1]
        span[name] = (px, pz, far)
        prev = None
        for j in range(links):
            b = eb.new(f"{name}_{j}")
            b.head = (px, 0, pz + (far - pz) * j / links)
            b.tail = (px, 0, pz + (far - pz) * (j + 1) / links)
            if prev:
                b.parent, b.use_connect = prev, True
            prev = b
    for name, (links, parent, grow, piv) in RIG[sid].items():
        eb[f"{name}_0"].parent = eb[parent] if parent else root
    for b in eb:
        b.align_roll((0, -1, 0))                             # every bone's turn is in the picture plane
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"

    def mesh(name, piece, png, box, depth, cuts):
        x, y, w, h = box
        mat = SA.emit_material(name, SA.image(os.path.join(PARTS, sid, png)))
        ob = SA.grid_plane(name, 1.0, cuts, mat)
        cx, cz = u(x + w / 2, y + h / 2)
        for v in ob.data.vertices:
            v.co.x, v.co.z = cx + v.co.x * w / 100.0, cz + v.co.z * h / 100.0
        ob.location = (0, depth, 0)
        links = RIG[sid][piece][0]
        px, pz, far = span[piece]
        groups = [ob.vertex_groups.new(name=f"{piece}_{j}") for j in range(links)]
        for v in ob.data.vertices:
            t = (v.co.z - pz) / (far - pz)                   # 0 at its pivot, 1 at its far end
            wts = [math.exp(-((t - (j + .5) / links) / (.6 / links)) ** 2) for j in range(links)]
            if t <= .5 / links:
                wts = [1.0] + [0.0] * (links - 1)
            elif t >= 1 - .5 / links:
                wts = [0.0] * (links - 1) + [1.0]
            s = sum(wts)
            for g, wi in zip(groups, wts):
                g.add([v.index], wi / s, "REPLACE")
        mod = ob.modifiers.new("rig", "ARMATURE")
        mod.object = arm
        ob.parent = arm
        return ob

    for k, name in enumerate(RIG[sid]):
        p = by[name]
        links = RIG[sid][name][0]
        mesh(name, name, name + ".png", p["box"], -.06 * k, 8 * links + 4)
        mesh(name + "_rim", name, name + "_rim.png", p["rim"], .3 + .01 * k, 8 * links + 4)
    gm = SA.emit_material("glow_" + sid, SA.image(os.path.join(SA.ICONS, sid + "_glow.png")), SA.GLOW[sid], 1.6)
    glow = SA.grid_plane("glow", 12.0, 1, gm)
    glow.parent = arm
    glow.parent_type = "BONE"
    glow.parent_bone = "root"
    glow.matrix_world = __import__("mathutils").Matrix.Translation((0, 0.6, 0))
    return arm, glow, ["root"] + [f"{n}_{j}" for n, v in RIG[sid].items() for j in range(v[0])]


# ---------------------------------------------------------------- motion helpers

def kf(x, *keys):
    """The value at frame x of keys (frame, value[, "i"]): a shape-preserving cubic through them (it runs through a
    key on the way between its neighbours without stopping, and turns round at rest on an extreme); a key tagged
    "i" is an impact - fallen onto, gathering speed. Held before the first key and after the last."""
    n = len(keys)
    if x <= keys[0][0]:
        return keys[0][1]
    if x >= keys[-1][0]:
        return keys[-1][1]
    k = 0
    while x > keys[k + 1][0]:
        k += 1
    x0, y0 = keys[k][0], keys[k][1]
    x1, y1 = keys[k + 1][0], keys[k + 1][1]
    h = max(1e-9, x1 - x0)
    t = (x - x0) / h
    if len(keys[k + 1]) > 2:
        return y0 + (y1 - y0) * t ** 2.2

    def slope(j):
        if j <= 0 or j >= n - 1 or len(keys[j]) > 2 or len(keys[j + 1]) > 2:
            return 0.0
        ha, hb = keys[j][0] - keys[j - 1][0], keys[j + 1][0] - keys[j][0]
        da, db = (keys[j][1] - keys[j - 1][1]) / max(1e-9, ha), (keys[j + 1][1] - keys[j][1]) / max(1e-9, hb)
        if da * db <= 0:
            return 0.0
        w1, w2 = 2 * hb + ha, hb + 2 * ha
        return (w1 + w2) / (w1 / da + w2 / db)
    m0, m1 = slope(k) * h, slope(k + 1) * h
    t2, t3 = t * t, t * t * t
    return (2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * m0 + (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * m1


def ring(t, freq, decay):
    """A knock ringing off: starts at nothing, swings out and dies away (t seconds since the knock)."""
    return math.exp(-decay * t) * math.sin(TAU * freq * t) if t > 0 else 0.0


def wave(a, ph):
    """A sine that is at rest at a = 0 whatever its phase (so the loop starts on the rest pose)."""
    return math.sin(a - ph) + math.sin(ph)


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def home(i, n, tail=6):
    """1 through a clip, eased to 0 over its last frames: what is still ringing is brought home."""
    return smooth((n - i) / tail)


def win(i, a, b, edge=4):
    """1 between frames a and b, eased in and out."""
    return smooth((i - a) / edge) * smooth((b - i) / edge)


class Pose(dict):
    def __init__(self, names):
        super().__init__((n, {}) for n in names)

    def add(self, b, x=0.0, y=0.0, r=0.0, sx=1.0, sy=1.0):
        c = self[b]
        c["x"], c["y"], c["r"] = c.get("x", 0.0) + x, c.get("y", 0.0) + y, c.get("r", 0.0) + r
        c["sx"], c["sy"] = c.get("sx", 1.0) * sx, c.get("sy", 1.0) * sy

    def squash(self, b, s):
        """s > 0 flat and wide, s < 0 tall and thin (volume kept, more or less)."""
        self.add(b, sx=1 + .75 * s, sy=1 - s)


# ---------------------------------------------------------------- FS: the gold letters, the ball, the beads, the smoke

HOP_Y = lambda f, h: kf(f, (0, 0), (6, 0), (14, h), (21, 0, "i"), (30, 0))
HOP_S = lambda f: kf(f, (0, 0), (5, .09), (9, -.07), (14, -.02), (20, -.06), (23, .14), (26, -.045), (30, 0))
HOP_R = lambda f: kf(f, (0, 0), (5, .4), (13, -1), (21, .4), (25, -.18), (30, 0))
BEAD_KICK = lambda f: kf(f, (0, 0), (8, 9), (16, -8), (24, 5), (32, -3), (40, 1.2), (47, 0))


def letter_hop(P, b, f, h, lean):
    """A letter crouches, hops, hangs, drops and squashes; its top half follows a beat behind."""
    P.add(b + "_0", y=HOP_Y(f, h), r=lean * HOP_R(f))
    P.squash(b + "_0", HOP_S(f))
    P.add(b + "_1", r=.7 * lean * HOP_R(f - 2))


def beads(P, base, kick):
    """The strand swings from its top bead: each link a beat behind the one above."""
    P.add("beads_0", r=base(0) + kick(0))
    P.add("beads_1", r=.8 * base(1) + .7 * kick(2))
    P.add("beads_2", r=1.0 * base(2) + .8 * kick(4))


def bs_idle(P, i):
    t = i / 72
    a = TAU * t
    letter_hop(P, "f", i - 3, .38, 5)                        # the letters hop one after the other...
    letter_hop(P, "s", i - 13, .38, -4.5)
    P.add("f_1", r=1.1 * math.sin(a))                        # ...and are never quite still between
    P.add("s_1", r=-1.1 * math.sin(a))
    P.add("root", sy=1 + .012 * math.sin(2 * a))
    # the ball bobs on its letter and jumps off it as the S comes down
    P.add("ball_0", y=.09 * math.sin(2 * a) + kf(i, (33, 0), (40, .32), (47, 0, "i"), (72, 0)), r=6 * math.sin(a))
    P.squash("ball_0", kf(i, (46, 0), (49, .11), (52, -.04), (56, 0)))
    for j, A in enumerate((4, 7, 11)):                       # the smoke: a wave running up it, all the time
        P.add(f"smoke_{j}", r=A * wave(2 * a, .9 * j))
    P.add("smoke_0", sy=1 + .08 * math.sin(2 * a), sx=1 - .03 * math.sin(2 * a))
    beads(P, lambda j: 4.5 * wave(a, .8 * j), lambda lag: BEAD_KICK(i - 5 - lag))


def bs_land(P, i):
    n = CLIPS["land"]
    if i == 0 or i >= n:
        return
    t, e = (i - 1) / FPS, home(i, n)
    k = SA.damp(t, 3.2, .34) * e
    P.add("root", sx=1 + .15 * k, sy=1 - .19 * k)            # the whole sticker hits the reel...
    for b, d, lean in (("f", 0, 4), ("s", 3, -4)):           # ...and its letters are thrown up off it, one then the other
        f = i - 2 - d
        P.add(b + "_0", y=kf(f, (0, 0), (2, 0), (7, .3), (12, 0, "i"), (20, 0)), r=lean * kf(f, (0, 0), (7, -.8), (13, .4), (18, 0)))
        P.squash(b + "_0", kf(f, (0, 0), (11, -.03), (14, .1), (17, -.03), (20, 0)))
    P.add("ball_0", y=kf(i, (0, 0), (3, 0), (9, .5), (16, 0, "i"), (24, 0)), r=14 * ring(t, 2.6, 4) * e)
    P.squash("ball_0", kf(i, (15, 0), (18, .12), (21, -.03), (24, 0)))
    for j, A in enumerate((5, 9, 13)):
        P.add(f"smoke_{j}", r=A * ring(t - .03 * j, 2.4, 3.5) * e)
    P.add("smoke_0", sy=1 + .3 * ring(t, 1.6, 4) * e)
    beads(P, lambda j: 0.0, lambda lag: 18 * ring(t - lag / FPS, 2.1, 3.2) * e)


def bs_hit(P, i):
    n = CLIPS["hit"]
    if i >= n:
        return
    e = home(i, n)
    c = kf(i, (0, 0), (5, 1), (8, 0))                        # the crouch before it
    P.add("root", sx=1 + .1 * c, sy=1 - .13 * c)
    for b, d, lean, h in (("f", 0, 8, .95), ("s", 4, -7, .7)):   # a high jump each, a beat apart, then a smaller one
        f = i - 5 - d                                        # (the S less high: the ball and its smoke ride on it, near the frame's top)
        P.add(b + "_0", y=kf(f, (0, 0), (8, h), (16, 0, "i"), (19, 0), (24, .27), (29, 0, "i"), (36, 0)),
              r=lean * kf(f, (0, 0), (4, -1), (10, 1), (16, 0), (19, -.3), (24, .3), (29, 0), (36, 0)))
        P.squash(b + "_0", kf(f, (0, 0), (3, -.09), (8, -.03), (15, -.07), (18, .17), (21, -.05), (24, -.02), (28, -.03),
                              (31, .09), (33, -.02), (36, 0)))
        P.add(b + "_1", r=.8 * lean * kf(f - 2, (0, 0), (4, -1), (10, 1), (16, 0), (19, -.4), (24, .3), (29, 0), (36, 0)))
    tb = (i - 9) / FPS
    P.add("ball_0", y=kf(i, (9, 0), (18, .36), (27, 0, "i"), (30, 0), (35, .16), (40, 0, "i"), (46, 0)), r=24 * ring(tb, 2.2, 2.6) * e)
    P.squash("ball_0", kf(i, (26, 0), (29, .14), (32, -.04), (36, 0)))
    env = math.sin(math.pi * min(1, i / (n * .85))) if i < n * .85 else 0
    for j, A in enumerate((6, 11, 16)):
        P.add(f"smoke_{j}", r=A * env * math.sin(TAU * 2.6 * i / FPS - .9 * j))
    P.add("smoke_0", sy=1 + .12 * env, sx=1 + .12 * env)
    beads(P, lambda j: 0.0, lambda lag: 26 * ring((i - 5 - lag) / FPS, 2.0, 2.4) * e)


def bs_multi(P, i):
    n = CLIPS["multi"]
    if i >= n:
        return
    e = home(i, n)
    if i < 18:                                               # it charges: trembles, swells, the ball lifts off its letter
        k = i / 18
        sh = math.sin(i * 2.6) * k
        P.add("root", sx=1 + .07 * k, sy=1 + .07 * k)
        P.add("f_0", x=-.05 * sh, r=2.2 * sh)
        P.add("s_0", x=.05 * sh, r=-2.2 * sh)
        P.add("ball_0", y=.24 * smooth(k), r=10 * sh)
        P.add("smoke_0", sy=1 + .08 * k)
        beads(P, lambda j: 6 * sh, lambda lag: 0.0)
    else:                                                    # and lets go: the letters are punched apart and spring back
        t = (i - 18) / FPS
        k = SA.damp(t, 3.4, .3) * e
        P.add("root", sx=1 + .14 * k, sy=1 + .09 * k, y=.12 * k)
        P.add("f_0", x=-.3 * k, r=6 * ring(t, 2.6, 4) * e)
        P.add("s_0", x=.3 * k, r=-6 * ring(t, 2.6, 4) * e)
        P.add("ball_0", y=kf(i, (18, .24), (23, .4), (31, 0, "i"), (42, 0)), r=18 * ring(t, 2.4, 3.5) * e)
        P.squash("ball_0", kf(i, (30, 0), (33, .12), (36, -.03), (40, 0)))
        P.add("smoke_0", sy=1 + .08 * k)
        for j, A in enumerate((6, 10, 14)):
            P.add(f"smoke_{j}", r=A * ring(t - .03 * j, 2.6, 3.5) * e)
        beads(P, lambda j: 0.0, lambda lag: 20 * ring(t - lag / FPS, 2.1, 3) * e)


# ---------------------------------------------------------------- XFS: the slime letters, the skull, his hands, the fire

def fire(P, a, amp=1.0, tall=0.0):
    """The three tongues waver, each on its own beat, a wave running up each; `tall` stretches them."""
    for m in (1, 2, 3):
        ph = 2.1 * m
        for j, A in enumerate((3, 6.5, 11)):
            P.add(f"flames{m}_{j}", r=amp * A * wave(3 * a, .9 * j + ph))
        fl = .5 * wave(2 * a, ph)
        P.add(f"flames{m}_0", sy=(1 + tall) * (1 + .1 * amp * fl), sx=1 - .04 * amp * fl)


def es_idle(P, i):
    t = i / 72
    a = TAU * t
    for k, b in enumerate("xfs"):                            # a wobble runs through the slime, letter to letter
        f = i - 2 - 6 * k
        P.squash(b + "_0", kf(f, (0, 0), (7, -.1), (14, .09), (21, -.05), (28, .025), (36, 0)))
        P.add(b + "_1", r=(1, -1, 1)[k] * kf(f - 2, (0, 0), (7, 3.5), (14, -4.5), (21, 2.5), (28, -1.2), (36, 0))
              + 1.2 * wave(2 * a, 1.3 * k))
    P.add("root", sy=1 + .012 * math.sin(2 * a))
    # the skull ducks, comes up over the letters, looks one way and the other, and sinks back
    look = lambda f: kf(f, (30, 0), (38, -9), (47, 8), (56, -3), (64, 0))
    P.add("skull_0", y=kf(i, (0, 0), (17, 0), (23, -.2), (32, .5), (42, .44), (52, .5), (62, -.05), (68, 0)), r=look(i))
    P.add("skull_1", r=.5 * look(i - 3), y=kf(i, (30, 0), (34, .1), (38, 0, "i"), (72, 0)))
    P.add("hands1_0", r=kf(i, (40, 0), (44, -12), (48, 0, "i"), (51, -7), (54, 0, "i"), (72, 0)))   # his fingers drum
    P.add("hands2_0", r=kf(i, (43, 0), (47, 12), (51, 0, "i"), (54, 7), (57, 0, "i"), (72, 0)))
    fire(P, a)


def es_land(P, i):
    n = CLIPS["land"]
    if i == 0 or i >= n:
        return
    t, e = (i - 1) / FPS, home(i, n)
    k = SA.damp(t, 3.2, .34) * e
    P.add("root", sx=1 + .14 * k, sy=1 - .18 * k)
    for q, b in enumerate("xfs"):                            # the slime shudders, each letter a moment after the last
        tt = t - .035 * q
        P.squash(b + "_0", .15 * ring(tt, 3.4, 4.5) * e)
        P.add(b + "_1", r=(1, -1, 1)[q] * 8 * ring(tt, 2.8, 4) * e)
    P.add("skull_0", y=kf(i, (0, 0), (1, 0), (4, -.42), (11, .32), (17, -.04), (21, 0)), r=7 * ring(t - .2, 2.6, 4) * e)
    P.add("skull_1", y=kf(i, (4, 0), (8, .2), (13, 0, "i"), (24, 0)), r=-9 * ring(t - .13, 2.6, 4) * e)
    P.add("hands1_0", r=-11 * ring(t, 3, 5) * e)
    P.add("hands2_0", r=11 * ring(t - .03, 3, 5) * e)
    fire(P, 0, 0, kf(i, (0, 0), (1, 0), (5, .45), (11, -.06), (17, .04), (24, 0)))
    for m in (1, 2, 3):
        for j, A in enumerate((4, 8, 13)):
            P.add(f"flames{m}_{j}", r=(-1) ** m * A * ring(t - .03 * j, 2.5, 3.2) * e)


def es_hit(P, i):
    n = CLIPS["hit"]
    if i >= n:
        return
    e = home(i, n)
    c = kf(i, (0, 0), (5, 1), (8, 0))
    P.add("root", sx=1 + .1 * c, sy=1 - .13 * c)
    for q, b in enumerate("xfs"):                            # each letter stretches up tall like slime let go, and slaps back
        f = i - 4 - 4 * q
        P.add(b + "_0", y=kf(f, (0, 0), (4, 0), (10, .42), (16, 0, "i"), (34, 0)))
        P.squash(b + "_0", kf(f, (0, 0), (4, .1), (10, -.24), (16, .13), (22, -.08), (28, .04), (34, 0)))
        P.add(b + "_1", r=(1, -1, 1)[q] * kf(f - 2, (0, 0), (5, -3), (11, 9), (17, -7), (23, 4), (29, -1.5), (34, 0)))
    # the skull shoots up over them and shakes with laughing; his hat bounces; his hands wave
    lw = win(i, 12, 37, 5)
    lph = TAU * 3.2 * (i - 12) / FPS
    P.add("skull_0", y=kf(i, (0, 0), (5, -.3), (12, .9), (24, .82), (35, .86), (42, -.04), (46, 0)), r=8 * math.sin(lph) * lw)
    P.add("skull_1", y=.09 * abs(math.sin(lph)) * lw, r=-5 * math.sin(lph - .6) * lw)
    P.add("hands1_0", r=-16 * math.sin(lph + .4) * lw)
    P.add("hands2_0", r=16 * math.sin(lph + 1.2) * lw)
    env = math.sin(math.pi * min(1, i / (n * .87))) if i < n * .87 else 0
    fire(P, TAU * i / 54, (1 + .7 * env) * e, .34 * env)     # and the fire blazes (its wavering brought home at the end)


def es_multi(P, i):
    n = CLIPS["multi"]
    if i >= n:
        return
    e = home(i, n)
    if i < 18:                                               # it charges: the slime trembles and swells, the skull sinks, the fire shrinks
        k = i / 18
        sh = math.sin(i * 2.6) * k
        P.add("root", sx=1 + .07 * k, sy=1 + .07 * k)
        for q, b in enumerate("xfs"):
            P.add(b + "_0", x=.045 * sh * (q - 1), r=2 * sh * (1, -1, 1)[q])
            P.squash(b + "_0", .05 * k)
        P.add("skull_0", y=-.34 * smooth(k), r=3 * sh)
        fire(P, 0, 0, -.25 * smooth(k))
        P.add("hands1_0", r=-6 * sh)
        P.add("hands2_0", r=6 * sh)
    else:                                                    # and lets go: letters punched tall, the skull thrown up, the fire flares
        t = (i - 18) / FPS
        k = SA.damp(t, 3.4, .3) * e
        P.add("root", sx=1 + .13 * k, sy=1 + .09 * k, y=.12 * k)
        for q, b in enumerate("xfs"):
            tt = t - .03 * q
            P.squash(b + "_0", -.16 * math.exp(-5 * max(0, tt)) * math.cos(TAU * 3 * max(0, tt)) * e * (1 if tt >= 0 else 0) + .05 * (1 if tt < 0 else 0))
            P.add(b + "_1", r=(1, -1, 1)[q] * 8 * ring(tt, 2.8, 4) * e)
        P.add("skull_0", y=kf(i, (18, -.34), (24, .7), (32, -.05), (37, 0)), r=8 * ring(t, 2.8, 3.5) * e)
        P.add("skull_1", y=kf(i, (22, 0), (27, .22), (33, 0, "i"), (42, 0)), r=-9 * ring(t - .1, 2.8, 3.5) * e)
        P.add("hands1_0", r=-14 * ring(t, 3, 4) * e)
        P.add("hands2_0", r=14 * ring(t - .03, 3, 4) * e)
        fire(P, 0, 0, kf(i, (18, -.25), (22, .4), (29, -.06), (35, .03), (42, 0)))
        for m in (1, 2, 3):
            for j, A in enumerate((4, 8, 13)):
                P.add(f"flames{m}_{j}", r=(-1) ** m * A * ring(t - .03 * j, 2.6, 3.2) * e)


POSE = {"BS": dict(idle=bs_idle, land=bs_land, hit=bs_hit, multi=bs_multi),
        "ES": dict(idle=es_idle, land=es_land, hit=es_hit, multi=es_multi)}


# ---------------------------------------------------------------- glow + effects

def glow_at(clip, i):
    n = CLIPS[clip]
    if clip == "idle":                                       # it breathes twice a loop, well up from its rest
        return GLOW0 + .34 * (1 - math.cos(2 * TAU * i / n)) / 2, 1.0
    if clip == "land":
        g = kf(i, (0, 0), (1, 1), (8, .25), (16, 0))
        return GLOW0 + .5 * g, 1 + .04 * g
    if clip == "hit":
        v = i / n
        g = math.sin(math.pi * min(1, v / .9)) if v < .9 else 0
        return GLOW0 + .6 * g, 1 + .04 * g
    g = min(1, i / 18) if i < 18 else max(0, 1 - (i - 18) / 16)
    return GLOW0 + .75 * g, 1 + .05 * g


def twinkle(pool, f0, x, z, rng, size=.75, frames=14):
    """A gold star turns up, flashes and is gone, where it is on the sticker."""
    pool.particle(f0, f0 + frames, lambda t: (x, z), rng, spin=70, grow=(.1, .1), fade=(1, 1))
    ob = pool.obs[(pool.next - 1) % len(pool.obs)]
    for f in range(f0, f0 + frames + 1, 2):
        SA.key_obj(ob, f, s=max(.02, size * math.sin(math.pi * (f - f0) / frames)))


def burst(pools, kind, f0, count, rng, life=18):
    """Thrown out from the middle and falling: beads off FS, slime off XFS."""
    for j in range(count):
        fs = f0 + int(j * 1.3)
        a = rng.uniform(0, TAU)
        sp = rng.uniform(3.4, 5.0)
        vx, vz = sp * math.cos(a) * 1.1, abs(sp * math.sin(a)) + 2.4
        g = 5 if kind == "leaf" else 9
        pools[kind].particle(fs, fs + life, lambda t, vx=vx, vz=vz, g=g: (vx * t * .75, .8 + (vz * t - .5 * g * t * t) * .75),
                             rng, spin=rng.choice([-1, 1]) * 300, grow=(.7, .55), fade=(1, 0) if kind == "leaf" else (1, 1))


def effects(sid, pools, rng):
    f_idle, f_land, f_hit, f_multi = (START[c] for c in ("idle", "land", "hit", "multi"))
    if sid == "BS":
        stars = [u(380, 225), u(892, 602), u(466, 862), u(150, 262)]       # where the sticker has its four stars
        for k, (x, z) in enumerate(stars):                    # they flash in turn, round and round
            twinkle(pools["sparkle"], f_idle + 2 + 17 * k, x, z, rng, 1.3 if k % 2 == 0 else 1.0, 16)
        for k, (x, z) in enumerate(stars):
            twinkle(pools["sparkle"], f_land + 2 + 2 * k, x, z, rng, 1.3, 12)
        for k in range(10):                                   # the win: stars all round it, and beads thrown off
            a = TAU * k / 10 + .3
            twinkle(pools["sparkle"], f_hit + 8 + 2 * (k % 5) + 9 * (k // 5), 4.6 * math.cos(a), 4.3 * math.sin(a), rng, 1.2, 12)
        burst(pools, "leaf", f_hit + 13, 8, rng)
        burst(pools, "leaf", f_multi + 18, 6, rng, 16)
        for k in range(8):
            a = TAU * k / 8 + .2
            twinkle(pools["sparkle"], f_multi + 18 + (k % 2), 4.8 * math.cos(a), 4.4 * math.sin(a), rng, 1.2, 12)
    else:
        drips = [u(140, 885), u(495, 905), u(775, 935), u(300, 850), u(660, 880)]   # under the letters' drips
        for k, fs in enumerate((f_idle + 6, f_idle + 28, f_idle + 50)):   # a drop of slime lets go, now and then
            x, z = drips[k]
            pools["drop"].particle(fs, fs + 16, lambda t, x=x, z=z: (x, z - .1 - 1.5 * t * t), rng, grow=(.45, .4), fade=(1, .2))
        for k, (x, z) in enumerate(drips):                    # the landing shakes drops off it
            pools["drop"].particle(f_land + 2 + k, f_land + 16 + k, lambda t, x=x, z=z: (x + .5 * (x / 4.5) * t, z - 1.6 * t * t),
                                   rng, grow=(.5, .4), fade=(1, .2))
        burst(pools, "drop", f_hit + 12, 9, rng)
        burst(pools, "drop", f_multi + 18, 7, rng, 16)
    # the shared big ones: rays turning behind a win, a ring as it peaks and as a Multi lets go
    ob = pools["rays"].obs[0]
    n = CLIPS["hit"]
    SA.key_fade(ob, f_hit + 4, 0)
    for f in range(f_hit + 6, f_hit + n - 2, 2):
        t = (f - f_hit - 6) / (n - 8)
        SA.key_obj(ob, f, s=.72 + .2 * SA.ease_out(t), r=60 * t)
        SA.key_fade(ob, f, .8 * math.sin(math.pi * t))
    SA.key_fade(ob, f_hit + n - 1, 0)
    pools["ring"].particle(f_hit + 9, f_hit + 21, lambda t: (0, 0), rng, grow=(.55, 1.18), fade=(1, 0))
    pools["ring"].particle(f_multi + 18, f_multi + 30, lambda t: (0, 0), rng, grow=(.55, 1.18), fade=(1, 0))


# ---------------------------------------------------------------- build + render

def build(sid):
    SA.clear()
    SA.setup_scene(sid)
    rng = random.Random(sum(map(ord, sid)) * 11)
    arm, glow, names = build_rig(sid)
    kinds = {"BS": {"sparkle": 14, "leaf": 12}, "ES": {"drop": 12}}[sid]
    pools = {k: SA.Pool(k, n, sid) for k, n in kinds.items()}
    pools["ring"] = SA.Pool2("ring", 2, 9.0, behind=True)
    pools["rays"] = SA.Pool2("rays", 1, 11.0, behind=True)
    for clip, n in CLIPS.items():
        for i in range(n + 1):
            P = Pose(names)
            POSE[sid][clip](P, i)
            SA.key_pose(arm, START[clip] + i, **P)
            g, gs = glow_at(clip, i) if i < n else (GLOW0, 1.0)
            SA.key_fade(glow, START[clip] + i, g)
            SA.key_obj(glow, START[clip] + i, s=gs)
    effects(sid, pools, rng)
    for ob in [arm] + [o for o in bpy.data.objects if o.animation_data]:
        ad = ob.animation_data
        if ad and ad.action:
            for fc in SA.fcurves(ad.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR" if ob is arm else "BEZIER"
    for m in bpy.data.materials:
        ad = m.node_tree.animation_data if m.node_tree else None
        if ad and ad.action:
            for fc in SA.fcurves(ad.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
    os.makedirs(SA.BLEND, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SA.BLEND, sid + ".blend"))


def preview(sid, step=5):
    sc = bpy.context.scene
    d = os.path.join(SA.REN, sid, "_preview")
    os.makedirs(d, exist_ok=True)
    for old in os.listdir(d):
        os.remove(os.path.join(d, old))
    sc.render.resolution_percentage = 50
    for clip, n in CLIPS.items():
        for i in range(0, n + 1, step):
            sc.frame_set(START[clip] + i)
            sc.render.filepath = os.path.join(d, f"{clip}_{i:03d}.png")
            bpy.ops.render.render(write_still=True)
    sc.render.resolution_percentage = 100


if __name__ == "__main__" and "--" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:]
    sid = args[0]
    steps = args[1].split(",") if len(args) > 1 else ["build", "render"]
    if "build" in steps:
        build(sid)
    else:
        bpy.ops.wm.open_mainfile(filepath=os.path.join(SA.BLEND, sid + ".blend"))
    if "preview" in steps:
        preview(sid)
    if "render" in steps:
        SA.render(sid, args[2].split(",") if len(args) > 2 else None)
    print("DONE", sid)
