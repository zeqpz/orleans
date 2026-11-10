// The board's symbols, drawn in one WebGL canvas (perf, 2026-11-04).
//
// Every symbol used to be a 2D canvas of its own inside its cell - 49 of them, each redrawn at 30 fps and
// each its own compositor layer - and on a phone the browser spent most of every frame committing those
// layers (owner: "not running well enough for mobile devices"). Now one Pixi canvas, laid in the board
// between the multiplier values and the reels, draws them all from per-clip atlases (each clip's Blender
// frames, resized once to the size the screen shows them). The cells stay in the page exactly as they
// were - every drop, tumble, burst, pop, spotlight and camera move is still the same CSS on the same
// elements, firing the same events the game waits on - they simply hold no picture any more: this canvas
// reads where each cell is (its layout, plus its animated transform and opacity while it is moving) and
// draws the symbol there. A resting board reads nothing and only redraws when an idle steps a frame.
// What a cell still shows itself (a Multi's value on its brick, the flat icons of the first seconds or of
// reduced motion) stays in the cell, over this canvas, as before.
//
//   BoardGL.init()                     -> Promise<boolean>   (false: the 2D path carries on)
//   BoardGL.atlas(id, clip, url, k)    -> Promise<{ frames }>
//   BoardGL.touch()                    the board needs drawing
(function () {
  "use strict";
  const PAD = 72;        // css px the canvas reaches past the board: the reels clip 60 px out at the sides; pops and bursts swell past the edge
  const MAX_RES = 2;     // device px per css px at most (a 3x phone draws its board at 2x: a third of the pixels to fill)
  const TOP_CLIP = { spinning: 20, tumbling: 20 }, SIDE_CLIP = 60;   // the reels' clip-paths (.reel.spinning / .reel.tumbling): to the iron frame's inner edge
  // ...and their bottom: the middle of the bottom bar's rail in assets/frame.webp (solid iron over art rows 1776-1802 of
  // 1982, the rail the spikes stand on), so a tile falling out of the board drops on behind the spikes and its cut edge
  // stays hidden in the iron as the frame drifts (owner, 2026-11-09). layout() measures it per reel and hands it to
  // the clip-paths in index.html as --reel-floor (px below the reel).
  const FRAME_RAIL = 1789 / 1982;

  let app = null, board = null, root = null, tried = null;
  let dirty = true, geoDirty = true, res = 1, W = 0, H = 0;
  const C = [];          // C[r][y]: per cell { cell, box, cont, spr, sm, cls, m, op, z, act, reread, at }
  const R = [];          // per reel { el, x, y, w, h, clip, cont, mask }
  const smearTex = new Map();
  const id3 = () => new DOMMatrix();

  function resolution() {
    const fit = board && board.offsetWidth ? board.getBoundingClientRect().width / board.offsetWidth : 1;
    return Math.max(.5, Math.min(MAX_RES, window.devicePixelRatio || 1) * (fit > 0 ? fit : 1));
  }

  async function init() {
    if (tried) return tried;
    tried = (async () => {
      if (/[?&]boardgl=0\b/.test(location.search) || typeof PIXI === "undefined") return false;
      board = document.getElementById("board");
      if (!board) return false;
      try {
        app = new PIXI.Application();
        await app.init({ backgroundAlpha: 0, antialias: false, autoDensity: true, resolution: resolution(), width: 4, height: 4, preference: "webgl" });
      } catch (e) { console.warn("board canvas unavailable:", e.message); app = null; return false; }
      app.ticker.remove(app.render, app);
      app.canvas.className = "boardgl";
      app.canvas.setAttribute("aria-hidden", "true");
      const ml = document.getElementById("multLayer");
      board.insertBefore(app.canvas, ml ? ml.nextSibling : board.firstChild);
      root = new PIXI.Container();
      root.sortableChildren = true;
      app.stage.addChild(root);
      board.classList.add("gl");
      // what moves a cell: its own animations and transitions, and its icon box's (the spotlight's fade)
      // which part of the cell moves: the cell (its transform, opacity), its icon box (the spotlight's fade)
      // or its motion blur - only that part is read while it does (the Multi's value and the rest draw themselves)
      const part = (c, t) => t === c.cell ? "aCell" : t === c.cell.ico ? "aIco" : t === c.cell.smear ? "aSm" : null;
      const on = e => { const c = cellOf(e.target), k = c && part(c, e.target); if (k) { c[k]++; c.act++; c.at = performance.now(); c.trk[k] = null; dirty = true; } };
      const off = e => { const c = cellOf(e.target), k = c && part(c, e.target); if (k) { c[k] = Math.max(0, c[k] - 1); c.act = Math.max(0, c.act - 1); c.trk[k] = null; c.reread = true; dirty = true; } };
      for (const t of ["animationstart", "transitionrun"]) board.addEventListener(t, on, true);
      for (const t of ["animationend", "animationcancel", "transitionend", "transitioncancel"]) board.addEventListener(t, off, true);
      addEventListener("resize", () => { geoDirty = true; });
      if (typeof ResizeObserver === "function") new ResizeObserver(() => { geoDirty = true; }).observe(board);
      app.ticker.add(tick, null, PIXI.UPDATE_PRIORITY.LOW);
      if (typeof ResizeObserver === "function" && !/[?&]glpost=0\b/.test(location.search)) {
        probe = document.createElement("div");
        probe.setAttribute("aria-hidden", "true");
        probe.style.cssText = "position:fixed;left:0;top:0;width:1px;height:1px;visibility:hidden;pointer-events:none;contain:strict";
        document.body.appendChild(probe);
        new ResizeObserver(afterLayout).observe(probe);
      }
      document.addEventListener("visibilitychange", () => { dirty = true; geoDirty = true; });
      BoardGL.on = true;
      return true;
    })();
    return tried;
  }

  function cellOf(t) {
    const el = t && t.closest ? t.closest(".cell") : null;
    return el && el._gl;
  }

  // ---------------------------------------------------------------- atlases
  // One clip's frames as one texture: the sheet decoded off the main thread and resized as a whole, on a
  // whole-pixel grid, to k of its size; each frame a rectangle of it. Built a couple at a time.
  // The fetch, the decode and the resize all run in a worker (perf, 2026-11-09): resizing a decoded bitmap
  // is done on the thread that asks for it, and on the page it took ~2.5 s of a phone's main thread, while
  // the round was already playing. The worker does the very same two steps, so the pixels are the same.
  // Two workers, so two sheets are resized at once (a worker does one at a time) - as many as were ever
  // fetched at once before, so the requests the page makes are no more crowded than they were.
  const POOL = (navigator.hardwareConcurrency || 4) > 2 ? 2 : 1;
  const sheetWorker = (() => {
    if (typeof Worker !== "function" || /[?&]sheetworker=0\b/.test(location.search)) return null;
    try {
      const src = `onmessage = async e => {
        const q = e.data;
        try {
          const r = await fetch(q.url);
          if (!r.ok) throw new Error(q.url + " -> HTTP " + r.status);
          const sheet = await createImageBitmap(await r.blob());
          let bmp = sheet;
          if (q.rw) { bmp = await createImageBitmap(sheet, 0, 0, q.sw, q.sh, { resizeWidth: q.rw, resizeHeight: q.rh, resizeQuality: "high" }); sheet.close(); }
          postMessage({ id: q.id, bmp }, [bmp]);
        } catch (err) { postMessage({ id: q.id, err: String((err && err.message) || err) }); }
      };`;
      const url = URL.createObjectURL(new Blob([src], { type: "text/javascript" })), wait = new Map();
      const onmessage = e => { const p = wait.get(e.data.id); if (!p) return; wait.delete(e.data.id); e.data.err ? p.no(new Error(e.data.err)) : p.ok(e.data.bmp); };
      const ws = Array.from({ length: POOL }, () => { const w = new Worker(url); w.onmessage = onmessage; return w; });
      let n = 0;
      return q => new Promise((ok, no) => { q.id = ++n; wait.set(q.id, { ok, no }); ws[n % ws.length].postMessage(q); });
    } catch (e) { return null; }
  })();
  let busy = 0;
  const waiting = [];
  const slot = () => busy < 2 ? (busy++, Promise.resolve()) : new Promise(r => waiting.push(r));
  const free = () => { const n = waiting.shift(); if (n) n(); else busy--; };
  async function atlas(id, clip, url, k) {
    await slot();
    try {
      const m = SYMF.man.symbols[id], sh = m.sheets[SYMF.density][clip], n = m.clips[clip].frames;
      const cols = sh.cols, rows = Math.ceil(n / cols);
      const fw = k < 1 ? Math.max(1, Math.round(sh.w * k)) : sh.w, fh = k < 1 ? Math.max(1, Math.round(sh.h * k)) : sh.h;
      const size = k < 1 ? { sw: cols * sh.w, sh: rows * sh.h, rw: cols * fw, rh: rows * fh } : {};
      let bmp = null;
      if (sheetWorker) bmp = await sheetWorker(Object.assign({ url: new URL(url, location.href).href }, size));
      else {
        const blob = await fetch(url).then(r => r.ok ? r.blob() : Promise.reject(new Error(url + " -> HTTP " + r.status)));
        const sheet = await createImageBitmap(blob);
        bmp = sheet;
        if (k < 1) {
          bmp = await createImageBitmap(sheet, 0, 0, size.sw, size.sh, { resizeWidth: size.rw, resizeHeight: size.rh, resizeQuality: "high" });
          sheet.close();
        }
      }
      const base = PIXI.Texture.from(bmp);
      base.source.scaleMode = "linear";
      try { app.renderer.texture.initSource(base.source); } catch (e) { /* uploaded on first draw instead */ }
      const frames = [];
      for (let f = 0; f < n; f++) frames.push(new PIXI.Texture({ source: base.source, frame: new PIXI.Rectangle((f % cols) * fw, Math.floor(f / cols) * fh, fw, fh) }));
      return { frames, fw, fh, k };
    } finally { free(); }
  }

  function smearTexture(cell) {
    const bg = cell.smear && cell.smear.style.backgroundImage;
    const u = bg && /url\("?([^")]+)"?\)/.exec(bg);
    if (!u) return null;
    let t = smearTex.get(u[1]);
    if (t === undefined) {
      smearTex.set(u[1], null);
      const im = new Image();
      im.onload = () => { smearTex.set(u[1], PIXI.Texture.from(im)); dirty = true; };
      im.src = u[1];
      return null;
    }
    return t;
  }

  // ---------------------------------------------------------------- layout
  // where each cell and reel sits inside the board (offsets walked up to it, like cellCentre: #app is
  // scaled to fit, so a rect would not be a layout length)
  function offsetIn(el) {
    let x = 0, y = 0, e = el;
    while (e && e !== board) {
      x += e.offsetLeft; y += e.offsetTop;
      e = e.offsetParent;
      if (e && e !== board) { x += e.clientLeft; y += e.clientTop; }
    }
    return { x, y };
  }
  function layout() {
    geoDirty = false;
    if (!board.offsetWidth) return;
    W = board.offsetWidth + 2 * PAD; H = board.offsetHeight + 2 * PAD;
    const r2 = resolution();
    if (r2 !== res || app.renderer.width !== Math.round(W * r2) || app.renderer.height !== Math.round(H * r2)) {
      res = r2;
      app.renderer.resolution = res;
      app.renderer.resize(W, H);
    }
    Object.assign(app.canvas.style, { left: -PAD - board.clientLeft + "px", top: -PAD - board.clientTop + "px", width: W + "px", height: H + "px" });
    for (let r = 0; r < cellEls.length; r++) {
      const reel = reelEls[r];
      if (!R[r]) {
        const cont = new PIXI.Container(); cont.sortableChildren = true;
        const mask = new PIXI.Graphics();
        R[r] = { el: reel, clip: "", cont, mask };
        root.addChild(cont); root.addChild(mask); mask.visible = false;
      }
      const p = offsetIn(reel);
      // the rail's line under this reel (the frame's layout box: its idle drift is a transform, not counted)
      const fr = document.getElementById("paintframe");
      const rail = fr && fr.offsetParent === board && fr.offsetHeight ? fr.offsetTop + fr.offsetHeight * FRAME_RAIL : 0;
      const floor = Math.round(Math.min(PAD + board.offsetHeight - p.y - reel.offsetHeight, Math.max(TOP_CLIP.spinning, rail - p.y - reel.offsetHeight)));
      Object.assign(R[r], { x: p.x, y: p.y, w: reel.offsetWidth, h: reel.offsetHeight, floor, clip: "?" });
      if (r === 0) board.style.setProperty("--reel-floor", floor + "px");
      for (let y = 0; y < cellEls[r].length; y++) {
        const cell = cellEls[r][y];
        if (!C[r]) C[r] = [];
        let c = C[r][y];
        if (!c) {
          const cont = new PIXI.Container(), sm = new PIXI.Sprite(), spr = new PIXI.Sprite();
          sm.visible = false; spr.visible = false;
          cont.addChild(sm, spr);
          c = C[r][y] = { cell, cont, spr, sm, cls: null, m: null, op: 1, ico: 1, z: 0, act: 0, aCell: 0, aIco: 0, aSm: 0, reread: true, at: 0, order: r * 100 + y, smop: 0, smm: null, tex: null,
                          trk: { aCell: null, aIco: null, aSm: null }, org: null, sorg: null };
          cell._gl = c;
          root.addChild(cont);
        }
        const q = offsetIn(cell);
        c.box = { x: q.x, y: q.y, w: cell.offsetWidth, h: cell.offsetHeight, cw: cell.clientWidth, ch: cell.clientHeight, bl: cell.clientLeft, bt: cell.clientTop };
        c.reread = true;
      }
    }
    dirty = true;
  }

  // ---------------------------------------------------------------- what CSS is doing to a cell now
  function matrixOf(cs) {
    const o = cs.transformOrigin.split(" ").map(parseFloat);
    let m = id3().translate(o[0] || 0, o[1] || 0);
    if (cs.translate && cs.translate !== "none") { const t = cs.translate.split(" ").map(parseFloat); m = m.translate(t[0] || 0, t[1] || 0); }
    if (cs.rotate && cs.rotate !== "none") m = m.rotate(parseFloat(cs.rotate.split(" ").pop()) || 0);
    if (cs.scale && cs.scale !== "none") { const s = cs.scale.split(" ").map(parseFloat); m = m.scale(s[0], s.length > 1 ? s[1] : s[0]); }
    if (cs.transform && cs.transform !== "none") m = m.multiply(new DOMMatrix(cs.transform));
    return m.translate(-(o[0] || 0), -(o[1] || 0));
  }
  // a 2D matrix about the element's own top left; the common case (only `transform`, a matrix) without DOMMatrix
  function mat(cs) {
    const tf = cs.transform, tr = cs.translate, ro = cs.rotate, sc = cs.scale;
    const plain = (!sc || sc === "none") && (!tr || tr === "none") && (!ro || ro === "none");
    if (plain && tf === "none") return null;
    if (plain && tf.startsWith("matrix(")) {
      const v = tf.slice(7, -1).split(","), a = +v[0], b = +v[1], c = +v[2], d = +v[3];
      const o = cs.transformOrigin, i = o.indexOf(" "), ox = parseFloat(o) || 0, oy = parseFloat(o.slice(i + 1)) || 0;
      return { a, b, c, d, e: +v[4] + ox - (a * ox + c * oy), f: +v[5] + oy - (b * ox + d * oy) };
    }
    const M = matrixOf(cs);
    return { a: M.a, b: M.b, c: M.c, d: M.d, e: M.e, f: M.f };
  }
  // its transform-origin in px, when nothing but `transform` moves it (translate/rotate/scale: not sampled)
  const originOf = cs => {
    const tr = cs.translate, ro = cs.rotate, sc = cs.scale;
    if ((sc && sc !== "none") || (tr && tr !== "none") || (ro && ro !== "none")) return null;
    const o = cs.transformOrigin, i = o.indexOf(" ");
    return [parseFloat(o) || 0, parseFloat(o.slice(i + 1)) || 0];
  };
  function readCell(c) {
    const cs = getComputedStyle(c.cell);
    c.m = mat(cs);
    c.op = parseFloat(cs.opacity);
    c.z = parseInt(cs.zIndex, 10) || 0;
    c.org = originOf(cs);
  }
  function readIco(c) { c.ico = c.cell.ico ? parseFloat(getComputedStyle(c.cell.ico).opacity) : 1; }
  function readSm(c) {
    const ss = getComputedStyle(c.cell.smear);
    c.smop = parseFloat(ss.opacity);
    c.smm = c.smop > .005 ? mat(ss) : null;
    c.sorg = originOf(ss);
  }
  function read(c, all) {
    if (all || c.aCell) readCell(c);
    if (all || c.aIco) readIco(c);
    if (!c.cell.smear) c.smop = 0;
    else if (all || c.aSm) readSm(c);
  }

  // ---------------------------------------------------------------- the same, without asking CSS
  // (perf, 2026-11-09) Reading a moving cell's computed style every frame made the browser work out the
  // page's styles (and layout) again mid-frame, frame after frame: ~2 s of a phone's 11 s round. The cells
  // move by CSS animations, so each one's keyframes - as the browser resolved them for that cell, var() and
  // calc() already worked out, the implicit 0%/100% filled in - and its timing are taken once, as it starts,
  // and sampled here on the animation clock with the browser's own rules: the active phase and fill, the
  // iteration and direction, each keyframe's easing, transform lists padded with identity functions and
  // blended function by function. Styles are still read once whenever a cell's classes change or an
  // animation starts or ends, and for anything this does not model (a matrix or 3D keyframe, an easing it
  // does not know, two lists it cannot pair, a paused or reversed animation, the gap after an unfilled
  // animation ends) the cell is read as before. ?glcheck=1 compares every sampled frame with the real style.
  const NO = {};   // "cannot model this": read the style instead
  const CHECK = /[?&]glcheck=1\b/.test(location.search);
  const EASES = new Map();
  const NAMED = { ease: [.25, .1, .25, 1], "ease-in": [.42, 0, 1, 1], "ease-out": [0, 0, .58, 1], "ease-in-out": [.42, 0, .58, 1] };
  function bezier(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx, cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const X = t => ((ax * t + bx) * t + cx) * t, Y = t => ((ay * t + by) * t + cy) * t, dX = t => (3 * ax * t + 2 * bx) * t + cx;
    const g0 = x1 > 0 ? y1 / x1 : !y1 && x2 > 0 ? y2 / x2 : 0, g1 = x2 < 1 ? (y2 - 1) / (x2 - 1) : x1 < 1 ? (y1 - 1) / (x1 - 1) : 0;
    return x => {
      if (x <= 0) return g0 * x;
      if (x >= 1) return 1 + g1 * (x - 1);
      let t = x;
      for (let i = 0; i < 8; i++) {
        const e = X(t) - x;
        if (Math.abs(e) < 1e-7) return Y(t);
        const d = dX(t);
        if (Math.abs(d) < 1e-6) break;
        t -= e / d;
      }
      let lo = 0, hi = 1; t = x;
      while (hi - lo > 1e-7) { const v = X(t); if (Math.abs(v - x) < 1e-7) break; if (v < x) lo = t; else hi = t; t = (lo + hi) / 2; }
      return Y(t);
    };
  }
  function easeOf(s) {
    s = String(s || "linear").trim();
    if (EASES.has(s)) return EASES.get(s);
    let f = null, m;
    if (s === "linear") f = x => x;
    else if (NAMED[s]) f = bezier(...NAMED[s]);
    else if ((m = /^cubic-bezier\(([^()]*)\)$/.exec(s))) { const v = m[1].split(",").map(Number); if (v.length === 4 && v.every(isFinite)) f = bezier(...v); }
    else if ((m = /^steps\(\s*(\d+)\s*(?:,\s*([\w-]+)\s*)?\)$/.exec(s)) || s === "step-start" || s === "step-end") {
      const n = m ? +m[1] : 1, pos = m ? (m[2] || "end") : s === "step-start" ? "start" : "end";
      const jumps = pos === "jump-none" ? n - 1 : pos === "jump-both" ? n + 1 : n;
      if (jumps > 0) f = x => {
        let st = Math.floor(x * n);
        if (pos === "start" || pos === "jump-start" || pos === "jump-both") st += 1;
        if (x >= 0 && st < 0) st = 0;
        if (x <= 1 && st > jumps) st = jumps;
        return st / jumps;
      };
    }
    EASES.set(s, f);
    return f;
  }
  // a transform list as the browser serialises a computed keyframe: [{ k: 0 translate | 1 scale | 2 rotate, ... }]
  const TF = /([a-zA-Z]+)\(([^()]*)\)/g;
  const lp = s => {   // a length-percentage -> [px, %]
    const m = /^(-?[\d.]+(?:e[-+]?\d+)?)(px|%)?$/i.exec(String(s).trim());
    return !m || (!m[2] && +m[1] !== 0) ? null : m[2] === "%" ? [0, +m[1]] : [+m[1], 0];
  };
  const DEG = { deg: 1, rad: 180 / Math.PI, turn: 360, grad: .9 };
  const ang = s => {
    const m = /^(-?[\d.]+(?:e[-+]?\d+)?)(deg|rad|turn|grad)?$/i.exec(String(s).trim());
    return !m || (!m[2] && +m[1] !== 0) ? null : +m[1] * (m[2] ? DEG[m[2].toLowerCase()] : 1);
  };
  function parseTf(s) {
    s = String(s).trim();
    if (s === "none") return [];
    if (/calc|var|matrix|3d|skew|perspective/i.test(s) || s.replace(TF, "").trim()) return null;
    const out = [];
    for (const m of s.matchAll(TF)) {
      const n = m[1], v = m[2].split(",");
      if (n === "translate" || n === "translateX" || n === "translateY") {
        const X = n === "translateY" ? [0, 0] : lp(v[0]), Y = n === "translateX" ? [0, 0] : lp(n === "translateY" ? v[0] : v[1] === undefined ? "0" : v[1]);
        if (!X || !Y || (n !== "translate" && v.length > 1)) return null;
        out.push({ k: 0, xp: X[0], xq: X[1], yp: Y[0], yq: Y[1] });
      } else if (n === "scale" || n === "scaleX" || n === "scaleY") {
        const a = +v[0], b = v[1] === undefined ? a : +v[1];
        const sx = n === "scaleY" ? 1 : a, sy = n === "scaleX" ? 1 : n === "scaleY" ? a : b;
        if (!isFinite(sx) || !isFinite(sy) || (n !== "scale" && v.length > 1)) return null;
        out.push({ k: 1, sx, sy });
      } else if (n === "rotate" || n === "rotateZ") {
        const r = v.length === 1 ? ang(v[0]) : null;
        if (r === null) return null;
        out.push({ k: 2, r });
      } else return null;
    }
    return out;
  }
  const IDF = [{ k: 0, xp: 0, xq: 0, yp: 0, yq: 0 }, { k: 1, sx: 1, sy: 1 }, { k: 2, r: 0 }];
  // every running animation by the element it moves (its own, not a pseudo-element's), in composite order -
  // the same lists el.getAnimations() gives, from one call for the whole frame instead of one per moving part
  let byTarget = null;
  function animsOf(el) {
    if (!byTarget) {
      byTarget = new Map();
      for (const a of document.getAnimations()) {
        const fx = a.effect, t = fx && fx.target;
        if (!t || fx.pseudoElement) continue;
        let l = byTarget.get(t);
        if (!l) byTarget.set(t, l = []);
        l.push(a);
      }
    }
    return byTarget.get(el) || [];
  }
  // what a part's animations need, taken once as they start: null if it cannot be sampled
  function tracksOf(el) {
    const out = [];
    for (const a of animsOf(el)) {
      const fx = a.effect;
      if (!fx || typeof fx.getKeyframes !== "function" || a.playbackRate !== 1) return null;
      if (fx.composite && fx.composite !== "replace") return null;
      const tm = fx.getComputedTiming(), ease = easeOf(tm.easing);
      if (!ease || !(tm.duration > 0) || !(tm.iterations > 0)) return null;
      const t = { a, ease, delay: tm.delay || 0, dur: tm.duration, it: tm.iterations, i0: tm.iterationStart || 0, dir: tm.direction, fill: tm.fill, end: tm.endTime, T: null, O: null };
      const kf = fx.getKeyframes();
      for (const prop of ["transform", "opacity"]) {
        const list = [];
        for (const q of kf) {
          if (q[prop] === undefined) continue;
          if (q.composite && q.composite !== "auto" && q.composite !== "replace") return null;
          const e = easeOf(q.easing), v = prop === "opacity" ? parseFloat(q[prop]) : parseTf(q[prop]);
          if (!e || v === null || (prop === "opacity" && !isFinite(v))) return null;
          list.push({ o: q.computedOffset, e, v });
        }
        if (!list.length) continue;
        if (list.length < 2 || list[0].o !== 0 || list[list.length - 1].o !== 1) return null;
        if (prop === "transform") t.T = list; else t.O = list;
      }
      out.push(t);
    }
    return out;
  }
  // its iteration progress now, eased (Web Animations timing model); null: not in effect
  function progressOf(t, now) {
    const st = t.a.startTime;
    let local;
    if (st === null || st === undefined) { local = t.a.currentTime; if (local === null) return null; }   // not started yet: held where it is
    else local = now - st;
    const ad = t.dur * t.it, back = t.fill === "backwards" || t.fill === "both", fwd = t.fill === "forwards" || t.fill === "both";
    let at;
    if (local < Math.max(Math.min(t.delay, t.end), 0)) { if (!back) return null; at = 0; }
    else if (local < Math.max(Math.min(t.delay + ad, t.end), 0)) at = local - t.delay;
    else { if (!fwd) return null; at = Math.max(Math.min(local - t.delay, ad), 0); }
    const overall = t.i0 + at / t.dur;
    let simple = overall % 1, it = Math.floor(overall);
    if (simple === 0 && at === ad && overall !== 0) { simple = 1; it -= 1; }
    const d = t.dir, flip = d === "reverse" || (d === "alternate" && it % 2 === 1) || (d === "alternate-reverse" && it % 2 === 0);
    return t.ease(flip ? 1 - simple : simple);
  }
  // the keyframe pair p falls in, and how far along it (eased by the first one's easing)
  function seg(list, p) {
    let i = 0;
    if (p >= 1) i = list.length - 2;
    else if (p >= 0) while (i < list.length - 2 && list[i + 1].o <= p) i++;
    const k0 = list[i], k1 = list[i + 1], span = k1.o - k0.o;
    return [k0, k1, span > 0 ? k0.e((p - k0.o) / span) : (p < k1.o ? 0 : 1)];
  }
  const lerp = (a, b, f) => a + (b - a) * f;
  function mul(M, a, b, c, d, e, f) {
    return [M[0] * a + M[2] * b, M[1] * a + M[3] * b, M[0] * c + M[2] * d, M[1] * c + M[3] * d, M[0] * e + M[2] * f + M[4], M[1] * e + M[3] * f + M[5]];
  }
  // the transform at p, as a matrix about the element's top left (like mat()); NO if the lists do not pair
  function transformAt(list, p, w, h, org) {
    const [k0, k1, f] = seg(list, p), A = k0.v, B = k1.v, n = Math.max(A.length, B.length);
    let M = [1, 0, 0, 1, org[0], org[1]];
    for (let i = 0; i < n; i++) {
      const x = A[i] || IDF[B[i].k], y = B[i] || IDF[A[i].k];
      if (x.k !== y.k) return NO;
      if (x.k === 0) M = mul(M, 1, 0, 0, 1, lerp(x.xp, y.xp, f) + lerp(x.xq, y.xq, f) * w / 100, lerp(x.yp, y.yp, f) + lerp(x.yq, y.yq, f) * h / 100);
      else if (x.k === 1) M = mul(M, lerp(x.sx, y.sx, f), 0, 0, lerp(x.sy, y.sy, f), 0, 0);
      else { const r = lerp(x.r, y.r, f) * Math.PI / 180, cs = Math.cos(r), sn = Math.sin(r); M = mul(M, cs, sn, -sn, cs, 0, 0); }
    }
    M = mul(M, 1, 0, 0, 1, -org[0], -org[1]);
    return { a: M[0], b: M[1], c: M[2], d: M[3], e: M[4], f: M[5] };
  }
  // one part's transform (m) and opacity (op) now; a key left undefined is not animated; null: read it instead
  function samplePart(c, k, el, now, w, h, org) {
    let tr = c.trk[k];
    if (tr === null) tr = c.trk[k] = tracksOf(el) || false;
    if (!tr) return null;
    let m, op, tAnim = false, oAnim = false;
    for (const t of tr) {
      if (t.T && org) tAnim = true;
      if (t.O) oAnim = true;
      const p = progressOf(t, now);
      if (p === null) continue;
      if (t.T && org) { m = transformAt(t.T, p, w, h, org); if (m === NO) return null; }
      if (t.O) { const [k0, k1, f] = seg(t.O, p); op = Math.min(1, Math.max(0, lerp(k0.v, k1.v, f))); }
    }
    // driven by an animation that is not in effect this frame: the value under it is the stylesheet's
    if ((tAnim && m === undefined) || (oAnim && op === undefined)) return null;
    return { m, op };
  }
  // a moving cell this frame: each moving part sampled, or read where it cannot be
  function sample(c, now) {
    const b = c.box;
    if (c.aCell) {
      const r = c.org ? samplePart(c, "aCell", c.cell, now, b.w, b.h, c.org) : null;
      if (!r) readCell(c);
      else { if (r.m !== undefined) c.m = r.m; if (r.op !== undefined) c.op = r.op; }
    }
    if (c.aIco) {
      const r = c.cell.ico ? samplePart(c, "aIco", c.cell.ico, now, 0, 0, null) : null;
      if (!r) readIco(c); else if (r.op !== undefined) c.ico = r.op;
    }
    const s = c.cell.smear;
    if (!s) c.smop = 0;
    else if (c.aSm) {
      const r = c.sorg ? samplePart(c, "aSm", s, now, b.cw * .88, b.ch * .88 * 2.1, c.sorg) : null;
      if (!r || (r.m === undefined && c.smm === null && r.op > .005)) readSm(c);
      else { if (r.op !== undefined) c.smop = r.op; if (r.m !== undefined) c.smm = r.m; if (c.smop <= .005) c.smm = null; }
    }
    if (CHECK) check(c);
  }
  // ?glcheck=1: the sampled values against the browser's own, every frame (the browser's are kept)
  const chk = { frames: 0, cells: 0, px: 0, op: 0, worst: "" };
  function check(c) {
    const s = { m: c.m, op: c.op, ico: c.ico, smop: c.smop, smm: c.smm };
    read(c, false);
    const b = c.box, I = { a: 1, b: 0, c: 0, d: 1, e: 0, f: 0 };
    const dm = (p, q, w, h) => { p = p || I; q = q || I; return Math.max(Math.abs(p.a - q.a) * w + Math.abs(p.c - q.c) * h + Math.abs(p.e - q.e), Math.abs(p.b - q.b) * w + Math.abs(p.d - q.d) * h + Math.abs(p.f - q.f)); };
    const px = Math.max(dm(s.m, c.m, b.w, b.h), c.smop > .005 && s.smop > .005 ? dm(s.smm, c.smm, b.cw * .88, b.ch * 1.85) : 0);
    const op = Math.max(Math.abs(s.op - c.op), Math.abs(s.ico - c.ico), Math.abs(s.smop - c.smop));
    chk.cells++;
    if (px > chk.px) { chk.px = px; chk.worst = c.cell.className + " px " + px.toFixed(3); }
    if (op > chk.op) chk.op = op;
    window.__glcheck = chk;
  }

  // ---------------------------------------------------------------- the frame
  // A frame on which a cell has to be read - its classes changed, or one of its animations started or ended
  // (its keyframes are taken then) - is drawn once the browser has worked out this frame's styles and layout
  // itself: from a ResizeObserver callback, which runs after layout and before paint, in the same frame, so
  // the reads find the styles already up to date and cost no style pass of their own (perf, 2026-11-09:
  // in the animation frame each one made the browser recompute the page's styles there and then). A tiny
  // hidden probe is resized to ask for the callback. Every other frame is sampled and drawn in the animation
  // frame. Should the callback not come, the next frame draws as before, reading where it must.
  let probe = null, flip = false, postDue = false, postMissed = 0;
  function wantsRead() {
    let want = false;
    for (const col of C) for (const c of col) {
      if (!c) continue;
      if (c.cell.className !== c.cls) { c.cls = c.cell.className; c.reread = true; }
      if (c.reread || (c.act > 0 && ((c.aCell && c.trk.aCell === null) || (c.aIco && c.trk.aIco === null) || (c.aSm && c.trk.aSm === null)))) want = true;
    }
    return want;
  }
  function afterLayout() {
    if (!postDue) return;
    postDue = false; postMissed = 0;
    if (!document.hidden && board) draw();
  }
  function tick() {
    if (document.hidden || !board) return;
    const missed = postDue;
    postDue = false;
    if (missed && ++postMissed > 3) probe = null;   // no callbacks here: always draw in the animation frame
    if (geoDirty) layout();
    if (!C.length) return;
    if (probe && !missed && wantsRead()) { postDue = true; probe.style.width = (flip = !flip) ? "2px" : "1px"; return; }
    draw();
  }
  function draw() {
    const now = performance.now(), tnow = document.timeline.currentTime;
    byTarget = null;   // taken afresh, once, the first time this frame needs it
    // the reels' clips while tiles are on the move
    for (const rr of R) {
      if (!rr) continue;
      const cl = rr.el.classList, clip = cl.contains("spinning") ? "spinning" : cl.contains("tumbling") ? "tumbling" : "";
      if (clip === rr.clip) continue;
      rr.clip = clip; dirty = true; rr.cont.zIndex = 0;
      if (clip) {
        const t = TOP_CLIP[clip];
        rr.mask.clear().rect(PAD + rr.x - SIDE_CLIP, PAD + rr.y - t, rr.w + 2 * SIDE_CLIP, rr.h + t + (rr.floor || t)).fill(0xffffff);
        rr.mask.visible = true; rr.cont.mask = rr.mask;
      } else { rr.cont.mask = null; rr.mask.visible = false; }
    }
    for (let r = 0; r < C.length; r++) {
      const rr = R[r], hiddenReel = rr && rr.clip === "spinning";
      for (const c of C[r]) {
        if (!c) continue;
        const cell = c.cell;
        if (cell.className !== c.cls) { c.cls = cell.className; c.reread = true; }
        if (c.act > 0 && now - c.at > 4000 && !cell.getAnimations({ subtree: true }).length) c.act = c.aCell = c.aIco = c.aSm = 0;
        if (c.reread) { read(c, true); c.reread = false; dirty = true; }
        else if (c.act > 0) { sample(c, tnow); dirty = true; }
        // the symbol: the frame its rig is showing (symDraw), on the clip's box inside the rig
        const ico = cell.ico, rig = ico && ico.firstElementChild;
        const g = rig && rig._gclip ? SYMF.sheets.get(rig._name + "_" + rig._gclip) : null;
        const tex = g && g.atlas ? g.atlas.frames[rig._gf] : null;
        const show = !!tex && !hiddenReel && c.op * c.ico > .003;
        if (tex !== c.tex) { c.tex = tex; dirty = true; }
        if (!show) { if (c.spr.visible || c.sm.visible) { c.spr.visible = false; c.sm.visible = false; dirty = true; } continue; }
        // the cell in the board, as CSS has it now
        const b = c.box, mm = new PIXI.Matrix();
        if (c.m) mm.set(c.m.a, c.m.b, c.m.c, c.m.d, c.m.e + PAD + b.x, c.m.f + PAD + b.y);
        else mm.set(1, 0, 0, 1, PAD + b.x, PAD + b.y);
        c.cont.setFromMatrix(mm);
        // only a tile on the move rides the reel's clip (half a cell or more off its slot: falling in, falling
        // out); one at rest or landing is drawn unclipped, so its glow can spread past the board's edge rows
        // and columns (owner, 2026-11-09: glows were cut at the edge boxes while a column tumbled)
        const moving = !!c.m && Math.abs(c.m.f) > b.h * .5;
        const parent = rr && rr.clip && moving ? rr.cont : root;
        if (c.cont.parent !== parent) parent.addChild(c.cont);
        c.cont.zIndex = c.z * 1000 + c.order;
        if (parent !== root) rr.cont.zIndex = Math.max(rr.cont.zIndex || 0, c.cont.zIndex);
        // the rig: the icon's footprint scaled into the cell's 88% box, centred; the clip's box inside it
        const m = rig._m, rw = m.icon[0] * 10, rh = m.icon[1] * 10, bx = m.clips[rig._gclip].box;
        const sR = Math.min(b.cw * .88 / rw, b.ch * .88 / rh);
        c.spr.texture = tex;
        c.spr.x = b.w / 2 + ((bx[0] + m.icon[0] / 2) * 10 - rw / 2) * sR;
        c.spr.y = b.h / 2 + ((bx[1] + m.icon[1] / 2) * 10 - rh / 2) * sR;
        c.spr.width = bx[2] * 10 * sR; c.spr.height = bx[3] * 10 * sR;
        c.spr.alpha = c.op * c.ico;
        c.spr.visible = true;
        // the motion blur behind a falling tile (.smear: left 6%, 88% wide, its foot 6% up, 2.1 boxes tall)
        const st = c.smop > .005 ? smearTexture(cell) : null;
        if (st) {
          const sw = b.cw * .88, sh = b.ch * .88 * 2.1, sx = b.bl + b.cw * .06, sy = b.bt + b.ch * .94 - sh;
          // its own transform (the stretch) is about its own box: then the box is moved to where it sits
          const sm = c.smm ? new PIXI.Matrix(c.smm.a, c.smm.b, c.smm.c, c.smm.d, c.smm.e, c.smm.f) : new PIXI.Matrix();
          sm.translate(sx, sy);
          c.sm.texture = st;
          c.sm.setFromMatrix(sm);
          c.sm.scale.set(c.sm.scale.x * sw / st.width, c.sm.scale.y * sh / st.height);
          c.sm.alpha = c.smop * c.op * c.ico;
          c.sm.visible = true;
        } else if (c.sm.visible) c.sm.visible = false;
      }
    }
    if (dirty) { dirty = false; app.render(); }
  }

  window.BoardGL = { on: false, init, atlas, touch: () => { dirty = true; }, MAX_RES, get app() { return app; } };
})();
