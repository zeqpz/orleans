// Voodoo on Bourbon: the live flame on the skull's candle (the iron frame's top-right corner).
// The frame art's own flame was painted out (art/nola-src/ui/frame.png); this canvas sits on the wick, in the frame's
// box (CSS #candleflame, placed from the same fractions as #paintframe), and draws a cartoon flame every frame in the
// game's look - a black ink outline, a voodoo-green body, a pale core, a dark wick - that never holds still:
//   sway     the tip wanders on three incommensurate waves, the body following it in a lazy S
//   breathe  its height and width flicker, tall and thin then short and fat
//   gusts    now and then a draught: it leans hard, shrinks and stutters back up
//   embers   a spark breaks off the tip once in a while and drifts up, fading
//   glow     a soft green light round it that pulses with its height (additive)
// Seeded, ~40 fps on its own clock, and still (one calm frame) with reduced motion.
(function () {
  "use strict";
  const board = document.getElementById("board");
  if (!board) return;
  const cv = document.createElement("canvas");
  cv.id = "candleflame";
  cv.setAttribute("aria-hidden", "true");
  board.appendChild(cv);
  const ctx = cv.getContext("2d");
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let seed = 4471;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
  let W = 0, H = 0, dpr = 1;
  function size() {
    const r = cv.getBoundingClientRect();
    dpr = Math.min(2, window.devicePixelRatio || 1);
    W = cv.clientWidth; H = cv.clientHeight;
    if (!W || !H) return;
    cv.width = Math.round(W * dpr * (r.width / W || 1)); cv.height = Math.round(H * dpr * (r.height / H || 1));
  }
  size();
  new ResizeObserver(size).observe(cv);

  const embers = [];
  let gust = null, nextGust = 3 + rnd() * 5, last = performance.now(), acc = 0;

  function flamePath(cx, by, bw, h, sway, bend) {
    // a teardrop from the wick up to a wandering tip, its sides bowing with the sway (a lazy S)
    const tipX = cx + sway, tipY = by - h;
    ctx.beginPath();
    ctx.moveTo(cx, by + bw * .18);
    ctx.bezierCurveTo(cx - bw * .78, by + bw * .05, cx - bw * .62 + bend, by - h * .45, tipX - bw * .05, tipY + h * .06);
    ctx.quadraticCurveTo(tipX, tipY - h * .02, tipX + bw * .05, tipY + h * .06);
    ctx.bezierCurveTo(cx + bw * .62 + bend, by - h * .45, cx + bw * .78, by + bw * .05, cx, by + bw * .18);
    ctx.closePath();
  }

  function draw(t, dt) {
    if (!W || !H) return;
    ctx.setTransform(cv.width / W, 0, 0, cv.height / H, 0, 0);
    ctx.clearRect(0, 0, W, H);
    // the draught
    nextGust -= dt;
    if (!gust && nextGust <= 0) { gust = { t: 0, len: .5 + rnd() * .7, dir: rnd() < .5 ? -1 : 1, k: .5 + rnd() * .5 }; nextGust = 4 + rnd() * 9; }
    let g = 0;
    if (gust) { gust.t += dt; const p = gust.t / gust.len; if (p >= 1) gust = null; else g = Math.sin(Math.PI * p) * (1 + .35 * Math.sin(p * 40)) * gust.k * gust.dir; }
    const cx = W * .5, by = H * .86;
    const U = H * .586;   // the flame's own width unit (the canvas is wider than the flame, so its glow fades out inside it)
    const breathe = 1 + .09 * Math.sin(t * 9.3) + .06 * Math.sin(t * 14.7 + 1.3) + .05 * Math.sin(t * 23.1 + 2.1);
    const h = H * .58 * breathe * (1 - .22 * Math.abs(g));
    const bw = U * .36 * (1.06 - .1 * (breathe - 1)) * (1 + .1 * Math.abs(g));
    const sway = U * (.07 * Math.sin(t * 3.1) + .045 * Math.sin(t * 5.7 + .8) + .03 * Math.sin(t * 11.3 + 2.4)) + g * U * .22;
    const bend = -sway * .35;
    // glow (additive), pulsing with the height
    ctx.globalCompositeOperation = "lighter";
    const gr = ctx.createRadialGradient(cx + sway * .4, by - h * .45, 0, cx + sway * .4, by - h * .45, H * .46);
    const ga = .34 + .16 * (breathe - 1) * 4;
    gr.addColorStop(0, `rgba(150, 255, 130, ${ga.toFixed(3)})`);
    gr.addColorStop(.45, `rgba(124, 255, 107, ${(ga * .35).toFixed(3)})`);
    gr.addColorStop(1, "rgba(124, 255, 107, 0)");
    ctx.fillStyle = gr;
    ctx.fillRect(0, 0, W, H);
    ctx.globalCompositeOperation = "source-over";
    // ink outline, then the green body, then the pale core
    const ink = Math.max(1.2, U * .045);
    flamePath(cx, by, bw, h, sway, bend);
    ctx.lineJoin = "round"; ctx.lineWidth = ink * 2; ctx.strokeStyle = "#141414"; ctx.stroke();
    ctx.fillStyle = "#5FE04E"; ctx.fill();
    flamePath(cx - bw * .06, by, bw * .82, h * .9, sway * .9, bend);   // the lit side, a flat lighter tone (the cel shade)
    ctx.fillStyle = "#8CFF6E"; ctx.fill();
    flamePath(cx, by - h * .02, bw * .48, h * .52, sway * .55, bend * .5);
    ctx.fillStyle = "#DFFFC4"; ctx.fill();
    flamePath(cx, by - h * .03, bw * .22, h * .22, sway * .3, 0);
    ctx.fillStyle = "#FFFFF2"; ctx.fill();
    // the wick
    ctx.strokeStyle = "#141414"; ctx.lineWidth = Math.max(1, U * .05); ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(cx, by + bw * .2); ctx.quadraticCurveTo(cx + sway * .05, by - h * .06, cx + sway * .12, by - h * .14); ctx.stroke();
    // embers
    if (!REDUCED && rnd() < dt * .9) embers.push({ x: cx + sway, y: by - h * .95, vx: (rnd() - .5) * H * .18, vy: -H * (.25 + rnd() * .2), life: .9 + rnd() * .6, age: 0 });
    for (let i = embers.length - 1; i >= 0; i--) {
      const e = embers[i];
      e.age += dt; if (e.age > e.life) { embers.splice(i, 1); continue; }
      e.x += (e.vx + Math.sin(t * 6 + i) * H * .09) * dt; e.y += e.vy * dt;
      const a = 1 - e.age / e.life;
      ctx.fillStyle = `rgba(190, 255, 160, ${a.toFixed(3)})`;
      ctx.beginPath(); ctx.arc(e.x, e.y, Math.max(.8, H * .018 * a), 0, 6.283); ctx.fill();
    }
  }

  if (REDUCED) { draw(0, 0); new ResizeObserver(() => draw(0, 0)).observe(cv); return; }
  function frame(now) {
    requestAnimationFrame(frame);
    const dt = Math.min(.1, (now - last) / 1000); last = now; acc += dt;
    if (acc < 1 / 42 || document.hidden) return;
    draw(now / 1000, acc); acc = 0;
  }
  requestAnimationFrame(frame);
})();
