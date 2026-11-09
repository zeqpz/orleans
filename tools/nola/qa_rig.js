// Doc's live rig in the game (headless Chromium): loads the game, enters, checks the rig player took over (not the
// baked frames), then poses every clip at a spread of frames through the debug handle and screenshots Doc's box;
// measures the frame rate the figure draws at and how long one pose (skinning + upload + draw) takes; and that his
// soles stay on one line (the ground) through every clip.
// usage: node tools/nola/qa_rig.js [port=8755] [WxH=1920x1080]   -> %TEMP%/nola_qa/rig_<clip>.png + a report
const path = require("path"), os = require("os"), fs = require("fs");
const { chromium } = require(path.join(__dirname, "..", "..", "..", ".tools", "pw", "node_modules", "playwright"));
const PORT = process.argv[2] || "8755", BASE = `http://localhost:${PORT}`;
const [VW, VH] = (process.argv[3] || "1920x1080").split("x").map(Number);
const OUT = path.join(os.tmpdir(), "nola_qa");
fs.mkdirSync(OUT, { recursive: true });
(async () => {
  const b = await chromium.launch({ args: ["--autoplay-policy=no-user-gesture-required"] });
  const p = await b.newPage({ viewport: { width: VW, height: VH } });
  const errs = [];
  p.on("console", m => { if (m.type() === "error" || m.type() === "warning") errs.push(m.type() + ": " + m.text()); });
  p.on("pageerror", e => errs.push("pageerror: " + e.message));
  p.on("response", r => { if (r.status() >= 400) errs.push(r.status() + " " + r.url()); });
  await p.goto(`${BASE}/index.html?sessionID=test&rgs_url=${BASE}&lang=en&device=desktop`, { waitUntil: "domcontentloaded", timeout: 90000 });
  await p.waitForFunction(() => window.__chars && window.__chars.length, null, { timeout: 120000 }).catch(() => errs.push("no character registered"));
  await p.waitForTimeout(6000);
  await p.mouse.click(VW / 2, VH - 30);
  await p.waitForTimeout(2500);
  const info = await p.evaluate(() => {
    const c = window.__chars[0];
    const r = c.app.canvas.getBoundingClientRect();
    return { rig: !!c.rig, canvas: [r.left, r.top, r.width, r.height].map(Math.round), verts: c.man ? c.man.parts.reduce((s, q) => s + q.verts, 0) : 0 };
  });
  await p.screenshot({ path: path.join(OUT, "rig_live.png") });
  // the figure's own draw rate over 3 s of idle/enter, and one pose's cost
  const perf = await p.evaluate(async () => {
    const c = window.__chars[0];
    let n = 0;
    const on = () => n++;
    c.app.renderer.runners.postrender.add({ postrender: on });
    await new Promise(r => setTimeout(r, 3000));
    c.app.renderer.runners.postrender.remove({ postrender: on });
    const t0 = performance.now();
    for (let i = 0; i < 60; i++) c.pose("big_win", 40 + i * .5);
    return { drawsPer3s: n, poseMs: (performance.now() - t0) / 60 };
  });
  // every clip, a spread of frames: screenshot of the box, and the soles' line per frame
  // stop the figure's own clock, so each pose asked for is the one screenshotted
  const clips = await p.evaluate(() => { window.__chars[0].app.ticker.stop(); return Object.keys(window.__chars[0].man.clips); });
  const box = info.canvas;
  const soles = {};
  for (const clip of clips) {
    const n = await p.evaluate(c => window.__chars[0].man.clips[c].frames, clip);
    const shots = [0, .15, .3, .45, .6, .75, .9, 1].map(k => Math.min(n - 1, Math.round(k * (n - 1))));
    soles[clip] = [];
    for (let k = 0; k < shots.length; k++) {
      const s = await p.evaluate(([c, f]) => {
        const ch = window.__chars[0];
        ch.pose(c, f);
        const sh = ch.fig.shoes(c, f);
        return sh.map(x => Math.round(x[2] * 10) / 10);
      }, [clip, shots[k]]);
      soles[clip].push(s);
      await p.screenshot({ path: path.join(OUT, `rig_${clip}_${k}.png`), clip: { x: Math.max(0, box[0]), y: Math.max(0, box[1]), width: Math.min(box[2], VW), height: Math.min(box[3], VH - Math.max(0, box[1])) } });
    }
  }
  console.log(JSON.stringify({ info, perf, soles, errors: [...new Set(errs)].slice(0, 20) }, null, 1));
  await b.close();
})();
