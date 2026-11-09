// The frame's top corners and the candle's live flame: a full screenshot, then 8 close-ups of the flame 150 ms apart
// (it must change), at 1920x1080 and on a portrait phone. usage: node tools/nola/qa_flame.js  (mock RGS on 8755)
const path = require("path");
const { chromium } = require(path.join(__dirname, "..", "..", "..", ".tools", "pw", "node_modules", "playwright"));
const OUT = path.join(__dirname, "..", "..", "art", "nola-src", "qa_browser") + "/";
(async () => {
  const b = await chromium.launch();
  for (const [name, vp, dev, dsf] of [["desk", { width: 1920, height: 1080 }, "desktop", 1], ["phone", { width: 390, height: 844 }, "mobile", 2]]) {
    const p = await b.newPage({ viewport: vp, deviceScaleFactor: dsf });
    const errs = []; p.on("pageerror", e => errs.push(e.message)); p.on("response", r => { if (r.status() >= 400) errs.push(r.status() + " " + r.url()); });
    await p.goto(`http://localhost:8755/index.html?sessionID=test&rgs_url=http://localhost:8755&lang=en&device=${dev}`);
    await p.waitForTimeout(8000); await p.mouse.click(vp.width / 2, vp.height * .9); await p.waitForTimeout(4000);
    await p.screenshot({ path: OUT + `flame_${name}_full.png` });
    const r = await p.evaluate(() => { const c = document.getElementById("candleflame").getBoundingClientRect(); return [c.x, c.y, c.width, c.height]; });
    const clip = { x: Math.max(0, r[0] - r[2]), y: Math.max(0, r[1] - r[3] * .3), width: r[2] * 3, height: r[3] * 1.8 };
    const sums = [];
    for (let i = 0; i < 8; i++) {
      const buf = await p.screenshot({ path: OUT + `flame_${name}_${i}.png`, clip });
      sums.push(buf.length);
      await p.waitForTimeout(150);
    }
    console.log(name, "flame box", r.map(Math.round), "frame sizes", sums.join(","), errs.length ? errs : "no errors");
  }
  await b.close();
})();
