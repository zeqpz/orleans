"""Doc, the voodoo showman, animated in Blender: a 2D cut-out on a bone rig with his face swapped per frame, rendered
to the frames the game plays (tools/blender/pack_chars.py packs them into frontend/assets/chars/doc/).

Layers (art/nola-src/doc, 4K, made by tools/nola/doc_layers.py): body_<face>.png (the figure without the cane and
the palm wisp, one per face), cane.png (behind the body, so his fingers wrap round the skull knob), wisp.png (the
green smoke over his open palm). The body is a finely subdivided plane bent by bones: hips, chest, head (lags the
body on a spring), hat (tips), each arm in three (shoulder, forearm, hand), coat tails (swing), legs with the feet
planted. The cane rides his right hand (on the viewer's left) and can spin in his fingers (its width flips through
zero: a turn about its own axis); the wisp rides his left palm and flickers, swells and coils. Faces: a keyed index.

  blender.exe -b --factory-startup --python tools/nola/blender/doc.py -- [build,render] [clip,clip..]
-> art/blender/chars/doc/doc.blend, renders/<clip>/####.png (800 x 1080), renders/meta.json
In the user's live Blender (MCP): runpy this file, then build() / animate() to preview."""
import json, math, os, random, sys

import bpy
import bmesh
from mathutils import Matrix

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LAY = os.path.join(ROOT, "art", "nola-src", "doc")
FX = os.path.join(ROOT, "art", "nola-src", "fx")
OUT = os.path.join(ROOT, "art", "blender", "chars", "doc")
FPS = 30
W_PX, H_PX = 1024, 1536                    # the drawing's coordinate space (the 4K plates map onto it); 100 px = 1 unit
RES = (1600, 2160)                         # 2x (owner, 2026-11-08: crisp beside the 4K street); the 4K plates carry it
ORTHO = 17.6                               # units across the frame's height (the art is 15.36 tall)
PX = RES[1] / ORTHO
FACES = json.load(open(os.path.join(LAY, "meta.json")))["faces"] if os.path.exists(os.path.join(LAY, "meta.json")) else []

CLIPS = {          # frames, loop
    "idle": (240, True), "enter": (44, False), "exit": (30, False), "anticipation": (54, False),
    "win": (96, False), "big_win": (132, False), "lose": (90, False),
    "cane_twirl": (84, False), "hat_tip": (72, False), "conjure": (96, False),
}


def u(x, y):
    """Art px -> (x, z) units."""
    return ((x - W_PX / 2) / 100.0, (H_PX / 2 - y) / 100.0)


# bones: name -> (head px, tail px, parent). "arm_l" = the arm on the viewer's LEFT (his right, the cane hand).
BONES = {
    "root": ((512, 1500), (512, 1420), None),
    "hips": ((510, 680), (512, 560), "root"),
    "chest": ((512, 560), (510, 400), "hips"),
    "head": ((505, 390), (495, 165), "chest"),
    "hat": ((480, 160), (470, 10), "head"),
    "arm_l": ((395, 415), (312, 655), "chest"),
    "fore_l": ((312, 655), (228, 728), "arm_l"),
    "hand_l": ((228, 728), (186, 834), "fore_l"),
    "cane": ((186, 834), (186, 1500), "hand_l"),
    "arm_r": ((608, 420), (698, 660), "chest"),
    "fore_r": ((698, 660), (788, 535), "arm_r"),
    "hand_r": ((788, 535), (905, 440), "fore_r"),
    "wisp": ((860, 440), (850, 230), "hand_r"),
    "coat": ((512, 720), (512, 1110), "hips"),
    "leg_l": ((462, 690), (428, 1200), "hips"),
    "leg_r": ((556, 690), (630, 1200), "hips"),
}


def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / max(1e-9, dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy), t


def soft(x, y, names, sigma=55.0):
    out = {}
    for n in names:
        h, t, _ = BONES[n]
        d, _ = seg_dist((x, y), h, t)
        out[n] = math.exp(-(d / sigma) ** 2)
    s = sum(out.values()) or 1
    return {k: v / s for k, v in out.items() if v / s > .003}


def weights_at(x, y):
    """Bone weights for an art pixel: region rules first, then soft nearest-bone blending inside each region."""
    if y < 400 and 300 < x < 740:                                 # the head and the hat (not the raised fingertips out right)
        if y < 140:
            return {"hat": 1.0}
        if y < 185:
            k = (185 - y) / 45
            return {"hat": k, "head": 1 - k}
        return {"head": 1.0}
    if y > 1395:                                                  # the shoes stay planted
        return {"root": 1.0}
    if x < 352 and y < 940:                                       # his right arm, down to the cane hand
        w = soft(x, y, ["arm_l", "fore_l", "hand_l"], 50)
        if x > 330 and y < 470:                                   # the shoulder seam blends into the chest
            k = (x - 330) / 22
            w = {kk: v * (1 - k) for kk, v in w.items()}
            w["chest"] = k
        return w
    if x > 655 and y < 700:                                       # his left arm, up to the open palm
        w = soft(x, y, ["arm_r", "fore_r", "hand_r"], 50)
        if x < 680 and y < 470:
            k = (680 - x) / 25
            w = {kk: v * (1 - k) for kk, v in w.items()}
            w["chest"] = k
        return w
    if y < 720:                                                   # torso: chest over hips
        k = max(0.0, min(1.0, (y - 520) / 160))
        return {"chest": 1 - k, "hips": k}
    # below the waist: the legs (thigh, then planted at the ankle) and the coat tails beside them
    leg = "leg_l" if x < 512 else "leg_r"
    kfoot = max(0.0, min(1.0, (y - 1180) / 215))                 # knee down, blending to the planted foot
    in_leg = (x < 512 and 395 < x < 490) or (x >= 512 and 530 < x < 650)
    if y < 1110 and not in_leg:                                   # a coat tail: swings from the hips
        k = max(0.0, min(1.0, (y - 720) / 300))
        return {"hips": 1 - k, "coat": k}
    return {leg: 1 - kfoot ** 1.5, "root": kfoot ** 1.5} if kfoot < 1 else {"root": 1.0}


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
        sc.eevee.taa_render_samples = 16
    except AttributeError:
        pass
    cd = bpy.data.cameras.get("cam") or bpy.data.cameras.new("cam")
    cd.type = "ORTHO"
    cd.ortho_scale = ORTHO
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    cam.location = (0, -30, -0.3)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    if sc.world is None:
        sc.world = bpy.data.worlds.new("world")


def load(path):
    im = bpy.data.images.get(os.path.basename(path)) or bpy.data.images.load(path)
    im.alpha_mode = "STRAIGHT"
    return im


def blended(m):
    try:
        m.surface_render_method = "BLENDED"
    except AttributeError:
        m.blend_method = "BLEND"


def face_material():
    """Emission material choosing between the body textures by a keyed 'face' index (constant keys)."""
    m = bpy.data.materials.new("body")
    m.use_nodes = True
    blended(m)
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


def plain_material(name, path, strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    blended(m)
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
        # every bone's local Z faces the camera, so a turn about Z stays in the picture plane (with roll 0 a
        # diagonal bone's Z lies IN the plane and the turn twists the cut-out edge-on - the hand went paper-thin)
        b.align_roll((0, -1, 0))
    for name, (h, t, par) in BONES.items():
        if par:
            ad.edit_bones[name].parent = ad.edit_bones[par]
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    return arm


def rigid(name, path, bone, arm, depth, strength=1.0):
    ob = plane(name, W_PX / 100, H_PX / 100, 1, 1, plain_material(name, path, strength), depth)
    g = ob.vertex_groups.new(name=bone)
    g.add([v.index for v in ob.data.vertices], 1.0, "REPLACE")
    m = ob.modifiers.new("rig", "ARMATURE")
    m.object = arm
    ob.parent = arm
    return ob


def build():
    clear()
    setup()
    arm = build_rig()
    body = plane("body", W_PX / 100, H_PX / 100, 96, 144, face_material(), 0.0)
    groups = {n: body.vertex_groups.new(name=n) for n in BONES}
    for v in body.data.vertices:
        x = v.co.x * 100 + W_PX / 2
        y = H_PX / 2 - v.co.z * 100
        for n, w in weights_at(x, y).items():
            groups[n].add([v.index], w, "REPLACE")
    mod = body.modifiers.new("rig", "ARMATURE")
    mod.object = arm
    body.parent = arm
    rigid("cane", os.path.join(LAY, "cane.png"), "cane", arm, 0.15)       # behind the body: the fingers wrap the knob
    rigid("wisp", os.path.join(LAY, "wisp.png"), "wisp", arm, -0.15, 1.6)  # in front, glowing
    fx = {}
    for kind, n, size in (("steam", 8, 1.6), ("sparkle", 10, 0.9), ("sparkle_w", 6, 0.8), ("leaf_red", 5, 0.7),
                          ("leaf_orange", 5, 0.7), ("leaf_gold", 5, 0.7), ("ring", 3, 2.0), ("star", 6, 0.8)):
        fx[kind] = []
        for i in range(n):
            ob = plane(f"{kind}_{i}", size, size, 1, 1,
                       plain_material(f"{kind}_{i}", os.path.join(FX, kind + ".png"), 1.5 if kind == "steam" else 1.0),
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
    s.default_value = float(FACES.index(name) if name in FACES else 0)
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
    """A damped angular spring: follows a target with lag and overshoot (the head, the coat tails, the hands)."""

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
    if t <= a or t >= b:
        return 0.0
    return math.sin(math.pi * (t - a) / (b - a))


def env(i, n, att=8, rel=14):
    return ease(i / att) * ease((n - i) / rel)


def run_clip(arm, body, fx, wisp, name, f0, rng):
    """Key one clip at frames f0.. ; every one starts and ends on the rest pose (neutral face)."""
    n, loop = CLIPS[name]
    head, coat, hand_l, hand_r = Spring(2.0, .3), Spring(1.2, .18), Spring(1.8, .3), Spring(1.6, .25)
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
            set_fade(ob, f0 + f, 1.0 if t < .7 else (1 - t) / .3)
        set_fade(ob, f0 + fe + 1, 0.0)

    PALM = u(880, 470)                                            # where the wisp lives, for effects
    faces = {}

    def face(i, nm):
        faces[i] = nm

    face(0, "neutral")
    for i in range(n + (0 if loop else 1)):
        t = i / FPS
        p = i / n
        sway = lean = hd = bob = 0.0                             # hips turn (deg), chest lean, head, hips bob
        hat = 0.0                                                 # hat tilt (deg)
        al = fl = hl = 0.0                                        # his right arm (cane): shoulder, forearm, hand
        ar = fr = hr = 0.0                                        # his left arm (palm)
        cane_r, cane_sx, cane_y = 0.0, 1.0, 0.0                   # cane swing, spin (width), lift
        wisp_s, wisp_r, wisp_a = 1.0, 0.0, 1.0                    # wisp swell, coil, opacity
        legs = 0.0
        if name == "idle":
            a = 2 * math.pi * p
            # a slow, sly sway: hips and chest on incommensurate waves that close exactly over the loop
            sway = 1.8 * math.sin(a) + .7 * math.sin(3 * a + .9) - .7 * math.sin(.9)
            lean = -1.2 * math.sin(2 * a + .3) + 1.2 * math.sin(.3)
            bob = .03 * math.sin(4 * a)
            hd = 3.5 * math.sin(a + .6) - 3.5 * math.sin(.6) + 1.5 * math.sin(2 * a)
            ar = 4 * math.sin(a + 1.2) - 4 * math.sin(1.2)
            fr = 6 * math.sin(2 * a + .5) - 6 * math.sin(.5)
            hr = 8 * math.sin(3 * a) + 3 * math.sin(5 * a + 1) - 3 * math.sin(1)   # fingers rippling under the wisp
            wisp_s = 1 + .12 * math.sin(4 * a) + .06 * math.sin(7 * a + 2) - .06 * math.sin(2)
            wisp_r = 6 * math.sin(3 * a)
            wisp_a = .85 + .15 * math.sin(8 * a)
            for b0 in (52, 160):
                for k in range(4):
                    face(b0 + k, "blink")
                face(b0 + 4, "neutral")
            face(100, "smug"); face(128, "neutral")
        elif name == "enter":
            # he steps in with a flourish: rises from a low bow, the palm sweeping up, the wisp blooming
            k = ease(p / .6)
            lean = -14 * (1 - k)
            hd = 18 * (1 - k)
            bob = -.3 * (1 - k)
            ar = -40 * (1 - k) + 12 * bump(p, .4, .85)
            fr = 30 * (1 - k)
            wisp_s = .2 + .8 * k + .3 * bump(p, .5, .85)
            wisp_a = k
            face(0, "blink"); face(int(n * .45), "smug"); face(int(n * .85), "neutral")
        elif name == "exit":
            k = ease(p / .8)                                      # a deep bow, out
            lean, hd, bob = -14 * k, 18 * k, -.3 * k
            ar, fr = -40 * k, 30 * k
            hat = -12 * k
            wisp_s, wisp_a = 1 - .8 * k, 1 - k
            face(int(n * .3), "wink")
        elif name == "anticipation":
            e = env(i, n, 6, 16)
            lean = -4 * e                                         # leans in toward the board
            hd = -6 * e + 1.5 * math.sin(t * 30) * e
            bob = .08 * e
            ar, fr, hr = -14 * e, 22 * e, 18 * math.sin(t * 22) * e    # fingers wiggling: a spell coming
            wisp_s = 1 + .5 * e + .1 * math.sin(t * 30) * e
            wisp_r = 25 * math.sin(t * 9) * e
            face(4, "shock"); face(int(n * .45), "smug"); face(n - 10, "neutral")
        elif name == "win":
            e = env(i, n, 8, 18)
            beat = math.sin(t * 2 * math.pi * 2.0)
            sway = 4 * beat * e
            bob = .12 * abs(beat) * e
            hd = -6 * math.sin(t * 2 * math.pi * 2.0 + .6) * e
            legs = 6 * math.sin(t * 2 * math.pi * 2.0 + 1.0) * e
            # two taps of the cane: lifted off the ground and brought down on the beat
            tap = bump(p, .2, .34) + bump(p, .46, .6)
            cane_y = .45 * tap
            al, fl = -6 * tap, -8 * tap
            ar = -18 * e + 6 * beat * e
            fr = 26 * e
            wisp_s = 1 + .35 * e
            face(3, "laugh"); face(n - 14, "smug"); face(n - 6, "neutral")
            if i in (18, 42, 64):
                emit("sparkle", i, i + 16, lambda tt, x0=rng.uniform(-2, 3): (x0, 4 + 2 * tt), spin=120, grow=(.5, .1))
        elif name == "big_win":
            e = env(i, n, 8, 22)
            beat = math.sin(t * 2 * math.pi * 2.6)
            sway = 7 * beat * e
            lean = 3 * math.sin(t * 2 * math.pi * 1.3) * e
            bob = .2 * abs(beat) * e
            hd = -10 * math.sin(t * 2 * math.pi * 2.6 + .7) * e
            legs = 6 * math.sin(t * 2 * math.pi * 2.6 + 1.2) * e
            hat = 10 * bump(p, .15, .45) - 6 * bump(p, .55, .8)
            # the cane spins in his fingers, twice round, then plants
            spin = ease((p - .12) / .55) * 2 * 2 * math.pi
            cane_sx = math.cos(spin) if .12 < p < .67 else 1.0
            cane_y = .5 * bump(p, .1, .72)
            al, fl = -10 * bump(p, .1, .72), -14 * bump(p, .1, .72)
            ar, fr, hr = -34 * e, 40 * e, 12 * math.sin(t * 18) * e    # the palm thrown up
            wisp_s = 1 + .55 * e + .12 * math.sin(t * 20) * e
            wisp_r = 18 * math.sin(t * 6) * e
            face(3, "cheer"); face(int(n * .55), "laugh"); face(n - 16, "smug"); face(n - 6, "neutral")
            if i % 6 == 0 and 8 < i < n - 30:
                kind = ("leaf_red", "leaf_orange", "leaf_gold")[(i // 6) % 3]       # Mardi Gras beads flying
                ang, sp = rng.uniform(.5, 2.6), rng.uniform(4, 6.5)
                emit(kind, i, i + 20, lambda tt, a=ang, s=sp: (math.cos(a) * s * tt, 2 + math.sin(a) * s * tt - 8 * tt * tt),
                     spin=400, grow=(.9, .8))
            if i % 7 == 3 and 8 < i < n - 30:
                x0, z0 = PALM
                emit("steam", i, i + 26, lambda tt, x0=x0, z0=z0: (x0 + .8 * math.sin(tt * 6), z0 + .8 + 2.6 * tt), spin=90,
                     grow=(.6, 1.15))   # stays under the frame top (QA: it left the frame at 4 units of rise)
            if i in (24, 60):
                emit("ring", i, i + 14, lambda tt: PALM, grow=(.3, 1.6))
        elif name == "lose":
            e = env(i, n, 14, 24)
            lean = 6 * e                                          # slumps back, unimpressed
            hd = 12 * e + 4 * math.sin(t * 8) * bump(p, .25, .6)  # shakes his head
            bob = -.12 * e
            ar, fr = 30 * e, -30 * e                              # the palm drops
            hat = -6 * e
            wisp_s, wisp_a = 1 - .6 * e, 1 - .7 * e               # his magic sputters
            cane_r = 4 * e
            face(4, "sad"); face(int(n * .72), "smug"); face(int(n * .85), "neutral")
        elif name == "cane_twirl":
            e = env(i, n, 8, 14)
            spin = ease((p - .15) / .6) * 2 * math.pi * 1.5
            cane_sx = math.cos(spin) if .15 < p < .75 else 1.0    # one and a half turns in the fingers
            cane_y = .55 * bump(p, .08, .85)
            al, fl, hl = -10 * bump(p, .08, .85), -16 * bump(p, .08, .85), 8 * math.sin(t * 12) * bump(p, .15, .75)
            sway = 2 * math.sin(t * 5) * e
            hd = -4 * bump(p, .1, .6) + 3 * bump(p, .6, .9)
            face(6, "smug"); face(int(n * .78), "wink"); face(n - 8, "neutral")
        elif name == "hat_tip":
            e = env(i, n, 6, 12)
            tip = bump(p, .15, .7)
            hat = 16 * tip                                        # tips his hat forward (about the brim)
            hd = 10 * tip                                         # with a nod
            lean = -4 * tip
            ar, fr = -10 * tip, 12 * tip
            face(int(n * .2), "wink"); face(int(n * .72), "smug"); face(n - 8, "neutral")
        elif name == "conjure":
            e = env(i, n, 8, 16)
            raise_ = bump(p, .1, .9)
            ar, fr, hr = -30 * raise_, 34 * raise_, 14 * math.sin(t * 16) * raise_
            hd = -6 * raise_
            lean = -2 * raise_
            wisp_s = 1 + .8 * bump(p, .2, .85) + .1 * math.sin(t * 24) * raise_
            wisp_r = 28 * math.sin(t * 7) * raise_
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
        if not loop and i == n and name != "exit":           # every one-shot ends exactly on the rest pose
            sway = lean = hd = bob = hat = al = fl = hl = ar = fr = hr = cane_r = cane_y = legs = wisp_r = 0.0
            cane_sx = wisp_s = wisp_a = 1.0
        h = head.step(hd + .5 * sway)
        c = coat.step(-1.5 * sway - 30 * bob)
        hl2 = hand_l.step(hl)
        hr2 = hand_r.step(hr)
        if not loop and i >= n - 1 and name != "exit":
            h = c = hl2 = hr2 = 0.0
        if loop:                                                 # loops ride the waves, not springs (seamless)
            h, c, hl2, hr2 = hd + .5 * sway, -1.5 * sway, hl, hr
        pose = {
            "hips": dict(r=sway, y=bob),
            "chest": dict(r=lean),
            "head": dict(r=h),
            "hat": dict(r=hat),
            "arm_l": dict(r=al - .6 * sway), "fore_l": dict(r=fl), "hand_l": dict(r=hl2),
            # the cane keeps its own angle in the world (plumb, plus cane_r): it never swings with the arm
            "cane": dict(r=cane_r - (sway + lean + (al - .6 * sway) + fl + hl2), y=-cane_y, sx=cane_sx),   # the cane bone points down its shaft: up is -y
            "arm_r": dict(r=ar - .6 * sway), "fore_r": dict(r=fr), "hand_r": dict(r=hr2),
            "wisp": dict(r=wisp_r, s=wisp_s),
            "coat": dict(r=c),
            "leg_l": dict(r=legs - .4 * sway),
            "leg_r": dict(r=-legs * .8 - .4 * sway),
        }
        key(arm, f0 + i, pose)
        set_fade(wisp, f0 + i, max(0.0, min(1.0, wisp_a)))
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
        const = any(n.name == "face" for n in getattr(idb, "nodes", []))
        for fc in fcs(ad.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT" if const else "LINEAR"


STARTS = {}


def animate(arm, body, fx, clips):
    rng = random.Random(1123)
    wisp = bpy.data.objects["wisp"]
    f = 1
    for c in CLIPS:
        STARTS[c] = f
        n = run_clip(arm, body, fx, wisp, c, f, rng) if c in clips else CLIPS[c][0]
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
    top = (H_PX / 2 - 4) / 100             # the top of his hat, art px 4
    base = (H_PX / 2 - 1522) / 100         # his soles' lowest point (the shoe tips), art px ~1522 - the game stands this line on its canvas's bottom edge, so anything under it is cut off (owner, 2026-11-08)
    cam_z = -0.3                            # the camera sits 0.3 units low
    meta = {"fps": FPS, "size": list(RES), "rest_height_px": round((top - base) * PX, 1),
            "ground_y": round(RES[1] / 2 - (base - cam_z) * PX, 1),
            "clips": {c: {"frames": (n if loop else n + 1), "loop": loop} for c, (n, loop) in CLIPS.items()}}
    os.makedirs(os.path.join(OUT, "renders"), exist_ok=True)
    json.dump(meta, open(os.path.join(OUT, "renders", "meta.json"), "w"), indent=1)


if __name__ == "__main__" and "--" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:]
    steps = (args[0] if args else "build,render").split(",")
    clips = args[1].split(",") if len(args) > 1 else list(CLIPS)
    arm, body, fx = build()
    animate(arm, body, fx, list(CLIPS))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "doc.blend"))
    write_meta()
    if "render" in steps:
        render(clips)
    print("DONE doc", clips)
