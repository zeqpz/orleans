"""The drunk scarecrow, animated in Blender: a 2D cut-out on a bone rig, his face swapped per frame, rendered to the
frames the game plays (tools/blender/pack_chars.py packs them).

Layers (art/nola-src/scare, made by tools/fall/scarecrow_layers.py): pole.png (the T-pole, static, behind) and
body_<face>.png (the scarecrow with no pole, one per face). The body is a finely subdivided plane bent by bones:
hips, two spine bones, the head (lolls, lags behind the body), arms whose wrists stay tied to the crossbar (the
sleeves stretch between), floppy straw hands, the jug on its rope (a pendulum on a spring), the crow (hops, bobs,
pecks, flies up), the legs (dangle) and the boots (tied to the post). Faces: a keyed index into the body textures.

  blender.exe -b --factory-startup --python tools/fall/blender/scarecrow.py -- [build,render] [clip,clip..]
-> art/blender/chars/scarecrow/scarecrow.blend, renders/<clip>/####.png (720 x 1080), renders/meta.json"""
import json, math, os, random, sys

import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LAY = os.path.join(ROOT, "art", "nola-src", "scare")
FX = os.path.join(ROOT, "art", "nola-src", "fx")
OUT = os.path.join(ROOT, "art", "blender", "chars", "scarecrow")
FPS = 30
W_PX, H_PX = 1024, 1536                    # the layers' size; 100 px = 1 unit, the art centred on the origin
RES = (800, 1080)
ORTHO = 18.0                               # units across the frame's height (the art is 15.36 tall)
PX = RES[1] / ORTHO                        # render px per unit
FACES = json.load(open(os.path.join(LAY, "meta.json")))["faces"] if os.path.exists(os.path.join(LAY, "meta.json")) else []

CLIPS = {          # frames, loop
    "idle": (240, True), "enter": (44, False), "exit": (30, False), "anticipation": (54, False),
    "win": (96, False), "big_win": (132, False), "lose": (90, False), "hiccup": (72, False), "peck": (84, False),
}


def u(x, y):
    """Art px -> (x, z) units."""
    return ((x - W_PX / 2) / 100.0, (H_PX / 2 - y) / 100.0)


# bones: name -> (head px, tail px, parent)
BONES = {
    "root": ((540, 1500), (540, 1400), None),
    "hips": ((540, 800), (535, 650), "root"),
    "chest": ((535, 650), (525, 480), "hips"),
    "head": ((520, 470), (470, 200), "chest"),
    "arm_l": ((430, 500), (175, 450), "chest"),       # viewer's left
    "arm_r": ((640, 500), (870, 450), "chest"),
    "hand_l": ((175, 450), (60, 540), "root"),
    "hand_r": ((870, 450), (975, 560), "root"),
    "rope": ((150, 450), (140, 620), "root"),
    "jug": ((140, 620), (120, 820), "rope"),
    "crow": ((880, 405), (870, 250), "root"),
    "leg_l": ((500, 820), (480, 1130), "hips"),
    "leg_r": ((590, 820), (600, 1130), "hips"),
    "boots": ((540, 1240), (540, 1400), "root"),
}


def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / max(1e-9, dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy), t


def weights_at(x, y):
    """Bone weights for an art pixel: region rules first, then soft nearest-bone blending."""
    # the crow: everything up on the right above the crossbar
    if x > 760 and y < 415:
        return {"crow": 1.0}
    # the jug and its rope (left, below the wrist tie)
    if x < 250 and y > 600:
        return {"jug": 1.0}
    if 95 < x < 205 and 470 < y <= 600:
        k = (y - 470) / 130
        return {"rope": 1 - .5 * k, "jug": .5 * k}
    # the boots hang tied to the post
    if y > 1215:
        return {"boots": 1.0}
    # the straw hands, past the wrist ties
    if x < 175 and y < 640:
        k = min(1, (175 - x) / 60)
        return {"hand_l": k, "root": 1 - k}
    if x > 870 and y < 660:
        k = min(1, (x - 870) / 60)
        return {"hand_r": k, "root": 1 - k}
    # the sleeves: tied at the wrist (root), following the chest at the shoulder - they stretch between
    if y < 640 and (x < 400 or x > 670):
        if x < 400:
            k = max(0, min(1, (x - 175) / 225))
            return {"chest": k ** 1.3, "root": 1 - k ** 1.3}
        k = max(0, min(1, (870 - x) / 200))
        return {"chest": k ** 1.3, "root": 1 - k ** 1.3}
    # head, chest, hips, legs: soft blend by distance to the bone segments
    out = {}
    for name in ("head", "chest", "hips", "leg_l", "leg_r"):
        (h, t, _) = BONES[name]
        d, _ = seg_dist((x, y), h, t)
        if name == "head":
            d = max(0, d - 120)          # the head's big round shape
        out[name] = math.exp(-(d / 70.0) ** 2)
    if y < 470:                          # above the collar it is all head
        out = {"head": 1.0}
    s = sum(out.values()) or 1
    return {k: v / s for k, v in out.items() if v / s > .002}


# ---------------------------------------------------------------- scene

def clear():
    if bpy.app.background:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)


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
        sc.eevee.taa_render_samples = 16
    except AttributeError:
        pass
    cd = bpy.data.cameras.new("cam")
    cd.type = "ORTHO"
    cd.ortho_scale = ORTHO
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    cam.location = (0, -30, 0)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    if sc.world is None:
        sc.world = bpy.data.worlds.new("world")


def load(path):
    im = bpy.data.images.get(os.path.basename(path)) or bpy.data.images.load(path)
    im.alpha_mode = "STRAIGHT"
    return im


def face_material():
    """Emission material choosing between the body textures by a keyed 'face' index (constant keys)."""
    m = bpy.data.materials.new("body")
    m.use_nodes = True
    try:
        m.surface_render_method = "BLENDED"
    except AttributeError:
        m.blend_method = "BLEND"
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    face = nt.nodes.new("ShaderNodeValue")
    face.name = face.label = "face"
    col = alpha = None
    for i, f in enumerate(FACES):
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = load(os.path.join(LAY, f"body_{f}.png"))
        tex.interpolation = "Cubic"
        tex.extension = "CLIP"
        if col is None:
            col, alpha = tex.outputs["Color"], tex.outputs["Alpha"]
            continue
        cmp = nt.nodes.new("ShaderNodeMath")
        cmp.operation = "COMPARE"
        cmp.inputs[1].default_value = float(i)
        cmp.inputs[2].default_value = 0.5
        nt.links.new(face.outputs[0], cmp.inputs[0])
        mc = nt.nodes.new("ShaderNodeMix")
        mc.data_type = "RGBA"
        nt.links.new(cmp.outputs[0], mc.inputs["Factor"])
        nt.links.new(col, mc.inputs[6])
        nt.links.new(tex.outputs["Color"], mc.inputs[7])
        ma = nt.nodes.new("ShaderNodeMix")
        ma.data_type = "FLOAT"
        nt.links.new(cmp.outputs[0], ma.inputs["Factor"])
        nt.links.new(alpha, ma.inputs[2])
        nt.links.new(tex.outputs["Alpha"], ma.inputs[3])
        col, alpha = mc.outputs[2], ma.outputs[0]
    em = nt.nodes.new("ShaderNodeEmission")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(col, em.inputs["Color"])
    nt.links.new(alpha, mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def plain_material(name, path):
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


def plane(name, w, h, nx, ny, mat, depth):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")
    bmesh.ops.create_grid(bm, x_segments=nx, y_segments=ny, size=.5, calc_uvs=True)
    bmesh.ops.scale(bm, vec=(w, h, 1), verts=bm.verts)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "X"))
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (0, depth, 0)
    return ob


def build_rig():
    ad = bpy.data.armatures.new("rig")
    arm = bpy.data.objects.new("rig", ad)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for name, (h, t, par) in BONES.items():
        b = ad.edit_bones.new(name)
        hx, hz = u(*h)
        tx, tz = u(*t)
        b.head, b.tail = (hx, 0, hz), (tx, 0, tz)
        b.roll = 0
    for name, (h, t, par) in BONES.items():
        if par:
            ad.edit_bones[name].parent = ad.edit_bones[par]
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    return arm


def build():
    clear()
    setup()
    arm = build_rig()
    pole = plane("pole", W_PX / 100, H_PX / 100, 1, 1, plain_material("pole", os.path.join(LAY, "pole.png")), 0.5)
    body = plane("body", W_PX / 100, H_PX / 100, 80, 120, face_material(), 0.0)
    groups = {n: body.vertex_groups.new(name=n) for n in BONES}
    for v in body.data.vertices:
        x = v.co.x * 100 + W_PX / 2
        y = H_PX / 2 - v.co.z * 100
        for n, w in weights_at(x, y).items():
            groups[n].add([v.index], w, "REPLACE")
    mod = body.modifiers.new("rig", "ARMATURE")
    mod.object = arm
    body.parent = arm
    crow = plane("crow", W_PX / 100, H_PX / 100, 1, 1, plain_material("crow", os.path.join(LAY, "crow.png")), -0.1)
    g = crow.vertex_groups.new(name="crow")
    g.add([v.index for v in crow.data.vertices], 1.0, "REPLACE")
    m2 = crow.modifiers.new("rig", "ARMATURE")
    m2.object = arm
    crow.parent = arm
    # effect sprites: hiccup bubbles, straw bits, leaves, music-less "hearts" are not his style - keep it farm
    fx = {}
    for kind, n, size in (("bubble", 4, 0.8), ("straw", 10, 1.0), ("leaf_red", 4, 1.1), ("leaf_orange", 4, 1.1),
                          ("leaf_gold", 4, 1.1), ("feather", 6, 0.9), ("sparkle", 8, 0.9)):
        fx[kind] = []
        for i in range(n):
            ob = plane(f"{kind}_{i}", size, size, 1, 1, plain_material(f"{kind}_{i}", os.path.join(FX, kind + ".png")),
                       -0.6 - .01 * i)
            set_fade(ob, 0, 0.0)
            fx[kind].append(ob)
    os.makedirs(OUT, exist_ok=True)
    return arm, body, fx


# ---------------------------------------------------------------- keys

def set_fade(ob, f, v):
    s = ob.active_material.node_tree.nodes["fade"].outputs[0]
    s.default_value = v
    s.keyframe_insert("default_value", frame=f)


def key_face(body, f, name):
    s = body.active_material.node_tree.nodes["face"].outputs[0]
    s.default_value = float(FACES.index(name))
    s.keyframe_insert("default_value", frame=f)


def key(arm, f, pose):
    for b in arm.pose.bones:
        ch = pose.get(b.name, {})
        b.location = (ch.get("x", 0.0), ch.get("y", 0.0), 0)
        b.rotation_euler = (0, 0, math.radians(ch.get("r", 0.0)))
        s = ch.get("s", 1.0)
        b.scale = (ch.get("sx", s), ch.get("sy", s), 1)
        b.keyframe_insert("location", frame=f)
        b.keyframe_insert("rotation_euler", frame=f)
        b.keyframe_insert("scale", frame=f)


class Spring:
    """A damped angular spring: follows a target with lag and overshoot (the jug, the head, the hands)."""

    def __init__(self, freq, zeta):
        self.w, self.z = 2 * math.pi * freq, zeta
        self.x = self.v = 0.0

    def step(self, target, dt=1 / FPS, sub=4):
        for _ in range(sub):
            h = dt / sub
            a = self.w * self.w * (target - self.x) - 2 * self.z * self.w * self.v
            self.v += a * h
            self.x += self.v * h
        return self.x


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def bump(t, a, b):
    """0 outside [a, b], a smooth hump peaking at the middle."""
    if t <= a or t >= b:
        return 0.0
    return math.sin(math.pi * (t - a) / (b - a))


def env(i, n, att=8, rel=14):
    """1 in the middle of a clip, easing up from 0 over att frames and back to 0 over the last rel frames."""
    return ease(i / att) * ease((n - i) / rel)


def run_clip(arm, body, fx, name, f0, rng):
    """Key one clip at frames f0.. ; every one starts and ends on the rest pose (neutral face) unless noted."""
    n, loop = CLIPS[name]
    jug, head, hand_l, hand_r, crow = Spring(.9, .12), Spring(2.2, .35), Spring(1.6, .2), Spring(1.5, .2), Spring(3, .4)
    used = {k: 0 for k in fx}

    def emit(kind, fs, fe, path, spin=0.0, grow=(1, 1)):
        obs = fx[kind]
        ob = obs[used[kind] % len(obs)]
        used[kind] += 1
        set_fade(ob, f0 + fs - 1, 0.0)
        r0 = rng.uniform(0, 360)
        for f in range(fs, fe + 1, 2):
            t = (f - fs) / max(1, fe - fs)
            x, z = path(t)
            ob.location = (x, ob.location.y, z)
            g = grow[0] + (grow[1] - grow[0]) * t
            ob.scale = (g, 1, g)
            ob.rotation_euler = (0, math.radians(r0 + spin * t), 0)
            ob.keyframe_insert("location", frame=f0 + f)
            ob.keyframe_insert("scale", frame=f0 + f)
            ob.keyframe_insert("rotation_euler", frame=f0 + f)
            set_fade(ob, f0 + f, 1.0)
        set_fade(ob, f0 + fe + 1, 0.0)

    faces = {}                                                   # frame -> face, applied with constant keys

    def face(i, nm):
        faces[i] = nm

    face(0, "neutral")
    for i in range(n + (0 if loop else 1)):
        t = i / FPS
        p = i / n
        sway = lean = hd = bob = 0.0                             # torso turn (deg), chest lean, head, hips bob
        s_chest = 1.0
        legs = 0.0
        crow_y = crow_r = crow_s = 0.0
        if name == "idle":
            # the drunk sway: two slow incommensurate waves that repeat exactly over the loop
            a = 2 * math.pi * p
            sway = 3.2 * math.sin(a) + 1.4 * math.sin(3 * a + 1.1) - 1.4 * math.sin(1.1)
            lean = 2.0 * math.sin(2 * a + .4) - 2.0 * math.sin(.4)
            bob = .05 * math.sin(4 * a)
            hd = -6 * math.sin(a - .3) + 6 * math.sin(-.3) + 3 * math.sin(2 * a) + 2.5 * bump(p, .55, .7)
            legs = 3 * math.sin(a + .5) - 3 * math.sin(.5)
            crow_y = .06 * max(0, math.sin(8 * a))                # little hops
            crow_r = 8 * bump(p, .3, .38) - 10 * bump(p, .8, .86)
            for b0 in (58, 171):
                for k in range(4):
                    face(b0 + k, "blink")
                face(b0 + 4, "neutral")
        elif name == "enter":
            # wakes up: starts slumped asleep, snaps up with a jolt, settles
            k = ease(p / .55)
            sway = -10 * (1 - k) + 3 * bump(p, .5, .8)
            lean = -6 * (1 - k)
            hd = 24 * (1 - k) - 6 * bump(p, .45, .75)
            bob = -.25 * (1 - k) + .12 * bump(p, .5, .7)
            face(0, "blink"); face(int(n * .45), "shock"); face(int(n * .8), "neutral")
        elif name == "exit":
            k = ease(p / .8)
            sway, lean, hd, bob = -10 * k, -6 * k, 24 * k, -.25 * k
            face(int(n * .3), "blink")
        elif name == "anticipation":
            e = env(i, n, 6, 16)
            sway = 1.5 * math.sin(t * 30) * e * .4
            lean = 4 * e
            s_chest = 1 + .04 * e
            hd = -8 * e + 2 * math.sin(t * 40) * e
            bob = .15 * e
            crow_y = .25 * bump(p, .1, .4)
            crow_s = .1 * e
            face(4, "shock"); face(n - 10, "neutral")
        elif name == "win":
            e = env(i, n, 8, 18)
            beat = math.sin(t * 2 * math.pi * 2.2)               # a bouncy little drunk dance
            sway = 7 * beat * e
            lean = 3 * math.sin(t * 2 * math.pi * 1.1) * e
            bob = .18 * abs(beat) * e
            hd = -9 * math.sin(t * 2 * math.pi * 2.2 + .6) * e
            legs = 14 * math.sin(t * 2 * math.pi * 2.2 + 1.0) * e
            crow_y = .2 * abs(math.sin(t * 2 * math.pi * 2.2)) * e
            face(3, "happy"); face(n - 12, "neutral")
            if i in (20, 44, 68):
                emit("sparkle", i, i + 14, lambda tt, x0=rng.uniform(-3, 1): (x0, 3.5 + 2 * tt), spin=120, grow=(.4, .1))
        elif name == "big_win":
            e = env(i, n, 8, 22)
            beat = math.sin(t * 2 * math.pi * 2.8)
            sway = 11 * beat * e
            lean = 5 * math.sin(t * 2 * math.pi * 1.4) * e
            bob = .3 * abs(beat) * e
            hd = -16 * math.sin(t * 2 * math.pi * 2.8 + .7) * e
            legs = 24 * math.sin(t * 2 * math.pi * 2.8 + 1.2) * e
            s_chest = 1 + .05 * abs(beat) * e
            # the crow flies up off the bar in fright and comes back
            fly = bump(p, .08, .75)
            crow_y = 2.6 * fly
            crow_r = 15 * math.sin(t * 30) * fly
            crow_s = .15 * math.sin(t * 50) * fly
            face(3, "cheer"); face(n - 16, "happy"); face(n - 6, "neutral")
            if i % 6 == 0 and 8 < i < n - 30:
                ang = rng.uniform(.3, 2.8)
                sp = rng.uniform(4, 7)
                emit("straw", i, i + 18, lambda tt, a=ang, s=sp: (.2 + math.cos(a) * s * tt, 1.5 + math.sin(a) * s * tt
                                                                  - 9 * tt * tt), spin=500, grow=(.8, .7))
            if i % 9 == 4 and 8 < i < n - 30:
                kind = ("leaf_red", "leaf_orange", "leaf_gold")[(i // 9) % 3]
                x0 = rng.uniform(-4, 4)
                emit(kind, i, i + 26, lambda tt, x0=x0: (x0 + 1.2 * math.sin(tt * 7), 7.5 - 6 * tt), spin=300,
                     grow=(.8, .7))
            if i in (30, 50, 70):
                for k in range(2):
                    emit("feather", i + k * 3, i + 30, lambda tt, x0=rng.uniform(2, 4): (x0 + math.sin(tt * 8),
                         4 + 1.5 * crow_y - 5 * tt), spin=200, grow=(.9, .8))
        elif name == "lose":
            e = env(i, n, 14, 24)
            sway = -6 * e
            lean = -7 * e
            hd = 20 * e + 3 * math.sin(t * 9) * bump(p, .2, .5)
            bob = -.22 * e
            legs = -2 * e
            face(4, "sad"); face(int(n * .7), "hiccup"); face(int(n * .78), "neutral")
        elif name == "hiccup":
            jolt = 0.0
            for h0 in (.12, .42, .72):
                jolt += bump(p, h0, h0 + .08)
            e = env(i, n, 6, 12)
            sway = 2 * math.sin(t * 5) * e
            bob = .35 * jolt
            hd = -7 * jolt + 4 * math.sin(t * 3) * e
            s_chest = 1 + .06 * jolt
            for h0 in (.12, .42, .72):
                a0 = int(h0 * n)
                face(a0, "hiccup"); face(a0 + 7, "smug" if h0 > .5 else "neutral")
                emit("bubble", a0 + 2, a0 + 26, lambda tt: (.6 + .4 * math.sin(tt * 9), 3.6 + 3 * tt), grow=(.5, 1.0))
            face(n - 8, "neutral")
        elif name == "peck":
            # the crow pecks his hat: it leans in and pecks three times, he flinches, glares (smug), shoos it
            e = env(i, n, 6, 14)
            lean_in = bump(p, .1, .75)
            peck = sum(bump(p, a, a + .06) for a in (.25, .38, .51))
            crow_r = 35 * lean_in + 25 * peck
            crow_y = -.1 * lean_in
            hd = -9 * peck - 4 * bump(p, .6, .9)
            sway = -3 * peck + 4 * bump(p, .62, .82)
            bob = .1 * peck
            face(int(n * .25), "shock"); face(int(n * .58), "smug"); face(n - 10, "neutral")
        if not loop and i == n and name != "exit":           # exit ends slumped (the figure leaves)
            sway = lean = hd = bob = legs = crow_y = crow_r = crow_s = 0.0
            s_chest = 1.0
        # secondary motion: the head lags the body, the jug swings off the torso's motion, the hands flop
        h = head.step(hd + .6 * sway)
        jv = jug.step(-1.6 * sway + 4 * bob * 10 * (1 if name in ("win", "big_win") else 0))
        hl = hand_l.step(.8 * sway + 30 * bob)
        hr = hand_r.step(.8 * sway - 30 * bob)
        cr = crow.step(crow_r)
        if not loop and i >= n - 1 and name != "exit":           # settle every spring exactly onto rest
            h, jv, hl, hr, cr = 0.0, 0.0, 0.0, 0.0, 0.0
        if loop:                                                  # loops ride the waves, not springs (seamless)
            h = hd + .6 * sway
            jv = -1.6 * sway + 2.5 * math.sin(2 * math.pi * p * 2)
            hl, hr = .8 * sway, .8 * sway
            cr = crow_r
        jv = max(-13.0, min(13.0, jv))                           # the jug hangs near the frame's left edge
        pose = {
            "hips": dict(r=sway, y=bob),
            "chest": dict(r=lean, s=s_chest),
            "head": dict(r=h),
            "rope": dict(r=jv),
            "jug": dict(r=.5 * jv),
            "hand_l": dict(r=hl),
            "hand_r": dict(r=-hr),
            "crow": dict(y=crow_y, r=cr, sx=1 + crow_s, sy=1 - .5 * crow_s),
            "leg_l": dict(r=legs - .5 * sway),
            "leg_r": dict(r=-legs * .8 - .5 * sway),
            "boots": dict(r=.15 * legs),
        }
        key(arm, f0 + i, pose)
    for i, nm in sorted(faces.items()):
        key_face(body, f0 + i, nm)
    if not loop:
        key_face(body, f0 + n, "neutral")
    return n


def finish_curves():
    def fcs(act):
        try:
            return list(act.fcurves)
        except AttributeError:
            return [fc for L in act.layers for s in L.strips for cb in s.channelbags for fc in cb.fcurves]

    for idb in list(bpy.data.objects) + [m.node_tree for m in bpy.data.materials if m.node_tree]:
        ad = idb.animation_data
        if not (ad and ad.action):
            continue
        for fc in fcs(ad.action):
            const = fc.data_path.endswith("default_value") and getattr(idb, "name", "") != "" and \
                any(n.name == "face" for n in getattr(idb, "nodes", []))
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT" if const else "LINEAR"


STARTS = {}


def animate(arm, body, fx, clips):
    rng = random.Random(1123)
    f = 1
    for c in CLIPS:
        STARTS[c] = f
        n = run_clip(arm, body, fx, c, f, rng) if c in clips else CLIPS[c][0]
        f += n + 20
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, f
    finish_curves()


def render(clips):
    sc = bpy.context.scene
    ren = os.path.join(OUT, "renders")
    for c in clips:
        n, loop = CLIPS[c]
        d = os.path.join(ren, c)
        os.makedirs(d, exist_ok=True)
        for old in os.listdir(d):
            os.remove(os.path.join(d, old))
        for k in range(n if loop else n + 1):
            sc.frame_set(STARTS[c] + k)
            sc.render.filepath = os.path.join(d, f"{k:04d}.png")
            bpy.ops.render.render(write_still=True)


def write_meta():
    """What pack_chars.py reads: frame size, standing height, ground line, the clips."""
    top = (H_PX / 2 - 10) / 100            # the post's top, art px 10
    base = (H_PX / 2 - 1500) / 100         # the grass under the post, art px 1500
    cy = RES[1] / 2
    meta = {"fps": FPS, "size": list(RES), "rest_height_px": round((top - base) * PX, 1),
            "ground_y": round(cy - base * PX, 1),
            "clips": {c: {"frames": (n if loop else n + 1), "loop": loop} for c, (n, loop) in CLIPS.items()}}
    os.makedirs(os.path.join(OUT, "renders"), exist_ok=True)
    json.dump(meta, open(os.path.join(OUT, "renders", "meta.json"), "w"), indent=1)


if __name__ == "__main__" and "--" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:]
    steps = (args[0] if args else "build,render").split(",")
    clips = args[1].split(",") if len(args) > 1 else list(CLIPS)
    arm, body, fx = build()
    animate(arm, body, fx, clips)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "scarecrow.blend"))
    write_meta()
    if "render" in steps:
        render(clips)
    print("DONE scarecrow", clips)
