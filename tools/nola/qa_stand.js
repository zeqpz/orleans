// Where Doc stands, at every screen shape: enters the game, then for each viewport reports his soles (the bottom edge
// of his canvas, where the rig stands them) against the painted left sidewalk under his shoes (WALK in index.html,
// through #bgscene's box): ON when the soles are between the sidewalk's back edge and the curb. Also: the top of his
// hat on screen, his box against the iron frame, and a screenshot per size.
// usage: node tools/nola/qa_stand.js [port=8755]   -> %TEMP%/nola_qa/stand_<w>x<h>.png + a report
const path = require("path"), os = require("os"), fs = require("fs");
const { chromium } = require(path.join(__dirname, "..", "..", "..", ".tools", "pw", "node_modules", "playwright"));
const PORT = process.argv[2] || "8755", BASE = `http://localhost:${PORT}`;
const OUT = path.join(os.tmpdir(), "nola_qa");
fs.mkdirSync(OUT, { recursive: true });
const SIZES = (process.argv[3] ? process.argv[3].split(",").map(s => s.split("x").map(Number)) :
  [[1920, 1080], [2560, 1440], [1366, 768], [1440, 900], [1280, 1024], [1600, 900], [2560, 1080], [1024, 768],
   [1024, 576], [800, 600], [844, 390], [390, 844], [768, 1024], [360, 740], [430, 932]]);
(async () => {
  const b = await chromium.launch();
  const rows = [];
  let bad = 0;
  for (const [w, h] of SIZES) {
    const p = await b.newPage({ viewport: { width: w, height: h } });
    const errs = [];
    p.on("pageerror", e => errs.push(e.message));
    await p.goto(`${BASE}/index.html?sessionID=test&rgs_url=${BASE}&lang=en&device=${w < 900 ? "mobile" : "desktop"}`,
      { waitUntil: "domcontentloaded", timeout: 90000 });
    await p.waitForFunction(() => window.__chars && window.__chars.length, null, { timeout: 120000 }).catch(() => errs.push("no character"));
    await p.waitForTimeout(3000);
    await p.mouse.click(w / 2, h - 30);
    await p.waitForTimeout(3500);
    const r = await p.evaluate(() => {
      const c = window.__chars[0], cv = c.app.canvas.getBoundingClientRect(), s = document.getElementById("bgscene").getBoundingClientRect();
      const fr = document.getElementById("paintframe").getBoundingClientRect();
      const headroom = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--char-headroom")) || 1;
      const sole = cv.bottom, hat = cv.bottom - cv.height / headroom, footX = cv.left + cv.width * .5;
      const fx = (footX - s.left) / s.width, fy = (sole - s.top) / s.height;
      const back = walkEdge(fx, "back"), front = walkEdge(fx, "front");
      // the figure's widest reach right of centre (the open hand), in screen px
      const reach = cv.left + cv.width / 2 + (990 - c.man.cx) * cv.height / headroom / c.man.rest_height;
      return { sole: Math.round(sole), hat: Math.round(hat), fx: +fx.toFixed(3), fy: +fy.toFixed(3), band: [+back.toFixed(3), +front.toFixed(3)],
               on: fx > 0 && fx < .37 && fy >= back - .005 && fy <= front + .005, overFrame: Math.round(reach - fr.left), frameTop: Math.round(fr.top),
               canvas: [cv.left, cv.top, cv.width, cv.height].map(Math.round) };
    });
    await p.screenshot({ path: path.join(OUT, `stand_${w}x${h}.png`) });
    if (!r.on || r.hat < 0) bad++;
    rows.push(`${w}x${h} ${r.on ? "ON " : "OFF"} soles ${r.sole} (plate y ${r.fy}, sidewalk ${r.band.join("..")} at x ${r.fx}) hat ${r.hat} handOverFrame ${r.overFrame}px` +
              (errs.length ? " ERR " + errs.join("; ") : ""));
    await p.close();
  }
  console.log(rows.join("\n") + `\n${bad ? bad + " OFF" : "all ON the sidewalk"}`);
  await b.close();
})();
