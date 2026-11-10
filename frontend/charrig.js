/* Live character rigs (Voodoo on Bourbon, 2026-11-09).

   A character made and animated in Blender (tools/nola/blender/doc_rig.py) and packed by tools/nola/pack_rig.py
   comes as a rig rather than baked frames: its parts (assets/chars/<name>/rig/: an atlas per density, a mesh per
   part, 4 bone weights per vertex) and, for every clip, each bone's 2D transform on every frame Blender keyed (30 a
   second). The game poses the meshes itself on every screen refresh, the bones' transforms eased between Blender's
   frames on a Catmull-Rom curve - so the figure moves smoothly at 60, 120 or 165 Hz and at any idle speed, where
   baked 30 fps frames stepped (and stepped at 17 fps through the slowed idle), and it weighs a few MB, not hundreds.

   Second pass (2026-11-09, owner: "rigid / uncanny ... the flame its own animation"):
   - the idle never rests: it loops at its own pace (rig.json "idle"), and a reaction cuts in from whatever frame is
     showing, the two poses eased across `cut` frames - a figure that stops breathing reads as a cut-out;
   - the flame over his palm is not a picture: makeFlame() draws it live - a shader flame on one quad (rising
     noise eats a teardrop into licking tongues, toon bands of green over an ink line), a glowing orb at its
     root, a soft halo and a few embers. It rides a spring that trails the rig's "orb" bone, bobs on its own
     wander, and leans away from the way it is moving; the bone's scale is its size, the clip's alpha.orb track its
     strength. It runs on the clock, not on the clip, so it never repeats and never freezes.

   CharRig.make({el, name, flavour, swap, shadow}) -> {react, enter, exit} like the frame player in index.html's
   makeCharacter (the same clip ranks, cues, idle rest and walk-on/off), or undefined when the character has no rig
   (the frame player takes over), or null when it fails to load. It uses the page's own CHAR_* settings, charSfx,
   REDUCED_MOTION, state and footShadow. */
(function () {
  "use strict";
  const CR = (window.CharRig = {});

  const catmull = (p0, p1, p2, p3, t) => {
    const t2 = t * t, t3 = t2 * t;
    return .5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (3 * p1 - p0 - 3 * p2 + p3) * t3);
  };
  const image = url => new Promise((ok, no) => {
    const im = new Image();
    im.decoding = "async";
    im.onload = () => ok(im);
    im.onerror = () => no(new Error(url + " did not load"));
    im.src = url;
  });
  const bytes = url => fetch(url).then(r => { if (!r.ok) throw new Error(url + " -> HTTP " + r.status); return r.arrayBuffer(); });

  async function load(name, figurePx) {
    const base = `assets/chars/${name}/rig/`;
    const r = await fetch(base + "rig.json");
    if (r.status === 404) return undefined;                       // no rig: the baked frames, if any
    if (!r.ok) throw new Error(`${name} rig.json -> HTTP ${r.status}`);
    const man = await r.json();
    // the smallest density that still draws the standing figure at a texel per screen pixel
    const want = figurePx / man.rest_height;
    const D = man.densities.find(d => d.d >= want) || man.densities[man.densities.length - 1];
    const [geo, clips, pages] = await Promise.all([bytes(base + man.geo), bytes(base + man.clips_bin),
      Promise.all(D.pages.map(p => image(base + p)))]);
    return { man, D, geo, clips: new Float32Array(clips), pages };
  }

  // ---------------------------------------------------------------- the flame over his palm
  // One quad, 280 x 420 art px at size 1, the orb's middle 74% of the way down it. In the fragment shader q is the
  // pixel in art px from the orb's middle (y up). The flame is a teardrop standing on the orb; noise that climbs
  // through it is taken off its edge - more the higher up - so the sides lick, split and let go of little tongues;
  // the same field, hotter low down and inside, steps through four greens (a toon flame: an ink line round it like
  // everything else he is drawn with, never a soft photographic fire). It sways on slow noise and leans by uLean.
  const FLAME_VS = `
    in vec2 aPosition;
    in vec2 aUV;
    out vec2 vUV;
    uniform mat3 uProjectionMatrix;
    uniform mat3 uWorldTransformMatrix;
    uniform mat3 uTransformMatrix;
    void main() {
      mat3 mvp = uProjectionMatrix * uWorldTransformMatrix * uTransformMatrix;
      gl_Position = vec4((mvp * vec3(aPosition, 1.0)).xy, 0.0, 1.0);
      vUV = aUV;
    }`;
  const FLAME_FS = `
    in vec2 vUV;
    uniform float uTime;
    uniform float uPower;
    uniform float uLean;
    uniform float uStretch;
    uniform float uPx;                                          // art px per screen px (no fwidth in this GLSL)
    float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123); }
    float vnoise(vec2 p) {
      vec2 i = floor(p); vec2 f = fract(p); f = f * f * (3.0 - 2.0 * f);
      return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
    }
    float fbm(vec2 p) {
      float s = 0.0; float a = 0.5;
      for (int k = 0; k < 4; k++) { s += a * vnoise(p); p = p * 2.02 + vec2(13.7, 7.3); a *= 0.5; }
      return s;
    }
    void main() {
      vec2 q = vec2((vUV.x - 0.5) * 280.0, (0.74 - vUV.y) * 420.0);
      float t = uTime;
      float H = 232.0 * uStretch;
      float h = q.y / H;
      float hh = clamp(h, 0.0, 1.2);
      float sway = (fbm(vec2(q.y * 0.011 - t * 1.25, t * 0.31)) - 0.47) * 2.0;
      float x = q.x - (uLean * 90.0 + sway * 34.0) * hh * hh - sin(q.y * 0.043 - t * 5.2) * 6.0 * hh;
      float w = 54.0 * pow(max(0.0, 1.0 - hh), 0.62) * smoothstep(-0.02, 0.12, h) + 2.0;
      float d = 1.0 - abs(x) / w;
      float n1 = fbm(vec2(x * 0.026, q.y * 0.018 - t * 2.3));
      float n2 = fbm(vec2(x * 0.06 + 31.0, q.y * 0.04 - t * 3.7));
      // now and then a notch climbs through it and the tip parts into two or three tongues
      float split = smoothstep(0.52, 0.7, fbm(vec2(x * 0.075 + 7.0, q.y * 0.010 - t * 1.6)));
      float f = d - (n1 * 1.1 + n2 * 0.6) * (0.14 + 1.2 * hh) - split * 0.75 * smoothstep(0.15, 0.6, hh) + 0.22;
      f = min(f, (h + 0.03) * 8.0);                             // the flame stands ON the orb...
      float aura = (1.0 - length(q) / 36.0) * 1.5;              // ...which wears a round skin of it, so its foot is a ball
      f = max(f, aura);
      float grad = 1.0 / max(mix(24.0, w, smoothstep(0.0, 0.15, h)), 9.0);   // how fast f falls off per art px, near enough
      float aa = 1.2 * uPx * grad;                              // one screen px of f: the edges' softness
      float e = 3.6 * grad;                                     // the ink line: 3.6 art px wide, whatever the size on screen
      float inside = smoothstep(0.0, aa, f);
      float body = smoothstep(e, e + aa, f);
      vec3 inkC = vec3(0.03, 0.13, 0.07);
      vec3 c0 = vec3(0.07, 0.62, 0.26);
      vec3 c1 = vec3(0.33, 0.93, 0.33);
      vec3 c2 = vec3(0.74, 1.00, 0.52);
      vec3 c3 = vec3(0.96, 1.00, 0.86);
      float heat = f + 0.55 * (1.0 - hh) - 0.25;                // hotter inside and low down
      float ah = aa;
      vec3 col = c0;
      col = mix(col, c1, smoothstep(0.10, 0.10 + 2.0 * ah, heat));
      col = mix(col, c2, smoothstep(0.42, 0.42 + 2.0 * ah, heat));
      col = mix(col, c3, smoothstep(0.80, 0.80 + 3.0 * ah, heat));
      col = mix(inkC, col, body);
      float a = inside * (1.0 - 0.4 * smoothstep(0.7, 1.15, hh));
      // the orb at its root: a ball of light, a slow swirl inside it
      float r = length(q * vec2(1.0, 1.04)) / 28.0;
      float o = 1.0 - r;
      float ao = 1.2 * uPx / 28.0;
      float om = smoothstep(0.0, ao, o);
      float swirl = fbm(q * 0.07 + vec2(t * 0.9, -t * 0.6)) - 0.5;
      vec3 oc = mix(c2, c3, smoothstep(0.2, 0.7, o + 0.25 * swirl));
      oc = mix(c1, oc, smoothstep(0.0, 0.2, o));
      col = mix(col, oc, om * 0.94);
      a = max(a, om) * uPower;
      float g = exp(-r * r * 0.4) * 0.28 * uPower;              // its bloom, added to whatever is behind
      gl_FragColor = vec4(col * a + vec3(0.35, 1.0, 0.4) * g * (1.0 - a), a);
    }`;
  function makeFlame(app, man) {
    const view = new PIXI.Container();
    const j = man.bones.indexOf(man.orb.bone) * 6, ax = man.orb.at[0], ay = man.orb.at[1];
    const disc = (size, stops) => {                          // a round fade, drawn here: no file
      const c = document.createElement("canvas");
      c.width = c.height = size;
      const g = c.getContext("2d"), gr = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
      for (const [o, col] of stops) gr.addColorStop(o, col);
      g.fillStyle = gr; g.fillRect(0, 0, size, size);
      return PIXI.Texture.from(c);
    };
    const halo = new PIXI.Sprite(disc(256, [[0, "rgba(150,255,120,.5)"], [.22, "rgba(110,255,100,.26)"], [.55, "rgba(60,220,90,.08)"], [1, "rgba(40,200,80,0)"]]));
    halo.anchor.set(.5); halo.blendMode = "add";
    view.addChild(halo);
    let mesh = null, uni = null;
    const gl = !PIXI.RendererType || app.renderer.type === PIXI.RendererType.WEBGL;
    if (gl && PIXI.Shader && PIXI.Geometry && PIXI.Mesh) {
      try {
        const geometry = new PIXI.Geometry({ attributes: { aPosition: [-.5, -.74, .5, -.74, .5, .26, -.5, .26], aUV: [0, 0, 1, 0, 1, 1, 0, 1] },
                                             indexBuffer: [0, 1, 2, 0, 2, 3] });
        const shader = PIXI.Shader.from({ gl: { vertex: FLAME_VS, fragment: FLAME_FS },
          resources: { flame: { uTime: { value: 0, type: "f32" }, uPower: { value: 1, type: "f32" }, uLean: { value: 0, type: "f32" },
                                uStretch: { value: 1, type: "f32" }, uPx: { value: 1, type: "f32" } } } });
        mesh = new PIXI.Mesh({ geometry, shader });
        uni = shader.resources.flame.uniforms;
        view.addChild(mesh);
      } catch (e) { console.warn("flame shader unavailable:", e.message); mesh = null; }
    }
    if (!mesh) {                                             // no shader: the orb alone, as a ball of light
      const ball = new PIXI.Sprite(disc(64, [[0, "rgba(245,255,225,1)"], [.45, "rgba(170,255,120,1)"], [.8, "rgba(80,235,90,.9)"], [1, "rgba(60,220,80,0)"]]));
      ball.anchor.set(.5); ball.scale.set(1.1);
      view.addChild(ball);
      view._ball = ball;
    }
    const sparkTex = disc(32, [[0, "rgba(240,255,220,1)"], [.3, "rgba(160,255,120,.9)"], [1, "rgba(80,255,90,0)"]]);
    const embers = Array.from({ length: 12 }, () => {
      const s = new PIXI.Sprite(sparkTex);
      s.anchor.set(.5); s.blendMode = "add"; s.visible = false;
      view.addChild(s);
      return { s, life: 0 };
    });
    let seed = 7919;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
    const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
    let tx = 0, ty = 0, ts = 1, ta = 1, has = false, px = 0, py = 0, vx = 0, vy = 0, sz = 1, pw = 1, last = 0, acc = 0;
    // where the rig wants it (the orb bone on its anchor), how big (the bone's scale) and how strong
    const aim = (M, alpha) => {
      tx = M[j] * ax + M[j + 2] * ay + M[j + 4];
      ty = M[j + 1] * ax + M[j + 3] * ay + M[j + 5];
      ts = Math.sqrt(Math.abs(M[j] * M[j + 3] - M[j + 1] * M[j + 2]));
      ta = alpha;
      if (!has) { has = true; px = tx; py = ty; sz = ts; pw = ta; }
    };
    const tick = (now, snap) => {
      if (!has) return;
      let dt = last ? clamp((now - last) / 1000, 0, .05) : 0;
      last = now;
      if (snap) { px = tx; py = ty; vx = vy = 0; sz = ts; pw = ta; dt = 0; }
      const t = now / 1000;
      // it trails the hand on a spring (2.4 Hz, half damped): late, a little past, back
      const w = 2 * Math.PI * 2.4, z = .5;
      for (let k = 0; k < 2; k++) {
        const h = dt / 2;
        vx += (w * w * (tx - px) - 2 * z * w * vx) * h;
        vy += (w * w * (ty - py) - 2 * z * w * vy) * h;
        px += vx * h; py += vy * h;
      }
      sz += (ts - sz) * Math.min(1, dt * 14);
      pw += (ta - pw) * Math.min(1, dt * 14);
      // and wanders on its own, on waves that never line up twice
      const bx = 3.4 * Math.sin(t * 1.13 + 1) + 1.7 * Math.sin(t * 2.71 + .4);
      const by = 5.2 * Math.sin(t * 1.7) + 2.3 * Math.sin(t * 3.9 + 2);
      const x = px + bx * sz, y = py + by * sz;
      const flick = 1 + .06 * Math.sin(t * 9.3) + .04 * Math.sin(t * 14.7 + 1.3);
      const grow = Math.pow(sz, .8);                         // a big flame is not as tall as it is wide times its size
      halo.position.set(x, y - 34 * grow);
      halo.scale.set(1.45 * grow * flick * (.5 + .5 * pw));
      halo.alpha = .8 * pw;
      halo.visible = pw > .01;
      if (mesh) {
        mesh.position.set(x, y);
        mesh.scale.set(280 * grow, 420 * grow);
        uni.uTime = t % 900;
        uni.uPx = 1 / Math.max(.02, grow * view.parent.scale.x * app.renderer.resolution);
        uni.uPower = clamp(pw * 1.6, 0, 1);
        uni.uLean = clamp(-vx / 360 + .1 * Math.sin(t * .7), -1, 1);      // the tip trails the way it came
        uni.uStretch = clamp(1 + vy / 900, .55, 1.4) * (.45 + .55 * pw) * (.94 + .06 * flick);
        mesh.visible = pw > .01;
      } else if (view._ball) {
        view._ball.position.set(x, y); view._ball.scale.set(1.1 * grow * flick); view._ball.alpha = pw;
      }
      // embers: one breaks off now and then, drifts up on a wobble and goes out
      acc += dt * 2.6 * pw * Math.sqrt(sz);
      while (acc >= 1) {
        acc -= 1;
        const e = embers.find(q => q.life <= 0);
        if (!e) break;
        e.life = e.max = .9 + rnd() * .9;
        e.x = x + (rnd() - .5) * 44 * grow; e.y = y - (50 + rnd() * 130) * grow;
        e.vx = (rnd() - .5) * 26; e.vy = -(48 + rnd() * 70); e.ph = rnd() * 6.28; e.r = (.26 + rnd() * .34) * Math.sqrt(grow);
      }
      for (const e of embers) {
        if (e.life <= 0) { e.s.visible = false; continue; }
        e.life -= dt;
        e.x += (e.vx + 18 * Math.sin(t * 5 + e.ph)) * dt;
        e.y += e.vy * dt;
        e.vy *= 1 - .6 * dt;
        const k = Math.max(0, e.life / e.max);
        e.s.position.set(e.x, e.y);
        e.s.scale.set(e.r * (.5 + .5 * k));
        e.s.alpha = Math.min(1, k * 2.2) * pw;
        e.s.visible = true;
      }
    };
    return { view, aim, tick };
  }

  CR.make = async function ({ el, name, flavour, swap = {}, shadow = true }) {
    const root = document.getElementById(el);
    if (!root || typeof PIXI === "undefined" || !PIXI.MeshSimple) return undefined;
    const headroom = () => parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--char-headroom")) || 1;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    let R;
    try { R = await load(name, root.clientHeight / headroom() * dpr); }
    catch (e) { console.warn("character rig failed to load:", name, e.message); return null; }
    if (!R) return undefined;
    const { man, D } = R;
    const B = man.bones.length, fps = man.fps, has = clip => !!man.clips[clip];
    if (!has("idle")) { console.warn("character rig has no idle:", name); return null; }

    // His canvas runs past his box at the sides and above it (.charstage, sized in the stylesheet): the flame's
    // glow, its embers and a reaction's rings were cut off square on the box's edge (owner, 2026-11-09: "the glow
    // is leaving their box / getting cut off on the edges"). He is still sized by the box and stands on its
    // bottom edge - only the room he is drawn in is bigger.
    const stageEl = document.createElement("div");
    stageEl.className = "charstage";
    root.appendChild(stageEl);
    const app = new PIXI.Application();
    await app.init({ backgroundAlpha: 0, antialias: true, autoDensity: true, resolution: dpr, resizeTo: stageEl });
    app.ticker.maxFPS = CHAR_FPS;
    stageEl.appendChild(app.canvas);
    // the stage is drawn only when the pose changes (a figure resting between idle cycles costs nothing)
    let dirty = true;
    const touch = () => { dirty = true; };
    app.ticker.remove(app.render, app);
    app.ticker.add(() => { if (dirty) { dirty = false; app.render(); } }, null, PIXI.UPDATE_PRIORITY.LOW);
    app.renderer.on("resize", touch);

    // ---- the parts: one mesh each, on the density's atlas pages
    const pages = R.pages.map(im => {
      const t = PIXI.Texture.from(im);
      t.source.autoGenerateMipmaps = true;    // drawn a little under its size: trilinear, no shimmer
      t.source.style.minFilter = "linear"; t.source.style.mipmapFilter = "linear";
      return t;
    });
    const actor = new PIXI.Container();
    app.stage.addChild(actor);
    const parts = man.parts.map(p => {
      const fr = D.frames[p.tex], page = pages[fr[0]], pw = page.source.width, ph = page.source.height;
      const rest = new Float32Array(R.geo, p.o_pos, p.verts * 2);
      const uv0 = new Float32Array(R.geo, p.o_uv, p.verts * 2), uvs = new Float32Array(p.verts * 2);
      for (let i = 0; i < p.verts; i++) {
        uvs[2 * i] = (fr[1] + uv0[2 * i] * fr[3]) / pw;
        uvs[2 * i + 1] = (fr[2] + uv0[2 * i + 1] * fr[4]) / ph;
      }
      const mesh = new PIXI.MeshSimple({ texture: page, vertices: new Float32Array(rest), uvs,
        indices: new Uint32Array(new Uint16Array(R.geo, p.o_idx, p.tris * 3)) });
      actor.addChild(mesh);
      return { p, mesh, rest, bi: new Uint8Array(R.geo, p.o_bi, p.verts * 4), bw: new Uint8Array(R.geo, p.o_bw, p.verts * 4),
               face: p.face ? man.faces.indexOf(p.face) : -1 };
    });
    const flame = man.orb ? makeFlame(app, man) : null;
    if (flame) actor.addChild(flame.view);
    // the clips' sparks, beads, smoke and rings: sprites from the atlas, pooled by Blender's object id
    const fxLayer = new PIXI.Container();
    actor.addChild(fxLayer);
    const fxTex = man.fx.map(k => {
      const fr = D.frames["fx_" + k];
      return fr ? new PIXI.Texture({ source: pages[fr[0]].source, frame: new PIXI.Rectangle(fr[1], fr[2], fr[3], fr[4]) }) : null;
    });
    const fxPool = new Map();
    const fxSprite = id => {
      let s = fxPool.get(id);
      if (!s) { s = new PIXI.Sprite(); s.anchor.set(.5); fxLayer.addChild(s); fxPool.set(id, s); }
      return s;
    };

    // ---- posing
    const M = new Float32Array(B * 6), M2 = new Float32Array(B * 6), X = new PIXI.Matrix();
    const clipBase = c => man.clips[c].o / 4;
    const sample = (clip, f, out) => {
      const C = man.clips[clip], n = C.frames, base = clipBase(clip), S = B * 6, d = R.clips;
      const i1 = Math.floor(f), t = f - i1;
      const at = k => base + (C.loop ? ((k % n) + n) % n : Math.max(0, Math.min(n - 1, k))) * S;
      const a1 = at(i1);
      if (t < 1e-4) { out.set(d.subarray(a1, a1 + S)); return; }
      const a0 = at(i1 - 1), a2 = at(i1 + 1), a3 = at(i1 + 2);
      for (let k = 0; k < S; k++) out[k] = catmull(d[a0 + k], d[a1 + k], d[a2 + k], d[a3 + k], t);
    };
    const skin = () => {
      for (const q of parts) {
        if (!q.mesh.visible) continue;
        const v = q.mesh.vertices, rest = q.rest, bi = q.bi, bw = q.bw, n = rest.length / 2;
        for (let i = 0; i < n; i++) {
          const x = rest[2 * i], y = rest[2 * i + 1];
          let sx = 0, sy = 0;
          for (let k = 4 * i, e = k + 4; k < e; k++) {
            const w = bw[k];
            if (!w) continue;
            const j = bi[k] * 6;
            sx += w * (M[j] * x + M[j + 2] * y + M[j + 4]);
            sy += w * (M[j + 1] * x + M[j + 3] * y + M[j + 5]);
          }
          v[2 * i] = sx / 255; v[2 * i + 1] = sy / 255;
        }
      }
    };
    const lerpTrack = (arr, f, loop) => {
      const n = arr.length, i = Math.floor(f), t = f - i, a = arr[loop ? i % n : Math.min(n - 1, i)];
      const b = arr[loop ? (i + 1) % n : Math.min(n - 1, i + 1)];
      return a + (b - a) * t;
    };
    const drawFx = (C, f) => {
      for (const s of fxPool.values()) s.visible = false;
      const i = Math.min(C.fx.length - 1, Math.floor(f)), t = f - i, now = C.fx[i] || [], nxt = C.fx[i + 1] || [];
      for (const dr of now) {
        const tex = fxTex[dr[0]];
        if (!tex) continue;
        const nb = t > 0 ? nxt.find(e => e[1] === dr[1]) : null;
        const g = k => nb ? dr[k] + (nb[k] - dr[k]) * t : dr[k];
        const s = fxSprite(dr[1]);
        if (s.texture !== tex) s.texture = tex;
        const tw = tex.frame.width, th = tex.frame.height;
        X.set(g(2) / tw, g(3) / tw, g(4) / th, g(5) / th, g(6), g(7));
        s.setFromMatrix(X);
        s.alpha = g(8);
        s.visible = true;
      }
    };
    let shownKey = "", shown = null;
    const show = (clip, f) => {
      const C = man.clips[clip];
      const fi = Math.max(0, Math.min(C.frames - 1, Math.round(f) % C.frames));
      const face = C.face[fi];
      for (const q of parts) if (q.face >= 0) q.mesh.visible = q.face === face;
      if (flame) flame.aim(M, C.alpha && C.alpha.orb ? lerpTrack(C.alpha.orb, f, C.loop) : 1);
      skin();
      drawFx(C, f);
      shown = { clip, i: fi, f };
      touch();
    };

    // ---- the figure on its canvas: soles on the bottom edge, centred, scaled so its standing height fills the box
    // the CSS sizes (less the headroom kept free above for a raised arm, smoke, a lifted hat)
    const fit = () => {
      const w = app.screen.width, h = app.screen.height;
      if (!w || !h) return;
      actor.pivot.set(man.cx, man.ground_y);
      actor.scale.set((root.clientHeight || h) / headroom() / man.rest_height);   // by his BOX, not the wider canvas
      actor.position.set(w / 2, h);
      touch();
    };
    fit();
    app.renderer.on("resize", fit);
    addEventListener("resize", fit);

    // the shoes, for the shadows: each shoe's sole through its foot bone, in art px
    const shoesNow = () => Object.entries(man.shoes).map(([bn, [x0, x1, y]]) => {
      const j = man.bones.indexOf(bn) * 6;
      const px = x => M[j] * x + M[j + 2] * y + M[j + 4], py = x => M[j + 1] * x + M[j + 3] * y + M[j + 5];
      return [Math.min(px(x0), px(x1)), Math.max(px(x0), px(x1)), Math.max(py(x0), py(x1))];
    });
    const restShoes = Object.values(man.shoes).map(s => s.slice());
    const fig = {
      showing: () => shown,
      shoes: (clip, i) => (clip === "idle" && i === 0 && !shown ? restShoes : shoesNow()),
      scale: () => actor.scale.x,
      alpha: () => 1,
      toStage: (x, y) => ({ x: actor.position.x + (x - man.cx) * actor.scale.x, y: actor.position.y + (y - man.ground_y) * actor.scale.x }),
    };

    // ---- the clock (as the frame player: clips never cut into each other; the idle plays a cycle, then rests)
    let cur = { clip: "idle", t0: performance.now() }, next = null, fade = null;
    let rank = -1, until = 0, away = true, timer = 0, fadeTimer = 0;
    const IDLE = man.idle || { rate: CHAR_IDLE_RATE, rest: CHAR_IDLE_REST, cut: 0 };
    const CUT = IDLE.cut || CHAR_XFADE;                     // frames a change of clip is eased over
    const rateOf = clip => clip === "idle" ? IDLE.rate : 1;
    const spanOf = clip => man.clips[clip].loop ? man.clips[clip].frames : man.clips[clip].frames - 1;
    const lengthOf = clip => spanOf(clip) * 1000 / fps / rateOf(clip);
    const frameAt = (c, now) => {
      const f = (now - c.t0) * fps * rateOf(c.clip) / 1000, C = man.clips[c.clip];
      return Math.max(0, Math.min(f, C.loop ? C.frames - 1e-3 : C.frames - 1));
    };
    const start = (clip, now, cut, r = -1) => {
      fade = cut && shown ? { clip: shown.clip, f: shown.f, t0: now } : null;
      cur = { clip, t0: now, rank: r };
      if (clip !== "idle") until = now + lengthOf(clip);
    };
    if (shadow && typeof footShadow === "function") { sample("idle", 0, M); footShadow(app, fig, root); }

    app.ticker.add(() => {
      const now = performance.now();
      const C = man.clips[cur.clip];
      if (!C.loop && cur.clip !== "exit" && now - cur.t0 >= lengthOf(cur.clip)) {
        const endAt = cur.t0 + lengthOf(cur.clip);
        if (next) { charSfx(name, next.clip); start(next.clip, endAt, false, next.rank); next = null; }
        else { start("idle", endAt, !!IDLE.cut); rank = -1; }
      }
      if (cur.clip === "idle") {
        const L = lengthOf("idle"), el = now - cur.t0;
        if (el >= L) {
          const endAt = cur.t0 + L;
          if (next) { charSfx(name, next.clip); start(next.clip, endAt, false, next.rank); next = null; }
          else cur.t0 = endAt + IDLE.rest[0] + Math.random() * (IDLE.rest[1] - IDLE.rest[0]);
        } else if (el < 0 && next) {
          charSfx(name, next.clip); start(next.clip, now, false, next.rank); next = null;
        }
      }
      const f = frameAt(cur, now);
      let a = 0;
      if (fade) {
        a = 1 - (now - fade.t0) * fps / 1000 / CUT;
        if (a <= 0) { fade = null; a = 0; } else a = a * a * (3 - 2 * a);
      }
      const key = cur.clip + ":" + f.toFixed(3) + (fade ? ":" + a.toFixed(3) : "");
      if (flame) flame.tick(now);                          // the flame is alive whatever the body does
      if (key === shownKey) { if (flame) touch(); return; }   // resting on a pose: only the flame to draw
      shownKey = key;
      sample(cur.clip, f, M);
      if (fade) {                                          // a cut: the last pose shown eases into the new one
        sample(fade.clip, fade.f, M2);
        for (let k = 0; k < M.length; k++) M[k] += (M2[k] - M[k]) * a;
      }
      show(cur.clip, f);
    });
    (window.__chars || (window.__chars = [])).push({ name, app, actor, rig: true, fig, man, flame, state: () => ({ cur, next, shown, rank }),
      pose: (clip, f, at) => { sample(clip, f, M); show(clip, f); if (flame) flame.tick(at === undefined ? performance.now() : at, true); app.render(); } });   // debug / QA handle (the flame put straight on its bone)

    const pick = list => list[Math.floor(Math.random() * list.length)];
    const oneShot = (clip, want) => {
      if (!has(clip)) return false;
      const now = performance.now();
      if (want <= rank && now < until) return false;
      if (next && want <= next.rank) return false;
      if (IDLE.cut && cur.clip === "idle" && !fade) {      // straight in from the idle, the poses eased across
        charSfx(name, clip);
        start(clip, now, true, want);
        rank = want; until = now + lengthOf(clip);
        return true;
      }
      next = { clip, rank: want, at: now };
      const L = lengthOf("idle");
      const startsAt = cur.clip !== "idle" && cur.clip !== "exit" ? Math.max(now, cur.t0 + lengthOf(cur.clip))
        : now < cur.t0 ? now : cur.t0 + L;
      rank = want; until = startsAt + lengthOf(clip);
      return true;
    };
    const armFlavour = () => {
      clearTimeout(timer);
      if (REDUCED_MOTION || away || !flavour.length) return;
      timer = setTimeout(() => {
        if (!document.hidden && !state.playing && performance.now() >= until) oneShot(pick(pick(flavour)), CHAR_RANK.flavour);
        armFlavour();
      }, CHAR_FLAVOUR_GAP[0] + Math.random() * (CHAR_FLAVOUR_GAP[1] - CHAR_FLAVOUR_GAP[0]));
    };
    const react = kind => {
      if (REDUCED_MOTION || away) return;
      const want = CHAR_RANK[kind];
      if (want === undefined) return;
      if (oneShot(swap[kind] || kind, want)) armFlavour();
    };
    const enter = () => {
      if (!away) return;
      away = false;
      rank = -1; until = 0; next = null;
      clearTimeout(fadeTimer);
      app.canvas.classList.add("on");
      if (REDUCED_MOTION) { app.ticker.stop(); start("idle", performance.now(), false); sample("idle", 0, M); show("idle", 0); if (flame) flame.tick(performance.now(), true); app.render(); return; }
      if (has("enter")) charSfx(name, "enter");
      start(has("enter") ? "enter" : "idle", performance.now(), false);
      rank = has("enter") ? CHAR_RANK.enter : -1;
      armFlavour();
    };
    const exit = () => {
      if (away) return;
      away = true;
      clearTimeout(timer);
      next = null;
      clearTimeout(fadeTimer);
      if (REDUCED_MOTION || !has("exit")) { app.canvas.classList.remove("on"); return; }
      charSfx(name, "exit");
      start("exit", performance.now(), cur.clip !== "idle");
      rank = CHAR_RANK.exit; until = performance.now() + lengthOf("exit");
      const fadeMs = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--char-fade")) || 280;
      fadeTimer = setTimeout(() => app.canvas.classList.remove("on"), Math.max(0, lengthOf("exit") - fadeMs));
    };
    // the first pose drawn and the atlas on the GPU before the loading screen lets go
    sample("idle", 0, M); show("idle", 0);
    if (flame) flame.tick(performance.now(), true);
    app.render();
    document.addEventListener("visibilitychange", () => { if (!document.hidden) fit(); });
    return { react, enter, exit };
  };
})();
