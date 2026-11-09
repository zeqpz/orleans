// Capture the Multi's hex-away (hexIcon) in a Bet Replay of a round with a Multi: polls the page for an active
// hex burst and screenshots the board while it plays. usage: node tools/nola/qa_hex.js [event=9] [port=8755]
const path = require("path"), fs = require("fs");
const { chromium } = require(path.join(__dirname, "..", "..", "..", ".tools", "pw", "node_modules", "playwright"));
const EV = process.argv[2] || "9", PORT = process.argv[3] || "8755", BASE = `http://localhost:${PORT}`;
const OUT = path.join(__dirname, "..", "..", "art", "nola-src", "qa_browser");
fs.mkdirSync(OUT, { recursive: true });
(async () => {
  const browser = await chromium.launch();
  const p = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  const errs = []; p.on("pageerror", e => errs.push(e.message));
  await p.goto(`${BASE}/index.html?replay=true&game=smukiez&version=1&mode=base&event=${EV}&amount=1&currency=USD&rgs_url=${BASE}&lang=en&device=desktop`);
  const t0 = Date.now(); let shots = 0, seen = false, reveal = 0;
  while (Date.now() - t0 < 40000 && shots < 14) {
    const st = await p.evaluate(() => ({
      hex: typeof bursts !== "undefined" && bursts.some(b => b.hex),
      wisps: document.querySelectorAll(".spraylayer .swisp").length,
    })).catch(() => ({}));
    if (st.wisps && reveal < 3) { await p.screenshot({ path: path.join(OUT, `reveal_${reveal++}.png`) }); }
    if (st.hex) { seen = true; await p.screenshot({ path: path.join(OUT, `hex_${String(shots++).padStart(2, "0")}.png`) }); }
    else if (seen && shots >= 4) break;
    else await p.waitForTimeout(25);
  }
  console.log(JSON.stringify({ hexFrames: shots, revealFrames: reveal, errors: errs }));
  await browser.close();
})();
