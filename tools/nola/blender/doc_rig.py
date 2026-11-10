"""Doc, the voodoo showman: his layered cut-out rig in Blender, every clip keyed there, exported as a LIVE rig the game
poses itself on every screen refresh (no baked frames), plus QA renders of every clip.

Parts (art/nola-src/doc_parts/: each piece drawn on its own canvas by the image model, tools/nola/doc_regen.py -
his hair under the hat, the hat's whole brim, a round cap on each shoulder and the trousers up to the waist are real
drawing, not smears) are separate meshes, each a grid fitted to its own pixels and bent by the bones it belongs to
(weights below): coat_back, leg_r, leg_l, cane, head, body, hat, arm_r, arm_l; each reaction face is a whole head of
its own, shown instead of the neutral one.

The rig, second pass (2026-11-09, owner: "rigid / uncanny / unhuman ... clothes like real clothes ... the flame its
own animation"). What makes a cut-out read as a paper doll is a stiff trunk, limbs that all move on the same frame,
cloth that only follows, and a figure that ever holds still; so:
  root > hips (the weight: it slides, dips and TILTS - the pelvis) > spine1 > spine2 > chest (breathes) - four bends
    from the pelvis to the collar, so the line of action is a curve and the shoulders can counter the hips
  chest > clav_l / clav_r (the shoulders: they rise on a breath, shrug, drop in a sigh) > upper > fore > hand
  chest > neck > head > face (slides the features a few px inside the skull: a head TURN and a nod, which a flat
    rotation cannot give) ; head > hat > feather1 > feather2 ; chest > cravat1 > cravat2
  the open hand: thumb + three fingers of two bones each (they curl, fan and ripple one after another)
  the cane hand holds the skull knob: its arm is IK to a wrist target, the cane keeps its own angle (plumb unless
    keyed), tilts about its planted tip when the body pulls away, and twirls as a wheel seen nearly edge-on
  hips > coat tails: four bones a side and three down the back panel, run as CLOTH (a chain of points with
    inertia, drag, a pull back to their drawn hang, a breeze that travels down them, flaring when he drops) - not
    keyed, simulated from whatever the body does
  hips > thigh > shin (IK to ankle targets on the root: the shoes stay planted) > foot
  root > orb: where the green flame floats - put over the palm every frame but never turned by the arm (it hovers
    ABOVE the hand whatever the wrist does), lifted, tossed and swelled by its own channels. The flame itself is not a picture: the
    game draws it live (frontend/charrig.js: a shader flame, glow, embers) on a spring that trails this bone.
Every action is keyed pose to pose with eased keys and OVERLAP (each link of a chain plays the same curve a few
frames later than the one before), the head stays level against the trunk's tilt on a spring, and the idle never
stops (two breaths and one shift of weight in its 8 s).

  blender.exe -b --factory-startup --python tools/nola/blender/doc_rig.py -- [build,export,render] [clip,..] [step]
-> art/blender/chars/doc_rig/doc_rig.blend, rig/ (rig.json, geo.bin, <clip>.bin: the live rig), renders/<clip>/ (QA;
"rom" is a range-of-motion stress test for seams, rendered on request, never exported)."""
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
QA_CLIPS = {"rom": (300, False)}                  # keyed and rendered for checking the seams; not in the game
ALL_CLIPS = dict(CLIPS, **QA_CLIPS)
FACES = ["neutral"] + list(META["faces"])
PALM0 = (852, 446)                                # the open palm's middle (art px): the flame's anchor on the hand
HOVER = 58                                        # how far above the palm the orb floats at rest


def u(x, y):
    return ((x - W_PX / 2) / 100.0, (H_PX / 2 - y) / 100.0)


def chain(name, pts, parent, opt=None):
    """Bones name1..nameN along a polyline, each connected to the one before."""
    out = []
    for k in range(len(pts) - 1):
        out.append((f"{name}{k + 1}", pts[k], pts[k + 1], parent if k == 0 else f"{name}{k}",
                    dict(opt or {}) if k == 0 else {"connect": True}))
    return out


TAIL_L = [(432, 700), (411, 800), (390, 900), (368, 1006), (345, 1112)]
TAIL_R = [(592, 700), (616, 800), (640, 900), (671, 1011), (702, 1122)]
TAIL_B = [(512, 700), (512, 800), (512, 900), (512, 1004)]
FINGERS = {"f1": [(876, 450), (912, 424), (936, 364)], "f2": [(884, 458), (932, 440), (984, 396)],
           "f3": [(884, 472), (934, 462), (990, 446)]}

# name, head, tail, parent, options (art px)
BONES = [
    ("root", (512, 1506), (512, 1446), None, {}),
    ("hips", (512, 690), (512, 640), "root", {}),
    ("spine1", (512, 640), (512, 560), "hips", {"connect": True}),
    ("spine2", (512, 560), (512, 470), "spine1", {"connect": True}),
    ("chest", (512, 470), (500, 372), "spine2", {"connect": True}),
    ("clav_l", (486, 392), (392, 428), "chest", {"noscale": True}),
    ("clav_r", (522, 394), (606, 440), "chest", {"noscale": True}),
    ("neck", (500, 372), (498, 300), "chest", {"connect": True, "noscale": True}),
    ("head", (498, 300), (488, 172), "neck", {"connect": True}),
    ("face", (482, 290), (482, 230), "head", {}),
    ("hat", (488, 172), (480, 20), "head", {}),
    ("feather1", (560, 140), (604, 97), "hat", {}),
    ("feather2", (604, 97), (648, 54), "feather1", {"connect": True}),
    ("cravat1", (510, 382), (511, 452), "chest", {"noscale": True}),
    ("cravat2", (511, 452), (512, 524), "cravat1", {"connect": True}),
    ("upper_l", (392, 428), (312, 652), "clav_l", {"connect": True}),
    ("fore_l", (312, 652), (236, 724), "upper_l", {"connect": True}),
    ("hand_l", (236, 724), (186, 834), "fore_l", {"connect": True, "norot": True, "noscale": True}),
    ("fingers_l", (178, 772), (138, 888), "hand_l", {}),
    ("thumb_l", (226, 784), (236, 860), "hand_l", {}),
    ("cane", (186, 834), (186, 1500), "hand_l", {"norot": True, "noscale": True}),
    ("upper_r", (606, 440), (684, 652), "clav_r", {"connect": True}),
    ("fore_r", (684, 652), (792, 548), "upper_r", {"connect": True}),
    ("hand_r", (792, 548), (850, 462), "fore_r", {"connect": True}),
    ("thumb_r", (812, 452), (846, 412), "hand_r", {}),
    *[b for f, pts in FINGERS.items() for b in chain(f + "_r", pts, "hand_r")],
    # the flame's bone hangs off the ROOT and is put where the palm is, plus its hover, every frame (orb_pt): as a
    # child of the hand its hover turned with the arm - a raised arm swung the flame out sideways across his face
    ("orb", PALM0, (PALM0[0], PALM0[1] - 60), "root", {}),
    *chain("tail_l", TAIL_L, "hips"),
    *chain("tail_r", TAIL_R, "hips"),
    *chain("tail_b", TAIL_B, "hips"),
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
CELL = {"coat_back": 12, "leg_r": 10, "leg_l": 10, "cane": 12, "head": 8, "body": 10, "hat": 9, "arm_r": 5,
        "arm_l": 6, "wisp": 14, "face": 8}


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


def along(y, name, joints, top, soft_px=38):
    """Weights down a chain by height: `top` above the first joint, then name1.. below each joint in turn, each
    joint blended over soft_px either side (a hem that curves, never a hinge)."""
    names = [top] + [f"{name}{k + 1}" for k in range(len(joints))]
    ks = [smooth(j - soft_px, j + soft_px, y) for j in joints]
    w, carry = {}, 1.0
    for k, nm in enumerate(names):
        nxt = ks[k] if k < len(ks) else 0.0
        w[nm] = carry * (1 - nxt)
        carry *= nxt
    return {k: v for k, v in w.items() if v > 1e-4}


def weights(part, x, y):
    """Bone weights for a vertex of a part (art px). Region rules first, soft nearest-bone blending inside."""
    p = (x, y)
    if part == "cane":
        return {"cane": 1.0}
    if part == "wisp":                                    # (the painted wisp: a stand-in for the live flame in QA renders)
        return {"orb": 1.0}
    if part == "hat":
        # the feather stands right of the crown (whose right edge runs from (590, 30) down-left to (555, 150))
        s = x - (590 - (y - 30) * .29)
        if 40 < y < 168 and s > -8:
            k = smooth(-8, 14, s)
            _, t = seg(p, (560, 140), (648, 54))
            f2 = smooth(.3, .7, t)
            return {"hat": 1 - k, "feather1": k * (1 - f2), "feather2": k * f2}
        return {"hat": 1.0}
    if part in ("head", "face"):
        if y > 380:                                       # the neck hidden under the collar rides the chest
            return {"chest": 1.0}
        k = smooth(380, 352, y)                           # collar -> neck
        h = smooth(340, 310, y)                           # neck -> head (the jaw and up are all head)
        wf = .92 * math.exp(-((x - 480) / 54.0) ** 2 - ((y - 262) / 84.0) ** 2)   # the features: eyes, nose, grin
        return {"chest": 1 - k, "neck": k * (1 - h), "head": k * h * (1 - wf), "face": k * h * wf}
    if part in ("leg_l", "leg_r"):
        s = part[-1]
        hipy = 700
        if y > 1418:                                      # spat and shoe: the foot
            k = smooth(1405, 1432, y)
            return {f"shin_{s}": 1 - k, f"foot_{s}": k}
        top = smooth(hipy - 30, hipy + 40, y)             # the top of the thigh, under the coat, sits on the hips
        kn = smooth(1000, 1120, y)                         # thigh -> shin across the knee
        return {"hips": 1 - top, f"thigh_{s}": top * (1 - kn), f"shin_{s}": top * kn}
    if part == "coat_back":
        return along(y, "tail_b", [730, 800, 900], "hips", 44)
    if part == "body":
        if y < 700 or (430 < x < 594 and y < 760):        # the torso: chest over the two spine bones over the hips
            kc, ks2, ks1 = smooth(425, 515, y), smooth(520, 600, y), smooth(608, 682, y)
            w = {"chest": 1 - kc, "spine2": kc * (1 - ks2), "spine1": kc * ks2 * (1 - ks1), "hips": kc * ks2 * ks1}
            # the shoulders ride their clavicles (the coat's shoulder lifts with a breath or a shrug)
            cl = (1 - smooth(398, 452, x)) * (1 - smooth(438, 486, y)) * .85
            cr = smooth(556, 610, x) * (1 - smooth(444, 490, y)) * .85
            if cl > .004 or cr > .004:
                w = {k: v * (1 - cl - cr) for k, v in w.items()}
                w["clav_l"], w["clav_r"] = cl, cr
            if 462 < x < 552 and 372 < y < 540:           # the cravat's ruffles
                c = smooth(372, 420, y) * (1 - smooth(505, 540, y)) * (1 - smooth(534, 552, x)) * smooth(462, 480, x)
                lo = smooth(430, 480, y)
                w = {k: v * (1 - .85 * c) for k, v in w.items()}
                w["cravat1"], w["cravat2"] = .85 * c * (1 - lo), .85 * c * lo
            return {k: v for k, v in w.items() if v > 1e-4}
        side = "l" if x < 512 else "r"                    # the front coat tails, from the waist down
        return along(y, f"tail_{side}", [735, 800, 900, 1008], "hips", 42)
    if part == "arm_l":
        d = math.hypot(x - 392, y - 428)
        if d < 34:                                        # the shoulder blends into the clavicle
            k = smooth(34, 8, d)
            return {"upper_l": 1 - .7 * k, "clav_l": .7 * k}
        if y > 788 and x < 222:                           # the fingers draped over the skull
            k = smooth(788, 822, y)
            return {"hand_l": 1 - k, "fingers_l": k}
        if x > 214 and y > 792:                           # the thumb, right of the knob
            k = smooth(792, 818, y)
            return {"hand_l": 1 - k, "thumb_l": k}
        return soft(p, ["upper_l", "fore_l", "hand_l"], 34)
    if part == "arm_r":
        d = math.hypot(x - 606, y - 440)
        if d < 36:
            k = smooth(36, 8, d)
            return {"upper_r": 1 - .7 * k, "clav_r": .7 * k}
        # past the knuckles: each digit on its own bones (they are spread apart, so the nearest digit wins)
        best, bd, bt = None, 1e9, 0.0
        for f, pts in FINGERS.items():
            l1, l2 = math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2])
            d1, t1 = seg(p, pts[0], pts[1])
            d2, t2 = seg(p, pts[1], pts[2])
            dd, t = (d1, t1 * l1 / (l1 + l2)) if d1 <= d2 else (d2, (l1 + t2 * l2) / (l1 + l2))
            if dd < bd:
                best, bd, bt, bj = f, dd, t, l1 / (l1 + l2)
        dth, tth = seg(p, BONE["thumb_r"][1], BONE["thumb_r"][2])
        if dth < bd and dth < 17 and y < 452:
            k = smooth(.0, .35, tth)
            return {"hand_r": 1 - k, "thumb_r": k}
        if bd < 17 and bt > .04:
            k = smooth(.0, .22, bt)                       # knuckle
            j = smooth(bj - .13, bj + .13, bt)            # the finger's own joint
            return {"hand_r": 1 - k, best + "_r1": k * (1 - j), best + "_r2": k * j}
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
    faces["neutral"] = parts["head"]                       # (each face is a whole head: one shows at a time)
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
    """A damped spring on a value: follows its target with lag and overshoot."""

    def __init__(self, freq, zeta):
        self.w, self.z = 2 * math.pi * freq, zeta
        self.x = self.v = 0.0

    def snap(self, target):
        self.x, self.v = target, 0.0
        return target

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


def kf(x, *keys):
    """Pose to pose, but flowing: the value at frame x of keys (frame, value[, "i"]). The curve through the keys is
    a shape-preserving cubic (PCHIP): it runs THROUGH a key that lies on the way between its neighbours without
    slowing, and turns round smoothly, at rest for an instant, on a key that is an extreme - never past a key, and
    never the stop-go of an ease per segment (which reads as a robot hitting marks). Held before the first key
    and after the last, where it starts and ends at rest. A key tagged "i" is an IMPACT: the value falls onto it
    gathering speed and stops dead (a cane on the pavement, a hat back on a head, a catch).
    Called with x = i - lag, the same curve plays later: that is the overlap down a chain."""
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
    if len(keys[k + 1]) > 2 and keys[k + 1][2] == "i":
        return y0 + (y1 - y0) * t ** 2.4

    def slope(j):                                         # the curve's slope at key j
        if j <= 0 or j >= n - 1:
            return 0.0
        if (len(keys[j]) > 2 and keys[j][2] == "i") or (len(keys[j + 1]) > 2 and keys[j + 1][2] == "i"):
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


def ring(x, f0, amp, freq, decay):
    """What is left over after an accent at frame f0: a decaying wobble (a landing, a catch, a stop)."""
    t = (x - f0) / FPS
    return amp * math.exp(-decay * t) * math.sin(2 * math.pi * freq * t) if t > 0 else 0.0


def bump(t, a, b):
    if t <= a or t >= b:
        return 0.0
    return math.sin(math.pi * (t - a) / (b - a))


def bump_e(t, a, b):
    """bump with eased shoulders: a soft rise, a soft fall (no linear corners)."""
    return ease(bump(t, a, b))


def loop_wave(a, *terms):
    """sum of amp*sin(k*a + ph) - amp*sin(ph): periodic over the loop and exactly 0 at its start."""
    return sum(amp * (math.sin(k * a + ph) - math.sin(ph)) for amp, k, ph in terms)


def dwell(s):
    """A sine that lingers at its ends and hurries through the middle: a weight shift settles, it does not swing."""
    return s * (1.35 - .35 * s * s)


def breath_curve(th, k=.45):
    """One breath a turn of th: in a little faster than out, a pause on empty lungs (never a plain sine)."""
    return .5 - .5 * math.cos(th - k * math.sin(th))


DIGITS = ("thumb_r", "f1", "f2", "f3")
CHANNELS = ("sx bob pelvis s1 s2 ch breath clav_l clav_r head face_x face_y hat hat_lift hat_x hat_sy feather "
            "hand_lx hl fing_l thumb_l cane_r cane_lift cane_spin cane_len "
            "ur fr hr thumb_r f1 f2 f3 orb_x orb_y orb_s orb_a "
            "lift_l lift_r step_l step_r foot_l foot_r wind").split()
REST = {c: 0.0 for c in CHANNELS}
REST.update(cane_len=1.0, orb_s=1.0, orb_a=1.0, hat_sy=1.0, wind=1.0)
CANE_A = -.24                                             # the twirl's wheel, seen nearly edge-on: its width / the cane


ACT = {
    "*": dict(sx=1.9, bob=1.6, pelvis=1.8, s1=1.7, s2=1.7, ch=1.7, clav_l=1.5, clav_r=1.5, head=1.6, face_x=1.4,
              face_y=1.4, ur=1.4, fr=1.4, hr=1.3, hat=1.4),
    "idle": dict(sx=1.7, bob=1.3, pelvis=1.6, s1=1.6, s2=1.6, ch=1.6, clav_l=1.4, clav_r=1.4, head=1.4, face_x=1.3,
                 face_y=1.3, ur=1.6, fr=1.6, hr=1.5),
    "enter": dict(bob=1.0, sx=1.3, pelvis=1.2, s1=1.2, s2=1.2, ch=1.2, head=1.1, face_y=1.0, ur=1.0, fr=1.0, hr=1.0, hat=1.0),
    "exit": dict(bob=1.0, sx=1.3, pelvis=1.2, s1=1.2, s2=1.2, ch=1.2, head=1.1, face_y=1.0, ur=1.0, fr=1.0, hr=1.0, hat=1.0),
    "big_win": dict(bob=1.3, sx=1.6, pelvis=1.5, s1=1.5, s2=1.5, ch=1.5, ur=1.0, fr=1.0, hr=1.0, face_y=1.2),
    "conjure": dict(ur=1.25, fr=1.25),
    "rom": {k: 1.0 for k in ("sx bob pelvis s1 s2 ch clav_l clav_r head face_x face_y ur fr hr hat").split()},
}


def twirl(c, th):
    """The cane as a wheel turning beside him, seen nearly edge-on: th = how far round (0 = tip down)."""
    x, y = CANE_A * math.sin(th), math.cos(th)
    c["cane_spin"] = math.degrees(math.atan2(x, y))
    c["cane_len"] = max(.16, math.hypot(x, y))


def drive(name, i, n):
    """The animator's channels for frame i of a clip: degrees for turns, art px for moves. Signs: a bone that points
    up (spine, head) leans to screen LEFT on a positive turn; one that hangs (arm, tail) swings to screen RIGHT.
    The board is to his right (+x); the flame hand is his right-of-screen hand, the cane the left."""
    c = dict(REST)
    t = i / FPS
    p = i / n
    T = n / FPS
    if name == "idle":
        a = 2 * math.pi * p
        lg = lambda fr: 2 * math.pi * fr / n
        W = lambda fr=0: dwell(math.sin(a - lg(fr))) - dwell(math.sin(-lg(fr)))          # the weight: right, then left
        B = lambda fr=0: breath_curve(2 * (a - lg(fr))) - breath_curve(-2 * lg(fr))      # two breaths a loop
        w = W()
        c["breath"] = B()
        # the weight settles onto one leg, then the other: the hips slide over it and that hip rides high, the spine
        # curves back the other way link by link, each a few frames after the one below
        c["sx"] = 10 * w
        c["pelvis"] = 2.1 * W(1)
        c["s1"], c["s2"], c["ch"] = -1.0 * W(3), -1.2 * W(6), -1.1 * W(9)
        c["clav_l"] = -1.7 * B(2) + .5 * W(10)
        c["clav_r"] = 1.7 * B(4) + .5 * W(10)
        # the free leg lets go: its heel comes off the ground a little, the toe stays
        plant(c, "l", 4.2 * max(0.0, w) ** 1.5)
        plant(c, "r", -4.2 * max(0.0, -w) ** 1.5)
        # the head: a look across at his flame (and the board behind it), a glance back the other way
        look = kf(i, (0, 0), (40, 0), (60, 1), (112, 1), (134, .1), (160, .1), (178, -.7),
                  (206, -.7), (232, 0), (240, 0))
        c["face_x"] = 5.5 * look + .8 * W(12)
        c["face_y"] = 2.2 * max(0.0, look) - .9 * B(6)
        c["head"] = -2.4 * look + loop_wave(a, (.5, 3, 1.3))
        c["hat"] = loop_wave(a, (.5, 2, 2.2))
        # the flame hand weighs its flame: the elbow floats on the breath, the wrist rolls, the fingers ripple one
        # after another; once a loop he stokes it - the fingers curl in turn and the flame climbs
        c["ur"] = 1.5 * B(5) + loop_wave(a, (1.3, 1, 1.2))
        c["fr"] = 1.0 * B(8) + loop_wave(a, (2.2, 2, .5))
        c["hr"] = loop_wave(a, (2.8, 2, -.3), (1.1, 3, 1.0))
        for k, f in enumerate(DIGITS):
            c[f] = loop_wave(a, (3.6, 3, -.55 * k), (1.4, 5, 1.3 - .7 * k)) + \
                (-7 if k == 0 else 13) * bump_e(i, 150 + 5 * k, 192 + 5 * k)
        c["orb_y"] = 16 * bump_e(i, 158, 216)
        c["orb_s"] = 1 + .16 * bump_e(i, 160, 218)
        # the cane hand: fingers drum on the skull once, the thumb strokes it
        c["fing_l"] = -9 * sum(bump_e(i, s, s + 7) for s in (96, 105, 114))
        c["thumb_l"] = loop_wave(a, (2.0, 2, .7))
    elif name == "enter":
        # up out of a deep plie, curled toward the board: he uncurls from the hips to the hat (each link later than
        # the one below), passes upright, settles; the palm sweeps out and the flame blooms on it
        up = lambda lag=0: kf(i - lag, (0, 1), (5, 1.03), (21, -.10), (31, .03), (40, 0))
        c["bob"] = 64 * up()
        c["sx"] = -14 * up(1)
        c["pelvis"] = -3 * up(1)
        c["s1"], c["s2"], c["ch"] = -5 * up(2), -6 * up(4), -5 * up(6)
        c["head"] = -9 * up(9)
        c["face_y"] = 5 * up(8)
        c["hat"] = -7 * up(11)
        c["clav_l"] = -3.5 * bump_e(i, 4, 30)
        c["clav_r"] = 3.5 * bump_e(i, 6, 32)
        c["breath"] = kf(i, (0, 0), (18, 1), (40, 0))
        c["ur"] = kf(i, (0, -30), (6, -32), (25, 9), (37, 0))
        c["fr"] = kf(i - 3, (0, 46), (6, 48), (25, -9), (36, 0))
        c["hr"] = kf(i - 6, (0, 24), (6, 26), (24, -12), (34, 0))
        for k, f in enumerate(DIGITS):                     # the fingers open one after another
            c[f] = (-.5 if k == 0 else 1) * kf(i - 3 * k, (0, 24), (13, 24), (24, -7), (33, 0))
        c["orb_s"] = kf(i, (0, .05), (13, .05), (25, 1.4), (38, 1.0))
        c["orb_a"] = kf(i, (10, 0), (18, 1))
        c["orb_y"] = kf(i, (12, -30), (26, 26), (40, 0))
        c["fing_l"] = -6 * bump_e(i, 20, 36)
        c["wind"] = kf(i, (0, 0), (30, 1))
    elif name == "exit":
        # he closes his hand on the flame - it gutters out in a wisp of smoke - and sinks into a bow
        k = kf(i, (6, 0), (27, 1))
        c["bob"] = 56 * k
        c["sx"] = -12 * kf(i - 1, (6, 0), (27, 1))
        c["s1"], c["s2"], c["ch"] = -5 * kf(i - 2, (6, 0), (27, 1)), -6 * kf(i - 4, (6, 0), (27, 1)), -5 * kf(i - 6, (6, 0), (27, 1))
        c["head"] = -9 * kf(i - 8, (6, 0), (27, 1))
        c["face_y"] = 5 * kf(i - 6, (6, 0), (27, 1))
        c["hat"] = -8 * kf(i - 10, (6, 0), (27, 1))
        for kk, f in enumerate(DIGITS):                    # little finger first
            c[f] = (-.5 if kk == 0 else 1) * 25 * kf(i - 2 * (3 - kk), (0, 0), (9, 1))
        c["hr"] = kf(i, (0, 0), (10, 10), (26, 22))
        c["fr"] = kf(i - 2, (4, 0), (26, 40))
        c["ur"] = kf(i, (6, 0), (27, -26))
        c["orb_s"] = kf(i, (0, 1), (4, 1.15), (12, .1, "i"))
        c["orb_a"] = kf(i, (6, 1), (13, 0))
        c["orb_y"] = kf(i, (0, 0), (12, -24))
    elif name == "anticipation":
        # two scatters down: he goes up on his toes on a held breath, shoulders high, leaning in, eyes on the
        # board; the flame swells and shivers in fingers that slowly close on it
        e = lambda lag=0: kf(i - lag, (0, 0), (11, 1), (40, 1), (53, 0))
        rise = lambda lag=0: kf(i - lag, (0, 0), (3, -.3), (11, 1.1), (17, 1), (40, 1), (53, 0))
        c["breath"] = kf(i, (0, 0), (9, 1), (40, .92), (53, 0))
        c["sx"] = 9 * e()
        c["pelvis"] = -1.0 * e(1)
        c["s1"], c["s2"], c["ch"] = -1.5 * e(2), -1.9 * e(4), -1.7 * e(6)
        c["clav_l"], c["clav_r"] = -3.4 * rise(3), 3.4 * rise(5)
        c["bob"] = -5 * rise()
        plant(c, "l", 5 * max(0.0, rise()))
        plant(c, "r", -5 * max(0.0, rise()))
        c["face_x"] = 6.5 * e(5)
        c["face_y"] = 1.5 * e(6)
        c["head"] = -3.2 * e(8)
        tr = math.sin(2 * math.pi * 9.5 * t) * kf(i, (10, 0), (24, 1), (40, 1), (48, 0))     # a shiver, in the hand only
        c["ur"] = -8 * e(3)
        c["fr"] = 15 * e(6)
        c["hr"] = 6 * e(9) + 1.3 * tr
        for k, f in enumerate(DIGITS):
            c[f] = (-.5 if k == 0 else 1) * 15 * kf(i, (4 + 3 * k, 0), (34 + 3 * k, 1), (43, 1), (53, 0)) + \
                1.6 * math.sin(2 * math.pi * 9.5 * t + k) * abs(tr)
        c["orb_s"] = 1 + .5 * kf(i, (4, 0), (38, 1), (44, 1), (53, 0)) + .05 * tr
        c["orb_y"] = 20 * e(8)
        c["fing_l"] = 4 * e()
    elif name == "win":
        # a dip, then up with his head back in a laugh - the shoulders shake with it - while the flame hand
        # flourishes and the flame flares; two taps of the cane, a tap of the toe, and he settles
        chk = math.sin(2 * math.pi * (i - 12) / 10.0) * kf(i, (10, 0), (16, 1), (40, .7), (58, 0))
        c["breath"] = kf(i, (0, 0), (5, -.3), (13, 1), (60, .5), (88, 0)) + .25 * chk
        c["bob"] = kf(i, (0, 0), (5, 11), (12, -5), (20, 0), (96, 0)) + 2.6 * abs(chk)
        sway = lambda lag=0: kf(i - lag, (0, 0), (8, -.5), (22, 1), (44, -.75), (64, .6), (86, 0))
        c["sx"] = 8 * sway()
        c["pelvis"] = 1.6 * sway(1)
        c["s1"], c["s2"], c["ch"] = -.9 * sway(3), -1.1 * sway(6), -1.0 * sway(9)
        c["clav_l"] = -4.2 * chk + kf(i, (0, 0), (5, 2), (13, -2), (24, 0))
        c["clav_r"] = 4.2 * math.sin(2 * math.pi * (i - 13.5) / 10.0) * kf(i, (10, 0), (16, 1), (40, .7), (58, 0)) + \
            kf(i, (0, 0), (5, -2), (13, 2), (24, 0))
        c["head"] = kf(i - 4, (0, 0), (5, -2), (15, 4.5), (56, 3), (80, 0)) + .8 * chk
        c["face_y"] = kf(i - 3, (0, 0), (5, 2.5), (15, -4.5), (56, -3), (80, 0))   # head thrown back
        c["face_x"] = 3 * sway(8)
        flo = lambda lag=0: kf(i - lag, (0, 0), (5, -.3), (19, 1), (42, .75), (72, 0))
        c["ur"] = 14 * flo()
        c["fr"] = 22 * flo(3)
        c["hr"] = kf(i - 6, (0, 0), (5, 10), (17, -16), (30, 8), (44, -4), (60, 0))       # the wrist rolls
        for k, f in enumerate(DIGITS):                     # the fingers fan open, one after another
            c[f] = (-.5 if k == 0 else 1) * kf(i - 2 * k, (0, 0), (8, 10), (19, -13), (46, -8), (74, 0))
        c["orb_s"] = kf(i, (0, 1), (8, .95), (21, 1.55), (44, 1.25), (74, 1))
        c["orb_y"] = kf(i - 2, (0, 0), (8, -6), (22, 44), (40, 20), (74, 0))
        # the cane: up and DOWN on the beat (it falls faster than it rises), the hand giving with each tap
        tap = kf(i, (38, 0), (45, 1), (50, 0, "i"), (55, 0), (61, .85), (66, 0, "i"))
        c["cane_lift"] = 48 * tap
        c["hand_lx"] = -8 * tap
        c["hl"] = 5 * tap + ring(i, 50, 2.5, 6, 9) + ring(i, 66, 2.5, 6, 9)
        c["bob"] += ring(i, 50, 1.6, 5, 10) + ring(i, 66, 1.6, 5, 10)
        plant(c, "r", 13 * (bump_e(i, 70, 77) + bump_e(i, 80, 87)), "heel")      # the toe taps, the heel down
    elif name == "big_win":
        # he winds up and THROWS the flame overhead: it climbs, swells into a blaze and hangs there while he dances
        # under it - the hat jumps, the cane wheels round - then it drops back into his palm and he catches it
        c["breath"] = kf(i, (0, 0), (8, -.4), (22, 1), (100, .7), (126, 0))
        dance = kf(i, (26, 0), (38, 1), (84, 1), (100, 0))
        beat = lambda lag=0: math.sin(2 * math.pi * 2.0 * (i - lag - 26) / FPS)
        c["bob"] = kf(i, (0, 0), (8, 34), (17, -9), (26, 0), (101, 0), (108, 12), (120, 0)) + \
            11 * (.5 - .5 * math.cos(2 * math.pi * 4.0 * (i - 26) / FPS)) * dance
        c["sx"] = kf(i, (0, 0), (8, -6), (18, 6), (28, 0)) + 16 * beat() * dance
        c["pelvis"] = 3.8 * beat(1) * dance
        c["s1"], c["s2"], c["ch"] = -1.6 * beat(3) * dance, -2.0 * beat(6) * dance, -1.8 * beat(9) * dance
        c["clav_l"] = kf(i, (0, 0), (8, 3), (18, -5), (30, -1.5), (120, 0))
        c["clav_r"] = kf(i, (0, 0), (8, -3), (17, 7), (30, 2.5), (120, 0))
        # the throwing arm: pulled in, flung up (the forearm and the hand each a beat behind), held high, then the catch
        thr = lambda lag=0: kf(i - lag, (0, 0), (8, -.4), (19, 1), (94, .9), (102, .6), (108, .06), (114, .16), (124, 0))
        c["ur"] = 30 * thr() + 6 * beat(5) * dance              # the raised arm pumps on the beat
        c["fr"] = 44 * thr(3) - 9 * beat(8) * dance
        c["hr"] = kf(i - 5, (0, 0), (8, -12), (14, -26), (21, 20), (34, 6), (96, 6), (103, -4), (108, -15), (115, 3), (124, 0))
        for k, f in enumerate(DIGITS):
            c[f] = (-.5 if k == 0 else 1) * (kf(i - 2 * k, (0, 0), (8, 18), (17, -16), (96, -10), (104, 2), (109, 13), (120, 0))
                                               + 4 * math.sin(2 * math.pi * 3 * t - k) * dance)
        c["orb_y"] = kf(i, (0, 0), (8, -14), (13, -10), (38, 236), (60, 250), (80, 234), (94, 130), (103, 12), (108, -13), (114, 4), (124, 0))
        c["orb_x"] = kf(i, (12, 0), (24, 34), (40, 46), (82, 40), (103, 2), (112, 0)) + 10 * beat(4) * dance   # out past his hat, never across his face
        c["orb_s"] = kf(i, (0, 1), (8, .8), (38, 2.3), (82, 2.15), (103, 1.0), (108, .8), (114, 1.18), (124, 1))
        # eyes follow it up
        c["face_y"] = kf(i - 4, (0, 0), (8, 3), (24, -6), (84, -5), (104, 3), (120, 0))
        c["face_x"] = kf(i - 4, (0, 0), (10, 3), (30, 1), (120, 0)) + 2.5 * beat(10) * dance
        c["head"] = kf(i - 6, (0, 0), (8, -3), (24, 3), (100, 2), (120, 0)) - 2.2 * beat(12) * dance
        # the hat jumps with the blaze and drops back with a bounce
        c["hat_lift"] = kf(i, (20, 0), (31, 38), (44, 0, "i")) + max(0.0, ring(i, 44, 7, 4.5, 8))
        c["hat"] = kf(i, (20, 0), (31, 9), (44, 0, "i")) + ring(i, 44, 3, 4, 7)
        c["hat_sy"] = 1 + kf(i, (20, 0), (24, .05), (40, 0), (44, -.07, "i"), (50, 0))
        # the cane wheels round twice beside him and comes down
        sp = kf(i, (30, 0), (74, 1))
        twirl(c, 2 * math.pi * 2 * sp)
        c["cane_lift"] = kf(i, (22, 0), (32, 64), (72, 64), (80, 0, "i")) + max(0.0, ring(i, 80, 5, 6, 9))
        c["hand_lx"] = kf(i, (22, 0), (32, -24), (72, -24), (80, 0, "i"))
        c["hl"] = 9 * math.sin(2 * math.pi * 2 * sp) * bump_e(i, 28, 78) + ring(i, 80, 3, 6, 9)
        c["fing_l"] = -9 * bump_e(i, 26, 80)
        # heel and toe on the beat, foot after foot
        for s_, sgn, ph in (("l", 1, 0.0), ("r", -1, .5)):
            tp = max(0.0, math.sin(2 * math.pi * (1.0 * (i - 26) / FPS + ph))) ** 2 * dance
            plant(c, s_, -sgn * 12 * tp, "heel")
    elif name == "lose":
        # the breath goes out of him: shoulders drop, the head sinks and shakes - no, no - the flame gutters on a
        # limp hand; fingers drum the skull; then a shrug, a flick, and it is alight again
        down = lambda lag=0: kf(i - lag, (0, 0), (16, 1), (60, 1), (80, 0))
        c["breath"] = kf(i, (0, 0), (4, .35), (24, -.75), (58, -.5), (76, .5), (88, 0))
        c["bob"] = 8 * down()
        c["sx"] = -6 * down(1)
        c["pelvis"] = -1.2 * down(2)
        c["s1"], c["s2"], c["ch"] = .8 * down(3), 1.1 * down(6), 1.2 * down(9)
        shrug = bump_e(i, 62, 80)
        c["clav_l"] = 3.6 * down(4) - 6.5 * shrug
        c["clav_r"] = -3.6 * down(6) + 6.5 * bump_e(i, 63, 81)
        c["head"] = 5 * down(8)
        c["face_y"] = 4.5 * down(7)
        c["face_x"] = kf(i, (16, 0), (25, -6.5), (35, 6), (45, -4), (54, 0))            # "no"
        c["hat"] = -3 * down(12)
        c["ur"], c["fr"] = -7 * down(4), -15 * down(7)
        c["hr"] = -13 * down(10) + kf(i, (66, 0), (70, -8), (75, 12), (84, 0))            # and the relighting flick
        for k, f in enumerate(DIGITS):                     # the fingers hang limp
            c[f] = (-.4 if k == 0 else 1) * (19 * down(10 + 2 * k) + kf(i - 2 * k, (66, 0), (70, 10), (76, -12), (86, 0)))
        c["orb_s"] = kf(i, (0, 1), (5, 1.05), (20, .42), (66, .38), (77, 1.25), (88, 1))
        c["orb_y"] = kf(i, (0, 0), (20, -16), (66, -18), (78, 8), (88, 0))
        c["cane_r"] = 2.5 * down(6)
        c["fing_l"] = -11 * sum(bump_e(i, s, s + 7) for s in (40, 48, 56))                     # impatient
        c["wind"] = 1 - .4 * down()
    elif name == "cane_twirl":
        # a glance down at the cane, the weight comes off it, it lifts, wheels twice round beside him - quick in
        # the middle - and comes down with a rap; the body rides against the swing
        e = kf(i, (0, 0), (12, 1), (62, 1), (80, 0))
        sp = kf(i, (14, 0), (60, 1))
        th = 2 * math.pi * 2 * sp
        twirl(c, th)
        c["cane_lift"] = kf(i, (3, 0), (15, 60), (58, 60), (66, 0, "i")) + max(0.0, ring(i, 66, 5, 6, 9))
        c["hand_lx"] = kf(i, (3, 0), (15, -24), (58, -24), (66, 0, "i")) + 5 * math.cos(th) * bump_e(i, 14, 62) - 5 * bump_e(i, 14, 62)
        c["hl"] = 10 * math.sin(th) * bump_e(i, 12, 62) + ring(i, 66, 3, 6, 9)
        c["fing_l"] = -10 * bump_e(i, 10, 66) + 3 * math.sin(2 * th) * bump_e(i, 14, 60)
        c["thumb_l"] = 6 * math.sin(2 * th + 1) * bump_e(i, 14, 60)
        c["sx"] = 9 * kf(i, (0, 0), (12, 1), (58, 1), (78, 0))
        c["pelvis"] = 1.6 * kf(i - 1, (0, 0), (12, 1), (58, 1), (78, 0))
        c["s1"] = -.8 * e + .7 * math.sin(th - .5) * bump_e(i, 14, 62)
        c["s2"] = -1.0 * e + .9 * math.sin(th - .9) * bump_e(i, 14, 62)
        c["ch"] = -.9 * e + .8 * math.sin(th - 1.3) * bump_e(i, 14, 62)
        c["clav_l"] = -4 * kf(i, (2, 0), (14, 1), (58, 1), (68, -.4), (78, 0))
        c["bob"] = ring(i, 66, 3, 5, 9)
        c["face_x"] = kf(i - 2, (0, 0), (9, -5.5), (50, -5), (70, 0))             # watching it go round
        c["face_y"] = kf(i - 2, (0, 0), (9, 3), (50, 2.5), (70, 0))
        c["head"] = kf(i - 4, (0, 0), (10, 3.5), (50, 3), (72, 0))
        c["breath"] = kf(i, (0, 0), (14, .9), (60, .6), (80, 0))
        c["ur"] = 4 * e
        c["orb_s"] = 1 - .12 * e
    elif name == "hat_tip":
        # a flick of two fingers and his magic lifts the hat off his head: it tips, he nods under it, it settles
        # back with a bounce (the flame hand conducts it all)
        c["hr"] = kf(i, (0, 0), (7, -9), (14, 14), (40, 9), (52, -6), (62, 0))
        c["fr"] = kf(i - 2, (0, 0), (7, -5), (15, 9), (40, 7), (54, -3), (64, 0))
        c["ur"] = kf(i - 4, (0, 0), (8, -2), (16, 5), (42, 4), (62, 0))
        c["f1"] = kf(i, (0, 0), (7, 16), (13, -20), (40, -15), (52, 6), (62, 0))
        c["f2"] = kf(i - 2, (0, 0), (7, 12), (13, -12), (40, -8), (52, 5), (62, 0))
        c["f3"] = kf(i - 3, (0, 0), (8, 14), (30, 16), (56, 0))
        c["thumb_r"] = kf(i, (0, 0), (8, -8), (30, -9), (56, 0))
        c["orb_s"] = kf(i, (0, 1), (7, .92), (14, 1.3), (44, 1.15), (60, 1))
        c["orb_y"] = kf(i, (0, 0), (7, -5), (15, 12), (44, 8), (60, 0))
        c["hat_lift"] = kf(i, (8, 0), (10, -3), (21, 66), (28, 60), (42, 57), (53, 0, "i")) + max(0.0, ring(i, 53, 7, 5, 9))
        c["hat"] = kf(i, (10, 0), (24, 17), (42, 15), (53, 0, "i")) + ring(i, 53, 3, 4, 7)
        c["hat_x"] = kf(i, (10, 0), (24, -13), (42, -12), (53, 0, "i"))
        c["hat_sy"] = 1 + kf(i, (6, 0), (10, -.05), (15, .07), (23, 0), (50, 0), (53, -.07, "i"), (59, 0))
        nod = lambda lag=0: kf(i - lag, (14, 0), (26, 1), (38, 1), (52, 0))
        c["head"] = 6 * nod(2)
        c["face_y"] = 5 * nod()
        c["face_x"] = -2 * nod()
        c["s2"], c["ch"] = .8 * nod(2), 1.2 * nod(4)
        c["bob"] = 4 * nod(1) + ring(i, 53, 1.2, 5, 9)
        c["breath"] = kf(i, (0, 0), (14, .8), (50, .5), (68, 0))
    elif name == "conjure":
        # he looks into the flame, then raises it: the arm lifts (forearm, wrist, fingers each a beat behind), the
        # fingers roll, and the flame climbs out of his hand, swells and pulses; he watches it, head back, lets it
        # sink home again
        r = lambda lag=0: kf(i - lag, (0, 0), (9, -.25), (32, 1), (62, 1), (86, 0))
        c["ur"] = 22 * r()
        c["fr"] = 32 * r(3)
        c["hr"] = kf(i - 6, (0, 0), (9, -7), (26, 12), (40, 4), (62, 5), (84, 0))
        roll = kf(i, (10, 0), (24, 1), (60, 1), (76, 0))
        for k, f in enumerate(DIGITS):
            c[f] = (-.5 if k == 0 else 1) * (16 * math.sin(2 * math.pi * 1.5 * t - 1.1 * k) * roll + 6 * r(8))
        c["orb_y"] = kf(i, (0, 0), (10, -13), (40, 150), (64, 142), (88, 0))
        c["orb_s"] = kf(i, (0, 1), (10, .88), (40, 1.95), (52, 1.75), (58, 1.95), (66, 1.75), (88, 1))
        c["face_x"] = kf(i - 2, (0, 0), (9, 5.5), (64, 5), (86, 0))
        c["face_y"] = kf(i - 3, (0, 0), (9, 3.5), (38, -4.5), (64, -4), (88, 0))
        c["head"] = kf(i - 5, (0, 0), (9, -3), (38, 3.5), (64, 3), (88, 0))
        c["breath"] = kf(i, (0, 0), (9, -.2), (36, 1), (64, .85), (90, 0))
        c["clav_r"] = 4.5 * r(1)
        c["clav_l"] = -1.5 * r(4)
        c["s1"], c["s2"], c["ch"] = .5 * r(2), .9 * r(4), 1.1 * r(6)                  # leaning back from the heat
        c["sx"] = -5 * r(1)
        c["bob"] = kf(i, (0, 0), (9, 5), (30, -3), (64, -2), (88, 0))
        c["fing_l"] = 5 * r(2)
    if name in CLIPS and name not in ("idle", "exit"):
        # a held pose is never dead: the hips drift round a slow flat loop (round, not up and down), the chest a beat
        # behind them, the head a breath behind that - small enough to be felt rather than seen, gone at both ends
        e = ease(i / 12.0) * ease((n - i) / 14.0)
        c["sx"] += 1.6 * math.sin(2 * math.pi * .42 * t) * e
        c["bob"] += .9 * (1 - math.cos(2 * math.pi * .42 * t + .6)) * e
        c["pelvis"] += .35 * math.sin(2 * math.pi * .42 * t - .5) * e
        c["s2"] += -.3 * math.sin(2 * math.pi * .42 * t - .9) * e
        c["head"] += .45 * math.sin(2 * math.pi * .31 * t + 1.1) * e
        c["ur"] += .7 * math.sin(2 * math.pi * .37 * t + .4) * e
        c["fr"] += .9 * math.sin(2 * math.pi * .53 * t + 1.9) * e
    # He is 1,500 px tall and stands about 700 px tall on a screen: a 10 px sway is 5 px there, and a figure acting in
    # 5 px moves reads as standing still (the first pass did). Every gesture is played this much bigger than keyed.
    for ch, g in dict(ACT["*"], **ACT.get(name, {})).items():
        c[ch] = REST[ch] + (c[ch] - REST[ch]) * g
    if name == "rom":
        # range of motion, one joint after another, well past what any clip asks: for looking at the seams
        seq = ["ur", "fr", "hr", "thumb_r", "f1", "f2", "f3", "clav_r", "clav_l", "head", "face_x", "face_y", "s1", "s2", "ch",
               "pelvis", "sx", "bob", "hat_lift", "cane_lift"]
        amp = {"ur": 40, "fr": 45, "hr": 30, "thumb_r": 25, "f1": 35, "f2": 35, "f3": 35, "clav_r": 9, "clav_l": 9,
               "head": 14, "face_x": 8, "face_y": 7, "s1": 7, "s2": 7, "ch": 7, "pelvis": 7, "sx": 30, "bob": 70,
               "hat_lift": 50, "cane_lift": 70}
        k = min(len(seq) - 1, i // 15)
        ph = (i % 15) / 15.0
        v = math.sin(2 * math.pi * ph) if seq[k] not in ("bob", "hat_lift", "cane_lift") else math.sin(math.pi * ph)
        c[seq[k]] = amp[seq[k]] * v
        if seq[k] == "cane_lift":
            twirl(c, 2 * math.pi * ph)
        c["wind"] = 0
    return c


def effects(name, i, n, c, rng, emit, face):
    """The faces he pulls and the few things that fly off him, frame i (after the pose is known: the sparks come
    off the flame where it actually is)."""
    ox, oz = u(*orb_pt(c))
    if name == "idle":
        for b0 in (38, 128, 174, 226):                     # he blinks as his head turns
            face(b0, "blink"); face(b0 + 4, "neutral")
        face(62, "smug")                                   # pleased with his flame
        face(92, "blink"); face(96, "smug"); face(120, "neutral")
    elif name == "enter":
        face(0, "blink"); face(17, "smug"); face(38, "neutral")
        if i == 22:
            emit("ring", i, i + 12, lambda tt, x=ox, z=oz: (x, z), grow=(.25, 1.2))
    elif name == "exit":
        face(5, "wink")
        if i == 11:
            emit("steam", i, i + 18, lambda tt, x=ox, z=oz: (x + .3 * math.sin(tt * 5), z + 2.2 * tt), spin=50, grow=(.5, 1.2))
    elif name == "anticipation":
        face(3, "shock"); face(n - 8, "neutral")
    elif name == "win":
        face(5, "laugh"); face(70, "smug"); face(n - 8, "neutral")
        if i in (20, 31, 43):
            a = rng.uniform(.6, 2.5)
            emit("sparkle", i, i + 16, lambda tt, x=ox, z=oz, a=a: (x + math.cos(a) * 1.6 * tt, z + .4 + (1.2 + math.sin(a)) * 1.5 * tt),
                 spin=120, grow=(.5, .1))
    elif name == "big_win":
        face(2, "shock"); face(14, "cheer"); face(86, "laugh"); face(n - 18, "smug"); face(n - 6, "neutral")
        if i in (36, 52):
            emit("ring", i, i + 16, lambda tt, x=ox, z=oz: (x, z), grow=(.4, 2.2))
        if i % 6 == 0 and 34 < i < 86:                     # Mardi Gras beads thrown from the blaze
            kind = ("leaf_red", "leaf_orange", "leaf_gold")[(i // 6) % 3]
            ang, sp = rng.uniform(.3, 2.84), rng.uniform(3.5, 6)
            emit(kind, i, i + 22, lambda tt, a=ang, s=sp, x=ox, z=oz: (x + math.cos(a) * s * tt, z + math.sin(a) * s * tt - 7 * tt * tt),
                 spin=400, grow=(.9, .8))
        if i == 106:
            emit("sparkle_w", i, i + 12, lambda tt, x=ox, z=oz: (x, z + .5 * tt), spin=90, grow=(.9, .2))
    elif name == "lose":
        face(6, "sad"); face(68, "smug"); face(n - 6, "neutral")
        if i == 18:
            emit("steam", i, i + 26, lambda tt, x=ox, z=oz: (x + .35 * math.sin(tt * 5), z + .3 + 2.0 * tt), spin=50, grow=(.5, 1.1))
    elif name == "cane_twirl":
        face(8, "smug"); face(60, "wink"); face(n - 8, "neutral")
    elif name == "hat_tip":
        face(20, "wink"); face(46, "smug"); face(n - 8, "neutral")
        if i in (14, 20, 27, 34):                          # his magic under the brim
            hx, hz = u(488 + c["hat_x"] + rng.uniform(-60, 60), 196 - c["hat_lift"] * .5)
            emit("sparkle_w", i, i + 12, lambda tt, x=hx, z=hz: (x, z + .5 * tt), spin=140, grow=(.55, .1))
    elif name == "conjure":
        face(6, "smug"); face(38, "laugh"); face(70, "smug"); face(n - 8, "neutral")
        if i in (40, 58):
            emit("ring", i, i + 14, lambda tt, x=ox, z=oz: (x, z), grow=(.3, 1.7))
        if i % 6 == 0 and 30 < i < 68:
            ang = rng.uniform(0, 6.28)
            emit("sparkle", i, i + 16, lambda tt, a=ang, x=ox, z=oz: (x + math.cos(a + tt * 4) * (.9 + .8 * tt),
                 z + math.sin(a + tt * 4) * .5 + 1.8 * tt), spin=200, grow=(.55, .15))


# ---------------------------------------------------------------- where things are (the same sums Blender does)

def rot_about(p, c, deg):
    """p turned deg about c, as Blender turns a bone about the camera axis (counter-clockwise on screen; art px are
    y-down)."""
    t = math.radians(deg)
    co, si = math.cos(t), math.sin(t)
    dx, dy = p[0] - c[0], p[1] - c[1]
    return (c[0] + dx * co + dy * si, c[1] - dx * si + dy * co)


def trunk(pt, c, upto="chest"):
    """Where a point carried by the chest (or spine2, spine1, hips) is, posed by the channels."""
    p = pt
    if upto == "chest":
        p = rot_about(p, (512, 470), c["ch"])
    if upto in ("chest", "spine2"):
        p = rot_about(p, (512, 560), c["s2"])
    if upto in ("chest", "spine2", "spine1"):
        p = rot_about(p, (512, 640), c["s1"])
    p = rot_about(p, (512, 690), c["pelvis"])
    return (p[0] + c["sx"], p[1] + c["bob"])


def trunk_turn(c):
    return c["pelvis"] + c["s1"] + c["s2"] + c["ch"]


def ur_local(c):
    """The flame arm hangs from the shoulder: it gives back half of the trunk's lean instead of swinging with it."""
    return c["ur"] - .5 * trunk_turn(c)


def breathed(p, c):
    """A point carried by the chest, moved by its breath (the chest bone swells about its foot)."""
    b = c["breath"]
    return (512 + (p[0] - 512) * (1 + .02 * b), 470 + (p[1] - 470) * (1 + .034 * b))


def shoulder_l(c):
    return trunk(rot_about(breathed((392, 428), c), breathed((486, 392), c), c["clav_l"]), c)


def palm_pt(c):
    p = rot_about(PALM0, (792, 548), c["hr"])
    p = rot_about(p, (684, 652), c["fr"])
    p = rot_about(p, (606, 440), ur_local(c))
    p = rot_about(p, (522, 394), c["clav_r"])
    bx, by = breathed((522, 394), c)                      # the shoulder rides the breath (the arm itself does not swell)
    return trunk((p[0] + bx - 522, p[1] + by - 394), c)


def orb_pt(c):
    x, y = palm_pt(c)
    return (x + c["orb_x"], y - HOVER - c["orb_y"])


LEGS = {"l": ((470, 700), (372, 1420)), "r": ((552, 700), (648, 1420))}
FOOT = {"l": {"ball": (268, 1502), "heel": (404, 1502)}, "r": {"ball": (792, 1502), "heel": (638, 1502)}}


def plant(c, s, deg, pivot="ball"):
    """Turn foot s by deg about its ball (heel up) or its heel (toe up), the pivot staying exactly where it stands:
    the ankle target is moved to wherever that puts the ankle (so nothing slides)."""
    a0 = LEGS[s][1]
    a = rot_about(a0, FOOT[s][pivot], deg)
    c["foot_" + s] = deg
    c["step_" + s] = a[0] - a0[0]
    c["lift_" + s] = a0[1] - a[1]
ARM_L = math.dist((392, 428), (312, 652)) + math.dist((312, 652), (236, 724))
CANE_TIP, WRIST_L, KNOB = (186, 1500), (236, 724), (186, 834)
LEAN = 3.0                                                # the most the planted cane leans over to keep his hand on it


def reach(c):
    """Keep the IK chains in reach, so nothing stretches. The legs are straight at rest: when the hips slide or tilt
    away from a planted foot, they dip until that leg reaches (he settles into his knees). The cane stays planted
    on its tip: when the body pulls the cane hand's shoulder out of reach, the cane (and the hand on it) tilts over
    on its tip toward him until the arm reaches; lifted, the hand is simply kept within the arm's length. Sets
    c["bob"], c["cane_tilt"] and c["wrist"] (the wrist target's offset from rest, art px)."""
    for _ in range(160):
        if all(math.dist(trunk(h, c, "hips"), (a[0] + c["step_" + s], a[1] - c["lift_" + s])) <= math.dist(h, a)
               for s, (h, a) in LEGS.items()):
            break
        c["bob"] += .5
    sh = shoulder_l(c)
    lim = ARM_L * 1.02                                    # (the sleeve gives 2%: at rest the arm is all but straight)
    wrist = lambda th: rot_about(WRIST_L, CANE_TIP, th)
    over = lambda th: math.dist(wrist(th), sh) - lim
    th = c["cane_r"]
    if over(th) > 0:
        # the cane leans toward him, as far as LEAN degrees, by exactly what brings the hand into reach (bisection:
        # it moves smoothly from frame to frame); what the lean cannot give, the hand takes - the cane comes up off
        # the pavement with it (below). Never a jump from one to the other.
        best = None
        for sgn in (1, -1):
            lo, hi = th, th + sgn * LEAN
            if over(hi) < over(lo):                       # this is the way that helps
                if over(hi) <= 0:
                    for _ in range(40):
                        mid = (lo + hi) / 2
                        lo, hi = (mid, hi) if over(mid) > 0 else (lo, mid)
                if best is None or over(hi) < over(best):
                    best = hi
        if best is not None:
            th = best
    planted = 1 - smooth(0, 14, c["cane_lift"])           # lifted, the cane hangs as it is keyed
    th = c["cane_r"] + (th - c["cane_r"]) * planted
    w = wrist(th)
    w = (w[0] + c["hand_lx"], w[1] - c["cane_lift"])
    d = math.dist(w, sh)
    if d > lim:                                           # a lifted hand cannot leave the arm behind
        w = (sh[0] + (w[0] - sh[0]) * lim / d, sh[1] + (w[1] - sh[1]) * lim / d)
    c["cane_tilt"] = th
    c["wrist"] = (w[0] - WRIST_L[0], w[1] - WRIST_L[1])
    return c


# ---------------------------------------------------------------- cloth

class Cloth:
    """A coat tail as a chain of points hung from the hips: each has inertia (it stays behind when the hips move
    and swings past when they stop), drag, a pull back to where the drawn tail hangs, and takes the breeze a little
    later than the point above it - then the links are pulled back to their lengths. What comes out is each link's
    turn from its drawn angle."""

    def __init__(self, pts, freq, zeta, follow, side):
        self.rest = [tuple(p) for p in pts]
        self.L = [math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1)]
        self.phi0 = [math.atan2(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]) for k in range(len(pts) - 1)]
        self.freq, self.zeta, self.follow, self.side = freq, zeta, follow, side
        self.reset()

    def reset(self):
        self.p = [list(p) for p in self.rest]
        self.v = [[0.0, 0.0] for _ in self.rest]
        self.root = None

    def step(self, c, gust, vb, sub=6):
        """One frame. c: the channels (the hips' place and tilt); gust(k): the breeze on link k (px/s2); vb: how fast
        the hips are dropping (px/s)."""
        A = trunk(self.rest[0], c, "hips")
        if self.root is None:                             # the first frame: hung, at rest, from wherever the hips are
            for k in range(len(self.p)):
                off = rot_about(self.rest[k], self.rest[0], c["pelvis"] * (self.follow[k - 1] if k else 0))
                self.p[k] = [A[0] + off[0] - self.rest[0][0], A[1] + off[1] - self.rest[0][1]]
        A0 = self.root or A
        self.root = A
        h = 1.0 / FPS / sub
        N = len(self.rest) - 1
        for s in range(sub):
            f = (s + 1) / sub
            root = (A0[0] + (A[0] - A0[0]) * f, A0[1] + (A[1] - A0[1]) * f)
            self.p[0] = [root[0], root[1]]
            q = [pt[:] for pt in self.p]
            for k in range(1, N + 1):
                off = rot_about(self.rest[k], self.rest[0], c["pelvis"] * self.follow[k - 1])
                tx, ty = root[0] + off[0] - self.rest[0][0], root[1] + off[1] - self.rest[0][1]
                w = 2 * math.pi * self.freq[k - 1]
                fl = self.side * 2.6 * vb * (k / N) ** 1.5         # dropping, the air spreads the tails; rising, it folds them
                ax = w * w * (tx - self.p[k][0]) - 2 * self.zeta * w * self.v[k][0] + gust(k) + fl
                ay = w * w * (ty - self.p[k][1]) - 2 * self.zeta * w * self.v[k][1]
                self.v[k][0] += ax * h
                self.v[k][1] += ay * h
                self.p[k][0] += self.v[k][0] * h
                self.p[k][1] += self.v[k][1] * h
            for _ in range(3):
                for k in range(1, N + 1):
                    dx, dy = self.p[k][0] - self.p[k - 1][0], self.p[k][1] - self.p[k - 1][1]
                    d = math.hypot(dx, dy) or 1e-6
                    self.p[k][0] = self.p[k - 1][0] + dx * self.L[k - 1] / d
                    self.p[k][1] = self.p[k - 1][1] + dy * self.L[k - 1] / d
            for k in range(1, N + 1):
                self.v[k][0] = (self.p[k][0] - q[k][0]) / h
                self.v[k][1] = (self.p[k][1] - q[k][1]) / h
        out = []
        for k in range(N):
            dx, dy = self.p[k + 1][0] - self.p[k][0], self.p[k + 1][1] - self.p[k][1]
            d = math.degrees(math.atan2(dx, dy) - self.phi0[k])
            out.append(max(-42.0, min(42.0, (d + 180) % 360 - 180)))
        return out


def breeze(name, i, n, loop, k, shift=0.0):
    """The night air on link k of a tail at frame i: slow gusts, each reaching a link 3 frames after the one above
    it (the ripple that runs down a hem). Periodic over a loop."""
    x = i - 3.0 * k + shift
    if loop:
        a = 2 * math.pi * x / n
        return .55 * math.sin(2 * a + .7) + .3 * math.sin(5 * a + 2.1) + .15 * math.sin(9 * a + .4)
    t = x / FPS
    return .55 * math.sin(2 * math.pi * .27 * t + .7) + .3 * math.sin(2 * math.pi * .71 * t + 2.1) + .15 * math.sin(2 * math.pi * 1.37 * t + .4)


WIND = 300.0                                              # px/s2 at the hem


def run_clip(arm, faces, fx, name, f0, rng):
    """Key one clip at frames f0.. Every one-shot starts on the rest pose and (but for exit) ends exactly on it."""
    n, loop = ALL_CLIPS[name]
    used = {k: 0 for k in fx}
    face_keys = {}
    orb_alpha = []

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

    quiet = (lambda *a, **k: None)
    face(0, "neutral")
    # springs: the head levels itself against the trunk with a lag, the hat lags the head, the feather and the
    # cravat flutter; the coat is cloth. A loop runs them over two cycles first, so it closes on their steady state.
    S = {"head": Spring(2.0, .5), "face_x": Spring(2.6, .6), "face_y": Spring(2.6, .6), "hat": Spring(2.6, .4),
         "feather1": Spring(2.3, .4), "feather2": Spring(3.0, .34), "cravat1": Spring(2.1, .35),
         "cravat2": Spring(2.7, .3), "hand_l": Spring(2.2, .5),
         # the cane hand rides its solved place on a stiff, dead-beat spring: where the solve changes its mind (the
         # lean reaching its limit, the cane leaving the pavement) the hand rounds the corner instead of kinking
         "wrist_x": Spring(6.0, 1.0), "wrist_y": Spring(6.0, 1.0), "tilt": Spring(6.0, 1.0)}
    cloth = {"tail_l": Cloth(TAIL_L, (2.1, 1.7, 1.45, 1.25), .34, (.85, .55, .32, .18), -1),
             "tail_r": Cloth(TAIL_R, (2.1, 1.7, 1.45, 1.25), .34, (.85, .55, .32, .18), 1),
             "tail_b": Cloth(TAIL_B, (1.8, 1.45, 1.2), .4, (.8, .5, .28), 0)}
    prev = None
    frames = list(range(n)) if loop else list(range(n + 1))
    passes = ([("pre", i) for i in frames] * 2 if loop else []) + [("key", i) for i in frames]
    for kind, i in passes:
        c = reach(drive(name, i, n))
        turn = trunk_turn(c)
        first = prev is None
        if first:                                         # a clip that opens off the rest pose opens settled in it
            prev = {"bob": c["bob"], "sx": c["sx"], "turn": turn, "head": c["head"] - .72 * turn}
        vb = (c["bob"] - prev["bob"]) * FPS
        vx = (c["sx"] - prev["sx"]) * FPS
        dturn = (turn - prev["turn"]) * FPS
        prev.update(bob=c["bob"], sx=c["sx"], turn=turn)
        go = (lambda sp, v: sp.snap(v)) if first else (lambda sp, v: sp.step(v))
        ws = WIND * c["wind"] * (1.0 if loop else ease(i / 10.0) * ease((n - i) / 14.0))
        air = breeze(name, i, n, loop, 0, 11.0) * ws / WIND
        # the head stays level: it gives back most of the trunk's tilt, a moment late
        h = go(S["head"], c["head"] - .72 * turn)
        fxs = go(S["face_x"], c["face_x"])
        fys = go(S["face_y"], c["face_y"])
        hat = go(S["hat"], c["hat"] - .025 * (h - prev["head"]) * FPS)
        prev["head"] = h
        f1 = go(S["feather1"], c["feather"] - .02 * dturn - .02 * vx - .25 * (hat - c["hat"]) + 2.2 * air)
        f2 = go(S["feather2"], 1.25 * (f1 - c["feather"]) + 1.5 * air)
        c1 = go(S["cravat1"], -.55 * turn - .012 * vx + .5 * air)
        c2 = go(S["cravat2"], 1.5 * c1 - .04 * vb + .6 * air)
        hl = go(S["hand_l"], c["hl"])
        if c["cane_lift"] < 1 and abs(c["cane_spin"]) < .01:  # (keyed taps and twirls land on their own frames)
            c["wrist"] = (go(S["wrist_x"], c["wrist"][0]), go(S["wrist_y"], c["wrist"][1]))
            c["cane_tilt"] = go(S["tilt"], c["cane_tilt"])
            sh = shoulder_l(c)                                # ... but never so late that the sleeve stretches
            wx, wy = WRIST_L[0] + c["wrist"][0], WRIST_L[1] + c["wrist"][1]
            d = math.dist((wx, wy), sh)
            if d > ARM_L * 1.02:
                k = ARM_L * 1.02 / d
                c["wrist"] = (sh[0] + (wx - sh[0]) * k - WRIST_L[0], sh[1] + (wy - sh[1]) * k - WRIST_L[1])
        else:
            S["wrist_x"].snap(c["wrist"][0]); S["wrist_y"].snap(c["wrist"][1]); S["tilt"].snap(c["cane_tilt"])
        tails = {}
        for nm, cl in cloth.items():
            N = len(cl.rest) - 1
            sh = {"tail_l": 0.0, "tail_r": 7.0, "tail_b": 3.0}[nm]
            tails[nm] = cl.step(c, lambda k, N=N, sh=sh: ws * (.35 + .65 * k / N) * breeze(name, i, n, loop, k, sh),
                                vb if nm != "tail_b" else 0.0)
        if kind != "key":
            continue
        effects(name, i, n, c, rng, emit, face)
        # a feather bends and a ruffle flaps only so far, however hard he dances (a soft stop: no kink where it bites)
        lim = lambda v, L: L * math.tanh(v / L)
        s = dict(head=h, face_x=fxs, face_y=fys, hat=hat, feather1=lim(f1, 20.0), feather2=lim(f2, 26.0),
                 cravat1=lim(c1, 8.0), cravat2=lim(c2, 12.0), hand_l=hl)
        if not loop and name != "exit":                   # the last frames settle exactly onto the rest pose
            w = ease((n - i) / 8.0)
            for ch in CHANNELS:
                c[ch] = REST[ch] + (c[ch] - REST[ch]) * w
            c["cane_tilt"] *= w
            c["wrist"] = (c["wrist"][0] * w, c["wrist"][1] * w)
            s = {k: v * w for k, v in s.items()}
            tails = {k: [v * w for v in vs] for k, vs in tails.items()}
        orb_alpha.append(round(max(0.0, min(1.0, c["orb_a"])), 3))
        pose(arm, f0 + i, c, s, tails)
    # faces: one patch at a time (neutral = none)
    cur = "neutral"
    for i in frames:
        cur = face_keys.get(i, cur)
        if not loop and name != "exit" and i >= n - 1:
            cur = "neutral"
        for f, ob in faces.items():
            set_fade(ob, f0 + i, 1.0 if f == cur else 0.0)
    TRACKS[name] = {"orb": orb_alpha}
    return n


TRACKS = {}


def pose(arm, f, c, s, tails):
    """Set and key every bone for frame f from the channels c, the spring outputs s and the cloth's turns."""
    P = arm.pose.bones
    R = math.radians

    def rot(nm, deg):
        P[nm].rotation_euler = (0, 0, R(deg))

    for pb in P:
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    # the hips: slide sideways, dip, and tilt (art px; the hips bone points up, so its local x is screen right and
    # local y is up)
    P["hips"].location = (c["sx"] / 100, -c["bob"] / 100, 0)
    rot("hips", c["pelvis"])
    rot("spine1", c["s1"])
    rot("spine2", c["s2"])
    rot("chest", c["ch"])
    b = c["breath"]
    P["chest"].scale = (1 + .02 * b, 1 + .034 * b, 1)
    rot("clav_l", c["clav_l"])
    rot("clav_r", c["clav_r"])
    rot("neck", .4 * s["head"])
    rot("head", .6 * s["head"])
    P["face"].location = (s["face_x"] / 100, -s["face_y"] / 100, 0)
    rot("hat", s["hat"])
    P["hat"].location = ((c["hat_x"] + .3 * s["face_x"]) / 100, (c["hat_lift"] - .25 * s["face_y"]) / 100, 0)
    P["hat"].scale = (2 - c["hat_sy"], c["hat_sy"], 1)
    rot("feather1", s["feather1"])
    rot("feather2", s["feather2"])
    rot("cravat1", s["cravat1"])
    rot("cravat2", s["cravat2"])
    rot("hand_l", s["hand_l"] + c["cane_tilt"])          # the hand turns with the cane it holds (its arm is IK)
    rot("fingers_l", c["fing_l"])
    rot("thumb_l", c["thumb_l"])
    # the cane keeps its own angle in the world: its lean about the planted tip, and the twirl's wheel
    rot("cane", c["cane_tilt"] + c["cane_spin"])
    P["cane"].scale = (1, c["cane_len"], 1)
    P["ik_hand_l"].location = (c["wrist"][0] / 100, -c["wrist"][1] / 100, 0)
    rot("upper_r", ur_local(c))
    rot("fore_r", c["fr"])
    rot("hand_r", c["hr"])
    rot("thumb_r", c["thumb_r"])
    for f_ in ("f1", "f2", "f3"):                         # a finger curls more at its tip than at its knuckle
        rot(f_ + "_r1", .55 * c[f_])
        rot(f_ + "_r2", .8 * c[f_])
    ox, oy = orb_pt(c)
    P["orb"].location = ((ox - PALM0[0]) / 100, (PALM0[1] - oy) / 100, 0)
    P["orb"].scale = (c["orb_s"], c["orb_s"], 1)
    for nm, turns in tails.items():                       # each link's turn from its drawn angle, in its parent's frame
        prev_turn = c["pelvis"]
        for k, d in enumerate(turns):
            rot(f"{nm}{k + 1}", d - prev_turn)
            prev_turn = d
    # the feet: their ankle targets stay planted unless a tap lifts one; the foot itself keeps its angle
    P["ik_l"].location = (c["step_l"] / 100, c["lift_l"] / 100, 0)
    P["ik_r"].location = (c["step_r"] / 100, c["lift_r"] / 100, 0)
    rot("foot_l", c["foot_l"])
    rot("foot_r", c["foot_r"])
    for pb in P:
        pb.keyframe_insert("location", frame=f)
        pb.keyframe_insert("rotation_euler", frame=f)
        pb.keyframe_insert("scale", frame=f)
    wisp = bpy.data.objects.get("wisp")
    if wisp:
        set_fade(wisp, f, max(0.0, min(1.0, c["orb_a"])))


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
    for c in ALL_CLIPS:
        STARTS[c] = f
        n = run_clip(arm, faces, fx, c, f, rng) if c in clips else ALL_CLIPS[c][0]
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
    for old in os.listdir(dst):
        os.remove(os.path.join(dst, old))
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
        if nm == "wisp":                                  # the flame is drawn live by the game (see "orb" below)
            continue
        box = [v / K for v in META["parts"][nm]["box"]]
        out_parts.append(mesh_out(parts[nm], nm, box, {"face": "neutral"} if nm == "head" else {}))
        if nm == "head":                                  # the other faces: whole heads, drawn in the head's place
            for f, ob in faces.items():
                if f != "neutral":
                    out_parts.append(mesh_out(ob, "face_" + f, [v / K for v in META["faces"][f]["box"]], {"face": f}))
    open(os.path.join(dst, "geo.bin"), "wb").write(bytes(geo))
    clips = {}
    fx_names = [k for k, _, _ in FX_KINDS]
    for c, (n, loop) in CLIPS.items():
        nf = n if loop else n + 1
        buf = bytearray()
        face_track, fx_draws = [], []
        stretch = 1.0
        for k in range(nf):
            sc.frame_set(STARTS[c] + k)
            dg = bpy.context.evaluated_depsgraph_get()
            ae = arm.evaluated_get(dg)
            for bn in bones:
                pb = ae.pose.bones[bn]
                m = ae.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
                buf.extend(struct.pack("<6f", *to_art(m)))
            for bn in ("thigh_l", "shin_l", "thigh_r", "shin_r", "upper_l", "fore_l"):
                stretch = max(stretch, ae.pose.bones[bn].matrix.to_scale().y)
            cur = 0
            for fi, f in enumerate(FACES[1:], 1):
                ob = faces.get(f)
                if ob and fade(ob) > .5:
                    cur = fi
            face_track.append(cur)
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
        clips[c] = {"frames": nf, "loop": loop, "face": face_track, "alpha": {"orb": TRACKS[c]["orb"][:nf]}, "fx": fx_draws}
        print(f"CLIP {c:13s} frames {nf:3d}  most an IK limb stretches x{stretch:.4f}", flush=True)
    # each shoe's sole, in art px at rest (the game turns them through the foot bones for the shadows)
    meta = {"version": 2, "fps": FPS, "art": [W_PX, H_PX], "cx": W_PX / 2, "ground_y": GROUND, "top_y": 4,
            "rest_height": GROUND - 4, "bones": bones, "parts": out_parts, "faces": FACES,
            "fx": fx_names, "shoes": {"foot_l": [205, 412, GROUND], "foot_r": [628, 856, GROUND]},
            # the flame: the game draws it live, trailing this bone (its anchor in art px at rest; the bone's own
            # scale is the flame's size, alpha.orb its strength)
            "orb": {"bone": "orb", "at": list(PALM0), "hover": HOVER},
            # the idle never rests and plays at its own pace; a reaction cuts in from any frame over `cut` frames
            "idle": {"rate": 1.0, "rest": [0, 0], "cut": 8},
            "clips": clips}
    json.dump(meta, open(os.path.join(dst, "rig.json"), "w"), separators=(",", ":"))
    print("EXPORT", dst, "bones", len(bones), "parts", len(out_parts), "geo", len(geo))


# ---------------------------------------------------------------- QA renders

def render(clips, step=1):
    sc = bpy.context.scene
    ren = os.path.join(OUT, "renders")
    for c in clips:
        n, loop = ALL_CLIPS[c]
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
    animate(arm, faces, fx, list(CLIPS) + [c for c in clips if c in QA_CLIPS])
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "doc_rig.blend"))
    if "export" in steps:
        export(arm, parts, faces, fx)
    if "render" in steps:
        render(clips, step)
    print("DONE doc_rig", steps, clips)
