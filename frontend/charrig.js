/* Live character rigs (Voodoo on Bourbon, 2026-11-09).

   A character made and animated in Blender (tools/nola/blender/doc_rig.py) and packed by tools/nola/pack_rig.py
   comes as a rig rather than baked frames: its parts (assets/chars/<name>/rig/: an atlas per density, a mesh per
   part, 4 bone weights per vertex) and, for every clip, each bone's 2D transform on every frame Blender keyed (30 a
   second). The game poses the meshes itself on every screen refresh, the bones' transforms eased between Blender's
   frames on a Catmull-Rom curve - so the figure moves smoothly at 60, 120 or 165 Hz and at any idle speed, where
   baked 30 fps frames stepped (and stepped at 17 fps through the slowed idle), and it weighs a few MB, not hundreds.

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

    const app = new PIXI.Application();
    await app.init({ backgroundAlpha: 0, antialias: true, autoDensity: true, resolution: dpr, resizeTo: root });
    app.ticker.maxFPS = CHAR_FPS;
    root.appendChild(app.canvas);
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
    const wisp = parts.find(q => q.p.alpha === "wisp");
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
      if (wisp) wisp.mesh.alpha = lerpTrack(C.alpha.wisp, f, C.loop);
      skin();
      drawFx(C, f);
      shown = { clip, i: fi, f };
      touch();
    };

    // ---- the figure on its canvas: soles on the bottom edge, centred, scaled so its standing height fills the box
    // the CSS sizes (less the headroom kept free above for a raised arm, smoke, a lifted hat)
    const fit = () => {
      const w = app.renderer.width, h = app.renderer.height;
      if (!w || !h) return;
      actor.pivot.set(man.cx, man.ground_y);
      actor.scale.set(h / headroom() / man.rest_height);
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
    const rateOf = clip => clip === "idle" ? CHAR_IDLE_RATE : 1;
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
        else { start("idle", endAt, false); rank = -1; }
      }
      if (cur.clip === "idle") {
        const L = lengthOf("idle"), el = now - cur.t0;
        if (el >= L) {
          const endAt = cur.t0 + L;
          if (next) { charSfx(name, next.clip); start(next.clip, endAt, false, next.rank); next = null; }
          else cur.t0 = endAt + CHAR_IDLE_REST[0] + Math.random() * (CHAR_IDLE_REST[1] - CHAR_IDLE_REST[0]);
        } else if (el < 0 && next) {
          charSfx(name, next.clip); start(next.clip, now, false, next.rank); next = null;
        }
      }
      const f = frameAt(cur, now);
      let a = 0;
      if (fade) { a = 1 - (now - fade.t0) * fps / 1000 / CHAR_XFADE; if (a <= 0) { fade = null; a = 0; } }
      const key = cur.clip + ":" + f.toFixed(3) + (fade ? ":" + a.toFixed(3) : "");
      if (key === shownKey) return;                        // resting on a pose: nothing to draw
      shownKey = key;
      sample(cur.clip, f, M);
      if (fade) {                                          // a cut: the last pose shown eases into the new one
        sample(fade.clip, fade.f, M2);
        for (let k = 0; k < M.length; k++) M[k] += (M2[k] - M[k]) * a;
      }
      show(cur.clip, f);
    });
    (window.__chars || (window.__chars = [])).push({ name, app, actor, rig: true, fig, man, state: () => ({ cur, next, shown, rank }),
      pose: (clip, f) => { sample(clip, f, M); show(clip, f); app.render(); } });   // debug / QA handle

    const pick = list => list[Math.floor(Math.random() * list.length)];
    const oneShot = (clip, want) => {
      if (!has(clip)) return false;
      const now = performance.now();
      if (want <= rank && now < until) return false;
      if (next && want <= next.rank) return false;
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
      if (REDUCED_MOTION) { app.ticker.stop(); start("idle", performance.now(), false); sample("idle", 0, M); show("idle", 0); app.render(); return; }
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
    app.render();
    document.addEventListener("visibilitychange", () => { if (!document.hidden) fit(); });
    return { react, enter, exit };
  };
})();
