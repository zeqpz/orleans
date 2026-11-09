// Bet Replay of book 9 (a round with a Multi): logs every board event and screenshots the hex-away while it plays.
// usage: node tools/nola/qa_replay.js   (mock RGS on 8755)
const { chromium } = require(require("path").join(__dirname, "..", "..", "..", ".tools", "pw", "node_modules", "playwright"));
const OUT = require("path").join(require("os").tmpdir(), "nola_qa") + "/";   // screenshots go to the temp folder (writes into the repo tripped Windows file locks)
require("fs").mkdirSync(OUT, { recursive: true });
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1600, height: 900 } });
  const log = []; p.on("console", m => { if (/^(EV|BURST|HEX)/.test(m.text())) log.push(m.text()); });
  await p.goto("http://localhost:8755/index.html?replay=true&game=smukiez&version=1&mode=base&event=9&amount=1&currency=USD&rgs_url=http://localhost:8755&lang=en&device=desktop");
  await p.waitForTimeout(4000);
  console.log("frozen", await p.evaluate(() => Object.isFrozen(handlers)));
  await p.evaluate(() => {
    window.__hex = 0;
    for (const k of Object.keys(handlers)) { const f = handlers[k]; handlers[k] = function () { console.log("EV " + k); return f.apply(this, arguments); }; }
  });
  await p.click("#replayPlay");
  let shots = 0; const t0 = Date.now();
  while (Date.now() - t0 < 25000) {
    const s = await p.evaluate(() => ({ playing: state.playing, hex: bursts.filter(b => b.hex).length, n: bursts.length, wisps: document.querySelectorAll(".spraylayer .swisp").length }));
    if ((s.hex || s.wisps) && shots < 16) await p.screenshot({ path: OUT + `hex_${String(shots++).padStart(2, "0")}.png` });
    if (!s.playing && Date.now() - t0 > 3000) break;
    await p.waitForTimeout(20);
  }
  console.log(log.join(" | ")); console.log("shots", shots);
  await b.close();
})().catch(e => console.log("FAIL", e.message));
