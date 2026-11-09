// Voodoo on Bourbon: the living street behind the board.
//
// The painting (assets/bonus_wall.webp) is a plate with every light switched off - no moon, no stars, no
// smoke (tools/nola/bg_layers.py). This puts them back on top and keeps them alive:
//   lamps    each gas lamp (and the candle) is its own additive layer: a flame's restless shimmer, and now and
//            then a gust - a quick dip and a stutter back up. Each lamp runs its own clock.
//   neon     the four signs hum steadily and every so often buzz: a stutter of off/on, the skull most often.
//   moon     its halo breathes, slowly.
//   street   the reflections on the wet cobbles follow the lamps above them.
//   stars    drawn live on a canvas from scene.json's 170 positions (all in the sky, none on the moon): each
//            twinkles on two incommensurate beats like real scintillation, the bright ones throw a soft cross,
//            and the whole field drifts a few px on a slow figure-eight.
//   mist     three tileable fog bands (green, pale green, violet) drift across the street at different speeds
//            and breathe in and out.
// Everything sits in #bgscene, a box with the painting's 16:9 sized to cover #bgwall (container units), so the
// layers stay on their lamps at any window shape. Reduced motion: everything lit, nothing moving.
(function () {
  "use strict";
  const wall = document.getElementById("bgwall");
  if (!wall) return;
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const scene = document.createElement("div");
  scene.id = "bgscene";
  scene.setAttribute("aria-hidden", "true");
  wall.appendChild(scene);

  // seeded randomness: the scene looks the same on every load and in replays
  let seed = 1803;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
  const lerp = (a, b, t) => a + (b - a) * t;

  fetch("assets/bg/scene.json").then(r => r.json()).then(build).catch(() => { /* the plate alone still reads */ });

  function place(el, box) {
    el.style.left = box[0] * 100 + "%"; el.style.top = box[1] * 100 + "%";
    el.style.width = box[2] * 100 + "%"; el.style.height = box[3] * 100 + "%";
  }

  function build(S) {
    // mist first (behind the lights): three bands
    const mists = [
      { img: "mist_a", top: 58, h: 30, dur: 95, dir: 1, op: .55, breathe: 13 },
      { img: "mist_b", top: 70, h: 32, dur: 140, dir: -1, op: .5, breathe: 17 },
      { img: "mist_c", top: 48, h: 22, dur: 190, dir: 1, op: .35, breathe: 23 },
    ];
    for (const m of mists) {
      const el = document.createElement("i");
      el.className = "bgmist";
      el.style.cssText = `top:${m.top}%;height:${m.h}%;--op:${m.op};--dur:${m.dur}s;--dir:${m.dir};--br:${m.breathe}s;` +
        `background-image:url("assets/bg/${m.img}.webp")`;
      scene.appendChild(el);
    }
    // stars
    const cv = document.createElement("canvas");
    cv.className = "bgstars";
    scene.appendChild(cv);
    const ctx = cv.getContext("2d");
    // lights
    const lights = [];
    for (const l of S.layers) {
      const wrap = document.createElement("div");
      wrap.className = "bgl " + l.kind;
      place(wrap, l.box);
      const img = new Image();
      img.alt = ""; img.decoding = "async"; img.draggable = false;
      img.src = `assets/bg/${l.name}.webp`;
      wrap.appendChild(img);
      // a soft halo of the light's own colour round lamps and signs (the painting's glow is in the layer;
      // this is the air lighting up), drawn additive too
      if (l.kind === "lamp" || l.kind === "neon" || l.kind === "moon") {
        const h = document.createElement("b");
        const [r, g, b] = l.hue;
        h.style.background = `radial-gradient(closest-side, rgba(${r},${g},${b},.42), rgba(${r},${g},${b},.12) 55%, rgba(${r},${g},${b},0))`;
        wrap.appendChild(h);
      }
      scene.appendChild(wrap);
      lights.push({ el: wrap, kind: l.kind, name: l.name, level: 1, phase: rnd() * 100, rate: lerp(.7, 1.4, rnd()),
                    nextGust: 2 + rnd() * 9, gust: null, nextBuzz: 4 + rnd() * 14, buzz: null });
    }
    const street = lights.find(l => l.kind === "street");
    const stars = S.stars || [];

    let W = 0, H = 0, dpr = 1;
    function size() {
      const r = scene.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      W = r.width; H = r.height;
      cv.width = Math.max(1, Math.round(W * dpr)); cv.height = Math.max(1, Math.round(H * dpr));
    }
    size();
    new ResizeObserver(size).observe(scene);

    function drawStars(t) {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, W, H);
      // the slow drift: a few px on a figure-eight, the same for every star (the sky turning, a little)
      const k = W / 1536;
      const dx = Math.sin(t / 47) * 4 * k, dy = Math.sin(t / 31) * 1.6 * k;
      ctx.globalCompositeOperation = "lighter";
      for (const s of stars) {
        // scintillation: two beats that never line up, plus a rare sharp glint
        const tw = .5 + .5 * Math.sin(t * s.s * 2.1 + s.p) * Math.sin(t * s.s * 0.83 + s.p * 1.7);
        let a = s.b * (.35 + .65 * tw);
        const glint = Math.sin(t * .37 * s.s + s.p * 3);
        if (glint > .985) a = Math.min(1, a + (glint - .985) * 40);
        const x = s.x * W + dx + Math.sin(t * .2 + s.p) * .35 * k, y = s.y * H + dy;
        const r = s.r * k * (s.cross ? 1 + .25 * tw : 1);
        ctx.globalAlpha = a;
        ctx.fillStyle = s.c;
        ctx.beginPath(); ctx.arc(x, y, Math.max(.5, r), 0, 6.283); ctx.fill();
        if (s.cross) {   // the bright ones: a soft four-point flare that grows as they twinkle up
          ctx.globalAlpha = a * .55;
          const L = r * (3 + 3 * tw);
          ctx.fillRect(x - L, y - .4 * k, L * 2, .8 * k);
          ctx.fillRect(x - .4 * k, y - L, .8 * k, L * 2);
          ctx.globalAlpha = a * .25;
          ctx.beginPath(); ctx.arc(x, y, r * 3, 0, 6.283); ctx.fill();
        }
      }
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "source-over";
    }

    function lampLevel(L, t, dt) {
      // a gas flame never sits still: a breath of shimmer on a few beats
      let v = .9 + .05 * Math.sin(t * 7.3 * L.rate + L.phase) + .035 * Math.sin(t * 13.1 * L.rate + L.phase * 2)
        + .025 * Math.sin(t * 2.2 + L.phase * .5);
      // and now and then a gust: down to ~half and a stutter back up over a fifth of a second
      L.nextGust -= dt;
      if (L.nextGust <= 0 && !L.gust) { L.gust = { t: 0, len: .16 + rnd() * .3, depth: .35 + rnd() * .3, twice: rnd() < .4 }; L.nextGust = 4 + rnd() * 12; }
      if (L.gust) {
        const g = L.gust; g.t += dt;
        const p = g.t / g.len;
        if (p >= 1) L.gust = null;
        else {
          let dip = Math.sin(p * Math.PI);
          if (g.twice) dip = Math.abs(Math.sin(p * Math.PI * 2));
          v -= g.depth * dip;
        }
      }
      return Math.max(.2, Math.min(1.05, v));
    }

    function neonLevel(L, t, dt) {
      let v = .96 + .03 * Math.sin(t * 50 + L.phase);        // the hum
      L.nextBuzz -= dt;
      const often = L.name === "neon_skull" ? .45 : 1;
      if (L.nextBuzz <= 0 && !L.buzz) { L.buzz = { t: 0, len: .25 + rnd() * .5, seq: Array.from({ length: 8 }, () => rnd()) }; L.nextBuzz = (5 + rnd() * 16) * often; }
      if (L.buzz) {
        const b = L.buzz; b.t += dt;
        if (b.t >= b.len) L.buzz = null;
        else v = b.seq[Math.floor(b.t / b.len * b.seq.length)] < .5 ? .08 + rnd() * .12 : 1;
      }
      return v;
    }

    if (REDUCED) { drawStars(0); return; }

    let last = performance.now(), acc = 0;
    function frame(now) {
      requestAnimationFrame(frame);
      const dt = Math.min(.1, (now - last) / 1000);
      last = now;
      acc += dt;
      if (acc < 1 / 32) return;                 // ~30 fps is plenty for flicker and twinkle
      const step = acc; acc = 0;
      if (document.hidden) return;
      const t = now / 1000;
      let lampSum = 0, lampN = 0;
      for (const L of lights) {
        if (L.kind === "lamp") { L.level = lampLevel(L, t, step); lampSum += L.level; lampN++; }
        else if (L.kind === "neon") L.level = neonLevel(L, t, step);
        else if (L.kind === "moon") L.level = .86 + .14 * (.5 + .5 * Math.sin(t * .45 + L.phase));
        else continue;
        L.el.style.opacity = L.level.toFixed(3);
      }
      // the wet cobbles mirror the lamps: their average, with a slow ripple of their own
      if (street) street.el.style.opacity = ((lampN ? lampSum / lampN : 1) * (.9 + .1 * Math.sin(t * 1.3))).toFixed(3);
      drawStars(t);
    }
    requestAnimationFrame(frame);
  }
})();
