"""Doc, the voodoo showman: his layered cut-out rig in Blender, every clip keyed there, exported as a LIVE rig the game
poses itself on every screen refresh (no baked frames), plus QA renders of every clip.

Parts (art/nola-src/doc_parts/, cut by tools/nola/doc_parts.py) are separate meshes, each a grid fitted to its own
pixels and bent by the bones it belongs to (weights below): coat_back, leg_r, leg_l, cane, head, body, hat, arm_r,
arm_l, wisp; the reaction faces are small patches over the head, shown one at a time by a keyed fade.

The rig (37 bones, every one rolled to face the camera so a turn stays in the picture plane):
  root > hips > spine > chest (breathes: scales, its children do not) > neck > head > hat > feather
  chest > cravat;  chest > upper/fore/hand on each side;  the cane hand has fingers + thumb, the open hand a thumb
  and three fingers; the cane hangs from the knob and keeps its own angle (plumb unless keyed); the wisp is two bones
  so the smoke can coil
  hips > coat tails (two bones a side, swinging on springs, follow-through down the chain) and the back panel
  hips > thigh > shin (IK to an ankle target on the root: the shoes stay planted on the pavement whatever the hips
  do; knees bend outward) > foot (keeps its own angle: flat on the ground)
  the cane arm is IK too: upper > fore reach for a wrist target on the root, and the hand keeps its own angle, so the
  hand stays on the skull knob and the cane's tip on the pavement while the body dips and sways round it (the elbow
  takes it up); he lifts the cane by lifting that target - the hand rises and the arm bends

  blender.exe -b --factory-startup --python tools/nola/blender/doc_rig.py -- [build,export,render] [clip,..]
-> art/blender/chars/doc_rig/doc_rig.blend, rig/ (rig.json, geo.bin, <clip>.bin: the live rig), renders/<clip>/ (QA)
In the user's live Blender (MCP): runpy this file, then build() / animate(CLIPS) to preview."""
import json, math, os, random, struct, sys

import bpy
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PARTS = os.path.join(ROOT, "art", "nola-src", "doc_parts")
FX = os.path.join(ROOT, "art", "nola-src", "fx")
OUT = os.path.join(ROOT, "art", "blender", "chars", "doc_rig")
META = json.load(open(os.path.join(PARTS, "parts.json")))
K = META["scale"]                                 # 4K plate px per art px
W_PX, H_PX = META["art"]                          # 1024 x 1536: the drawing's px, 100 px = 1 Blender unit
FPS = 30
RES = (800, 1080)                                 # QA renders (the game draws the rig live, at any size)
ORTHO = 17.6
CAM_Z = -0.3
GROUND = 1506                                     # art px: the soles' line (the shoe tips' lowest pixels)

CLIPS = {          # frames, loop (the same lengths the game was timed against)
    "idle": (240, True), "enter": (44, False), "exit": (30, False), "anticipation": (54, False),
    "win": (96, False), "big_win": (132, False), "lose": (90, False),
    "cane_twirl": (84, False), "hat_tip": (72, False), "conjure": (96, False),
}
FACES = ["neutral"] + list(META["faces"])


def u(x, y):
    return ((x - W_PX / 2) / 100.0, (H_PX / 2 - y) / 100.0)


# name, head, tail, parent, options (art px)
BONES = [
    ("root", (512, 1506), (512, 1446), None, {}),
    ("hips", (512, 690), (512, 600), "root", {}),
    ("spine", (512, 600), (512, 470), "hips", {"connect": True}),
    ("chest", (512, 470), (500, 372), "spine", {"connect": True}),
    ("neck", (500, 372), (498, 300), "chest", {"connect": True, "noscale": True}),
    ("head", (498, 300), (488, 172), "neck", {"connect": True}),
    ("hat", (488, 172), (480, 20), "head", {"connect": True}),
    ("feather", (596, 122), (652, 52), "hat", {}),
    ("cravat", (510, 382), (512, 524), "chest", {"noscale": True}),
    ("upper_l", (392, 428), (312, 652), "chest", {"noscale": True}),
    ("fore_l", (312, 652), (236, 724), "upper_l", {"connect": True}),
    ("hand_l", (236, 724), (186, 834), "fore_l", {"connect": True, "norot": True, "noscale": True}),
    ("fingers_l", (178, 772), (138, 888), "hand_l", {}),
    ("thumb_l", (226, 784), (236, 860), "hand_l", {}),
    ("cane", (186, 834), (186, 1500), "hand_l", {"norot": True, "noscale": True}),
    ("upper_r", (606, 440), (684, 652), "chest", {"noscale": True}),
    ("fore_r", (684, 652), (792, 548), "upper_r", {"connect": True}),
    ("hand_r", (792, 548), (850, 462), "fore_r", {"connect": True}),
    ("thumb_r", (812, 455), (847, 410), "hand_r", {}),
    ("f1_r", (868, 448), (933, 366), "hand_r", {}),
    ("f2_r", (880, 458), (978, 399), "hand_r", {}),
    ("f3_r", (885, 470), (981, 448), "hand_r", {}),
    ("wisp", (858, 440), (852, 330), "hand_r", {}),
    ("wisp2", (852, 330), (862, 226), "wisp", {"connect": True}),
    ("tail_l", (432, 700), (390, 900), "hips", {}),
    ("tail_l2", (390, 900), (345, 1112), "tail_l", {"connect": True}),
    ("tail_r", (592, 700), (640, 900), "hips", {}),
    ("tail_r2", (640, 900), (702, 1122), "tail_r", {"connect": True}),
    ("tail_b", (512, 700), (512, 1004), "hips", {}),
    ("thigh_l", (470, 700), (414, 1060), "hips", {}),
    ("shin_l", (414, 1060), (372, 1420), "thigh_l", {"connect": True}),
    ("foot_l", (372, 1420), (300, 1496), "shin_l", {"connect": True, "norot": True, "noscale": True}),
    ("thigh_r", (552, 700), (606, 1060), "hips", {}),
    ("shin_r", (606, 1060), (648, 1420), "thigh_r", {"connect": True}),
    ("foot_r", (648, 1420), (730, 1494), "shin_r", {"connect": True, "norot": True, "noscale": True}),
    ("ik_l", (372, 1420), (372, 1360), "root", {}),
    ("ik_r", (648, 1420), (648, 1360), "root", {}),
    ("ik_hand_l", (236, 724), (236, 664), "root", {}),   # the cane hand's wrist: the arm reaches for it (IK)
]
BONE = {b[0]: b for b in BONES}
DEFORM = [b[0] for b in BONES if not b[0].startswith("ik_")]

# each part: its mesh cell (art px), its depth, and the bones it may bend with
PART_BONES = {
    "coat_back": ["hips", "tail_b"],
    "leg_r": ["hips", "thigh_r", "shin_r", "foot_r"],
    "leg_l": ["hips", "thigh_l", "shin_l", "foot_l"],
    "cane": ["cane"],
    "head": ["chest", "neck", "head"],
    "body": ["hips", "spine", "chest", "cravat", "tail_l", "tail_l2", "tail_r", "tail_r2"],
    "hat": ["hat", "feather"],
    "arm_r": ["chest", "upper_r", "fore_r", "hand_r", "thumb_r", "f1_r", "f2_r", "f3_r"],
    "arm_l": ["chest", "upper_l", "fore_l", "hand_l", "fingers_l", "thumb_l"],
    "wisp": ["wisp", "wisp2"],
}
CELL = {"coat_back": 12, "leg_r": 10, "leg_l": 10, "cane": 12, "head": 8, "body": 10, "hat": 9, "arm_r": 5,
        "arm_l": 6, "wisp": 7, "face": 8}


def seg(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / max(1e-9, dx * dx + dy * dy)))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy), t


def soft(p, names, sigma):
    w = {}
    for n in names:
        d, _ = seg(p, BONE[n][1], BONE[n][2])
        w[n] = math.exp(-(d / sigma) ** 2)
    s = sum(w.values()) or 1.0
    return {k: v / s for k, v in w.items()}


def smooth(e0, e1, v):
    t = max(0.0, min(1.0, (v - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def weights(part, x, y):
    """Bone weights for a vertex of a part (art px). Region rules first, soft nearest-bone blending inside."""
    p = (x, y)
    if part == "cane":
        return {"cane": 1.0}
    if part == "wisp":
        k = smooth(380, 280, y)
        return {"wisp": 1 - k, "wisp2": k}
    if part == "hat":
        k = smooth(150, 110, math.hypot(x - 610, y - 95)) if x > 560 else 0.0   # the feather, past the band
        return {"hat": 1 - k, "feather": k}
    if part in ("head", "face"):
        if y > 380:                                       # the neck hidden under the collar rides the chest
            return {"chest": 1.0}
        k = smooth(380, 352, y)                           # collar -> neck
        h = smooth(340, 310, y)                           # neck -> head (the jaw and up are all head)
        return {"chest": 1 - k, "neck": k * (1 - h), "head": k * h}
    if part in ("leg_l", "leg_r"):
        s = part[-1]
        hipy = 700
        if y > 1418:                                      # spat and shoe: the foot
            k = smooth(1405, 1432, y)
            return {f"shin_{s}": 1 - k, f"foot_{s}": k}
        top = smooth(hipy - 30, hipy + 40, y)             # the top of the thigh, under the coat, sits on the hips
        kn = smooth(1010, 1110, y)                         # thigh -> shin across the knee
        return {"hips": 1 - top, f"thigh_{s}": top * (1 - kn), f"shin_{s}": top * kn}
    if part == "coat_back":
        k = smooth(720, 900, y)
        return {"hips": 1 - k, "tail_b": k}
    if part == "body":
        if y < 360:
            return {"chest": 1.0}
        if y < 700 or (430 < x < 594 and y < 760):        # the torso: chest over spine over hips; the cravat sways
            w = {}
            kc = smooth(470, 600, y)
            w["chest"] = 1 - kc
            ks = smooth(600, 690, y)
            w["spine"] = kc * (1 - ks)
            w["hips"] = kc * ks
            if 470 < x < 552 and 380 < y < 540:           # the cravat's ruffles
                c = smooth(380, 430, y) * (1 - smooth(500, 540, y)) * (1 - smooth(536, 552, x)) * smooth(470, 486, x)
                w = {k: v * (1 - .8 * c) for k, v in w.items()}
                w["cravat"] = .8 * c
            return w
        side = "l" if x < 512 else "r"                    # the front coat tails, from the waist down
        k1 = smooth(700, 790, y)
        k2 = smooth(860, 960, y)
        return {"hips": 1 - k1, f"tail_{side}": k1 * (1 - k2), f"tail_{side}2": k1 * k2}
    if part == "arm_l":
        if math.hypot(x - 392, y - 428) < 30:             # the shoulder blends into the chest
            k = smooth(30, 8, math.hypot(x - 392, y - 428))
            w = soft(p, ["upper_l"], 40)
            return {"upper_l": 1 - .7 * k, "chest": .7 * k}
        if y > 788 and x < 222:                           # the fingers draped over the skull
            k = smooth(788, 822, y)
            return {"hand_l": 1 - k, "fingers_l": k}
        if x > 214 and y > 792:                           # the thumb, right of the knob
            k = smooth(792, 818, y)
            return {"hand_l": 1 - k, "thumb_l": k}
        return soft(p, ["upper_l", "fore_l", "hand_l"], 34)
    if part == "arm_r":
        d = math.hypot(x - 606, y - 440)
        if d < 32:
            k = smooth(32, 8, d)
            return {"upper_r": 1 - .7 * k, "chest": .7 * k}
        # past the knuckles: each digit on its own bone (they are spread apart, so the nearest digit wins)
        fingers = ["thumb_r", "f1_r", "f2_r", "f3_r"]
        best, bd = None, 1e9
        for f in fingers:
            dd, t = seg(p, BONE[f][1], BONE[f][2])
            if dd < bd:
                best, bd, bt = f, dd, t
        if bd < 18 and (bt > .05 or best == "thumb_r"):
            k = smooth(.0, .3, bt)
            return {"hand_r": 1 - k, best: k}
        return soft(p, ["upper_r", "fore_r", "hand_r"], 30)
    raise KeyError(part)


# ---------------------------------------------------------------- scene

def clear():
    if bpy.app.background:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.armatures, bpy.data.actions):
        for b in list(coll):
            coll.remove(b)


def setup():
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.fps = FPS
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    try:
        sc.eevee.taa_render_samples = 8
    except AttributeError:
        pass
    cd = bpy.data.cameras.new("cam")
    cd.type = "ORTHO"
    cd.ortho_scale = ORTHO
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    cam.location = (0, -30, CAM_Z)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    if sc.world is None:
        sc.world = bpy.data.worlds.new("world")


def load(path):
    im = bpy.data.images.get(os.path.basename(path)) or bpy.data.images.load(path)
    im.alpha_mode = "STRAIGHT"
    return im


def material(name, path, strength=1.0):
    """Emission (the art is flat-lit) with the texture's alpha, times a keyable 'fade'."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    try:
        m.surface_render_method = "BLENDED"
    except AttributeError:
        m.blend_method = "BLEND"
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = load(path)
    tex.interpolation = "Cubic"
    tex.extension = "CLIP"
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    fade = nt.nodes.new("ShaderNodeValue")
    fade.name = "fade"
    fade.outputs[0].default_value = 1.0
    am = nt.nodes.new("ShaderNodeMath")
    am.operation = "MULTIPLY"
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(tex.outputs["Alpha"], am.inputs[0])
    nt.links.new(fade.outputs[0], am.inputs[1])
    nt.links.new(am.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def build_rig():
    ad = bpy.data.armatures.new("rig")
    arm = bpy.data.objects.new("rig", ad)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for name, h, t, par, opt in BONES:
        b = ad.edit_bones.new(name)
        hx, hz = u(*h)
        tx, tz = u(*t)
        b.head, b.tail = (hx, 0, hz), (tx, 0, tz)
        b.align_roll((0, -1, 0))          # local Z faces the camera: a turn about Z stays in the picture plane
        b.use_deform = name in DEFORM
    for name, h, t, par, opt in BONES:
        if par:
            eb = ad.edit_bones[name]
            eb.parent = ad.edit_bones[par]
            eb.use_connect = bool(opt.get("connect"))
            if opt.get("norot"):
                eb.use_inherit_rotation = False
            if opt.get("noscale"):
                eb.inherit_scale = "NONE"
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    # the legs: IK from the shin to its ankle target, turning only in the picture plane, knees out
    for s in "lr":
        for nm in (f"thigh_{s}", f"shin_{s}"):
            pb = arm.pose.bones[nm]
            pb.lock_ik_x = pb.lock_ik_y = True
            pb.ik_stretch = .06
        c = arm.pose.bones[f"shin_{s}"].constraints.new("IK")
        c.target, c.subtarget = arm, f"ik_{s}"
        c.chain_count = 2
        c.use_tail = True
        c.use_stretch = True
    for nm in ("upper_l", "fore_l"):
        pb = arm.pose.bones[nm]
        pb.lock_ik_x = pb.lock_ik_y = True
        pb.ik_stretch = .04
    c = arm.pose.bones["fore_l"].constraints.new("IK")
    c.target, c.subtarget = arm, "ik_hand_l"
    c.chain_count = 2
    c.use_tail = True
    c.use_stretch = True
    return arm


def grid_mesh(name, path, box4k, cell, wfn, depth, arm, mat):
    """A mesh fitted to a part's pixels: a grid of `cell` art px over its box, only the cells with ink in them (and
    a ring round those), UVs onto the part's texture, weights from wfn."""
    import numpy as np
    img = load(path)
    tw, th = img.size
    arr = np.empty(tw * th * 4, np.float32)
    img.pixels.foreach_get(arr)
    alpha = arr[3::4].reshape(th, tw)[::-1]                # top row first
    x0, y0, w, h = [v / K for v in box4k]
    nx, ny = max(1, math.ceil(w / cell)), max(1, math.ceil(h / cell))
    used = set()
    for j in range(ny):
        r0, r1 = int(j * cell * K), min(th, int(math.ceil((j + 1) * cell * K)))
        row = alpha[r0:r1]
        if not row.size:
            continue
        for i in range(nx):
            c0, c1 = int(i * cell * K), min(tw, int(math.ceil((i + 1) * cell * K)))
            blk = row[:, c0:c1]
            if blk.size and blk.max() > .01:
                used.add((i, j))
    ring = {(i + di, j + dj) for (i, j) in used for di in (-1, 0, 1) for dj in (-1, 0, 1)}
    used = {(i, j) for (i, j) in ring if 0 <= i < nx and 0 <= j < ny}
    vid, verts, uvs, faces = {}, [], [], []

    def v(i, j):
        if (i, j) not in vid:
            ax = x0 + min(i * cell, w)
            ay = y0 + min(j * cell, h)
            vid[(i, j)] = len(verts)
            X, Z = u(ax, ay)
            verts.append((X, 0.0, Z))
            uvs.append(((ax - x0) / w, 1 - (ay - y0) / h))
        return vid[(i, j)]

    for (i, j) in sorted(used):
        faces.append((v(i, j + 1), v(i + 1, j + 1), v(i + 1, j), v(i, j)))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            uvl.data[li].uv = uvs[me.loops[li].vertex_index]
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (0, depth, 0)
    groups = {}
    for vi, (X, _, Z) in enumerate(verts):
        ax, ay = X * 100 + W_PX / 2, H_PX / 2 - Z * 100
        for bn, wt in wfn(ax, ay).items():
            if wt < .004:
                continue
            g = groups.get(bn) or ob.vertex_groups.new(name=bn)
            groups[bn] = g
            g.add([vi], wt, "REPLACE")
    mod = ob.modifiers.new("rig", "ARMATURE")
    mod.object = arm
    ob.parent = arm
    return ob


FX_KINDS = (("steam", 8, 160), ("sparkle", 12, 90), ("sparkle_w", 6, 80), ("leaf_red", 6, 70), ("leaf_orange", 6, 70),
            ("leaf_gold", 6, 70), ("ring", 3, 200), ("star", 6, 80))


def build():
    clear()
    setup()
    arm = build_rig()
    parts = {}
    for i, nm in enumerate(META["order"]):
        path = os.path.join(PARTS, nm + ".png")
        depth = .3 - i * .05                               # back to front, toward the camera
        parts[nm] = grid_mesh(nm, path, META["parts"][nm]["box"], CELL[nm], lambda x, y, n=nm: weights(n, x, y),
                              depth, arm, material(nm, path, 1.6 if nm == "wisp" else 1.0))
    faces = {}
    hd = .3 - META["order"].index("head") * .05 - .02        # just over the head, under the body (collar)
    for f, info in META["faces"].items():
        path = os.path.join(PARTS, f"face_{f}.png")
        ob = grid_mesh("face_" + f, path, info["box"], CELL["face"], lambda x, y: weights("face", x, y), hd, arm,
                       material("face_" + f, path))
        set_fade(ob, 0, 0.0)
        faces[f] = ob
    fx = {}
    for kind, n, size in FX_KINDS:
        fx[kind] = []
        for i in range(n):
            me = bpy.data.meshes.new(f"{kind}_{i}")
            s = size / 200.0
            me.from_pydata([(-s, 0, -s), (s, 0, -s), (s, 0, s), (-s, 0, s)], [], [(0, 1, 2, 3)])
            uvl = me.uv_layers.new(name="UVMap")
            for li, uv in zip(me.polygons[0].loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
                uvl.data[li].uv = uv
            me.materials.append(material(f"{kind}_{i}", os.path.join(FX, kind + ".png"), 1.5 if kind == "steam" else 1.0))
            ob = bpy.data.objects.new(f"{kind}_{i}", me)
            bpy.context.scene.collection.objects.link(ob)
            ob.location = (0, -1.0 - .01 * i, 0)
            ob["fx"] = kind
            ob["fx_size"] = size
            set_fade(ob, 0, 0.0)
            fx[kind].append(ob)
    os.makedirs(OUT, exist_ok=True)
    return arm, parts, faces, fx


# ---------------------------------------------------------------- keys

def set_fade(ob, f, v):
    s = ob.active_material.node_tree.nodes["fade"].outputs[0]
    s.default_value = v
    s.keyframe_insert("default_value", frame=f)


class Spring:
    """A damped spring on an angle: follows its target with lag and overshoot."""

    def __init__(self, freq, zeta):
        self.w, self.z = 2 * math.pi * freq, zeta
        self.x = self.v = 0.0

    def step(self, target, dt=1 / FPS, sub=8):
        for _ in range(sub):
            h = dt / sub
            a = self.w * self.w * (target - self.x) - 2 * self.z * self.w * self.v
            self.v += a * h
            self.x += self.v * h
        return self.x


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ease_out_back(t, s=1.7):
    t = max(0.0, min(1.0, t)) - 1
    return t * t * ((s + 1) * t + s) + 1


def bump(t, a, b):
    if t <= a or t >= b:
        return 0.0
    return math.sin(math.pi * (t - a) / (b - a))


def bump_e(t, a, b):
    """bump with eased shoulders: a soft rise, a soft fall (no linear corners)."""
    return ease(bump(t, a, b))


def env(i, n, att=8, rel=14):
    return ease(i / att) * ease((n - i) / rel)


def loop_wave(a, *terms):
    """sum of amp*sin(k*a + ph) - amp*sin(ph): periodic over the loop and exactly 0 at its start."""
    return sum(amp * (math.sin(k * a + ph) - math.sin(ph)) for amp, k, ph in terms)


CHANNELS = ("sway sx bob lean lean2 breath head neck hat hat_lift hat_x feather hand_lx "
            "ul fl hl fing_l thumb_l cane_r cane_lift cane_sx "
            "ur fr hr thumb_r f1 f2 f3 wisp_s wisp_r wisp2_r wisp_a "
            "lift_l lift_r foot_l foot_r").split()
REST = {c: 0.0 for c in CHANNELS}
REST.update(cane_sx=1.0, wisp_s=1.0, wisp_a=1.0)


def drive(name, i, n, rng, emit, face, PALM):
    """The animator's channels for frame i of a clip: degrees for turns, art px for moves."""
    c = dict(REST)
    t = i / FPS
    p = i / n
    loop = CLIPS[name][1]
    # breathing runs under everything: about one breath every 3.2 s (the idle's own, closed over the loop)
    if loop:
        a = 2 * math.pi * p
        c["breath"] = .5 - .5 * math.cos(4 * a)
    else:
        c["breath"] = (.5 - .5 * math.cos(2 * math.pi * t / 3.2)) * ease((n - i) / 12)
    if name == "idle":
        a = 2 * math.pi * p
        # a slow, sly weight shift: the hips slide and turn over the planted feet, the chest counters, the head
        # drifts on its own beat; the palm hand's fingers ripple under the wisp, the cane hand's fingers drum
        c["sx"] = loop_wave(a, (7, 1, .4), (2, 3, 1.1))
        c["sway"] = loop_wave(a, (1.6, 1, .4), (.6, 3, .9))
        c["bob"] = loop_wave(a, (2.2, 2, -1.2))
        c["lean"] = loop_wave(a, (-1.0, 1, .9), (.5, 2, .3))
        c["lean2"] = loop_wave(a, (-.8, 2, .2))
        c["head"] = loop_wave(a, (3.2, 1, 1.4), (1.4, 2, .2), (.6, 5, 2.0))
        c["hat"] = loop_wave(a, (1.0, 2, 2.2))
        c["ur"] = loop_wave(a, (3.0, 1, 1.2))
        c["fr"] = loop_wave(a, (5.0, 2, .5))
        c["hr"] = loop_wave(a, (6.0, 3, 0), (2.5, 5, 1))
        for k, f in enumerate(("thumb_r", "f1", "f2", "f3")):       # a ripple across the fingers, one after another
            c[f] = loop_wave(a, (7.0, 4, -.9 * k), (3.0, 7, 1.3 - .7 * k))
        drum = sum(bump_e(p, s, s + .035) for s in (.12, .17, .22, .62, .67, .72))
        c["fing_l"] = -9 * drum
        c["thumb_l"] = loop_wave(a, (2.0, 2, .7))
        c["ul"] = loop_wave(a, (1.2, 1, 2.0))
        c["wisp_s"] = 1 + loop_wave(a, (.1, 4, 0), (.05, 7, 2))
        c["wisp_r"] = loop_wave(a, (5, 3, 0))
        c["wisp2_r"] = loop_wave(a, (12, 3, 1.1), (6, 5, .3))
        c["wisp_a"] = .86 + .14 * math.cos(8 * a)
        c["feather"] = loop_wave(a, (4, 3, .5), (2, 7, 1.7))
        for b0 in (40, 128, 196):
            for k in range(4):
                face(b0 + k, "blink")
            face(b0 + 4, "neutral")
        face(84, "smug"); face(116, "neutral")
    elif name == "enter":
        # rises out of a low bow with a flourish: the palm sweeps up, the wisp blooms, the hat settles
        k = ease_out_back(p / .62, 1.2)
        c["lean"] = -12 * (1 - k)
        c["lean2"] = -6 * (1 - k)
        c["head"] = 16 * (1 - k)
        c["bob"] = 26 * (1 - ease(p / .62))
        c["ur"] = -34 * (1 - k) + 10 * bump_e(p, .38, .85)
        c["fr"] = 26 * (1 - k)
        c["hr"] = -18 * (1 - k) + 8 * bump_e(p, .45, .8)
        for kk, f in enumerate(("thumb_r", "f1", "f2", "f3")):     # fingers open out one by one
            c[f] = -25 * (1 - ease((p - .25 - .05 * kk) / .3))
        c["hat"] = -8 * (1 - k)
        c["wisp_s"] = .25 + .75 * ease(p / .6) + .25 * bump_e(p, .5, .85)
        c["wisp_a"] = ease(p / .5)
        c["fing_l"] = -6 * bump_e(p, .5, .8)
        face(0, "blink"); face(int(n * .45), "smug"); face(int(n * .86), "neutral")
    elif name == "exit":
        k = ease(p / .82)                                 # a deep bow, out, the hat lifted
        c["lean"], c["lean2"], c["head"], c["bob"] = -12 * k, -6 * k, 16 * k, 26 * k
        c["ur"], c["fr"], c["hr"] = -34 * k, 26 * k, -18 * k
        c["hat"] = -10 * k
        c["hat_lift"] = 14 * bump_e(p, .2, .9)
        c["wisp_s"], c["wisp_a"] = 1 - .8 * k, 1 - k
        face(int(n * .3), "wink")
    elif name == "anticipation":
        e = env(i, n, 6, 16)
        c["lean"] = -3.5 * e                               # leans in toward the board, rising onto it
        c["lean2"] = -2 * e
        c["sx"] = 8 * e
        c["bob"] = 6 * e
        c["head"] = -6 * e + 1.5 * math.sin(t * 28) * e
        c["ur"], c["fr"] = -12 * e, 20 * e
        c["hr"] = 12 * math.sin(t * 20) * e
        for k, f in enumerate(("thumb_r", "f1", "f2", "f3")):      # fingers wiggling in turn: a spell coming
            c[f] = 16 * math.sin(t * 24 - k * 1.1) * e
        c["fing_l"] = -10 * (.5 + .5 * math.sin(t * 18)) * e
        c["wisp_s"] = 1 + .45 * e + .1 * math.sin(t * 30) * e
        c["wisp_r"] = 18 * math.sin(t * 9) * e
        c["wisp2_r"] = 30 * math.sin(t * 13 + 1) * e
        c["feather"] = 6 * math.sin(t * 17) * e
        face(4, "shock"); face(int(n * .45), "smug"); face(n - 10, "neutral")
    elif name == "win":
        e = env(i, n, 8, 18)
        beat = math.sin(t * 2 * math.pi * 2.0)
        c["sway"] = 3.5 * beat * e
        c["sx"] = 6 * beat * e
        c["bob"] = 10 * abs(beat) * e                      # knees give on every beat (the feet stay put)
        c["head"] = -5 * math.sin(t * 2 * math.pi * 2.0 + .7) * e
        c["lean2"] = 2 * math.sin(t * 2 * math.pi * 1.0) * e
        tap = bump_e(p, .2, .34) + bump_e(p, .46, .6)      # two taps of the cane on the beat
        c["cane_lift"] = 44 * tap
        c["hand_lx"], c["hl"] = -6 * tap, 6 * tap
        c["ur"] = -16 * e + 5 * beat * e
        c["fr"] = 24 * e
        c["hr"] = 10 * math.sin(t * 2 * math.pi * 2.0 + 1.6) * e
        for k, f in enumerate(("thumb_r", "f1", "f2", "f3")):
            c[f] = -10 * e + 6 * math.sin(t * 14 - k) * e
        c["wisp_s"] = 1 + .35 * e
        c["wisp2_r"] = 15 * math.sin(t * 8) * e
        c["lift_r"] = 10 * (bump_e(p, .66, .74) + bump_e(p, .78, .86))   # a toe tap at the end
        c["foot_r"] = 9 * (bump_e(p, .66, .74) + bump_e(p, .78, .86))
        face(3, "laugh"); face(n - 14, "smug"); face(n - 6, "neutral")
        if i in (18, 42, 64):
            emit("sparkle", i, i + 16, lambda tt, x0=rng.uniform(-2, 3): (x0, 4 + 2 * tt), spin=120, grow=(.5, .1))
    elif name == "big_win":
        e = env(i, n, 8, 22)
        beat = math.sin(t * 2 * math.pi * 2.6)
        c["sway"] = 6 * beat * e
        c["sx"] = 12 * beat * e
        c["lean"] = 3 * math.sin(t * 2 * math.pi * 1.3) * e
        c["bob"] = 16 * abs(beat) * e
        c["head"] = -9 * math.sin(t * 2 * math.pi * 2.6 + .7) * e
        c["hat"] = 9 * bump_e(p, .15, .45) - 6 * bump_e(p, .55, .8)
        c["hat_lift"] = 30 * bump_e(p, .15, .4)            # it pops up off his head and drops back
        spin = ease((p - .12) / .55) * 2 * 2 * math.pi     # the cane spins in his fingers, twice round, then plants
        c["cane_sx"] = math.cos(spin) if .12 < p < .67 else 1.0
        c["cane_lift"] = 50 * bump_e(p, .1, .72)
        c["hand_lx"] = -12 * bump_e(p, .1, .72) + 6 * beat * bump_e(p, .1, .72)
        c["hl"] = 10 * math.sin(t * 14) * bump_e(p, .12, .67)
        c["fing_l"] = -8 * bump_e(p, .12, .67)
        c["ur"], c["fr"] = -32 * e, 38 * e                 # the palm thrown up
        c["hr"] = 12 * math.sin(t * 18) * e
        for k, f in enumerate(("thumb_r", "f1", "f2", "f3")):
            c[f] = 14 * math.sin(t * 20 - k * .9) * e
        c["wisp_s"] = 1 + .55 * e + .12 * math.sin(t * 20) * e
        c["wisp_r"] = 16 * math.sin(t * 6) * e
        c["wisp2_r"] = 34 * math.sin(t * 10 + .5) * e
        c["feather"] = 10 * math.sin(t * 15) * e
        tap = [bump_e(p, s, s + .07) for s in (.2, .34, .48, .62)]   # heel-toe on the beat, foot after foot
        c["lift_l"] = 10 * (tap[0] + tap[2])
        c["foot_l"] = -8 * (tap[0] + tap[2])
        c["lift_r"] = 10 * (tap[1] + tap[3])
        c["foot_r"] = 8 * (tap[1] + tap[3])
        face(3, "cheer"); face(int(n * .55), "laugh"); face(n - 16, "smug"); face(n - 6, "neutral")
        if i % 6 == 0 and 8 < i < n - 30:
            kind = ("leaf_red", "leaf_orange", "leaf_gold")[(i // 6) % 3]       # Mardi Gras beads flying
            ang, sp = rng.uniform(.5, 2.6), rng.uniform(4, 6.5)
            emit(kind, i, i + 20, lambda tt, a=ang, s=sp: (math.cos(a) * s * tt, 2 + math.sin(a) * s * tt - 8 * tt * tt),
                 spin=400, grow=(.9, .8))
        if i % 7 == 3 and 8 < i < n - 30:
            x0, z0 = PALM
            emit("steam", i, i + 26, lambda tt, x0=x0, z0=z0: (x0 + .8 * math.sin(tt * 6), z0 + .8 + 2.6 * tt), spin=90,
                 grow=(.6, 1.15))
        if i in (24, 60):
            emit("ring", i, i + 14, lambda tt: PALM, grow=(.3, 1.6))
    elif name == "lose":
        e = env(i, n, 14, 24)
        c["lean"] = 5 * e                                  # slumps back, unimpressed
        c["lean2"] = 3 * e
        c["head"] = 11 * e + 5 * math.sin(t * 8) * bump_e(p, .25, .6)   # and shakes his head
        c["bob"] = 8 * e
        c["sx"] = -5 * e
        c["breath"] = c["breath"] * .4 + .9 * bump_e(p, .15, .45)     # a long sigh
        c["ur"], c["fr"], c["hr"] = 28 * e, -28 * e, 14 * e          # the palm drops
        for k, f in enumerate(("thumb_r", "f1", "f2", "f3")):       # the fingers curl, limp
            c[f] = 22 * e
        c["hat"] = -6 * e
        c["wisp_s"], c["wisp_a"] = 1 - .6 * e, 1 - .7 * e           # his magic sputters
        c["wisp2_r"] = 25 * math.sin(t * 22) * bump_e(p, .1, .5)
        c["cane_r"] = 4 * e
        c["fing_l"] = -12 * sum(bump_e(p, s, s + .05) for s in (.55, .63, .71))   # impatient drumming on the skull
        face(4, "sad"); face(int(n * .72), "smug"); face(int(n * .85), "neutral")
    elif name == "cane_twirl":
        e = env(i, n, 8, 14)
        spin = ease((p - .15) / .6) * 2 * math.pi * 1.5
        c["cane_sx"] = math.cos(spin) if .15 < p < .75 else 1.0    # one and a half turns in the fingers
        c["cane_lift"] = 55 * bump_e(p, .08, .85)
        c["hand_lx"] = -14 * bump_e(p, .08, .85)           # the hand comes out from his side to twirl it
        c["hl"] = 9 * math.sin(t * 12) * bump_e(p, .15, .75)
        c["fing_l"] = -10 * bump_e(p, .15, .75) + 6 * math.sin(t * 24) * bump_e(p, .15, .75)
        c["thumb_l"] = 8 * math.sin(t * 24 + 1) * bump_e(p, .15, .75)
        c["sway"] = 2 * math.sin(t * 5) * e
        c["sx"] = -6 * bump_e(p, .1, .8)
        c["head"] = -5 * bump_e(p, .1, .6) + 4 * bump_e(p, .6, .9)
        face(6, "smug"); face(int(n * .78), "wink"); face(n - 8, "neutral")
    elif name == "hat_tip":
        tip = bump_e(p, .12, .72)
        c["hat"] = 14 * tip                                # lifts his hat off his head and tips it, with a nod
        c["hat_lift"] = 34 * tip
        c["hat_x"] = -10 * tip
        c["head"] = 9 * tip
        c["lean"] = -3 * tip
        c["lean2"] = -2 * tip
        c["bob"] = 5 * tip
        c["ur"], c["fr"] = -10 * tip, 12 * tip
        c["feather"] = -8 * tip
        face(int(n * .2), "wink"); face(int(n * .72), "smug"); face(n - 8, "neutral")
    elif name == "conjure":
        e = env(i, n, 8, 16)
        raise_ = bump_e(p, .1, .9)
        c["ur"], c["fr"] = -28 * raise_, 32 * raise_
        c["hr"] = 12 * math.sin(t * 14) * raise_
        for k, f in enumerate(("thumb_r", "f1", "f2", "f3")):      # the fingers roll, one after another
            c[f] = 20 * math.sin(t * 12 - k * 1.2) * raise_
        c["head"] = -6 * raise_
        c["lean"] = -2 * raise_
        c["sx"] = 6 * raise_
        c["wisp_s"] = 1 + .8 * bump_e(p, .2, .85) + .1 * math.sin(t * 24) * raise_
        c["wisp_r"] = 26 * math.sin(t * 7) * raise_
        c["wisp2_r"] = 40 * math.sin(t * 9 + .8) * raise_
        face(5, "smug"); face(int(n * .4), "laugh"); face(int(n * .78), "smug"); face(n - 8, "neutral")
        if i % 5 == 0 and .2 < p < .8:
            x0, z0 = PALM
            ang = rng.uniform(0, 6.28)
            emit("sparkle", i, i + 18, lambda tt, a=ang, x0=x0, z0=z0: (x0 + math.cos(a + tt * 4) * (1.2 + tt),
                 z0 + 1.2 + math.sin(a + tt * 4) * .6 + 2.4 * tt), spin=200, grow=(.6, .2))
        if i in (30, 54):
            x0, z0 = PALM
            emit("steam", i, i + 30, lambda tt, x0=x0, z0=z0: (x0 + .5 * math.sin(tt * 5), z0 + 1.2 + 2.4 * tt),
                 spin=60, grow=(.8, 1.4))
    return c


def rot_about(p, c, deg):
    """p turned deg about c, as Blender turns a bone about the camera axis (counter-clockwise on screen; art px are
    y-down)."""
    t = math.radians(deg)
    co, si = math.cos(t), math.sin(t)
    dx, dy = p[0] - c[0], p[1] - c[1]
    return (c[0] + dx * co + dy * si, c[1] - dx * si + dy * co)


def body_pt(pt, c, chest=True):
    """Where a point on the chest (or on the hips) is, posed by the channels: chest, spine, hips turns, then the
    hips' slide and dip (checked against Blender's evaluated bones)."""
    p = rot_about(pt, (512, 470), c["lean2"] - .4 * c["sway"]) if chest else pt
    if chest:
        p = rot_about(p, (512, 600), c["lean"])
    p = rot_about(p, (512, 690), c["sway"])
    return (p[0] + c["sx"], p[1] + c["bob"])


LEGS = {"l": ((470, 700), (372, 1420)), "r": ((552, 700), (648, 1420))}
ARM_L = math.dist((392, 428), (312, 652)) + math.dist((312, 652), (236, 724))
CANE_TIP, WRIST_L, KNOB = (186, 1500), (236, 724), (186, 834)


def reach(c):
    """Keep the IK chains in reach, so nothing stretches. The legs are straight at rest: when the hips slide or turn
    away from a planted foot, they dip until that leg reaches (he settles into his knees). The cane stays planted
    on its tip: when the body pulls the cane hand's shoulder out of reach, the cane (and the hand on it) tilts over
    on its tip toward him until the arm reaches. Sets c["bob"], c["cane_tilt"] and c["wrist"] (the wrist target's
    offset from rest, art px)."""
    for _ in range(80):
        if all(math.dist(body_pt(h, c, False), (a[0], a[1] - c["lift_" + s])) <= math.dist(h, a) for s, (h, a) in LEGS.items()):
            break
        c["bob"] += .5
    sh = body_pt((392, 428), c)
    lim = ARM_L * .985
    wrist = lambda th: rot_about(WRIST_L, CANE_TIP, th)
    th = c["cane_r"]
    if math.dist(wrist(th), sh) > lim:
        best = None
        for k in range(1, 121):
            for sgn in (1, -1):
                t2 = c["cane_r"] + sgn * k * .25
                if math.dist(wrist(t2), sh) <= lim:
                    best = t2
                    break
            if best is not None:
                break
        th = best if best is not None else th
    w = wrist(th)
    c["cane_tilt"] = th
    c["wrist"] = (w[0] - WRIST_L[0] + c["hand_lx"], w[1] - WRIST_L[1] - c["cane_lift"])
    return c


def run_clip(arm, faces, fx, name, f0, rng):
    """Key one clip at frames f0.. Every clip starts on the rest pose and every one-shot ends exactly on it."""
    n, loop = CLIPS[name]
    used = {k: 0 for k in fx}
    face_keys = {}

    def emit(kind, fs, fe, path, spin=0.0, grow=(1, 1)):
        obs = fx[kind]
        ob = obs[used[kind] % len(obs)]
        used[kind] += 1
        set_fade(ob, f0 + fs - 1, 0.0)
        r0 = rng.uniform(0, 360)
        for f in range(fs, fe + 1):
            tt = (f - fs) / max(1, fe - fs)
            x, z = path(tt)
            ob.location = (x, ob.location.y, z)
            g = grow[0] + (grow[1] - grow[0]) * tt
            ob.scale = (g, 1, g)
            ob.rotation_euler = (0, math.radians(r0 + spin * tt), 0)
            ob.keyframe_insert("location", frame=f0 + f)
            ob.keyframe_insert("scale", frame=f0 + f)
            ob.keyframe_insert("rotation_euler", frame=f0 + f)
            set_fade(ob, f0 + f, 1.0 if tt < .7 else (1 - tt) / .3)
        set_fade(ob, f0 + fe + 1, 0.0)

    def face(i, nm):
        face_keys[i] = nm

    PALM = u(870, 450)
    face(0, "neutral")
    # springs: the head lags the body, the hat the head, the coat tails swing and follow through, the feather and
    # the cravat flutter. A loop runs its springs over two cycles first, so it closes on their steady state.
    S = {"head": Spring(2.2, .32), "hat": Spring(3.0, .28), "tail_l": Spring(1.3, .2), "tail_l2": Spring(1.7, .22),
         "tail_r": Spring(1.3, .2), "tail_r2": Spring(1.7, .22), "tail_b": Spring(1.1, .25),
         "feather": Spring(2.6, .18), "cravat": Spring(2.0, .22), "hand_l": Spring(2.2, .35)}
    prev = {"sx": 0.0, "vx": 0.0, "bob": 0.0, "sway": 0.0}
    frames = list(range(n)) if loop else list(range(n + 1))
    passes = ([("pre", i) for i in frames] * 2 if loop else []) + [("key", i) for i in frames]
    for kind, i in passes:
        quiet = (lambda *a, **k: None)
        c = reach(drive(name, i, n, rng if kind == "key" else random.Random(0), emit if kind == "key" else quiet,
                        face if kind == "key" else quiet, PALM))
        # the hips' sideways speed and push, for the cloth
        vx = (c["sx"] - prev["sx"]) * FPS
        ax = (vx - prev["vx"]) * FPS
        vb = (c["bob"] - prev["bob"]) * FPS
        dsw = (c["sway"] - prev["sway"]) * FPS
        prev.update(sx=c["sx"], vx=vx, bob=c["bob"], sway=c["sway"])
        if kind == "pre" and i == 0 and not loop:
            continue
        h = S["head"].step(c["head"] + .5 * c["sway"] - .6 * c["lean"])
        hat = S["hat"].step(c["hat"] + .15 * (h - c["head"]))
        # coat tails: they hang (counter the hips' turn), swing with the push, flare as he dips
        tl = S["tail_l"].step(-.7 * c["sway"] - .010 * ax - .05 * vb)
        tr = S["tail_r"].step(-.7 * c["sway"] - .010 * ax + .05 * vb)
        tl2 = S["tail_l2"].step(.6 * (-.7 * c["sway"] - .010 * ax - tl) - .03 * vb)
        tr2 = S["tail_r2"].step(.6 * (-.7 * c["sway"] - .010 * ax - tr) + .03 * vb)
        tb = S["tail_b"].step(-.6 * c["sway"] - .006 * ax)
        fe = S["feather"].step(c["feather"] - .05 * dsw - .4 * (h - c["head"]))
        cr = S["cravat"].step(-.5 * c["sway"] - .8 * c["lean2"] - .006 * ax)
        hl = S["hand_l"].step(c["hl"])
        if kind != "key":
            continue
        if not loop and name != "exit":                   # the last frames settle exactly onto the rest pose
            w = ease((n - i) / 6.0)
            for ch in CHANNELS:
                c[ch] = REST[ch] + (c[ch] - REST[ch]) * w
            c["cane_tilt"] *= w
            c["wrist"] = (c["wrist"][0] * w, c["wrist"][1] * w)
            h, hat, tl, tr, tl2, tr2, tb, fe, cr, hl = (v * w for v in (h, hat, tl, tr, tl2, tr2, tb, fe, cr, hl))
        pose(arm, f0 + i, c, dict(head=h, hat=hat, tail_l=tl, tail_r=tr, tail_l2=tl2, tail_r2=tr2, tail_b=tb,
                                   feather=fe, cravat=cr, hand_l=hl))
    # faces: one patch at a time (neutral = none)
    cur = "neutral"
    for i in frames:
        cur = face_keys.get(i, cur)
        if not loop and name != "exit" and i >= n - 1:
            cur = "neutral"
        for f, ob in faces.items():
            set_fade(ob, f0 + i, 1.0 if f == cur else 0.0)
    return n


def pose(arm, f, c, s):
    """Set and key every bone for frame f from the channels c and the spring outputs s."""
    P = arm.pose.bones
    R = math.radians

    def rot(nm, deg):
        P[nm].rotation_euler = (0, 0, R(deg))

    for pb in P:
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    # the hips: turn about the waist, slide sideways and dip (art px; the hips bone points up, so its local x is
    # screen right and local y is up)
    P["hips"].location = (c["sx"] / 100, -c["bob"] / 100, 0)
    rot("hips", c["sway"])
    rot("spine", c["lean"])
    rot("chest", c["lean2"] - .4 * c["sway"])
    b = c["breath"]
    P["chest"].scale = (1 + .006 * b, 1 + .014 * b, 1)
    rot("neck", .35 * s["head"])
    rot("head", .65 * s["head"])
    rot("hat", s["hat"])
    P["hat"].location = (c["hat_x"] / 100, c["hat_lift"] / 100, 0)   # (local y = up the hat)
    rot("feather", s["feather"])
    rot("cravat", s["cravat"])
    rot("upper_l", 0)                                   # (the cane arm is solved by its IK: see ik_hand_l)
    rot("fore_l", 0)
    rot("hand_l", s["hand_l"] + c["cane_tilt"])          # the hand turns with the cane it holds
    rot("fingers_l", c["fing_l"])
    rot("thumb_l", c["thumb_l"])
    # the cane keeps its own angle in the world; the lift is up its shaft (the bone points down it: up is -y)
    rot("cane", c["cane_tilt"])                          # (cane_r and the reach tilt, about its tip: see reach())
    P["cane"].scale = (c["cane_sx"], 1, 1)
    # the cane hand's wrist target: where the tilted cane puts the hand, up by the lift (he raises the cane)
    P["ik_hand_l"].location = (c["wrist"][0] / 100, -c["wrist"][1] / 100, 0)
    rot("upper_r", c["ur"] - .5 * c["sway"])
    rot("fore_r", c["fr"])
    rot("hand_r", c["hr"])
    for nm, ch in (("thumb_r", "thumb_r"), ("f1_r", "f1"), ("f2_r", "f2"), ("f3_r", "f3")):
        rot(nm, c[ch])
    rot("wisp", c["wisp_r"])
    P["wisp"].scale = (c["wisp_s"], c["wisp_s"], 1)
    rot("wisp2", c["wisp2_r"])
    for nm in ("tail_l", "tail_r", "tail_l2", "tail_r2", "tail_b"):
        rot(nm, s[nm])
    # the feet: their ankle targets stay planted unless a tap lifts one; the foot itself keeps its angle
    P["ik_l"].location = (0, c["lift_l"] / 100, 0)
    P["ik_r"].location = (0, c["lift_r"] / 100, 0)
    rot("foot_l", c["foot_l"])
    rot("foot_r", c["foot_r"])
    for pb in P:
        pb.keyframe_insert("location", frame=f)
        pb.keyframe_insert("rotation_euler", frame=f)
        pb.keyframe_insert("scale", frame=f)
    wisp = bpy.data.objects.get("wisp")
    if wisp:
        set_fade(wisp, f, max(0.0, min(1.0, c["wisp_a"])))


def fcurves(act):
    try:
        return list(act.fcurves)
    except AttributeError:
        return [fc for L in act.layers for s in L.strips for cb in s.channelbags for fc in cb.fcurves]


def finish_curves():
    for idb in list(bpy.data.objects) + [m.node_tree for m in bpy.data.materials if m.node_tree]:
        ad = idb.animation_data
        if not (ad and ad.action):
            continue
        for fc in fcurves(ad.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"


STARTS = {}


def animate(arm, faces, fx, clips):
    rng = random.Random(1123)
    f = 1
    for c in CLIPS:
        STARTS[c] = f
        n = run_clip(arm, faces, fx, c, f, rng) if c in clips else CLIPS[c][0]
        f += n + 20
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, f
    finish_curves()


# ---------------------------------------------------------------- export: the live rig

def to_art(m):
    """A Blender world/armature matrix (acting on the XZ plane) -> the 2D affine on art px: x' = a x + c y + tx,
    y' = b x + d y + ty."""
    # art -> blender: X = (x - W/2)/100, Z = (H/2 - y)/100 ; blender -> art: x = 100 X + W/2, y = H/2 - 100 Z
    m00, m02, m03 = m[0][0], m[0][2], m[0][3]
    m20, m22, m23 = m[2][0], m[2][2], m[2][3]
    cx, cy = W_PX / 2, H_PX / 2
    a, cc = m00, -m02
    b, d = -m20, m22
    tx = 100 * m03 + cx - a * cx - cc * cy
    ty = cy - 100 * m23 - b * cx - d * cy
    return a, b, cc, d, tx, ty


def fx_affine(m, size):
    """A sprite quad's world matrix -> the 2D affine taking the unit square (centred on 0, y down) to art px."""
    k = 100 * size
    return (k * m[0][0], -k * m[2][0], -k * m[0][2], k * m[2][2], 100 * m[0][3] + W_PX / 2, H_PX / 2 - 100 * m[2][3])


def export(arm, parts, faces, fx):
    """rig/rig.json + rig/geo.bin (every part's mesh: rest positions in art px, UVs, triangles, 4 bone weights per
    vertex) + rig/<clip>.bin (per frame, per deforming bone, its 2D affine in art px, float32)."""
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    fade = lambda ob: ob.active_material.evaluated_get(dg).node_tree.nodes["fade"].outputs[0].default_value
    dst = os.path.join(OUT, "rig")
    os.makedirs(dst, exist_ok=True)
    bones = DEFORM
    bidx = {b: i for i, b in enumerate(bones)}
    geo = bytearray()
    out_parts = []

    def mesh_out(ob, tex, box, extra):
        me = ob.data
        names = {g.index: g.name for g in ob.vertex_groups}
        vs, uvs = [], [None] * len(me.vertices)
        uvl = me.uv_layers[0].data
        for poly in me.polygons:
            for li in poly.loop_indices:
                uvs[me.loops[li].vertex_index] = tuple(uvl[li].uv)
        bi, bw = [], []
        for v in me.vertices:
            X, Z = v.co.x, v.co.z
            vs += [100 * X + W_PX / 2, H_PX / 2 - 100 * Z]
            ws = sorted(((g.weight, names[g.group]) for g in v.groups if g.weight > .004), reverse=True)[:4]
            tot = sum(w for w, _ in ws) or 1.0
            q = [int(round(255 * w / tot)) for w, _ in ws]
            if q:
                q[0] += 255 - sum(q)
            ids = [bidx[nm] for _, nm in ws]
            while len(q) < 4:
                q.append(0)
                ids.append(0)
            bi += ids
            bw += q
        tris = []
        for poly in me.polygons:
            vv = list(poly.vertices)
            tris += [vv[0], vv[1], vv[2], vv[0], vv[2], vv[3]]
        rec = dict(extra, name=ob.name, tex=tex, box=box, verts=len(me.vertices), tris=len(tris) // 3)
        rec["o_pos"] = len(geo); geo.extend(struct.pack(f"<{len(vs)}f", *vs))
        rec["o_uv"] = len(geo); geo.extend(struct.pack(f"<{2 * len(uvs)}f", *[c for uv in uvs for c in (uv[0], 1 - uv[1])]))
        rec["o_idx"] = len(geo); geo.extend(struct.pack(f"<{len(tris)}H", *tris))
        while len(geo) % 4:
            geo.append(0)
        rec["o_bi"] = len(geo); geo.extend(bytes(bi))
        rec["o_bw"] = len(geo); geo.extend(bytes(bw))
        while len(geo) % 4:
            geo.append(0)
        return rec

    for nm in META["order"]:
        box = [v / K for v in META["parts"][nm]["box"]]
        out_parts.append(mesh_out(parts[nm], nm, box, {"alpha": "wisp" if nm == "wisp" else None}))
        if nm == "head":                                  # the faces draw right over the head
            for f, ob in faces.items():
                out_parts.append(mesh_out(ob, "face_" + f, [v / K for v in META["faces"][f]["box"]], {"face": f}))
    open(os.path.join(dst, "geo.bin"), "wb").write(bytes(geo))
    clips = {}
    fx_names = [k for k, _, _ in FX_KINDS]
    for c, (n, loop) in CLIPS.items():
        nf = n if loop else n + 1
        buf = bytearray()
        face_track, wisp_a, fx_draws = [], [], []
        for k in range(nf):
            sc.frame_set(STARTS[c] + k)
            dg = bpy.context.evaluated_depsgraph_get()
            ae = arm.evaluated_get(dg)
            for bn in bones:
                pb = ae.pose.bones[bn]
                m = ae.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
                buf.extend(struct.pack("<6f", *to_art(m)))
            cur = 0
            for fi, f in enumerate(FACES[1:], 1):
                ob = faces.get(f)
                if ob and fade(ob) > .5:
                    cur = fi
            face_track.append(cur)
            wisp_a.append(round(fade(bpy.data.objects["wisp"]), 3))
            draws = []
            oid = 0
            for kind, obs in fx.items():
                for ob in obs:
                    oid += 1
                    a = fade(ob)
                    if a <= .003:
                        continue
                    # the unit square centred on 0 (sprite space, y down) -> art px, through the quad (-s..s)
                    mw = ob.evaluated_get(dg).matrix_world
                    s = ob["fx_size"] / 200.0
                    aa = fx_affine(mw, 2 * s)
                    draws.append([fx_names.index(kind), oid] + [round(v, 3) for v in aa] + [round(a, 3)])
            fx_draws.append(draws)
        open(os.path.join(dst, f"{c}.bin"), "wb").write(bytes(buf))
        clips[c] = {"frames": nf, "loop": loop, "face": face_track, "alpha": {"wisp": wisp_a}, "fx": fx_draws}
    # each shoe's sole, in art px at rest (the game turns them through the foot bones for the shadows)
    meta = {"version": 1, "fps": FPS, "art": [W_PX, H_PX], "cx": W_PX / 2, "ground_y": GROUND, "top_y": 4,
            "rest_height": GROUND - 4, "bones": bones, "parts": out_parts, "faces": FACES,
            "fx": fx_names, "shoes": {"foot_l": [205, 412, GROUND], "foot_r": [628, 856, GROUND]},
            "clips": clips}
    json.dump(meta, open(os.path.join(dst, "rig.json"), "w"), separators=(",", ":"))
    print("EXPORT", dst, "bones", len(bones), "parts", len(out_parts), "geo", len(geo))


# ---------------------------------------------------------------- QA renders

def render(clips, step=1):
    sc = bpy.context.scene
    ren = os.path.join(OUT, "renders")
    for c in clips:
        n, loop = CLIPS[c]
        d = os.path.join(ren, c)
        os.makedirs(d, exist_ok=True)
        for old in os.listdir(d):
            os.remove(os.path.join(d, old))
        for k in range(0, n if loop else n + 1, step):
            sc.frame_set(STARTS[c] + k)
            sc.render.filepath = os.path.join(d, f"{k:04d}.png")
            bpy.ops.render.render(write_still=True)


if __name__ == "__main__" and "--" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:]
    steps = (args[0] if args else "build,export,render").split(",")
    clips = args[1].split(",") if len(args) > 1 and args[1] else list(CLIPS)
    step = int(args[2]) if len(args) > 2 else 1
    arm, parts, faces, fx = build()
    animate(arm, faces, fx, list(CLIPS))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "doc_rig.blend"))
    if "export" in steps:
        export(arm, parts, faces, fx)
    if "render" in steps:
        render(clips, step)
    print("DONE doc_rig", steps, clips)
