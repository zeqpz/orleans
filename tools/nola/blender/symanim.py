"""Voodoo on Bourbon symbols, animated in Blender: one scene per symbol, four clips, rendered to the frames the game plays.

The icon (art/nola-src/icons/<ID>.png, 1000 px = 10 Blender units) sits on a finely subdivided plane bent by a
chain of bones (squash and stretch, lean, bend, wobble); a glow halo of its silhouette sits behind it; cartoon
effect sprites (art/nola-src/fx) are animated around it. Each symbol has its own idle, land, hit and multi.
Camera: orthographic, 14 units across, looking along +y, the icon centred (tools/blender/pack_frames.py's frame).

Runs in the user's live Blender over the MCP socket (build + preview), or in the background for the renders:
  blender.exe -b --factory-startup --python tools/fall/blender/symanim.py -- <ID> [build,render]
-> art/blender/symbols/<ID>.blend, art/blender/renders/<ID>/<clip>/####.png (512 px, RGBA)"""
import math, os, random, sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ICONS = os.path.join(ROOT, "art", "nola-src", "icons")
FX = os.path.join(ROOT, "art", "nola-src", "fx")
REN = os.path.join(ROOT, "art", "blender", "renders")
BLEND = os.path.join(ROOT, "art", "blender", "symbols")
FPS = 30
CLIPS = {"idle": 72, "land": 24, "hit": 46, "multi": 42}
START = {"idle": 1, "land": 101, "hit": 201, "multi": 301}     # each clip's first frame on the timeline
HALF = 4.7                                                    # half the art's longer side, units (940 px)
GLOW = {                                                      # halo colour per tier (Mardi Gras gold, violet, voodoo green)
    1: (1.0, 0.76, 0.24), 2: (0.72, 0.42, 1.0), "M": (0.5, 1.0, 0.42), "BS": (0.78, 0.48, 1.0),
    "ES": (0.48, 1.0, 0.4), 0: (1.0, 0.92, 0.7)}
TIER = {"H1": 1, "H2": 1, "H3": 1, "H4": 2, "H5": 2, "H6": 2, "H7": 2}


# ---------------------------------------------------------------- scene

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True) if bpy.app.background else None
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.armatures, bpy.data.actions,
                 bpy.data.cameras):
        for b in list(coll):
            coll.remove(b)


def setup_scene(sid):
    sc = bpy.context.scene
    sc.name = sid
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x = sc.render.resolution_y = 552   # 512 px per 13 units before the camera widened to 14
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.fps = FPS
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"           # the art's colours exactly, no filmic curve
    sc.view_settings.look = "None"
    try:
        sc.eevee.taa_render_samples = 16
    except AttributeError:
        pass
    sc.frame_start, sc.frame_end = 1, START["multi"] + CLIPS["multi"] - 1
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 14.0
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    cam.location = (0, -30, 0)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    if sc.world is None:
        sc.world = bpy.data.worlds.new("world")


def image(path):
    name = os.path.basename(path)
    im = bpy.data.images.get(name) or bpy.data.images.load(path)
    im.alpha_mode = "STRAIGHT"
    return im


def emit_material(name, img, tint=(1, 1, 1), strength=1.0):
    """Unlit image material: colour = image x tint, alpha = image alpha x the material's 'fade' (keyable)."""
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
    tex.image = img
    tex.interpolation = "Cubic"
    tex.extension = "CLIP"
    mul = nt.nodes.new("ShaderNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    mul.inputs[0].default_value = 1.0
    mul.inputs[2].default_value = (*tint, 1)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    fade = nt.nodes.new("ShaderNodeValue")
    fade.name = fade.label = "fade"
    fade.outputs[0].default_value = 1.0
    am = nt.nodes.new("ShaderNodeMath")
    am.operation = "MULTIPLY"
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tex.outputs["Color"], mul.inputs[1])
    nt.links.new(mul.outputs[0], em.inputs["Color"])
    nt.links.new(tex.outputs["Alpha"], am.inputs[0])
    nt.links.new(fade.outputs[0], am.inputs[1])
    nt.links.new(am.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def grid_plane(name, size, cuts, mat):
    """A plane in the picture (x right, z up), `size` units square, `cuts` subdivisions, UVs 0..1."""
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")                 # create_grid only fills UVs into a layer that exists
    bmesh.ops.create_grid(bm, x_segments=cuts, y_segments=cuts, size=size / 2, calc_uvs=True)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                     matrix=__import__("mathutils").Matrix.Rotation(math.radians(90), 3, "X"))
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def sprite(name, png, size, tint=(1, 1, 1), depth=-1.0, strength=1.0):
    mat = emit_material(name, image(os.path.join(FX, png)), tint, strength)
    ob = grid_plane(name, size, 1, mat)
    ob.location = (0, depth, 0)
    return ob


def build_icon(sid):
    """The icon mesh + its bone chain + its halo. Bones point up the picture; local y = up, rotation z = turn."""
    mat = emit_material("icon_" + sid, image(os.path.join(ICONS, sid + ".png")))
    icon = grid_plane("icon", 10.0, 48, mat)
    arm_d = bpy.data.armatures.new("rig")
    arm = bpy.data.objects.new("rig", arm_d)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_d.edit_bones
    root = eb.new("root")
    root.head, root.tail = (0, 0, -HALF), (0, 0, -HALF + 1.0)
    chain = []
    zs = [-HALF, -1.6, 1.4, HALF + 0.3]
    for i in range(3):
        b = eb.new(f"b{i}")
        b.head, b.tail = (0, 0, zs[i]), (0, 0, zs[i + 1])
        b.parent = chain[-1] if chain else root
        b.use_connect = bool(chain)
        chain.append(b)
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    # weights: smooth vertical blend between the three bones
    groups = [icon.vertex_groups.new(name=f"b{i}") for i in range(3)]
    centres = [(zs[i] + zs[i + 1]) / 2 for i in range(3)]
    for v in icon.data.vertices:
        z = v.co.z
        w = [math.exp(-((z - c) / 1.9) ** 2) for c in centres]
        s = sum(w)
        for g, wi in zip(groups, w):
            g.add([v.index], wi / s, "REPLACE")
    mod = icon.modifiers.new("rig", "ARMATURE")
    mod.object = arm
    icon.parent = arm
    tier = TIER.get(sid, sid if sid in GLOW else 0)
    glow = sprite("glow", None, 10.0) if False else None
    gm = emit_material("glow_" + sid, image(os.path.join(ICONS, sid + "_glow.png")), GLOW[tier], 1.6)
    glow = grid_plane("glow", 12.0, 1, gm)
    glow.location = (0, 0.6, 0)
    glow.parent = arm
    glow.parent_type = "BONE"
    glow.parent_bone = "b1"
    glow.matrix_world = __import__("mathutils").Matrix.Translation((0, 0.6, 0))
    return arm, icon, glow


# ---------------------------------------------------------------- keying helpers

def base_glow(sid):
    """The halo's resting level: a faint warm glow behind the paying tiers and the specials, none on the lows."""
    return .2 if sid in TIER or sid in ("M", "BS", "ES") else 0.0


def pb(arm, name):
    return arm.pose.bones[name]


def key_pose(arm, f, **bones):
    """bones: name -> dict(x, y, r (deg), sx, sy). Unset channels go to rest."""
    for name, ch in bones.items():
        b = pb(arm, name)
        b.location = (ch.get("x", 0.0), ch.get("y", 0.0), 0.0)
        b.rotation_euler = (0.0, 0.0, math.radians(ch.get("r", 0.0)))
        b.scale = (ch.get("sx", 1.0), ch.get("sy", 1.0), 1.0)
        b.keyframe_insert("location", frame=f)
        b.keyframe_insert("rotation_euler", frame=f)
        b.keyframe_insert("scale", frame=f)


def key_fade(ob, f, v):
    n = ob.active_material.node_tree.nodes["fade"].outputs[0]
    n.default_value = v
    n.keyframe_insert("default_value", frame=f)


def key_obj(ob, f, x=None, z=None, s=None, r=None, sx=None, sz=None):
    if x is not None or z is not None:
        loc = ob.location.copy()
        if x is not None:
            loc.x = x
        if z is not None:
            loc.z = z
        ob.location = loc
        ob.keyframe_insert("location", frame=f)
    if s is not None or sx is not None or sz is not None:
        ob.scale = (sx if sx is not None else s, 1.0, sz if sz is not None else s)
        ob.keyframe_insert("scale", frame=f)
    if r is not None:
        ob.rotation_euler = (0, math.radians(r), 0)      # the picture-plane turn of an object is about y
        ob.keyframe_insert("rotation_euler", frame=f)


def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    return t * t * (3 - 2 * t)


def damp(t, freq, zeta=0.25):
    """A damped spring settling from 1 to 0 (t seconds)."""
    w = 2 * math.pi * freq
    return math.exp(-zeta * w * t) * math.cos(w * math.sqrt(max(1e-6, 1 - zeta * zeta)) * t)


def hide_all(obs, f):
    for ob in obs:
        key_fade(ob, f, 0.0)


# ---------------------------------------------------------------- per-symbol character

# Each symbol's personality: how it breathes, how it lands, how it reacts. Idle is calm (every cell plays it).
#  idle: (breath squash, sway deg, bend deg, bob units, cycles in 72 f)    fx: names of the effect kinds it uses
P = {          # idle (bob, sway Hz, breathe Hz, lean, harmonics), softness, effects, hit style
    "H1": dict(idle=(.025, 1.2, 1.5, .03, 2), soft=1.0, fx=["sparkle", "leaf"], hit="jiggle"),        # Mardi Gras mask: beads
    "H2": dict(idle=(.02, .8, 1.0, .02, 2), soft=.9, fx=["straw", "steam"], hit="wobbletop"),         # voodoo doll: pins, wisps
    "H3": dict(idle=(.018, 2.0, 2.4, .02, 1), soft=.6, fx=["popcorn", "sparkle"], hit="jiggle"),      # trumpet: music notes
    "H4": dict(idle=(.015, 2.6, .8, .04, 1), soft=.5, fx=["steam", "drop"], hit="hiccup"),            # skull + candle: chatter
    "H5": dict(idle=(.02, 3.0, 1.2, .02, 1), soft=.7, fx=["steam", "sparkle"], hit="wobbletop"),      # gris-gris bag
    "H6": dict(idle=(.015, 1.6, 3.0, .02, 2), soft=.7, fx=["bubble"], hit="bounce"),                  # gator: snap
    "H7": dict(idle=(.03, .8, .8, .02, 2), soft=1.1, fx=["puff", "crumb"], hit="bounce"),             # beignets: sugar
    "L1": dict(idle=(.01, 4.5, 3.5, .06, 1), soft=.4, fx=["sparkle"], hit="spin"),                    # fleur-de-lis
    "L2": dict(idle=(.02, 2.2, .6, .05, 2), soft=.8, fx=["leaf"], hit="jiggle"),                      # beads
    "L3": dict(idle=(.02, 1.5, .6, .03, 1), soft=.8, fx=["bubble"], hit="hop"),                       # crawfish
    "L4": dict(idle=(.03, 1.6, 2.2, .02, 2), soft=1.2, fx=["crumb", "sparkle"], hit="jiggle"),        # king cake
    "L5": dict(idle=(.012, 0.0, .8, .02, 1), soft=.5, fx=["sparkle"], hit="flutter"),                 # candle
    "L6": dict(idle=(.03, 2.4, 2.0, .03, 2), soft=.4, fx=["glint"], hit="spin"),                      # skeleton key
    "L7": dict(idle=(.01, 2.4, 5.0, .03, 1), soft=.3, fx=["glint", "sparkle"], hit="spin"),           # doubloon
    "L8": dict(idle=(.045, .6, 2.6, .0, 3), soft=.5, fx=["sparkle"], hit="flutter"),                  # tarot card
    "L9": dict(idle=(.015, 1.0, .5, .02, 1), soft=.6, fx=["puff"], hit="bounce"),                     # bone
    "L10": dict(idle=(.02, .8, .6, .02, 1), soft=.5, fx=["sparkle", "glint"], hit="hop"),             # gas lamp
    "M": dict(idle=(.02, 2.0, 1.4, .02, 2), soft=.8, fx=["bubble", "drop", "steam"], hit="pop"),      # potion: bubbles + wisps
    "BS": dict(idle=(.025, 1.8, 1.4, .04, 2), soft=.9, fx=["sparkle", "leaf"], hit="jiggle"),         # FS: gold letters, beads fly
    "ES": dict(idle=(.035, 1.2, 2.6, .02, 3), soft=1.4, fx=["drop", "steam"], hit="wobbletop"),       # XFS: gooey letters drip ectoplasm
}

FX_SPEC = {        # effect kind -> sprite file(s), size (units), tint
    "steam": (["steam"], 2.6, (1, 1, 1)), "sparkle": (["sparkle", "sparkle_w"], 1.3, (1, 1, 1)),
    "glint": (["sparkle_w"], 1.6, (1, 1, 1)), "crumb": (["crumb"], .7, (1, 1, 1)),
    "leaf": (["leaf_red", "leaf_orange", "leaf_gold"], 1.5, (1, 1, 1)), "bubble": (["bubble"], 1.0, (1, 1, 1)),
    "popcorn": (["popcorn"], 1.2, (1, 1, 1)), "puff": (["puff"], 1.6, (1, 1, 1)),
    "drop": (["drop"], .8, (1, 1, 1)), "straw": (["straw"], 1.3, (1, 1, 1)), "feather": (["feather"], 1.3, (1, 1, 1)),
}


class Pool:
    """A small pool of effect sprites of one kind, each keyed on and off per particle."""

    def __init__(self, kind, n, sid):
        files, self.size, tint = FX_SPEC[kind]
        self.obs = []
        for i in range(n):
            ob = sprite(f"{kind}_{i}", files[i % len(files)] + ".png", self.size, tint, depth=-1.2 - .01 * i)
            key_fade(ob, 0, 0.0)
            self.obs.append(ob)
        self.next = 0
        self.busy = [0] * n

    def take(self, f0):
        for k in range(len(self.obs)):
            i = (self.next + k) % len(self.obs)
            if self.busy[i] <= f0:
                self.next = i + 1
                return i, self.obs[i]
        return None, None

    def particle(self, f0, f1, path, rng, spin=0.0, grow=(1, 1), fade=(1, 1), behind=False):
        """path(t) -> (x, z) for t 0..1; keyed every 2nd frame (on twos, the cartoon way)."""
        i, ob = self.take(f0)
        if ob is None:
            return
        self.busy[i] = f1 + 1
        r0 = rng.uniform(0, 360)
        key_fade(ob, f0 - 1, 0.0)
        for f in list(range(f0, f1 + 1, 2)) + [f1]:
            t = (f - f0) / max(1, f1 - f0)
            x, z = path(t)
            g = grow[0] + (grow[1] - grow[0]) * t
            lim = 6.8 - self.size * g * .72                     # keep the whole sprite inside the 13-unit frame
            x, z = max(-lim, min(lim, x)), max(-lim, min(lim, z))
            key_obj(ob, f, x=x, z=z, s=max(.01, g), r=r0 + spin * t)
            a = fade[0] + (fade[1] - fade[0]) * t
            key_fade(ob, f, max(0.0, min(1.0, a)))
        key_fade(ob, f1 + 1, 0.0)
        if behind:
            ob.location.y = 1.0


# ---------------------------------------------------------------- the clips

def clip_idle(sid, arm, glow, pools, rng):
    br, sway, bend, bob, cyc = P[sid]["idle"]
    f0, n = START["idle"], CLIPS["idle"]
    ph = 0.0                                                  # every term is zero at t=0: the loop starts on rest
    for i in range(n + 1):
        t = i / n
        a = 2 * math.pi * cyc * t
        s = math.sin(a)
        c = math.sin(2 * math.pi * t + ph * 6.28)            # one slow sway a loop
        pose = dict(root=dict(y=bob * math.sin(a), sx=1 - br * s * .6, sy=1 + br * s,
                              r=sway * c),
                    b1=dict(r=bend * (math.sin(2 * math.pi * t + .7) - math.sin(.7))),
                    b2=dict(r=bend * 1.3 * (math.sin(2 * math.pi * t + 1.4) - math.sin(1.4)), sy=1 + br * .5 * s))
        if sid == "L5":                                       # the sunflower turns slowly like a wheel
            pose["root"]["r"] = 6 * math.sin(2 * math.pi * t)
        key_pose(arm, f0 + i, **pose)
        key_fade(glow, f0 + i, base_glow(sid) * (1 + .4 * math.sin(2 * math.pi * t * 2)))
    # ambient effects that loop: emit on fixed frames so the loop is seamless (each ends before the loop does)
    fx = P[sid]["fx"]
    kind = fx[0]
    if kind in pools:
        for k, fs in enumerate((f0 + 2, f0 + 26, f0 + 50)):
            if kind == "steam":
                x0 = rng.uniform(-1.2, 1.2)
                pools[kind].particle(fs, fs + 20, lambda t, x0=x0: (x0 + .4 * math.sin(t * 5), 2.2 + 3.2 * t), rng,
                                     spin=40, grow=(.4, 1.2), fade=(.0, .0) if False else (.85, 0))
            elif kind == "bubble":
                x0 = rng.uniform(-1.5, 1.5)
                pools[kind].particle(fs, fs + 20, lambda t, x0=x0: (x0 + .3 * math.sin(t * 8), 1.0 + 4.6 * t), rng,
                                     grow=(.3, .7), fade=(1, 1))
            elif kind == "leaf" and k < 2:
                x0 = rng.uniform(-3, 3)
                pools[kind].particle(fs, fs + 22, lambda t, x0=x0: (x0 + 1.0 * math.sin(t * 6), 5.6 - 2.6 * t), rng,
                                     spin=rng.choice([-1, 1]) * 220, grow=(.55, .5), fade=(1, 0))
            elif kind in ("sparkle", "glint") and k < 2:
                x0, z0 = rng.uniform(-3.4, 3.4), rng.uniform(-2.5, 3.4)
                pools[kind].particle(fs, fs + 12, lambda t, x0=x0, z0=z0: (x0, z0), rng, spin=90,
                                     grow=(.1, .1), fade=(1, 1))
                ob = pools[kind].obs[(pools[kind].next - 1) % len(pools[kind].obs)]
                for j, f in enumerate(range(fs, fs + 13, 2)):
                    s = math.sin(math.pi * (f - fs) / 12)
                    key_obj(ob, f, s=max(.02, .7 * s))
            elif kind == "feather" and k == 1:
                x0 = rng.uniform(-2, 2)
                pools[kind].particle(fs, fs + 20, lambda t, x0=x0: (x0 + .9 * math.sin(t * 7), 1.0 - 4 * t), rng,
                                     spin=160, grow=(.6, .55), fade=(1, 0))
            elif kind == "drop" and k == 1:
                pools[kind].particle(fs, fs + 18, lambda t: (2.2, 3.6 - 6 * t * t), rng, grow=(.5, .4),
                                     fade=(1, 0))
            elif kind == "straw" and k < 2:
                x0 = rng.uniform(-3, 3)
                pools[kind].particle(fs, fs + 18, lambda t, x0=x0: (x0 + t, 2.5 - 4 * t * t), rng, spin=300,
                                     grow=(.5, .5), fade=(1, 0))
            elif kind == "popcorn" and k == 1:
                pools[kind].particle(fs, fs + 16, lambda t: (1.6 * t, 3.0 + 2.6 * t - 5 * t * t), rng, spin=200,
                                     grow=(.3, .5), fade=(1, 0))
            elif kind == "puff" and k == 0:
                pass


def clip_land(sid, arm, glow, pools, rng):
    """Drops in from above stretched, hits the reel (hard), squashes, springs back, settles to rest."""
    f0, n = START["land"], CLIPS["land"]
    soft = P[sid]["soft"]
    for i in range(n + 1):
        f = f0 + i
        if i == 0:                                            # the game shows frame 0 as the resting icon
            pose = dict(root={})
        else:                                                 # the reel drops it in; this is the impact
            t = (i - 1) / FPS
            k = damp(t, 3.2, .32) if i < n else 0
            pose = dict(root=dict(sx=1 + .2 * soft * k, sy=1 - .22 * soft * k, y=0),
                        b2=dict(r=5 * soft * damp(t + .05, 2.4, .3) * (1 if i < n else 0)),
                        b1=dict(r=-2.5 * soft * damp(t, 2.4, .3) * (1 if i < n else 0)))
        if i == n:
            pose = dict(root={}, b1={}, b2={})
        pose.setdefault("b0", {})
        pose.setdefault("b1", {})
        pose.setdefault("b2", {})
        key_pose(arm, f, **pose)
        key_fade(glow, f, base_glow(sid))
    if "puff" in pools:
        for side in (-1, 1):
            pools["puff"].particle(f0 + 2, f0 + 12, lambda t, s=side: (s * (2.6 + 1.6 * ease_out(t)), -4.3 + .4 * t),
                                   rng, grow=(.5, .1), fade=(1, 1))
    # the clip's glow returns to the idle's starting level so the hand-over is seamless
    key_fade(glow, f0 + n, base_glow(sid))


def hit_pose(sid, t, i, n):
    """The win reaction's body pose at t seconds (frame i of n)."""
    style = P[sid]["hit"]
    soft = P[sid]["soft"]
    u = i / n
    env = math.sin(math.pi * min(1, u / .85)) if u < .85 else 0     # rises, holds, comes home
    pose = dict(root={}, b0={}, b1={}, b2={})
    # shared anticipation (0-5 f): crouch
    if i <= 5:
        k = ease_in_out(i / 5)
        pose["root"] = dict(sx=1 + .12 * k, sy=1 - .14 * k)
        return pose
    tt = (i - 5) / FPS
    if style in ("bounce", "hop", "spin", "pop", "hiccup"):
        jump = max(0.0, math.sin(math.pi * min(1, tt / .42)))         # one jump in .42 s
        land = damp(max(0, tt - .42), 3.0, .3) if tt > .42 else 0
        pose["root"] = dict(y=.6 * jump, sx=1 - .06 * jump + .14 * soft * land, sy=1 + .08 * jump - .16 * soft * land)
        if style == "spin":
            sp = ease_in_out(min(1, tt / .55))
            pose["root"]["r"] = -360 * sp
            shrink = 1 - .16 * math.sin(math.pi * sp)            # a square icon's corners stay in the frame
            pose["root"]["sx"] *= shrink
            pose["root"]["sy"] *= shrink
            pose["root"]["y"] = pose["root"]["y"] + HALF * (1 - shrink)  # keep the shrink centred
        if style == "hop":
            pose["root"]["r"] = 12 * math.sin(math.pi * min(1, tt / .42)) * (1 if i % 2 else 1)
            pose["b2"] = dict(r=-10 * jump)
        if style == "hiccup":
            pose["root"]["r"] = 8 * math.sin(tt * 18) * math.exp(-tt * 2)
            pose["b2"] = dict(sx=1 + .12 * jump, sy=1 + .1 * jump)
        if style == "pop":
            pose["b2"] = dict(sy=1 + .1 * jump, sx=1 - .06 * jump)
    elif style == "jiggle":
        k = damp(tt, 4.2, .12)
        pose["root"] = dict(sx=1 + .16 * soft * k * env, sy=1 - .16 * soft * k * env, y=.3 * env)
        pose["b2"] = dict(r=6 * soft * math.sin(tt * 20) * env)
    elif style == "wobbletop":
        pose["root"] = dict(y=.3 * env, sx=1 + .05 * env, sy=1 + .04 * env)
        pose["b2"] = dict(r=14 * math.sin(tt * 16) * math.exp(-tt * 1.5) * env, sy=1 + .1 * env)
        pose["b1"] = dict(r=-6 * math.sin(tt * 16 + .5) * math.exp(-tt * 1.5) * env)
    elif style == "spill":
        pose["root"] = dict(r=-10 * env, y=.4 * env, sx=1 + .05 * env, sy=1 + .05 * env)
        pose["b2"] = dict(r=-8 * env + 4 * math.sin(tt * 14) * env)
    elif style == "flutter":
        pose["root"] = dict(r=18 * math.sin(tt * 9) * env, y=.4 * env, sx=1 - .06 * env, sy=1 - .06 * env)
        pose["b1"] = dict(r=10 * math.sin(tt * 9 + 1) * env)
        pose["b2"] = dict(r=16 * math.sin(tt * 9 + 2) * env)
    elif style == "flap":
        f = math.sin(tt * 26)
        pose["root"] = dict(y=.45 * env, sx=1 + .12 * f * env, sy=1 - .05 * f * env)
        pose["b2"] = dict(r=8 * math.sin(tt * 13) * env)
    if style in ("spin", "flutter", "spill"):
        about_centre(pose["root"])
    return pose


def about_centre(root):
    """Turn the root about the icon's centre, not its foot: the root bone sits at the art's bottom edge, so a turn
    there swings the icon out of the frame. Rotating the centre (0, h) by r moves it to (-h sin r, h cos r)."""
    r = math.radians(root.get("r", 0.0))
    h = HALF * root.get("sy", 1.0)
    root["x"] = root.get("x", 0.0) + h * math.sin(r)
    root["y"] = root.get("y", 0.0) + h * (1 - math.cos(r))


def clip_hit(sid, arm, glow, pools, rng):
    f0, n = START["hit"], CLIPS["hit"]
    tier = TIER.get(sid, 3)
    for i in range(n + 1):
        f = f0 + i
        pose = hit_pose(sid, (i - 5) / FPS, i, n) if i < n else dict(root={}, b0={}, b1={}, b2={})
        key_pose(arm, f, **pose)
        u = i / n
        g = math.sin(math.pi * min(1, u / .9)) if u < .9 else 0
        peak = .75 if tier <= 2 or sid in ("BS", "ES", "M") else .55
        key_fade(glow, f, base_glow(sid) + (peak - base_glow(sid)) * g)
        key_obj(glow, f, s=1 + .04 * g)
    key_fade(glow, f0 + n, base_glow(sid))
    key_obj(glow, f0 + n, s=1.0)
    # rays behind the big ones
    if "rays" in pools:
        ob = pools["rays"].obs[0]
        key_fade(ob, f0 + 4, 0)
        for f in range(f0 + 6, f0 + n - 2, 2):
            t = (f - f0 - 6) / (n - 8)
            key_obj(ob, f, s=.72 + .2 * ease_out(t), r=60 * t)
            key_fade(ob, f, .8 * math.sin(math.pi * t))
        key_fade(ob, f0 + n - 1, 0)
    # a ring when it peaks
    if "ring" in pools:
        pools["ring"].particle(f0 + 7, f0 + 19, lambda t: (0, 0), rng, grow=(.55, 1.18), fade=(1, 0))
    # its own burst
    fx = P[sid]["fx"]
    for kind in fx:
        if kind not in pools:
            continue
        m = {"sparkle": 6, "glint": 3, "leaf": 6, "steam": 3, "crumb": 6, "bubble": 6, "popcorn": 8, "puff": 3,
             "drop": 7, "straw": 7, "feather": 6}.get(kind, 4)
        for j in range(m):
            fs = f0 + 7 + int(j * 1.5)
            a = rng.uniform(0, 2 * math.pi)
            if kind in ("sparkle", "glint"):
                x0, z0 = 3.8 * math.cos(a) * rng.uniform(.7, 1), 3.8 * math.sin(a) * rng.uniform(.7, 1)
                pools[kind].particle(fs, fs + 12, lambda t, x0=x0, z0=z0: (x0 * (.8 + .3 * t), z0 * (.8 + .3 * t)),
                                     rng, spin=120, grow=(.9, .05), fade=(1, 1))
            elif kind == "steam":
                x0 = rng.uniform(-1.5, 1.5)
                pools[kind].particle(fs, fs + 18, lambda t, x0=x0: (x0 + .5 * math.sin(t * 6), 2.4 + 3.4 * t), rng,
                                     spin=60, grow=(.5, 1.4), fade=(.95, 0))
            elif kind == "bubble":
                x0 = rng.uniform(-2, 2)
                pools[kind].particle(fs, fs + 16, lambda t, x0=x0: (x0 + .4 * math.sin(t * 9), 1.5 + 4.8 * t), rng,
                                     grow=(.4, .9), fade=(1, 1))
            else:                                               # thrown out and falling: leaves, crumbs, kernels
                sp = rng.uniform(3.4, 5.2)
                vx, vz = sp * math.cos(a) * 1.1, abs(sp * math.sin(a)) + 2.5
                g = 9 if kind not in ("leaf", "feather") else 4
                pools[kind].particle(fs, fs + 18, lambda t, vx=vx, vz=vz, g=g: (vx * t * .75,
                                     1.0 + (vz * t - .5 * g * t * t) * .75), rng,
                                     spin=rng.choice([-1, 1]) * 360, grow=(.75, .6),
                                     fade=(1, 0) if kind in ("leaf", "feather") else (1, 1))


def clip_multi(sid, arm, glow, pools, rng):
    """A multiplier lands on it: it shudders and charges up (glow swells), then releases with a ring and a pop."""
    f0, n = START["multi"], CLIPS["multi"]
    soft = min(1.0, P[sid]["soft"])                             # the jelly's softness would push it out of frame
    for i in range(n + 1):
        f = f0 + i
        if i >= n:
            pose = dict(root={}, b0={}, b1={}, b2={})
        elif i < 18:                                            # charge: tremble, swell
            k = i / 18
            sh = math.sin(i * 2.6) * k
            pose = dict(root=dict(x=.08 * sh, sx=1 + .08 * k, sy=1 + .08 * k, r=2.5 * sh), b2=dict(r=3 * sh))
        else:                                                   # release: punch out then settle
            t = (i - 18) / FPS
            k = damp(t, 3.4, .3)
            pose = dict(root=dict(sx=1 + .16 * soft * k, sy=1 + .1 * k, y=.15 * k),
                        b2=dict(r=-5 * soft * damp(t, 2.6, .3)))
        pose.setdefault("b0", {}); pose.setdefault("b1", {}); pose.setdefault("b2", {})
        key_pose(arm, f, **pose)
        g = min(1, i / 18) if i < 18 else max(0, 1 - (i - 18) / 16)
        key_fade(glow, f, base_glow(sid) + (.95 - base_glow(sid)) * g)
        key_obj(glow, f, s=1 + .05 * g)
    key_fade(glow, f0 + n, base_glow(sid))
    key_obj(glow, f0 + n, s=1.0)
    if "ring" in pools:
        pools["ring"].particle(f0 + 18, f0 + 30, lambda t: (0, 0), rng, grow=(.55, 1.18), fade=(1, 0))
    if "sparkle" in pools:
        for j in range(8):
            a = 2 * math.pi * j / 8 + .3
            pools["sparkle"].particle(f0 + 18, f0 + 30, lambda t, a=a: (math.cos(a) * (3.6 + 1.5 * ease_out(t)),
                                      math.sin(a) * (3.6 + 1.5 * ease_out(t))), rng, spin=180, grow=(.8, .05))
    if sid == "M" and "drop" in pools:                          # the cider bottle's cork pops and it sprays
        for j in range(7):
            a = math.radians(rng.uniform(55, 125))
            pools["drop"].particle(f0 + 18 + j, f0 + 34 + j, lambda t, a=a: (math.cos(a) * 5 * t + 1.4,
                                   3.4 + math.sin(a) * 5 * t - 5 * t * t), rng, grow=(.7, .5), fade=(1, 1))


def build(sid, seed=None):
    clear()
    setup_scene(sid)
    rng = random.Random(seed if seed is not None else sum(map(ord, sid)) * 7)
    arm, icon, glow = build_icon(sid)
    kinds = set(P[sid]["fx"]) | {"sparkle"}
    sizes = {"leaf": 10, "sparkle": 12, "glint": 6, "steam": 8, "bubble": 10, "popcorn": 10, "puff": 4, "drop": 10,
             "straw": 9, "feather": 8, "crumb": 8}
    pools = {k: Pool(k, sizes.get(k, 8), sid) for k in kinds}
    pools["ring"] = Pool2("ring", 2, 9.0, behind=True)
    if sid in TIER and TIER[sid] == 1 or sid in ("BS", "ES", "M"):
        pools["rays"] = Pool2("rays", 1, 11.0, behind=True)
    clip_idle(sid, arm, glow, pools, rng)
    clip_land(sid, arm, glow, pools, rng)
    clip_hit(sid, arm, glow, pools, rng)
    clip_multi(sid, arm, glow, pools, rng)
    # steps between clips are not seen; make every curve linear where we keyed every frame (keeps loops exact)
    for ob in [arm] + [o for o in bpy.data.objects if o.animation_data]:
        ad = ob.animation_data
        if ad and ad.action:
            for fc in fcurves(ad.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR" if ob is arm else "BEZIER"
    for m in bpy.data.materials:
        ad = m.node_tree.animation_data if m.node_tree else None
        if ad and ad.action:
            for fc in fcurves(ad.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
    os.makedirs(BLEND, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BLEND, sid + ".blend"))
    return arm


def Pool2(kind, n, size, behind=False):
    """A pool for the shared big effects (ring, rays), which are not in FX_SPEC."""
    p = Pool.__new__(Pool)
    p.size = size
    p.obs = []
    for i in range(n):
        ob = sprite(f"{kind}_{i}", kind + ".png", size, depth=(1.4 if behind else -1.6) - .01 * i)
        key_fade(ob, 0, 0.0)
        p.obs.append(ob)
    p.next = 0
    p.busy = [0] * n
    return p


def fcurves(act):
    try:
        return list(act.fcurves)
    except AttributeError:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    out.extend(cb.fcurves)
        return out


def render(sid, clips=None):
    sc = bpy.context.scene
    for clip in (clips or CLIPS):
        d = os.path.join(REN, sid, clip)
        os.makedirs(d, exist_ok=True)
        for old in os.listdir(d):
            os.remove(os.path.join(d, old))
        n = CLIPS[clip]
        frames = range(START[clip], START[clip] + n) if clip == "idle" else range(START[clip], START[clip] + n + 1)
        for k, f in enumerate(frames):
            sc.frame_set(f)
            sc.render.filepath = os.path.join(d, f"{k:04d}.png")
            bpy.ops.render.render(write_still=True)


if __name__ == "__main__" and "--" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:]
    sid = args[0]
    steps = args[1].split(",") if len(args) > 1 else ["build", "render"]
    if "build" in steps:
        build(sid)
    else:
        bpy.ops.wm.open_mainfile(filepath=os.path.join(BLEND, sid + ".blend"))
    if "render" in steps:
        render(sid)
    print("DONE", sid)
