// Screens QA: the SMUKIEZ loading ident mid-drop and landed, the title over the three how-to-play cards, the board
// after a spin, and the bonus shop (banners, skull volatility pips). usage: node tools/nola/qa_screens.js
const path = require("path");
const { chromium } = require(path.join(__dirname, "..", "..", "..", ".tools", "pw", "node_modules", "playwright"));
const OUT = require("path").join(require("os").tmpdir(), "nola_qa") + "/";   // screenshots go to the temp folder (writes into the repo tripped Windows file locks)
require("fs").mkdirSync(OUT, { recursive: true });
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  const errs = []; p.on("pageerror", e => errs.push(e.message)); p.on("response", r => { if (r.status() >= 400) errs.push(r.status() + " " + r.url()); });
  await p.goto("http://localhost:8755/index.html?sessionID=test&rgs_url=http://localhost:8755&lang=en&device=desktop");
  for (const [ms, n] of [[900, "intro_a"], [700, "intro_b"], [1500, "intro_c"]]) { await p.waitForTimeout(ms); await p.screenshot({ path: OUT + n + ".png" }); }
  await p.waitForTimeout(6000); await p.screenshot({ path: OUT + "features.png" });
  await p.mouse.click(960, 1040); await p.waitForTimeout(3500);
  await p.keyboard.press("Space"); await p.waitForTimeout(5000); await p.screenshot({ path: OUT + "board.png" });
  await p.click("#bonusBtn", { force: true }).catch(e => errs.push("bonus " + e.message)); await p.waitForTimeout(1500); await p.screenshot({ path: OUT + "shop.png" });
  console.log(errs.length ? errs : "no errors");
  await b.close();
})();
