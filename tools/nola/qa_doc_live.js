// Doc as the game draws him (the live rig + his live flame), for looking at: enters the game, then screenshots his
// corner of the screen
//   live    N frames of whatever he is doing, `gap` ms apart (the idle, the flame never the same twice)
//   poses   clip:frame,... posed through the rig's QA handle (the flame put straight on its bone), one tile each
// and prints any console error (a shader that failed to compile shows here).
// usage: node tools/nola/qa_doc_live.js [port=8755] [live=6] [gap=300] ["clip:frame,clip:frame"] [WxH=1920x1080]
//   -> %TEMP%/nola_qa/doc_live_<n>.png, doc_pose_<clip>_<frame>.png
const path = require("path"), os = require("os"), fs = require("fs");
const { chromium } = require(path.join(__dirname, "..", "..", "..", ".tools", "pw", "node_modules", "playwright"));
const PORT = process.argv[2] || "8755", LIVE = +(process.argv[3] || 6), GAP = +(process.argv[4] || 300);
const POSES = (process.argv[5] || "").split(",").filter(Boolean).map(s => s.split(":"));
const [W, H] = (process.argv[6] || "1920x1080").split("x").map(Number);
const REACT = process.argv[7] || "";                       // a reaction to fire while he idles: frames of it cutting in
const OUT = path.join(os.tmpdir(), "nola_qa");
fs.mkdirSync(OUT, { recursive: true });
(async () => {
  const b = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
  const p = await b.newPage({ viewport: { width: W, height: H } });
  const errs = [];
  p.on("pageerror", e => errs.push("pageerror " + e.message));
  p.on("console", m => { if (m.type() === "error" || /flame|shader|WebGL: INVALID|ERROR:/i.test(m.text())) errs.push(m.type() + " " + m.text().slice(0, 2600)); });
  const BASE = `http://localhost:${PORT}`;
  await p.goto(`${BASE}/index.html?sessionID=test&rgs_url=${BASE}&lang=en&device=${W < 900 ? "mobile" : "desktop"}`, { waitUntil: "domcontentloaded", timeout: 90000 });
  await p.waitForFunction(() => window.__chars && window.__chars.length, null, { timeout: 180000 });
  for (let i = 0; i < 90; i++) {                            // through the intro and the three cards: Play shows once the round's FX are made
    await p.waitForTimeout(1000);
    if (await p.evaluate(() => !document.body.classList.contains("features-up") && (!document.getElementById("intro") || document.getElementById("intro").classList.contains("gone")))) break;
    await p.mouse.click(W / 2, H - 30);
  }
  await p.waitForTimeout(4500);
  const box = await p.evaluate(() => {
    const c = window.__chars[0], r = c.app.canvas.getBoundingClientRect();
    return { x: Math.max(0, Math.floor(r.left)), y: Math.max(0, Math.floor(r.top)), width: Math.ceil(r.width), height: Math.ceil(r.height),
             rig: !!c.rig, ver: c.man.version, flame: !!c.flame, renderer: c.app.renderer.type, scale: c.actor.scale.x };
  });
  console.log(JSON.stringify(box));
  const clip = { x: box.x, y: box.y, width: Math.min(box.width, W - box.x), height: Math.min(box.height, H - box.y) };
  for (let i = 0; i < LIVE; i++) {
    await p.screenshot({ path: path.join(OUT, `doc_live_${i}.png`), clip });
    await p.waitForTimeout(GAP);
  }
  if (REACT) {                                               // -> doc_react_<n>.png, every 100 ms from the cue
    const st = await p.evaluate(k => { const c = window.__chars[0]; const before = c.state().cur.clip; charReact(k); return before + " -> " + c.state().cur.clip; }, REACT);
    console.log("react", REACT, st);
    for (let i = 0; i < 14; i++) {
      await p.screenshot({ path: path.join(OUT, `doc_react_${String(i).padStart(2, "0")}.png`), clip });
      await p.waitForTimeout(100);
    }
  }
  if (POSES.length) {
    await p.evaluate(() => window.__chars[0].app.ticker.stop());
    for (const [c, f] of POSES) {
      await p.evaluate(([c, f]) => { const t = performance.now(); window.__chars[0].pose(c, +f, t); }, [c, f]);
      await p.waitForTimeout(60);
      await p.screenshot({ path: path.join(OUT, `doc_pose_${c}_${f}.png`), clip });
    }
  }
  console.log(errs.length ? "ERRORS:\n" + [...new Set(errs)].join("\n") : "no errors");
  await b.close();
})();
