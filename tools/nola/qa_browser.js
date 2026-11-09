// Voodoo on Bourbon browser QA (headless Chromium via the shared Playwright in ClaudeRoblox/.tools/pw):
//  1. the game at 1920x1080: the street's live layers really change over time (lamp flicker, neon, stars), Doc is
//     drawn, the symbols load, and the console stays clean; screenshots of the board
//  2. a Bet Replay of a round with a Multi (book 9), frames captured through the hex-away
// usage: node tools/nola/qa_browser.js [port=8755]   -> art/nola-src/qa_browser/*.png + a report on stdout
const path = require("path"), fs = require("fs");
const { chromium } = require(path.join(__dirname, "..", "..", "..", ".tools", "pw", "node_modules", "playwright"));
const PORT = process.argv[2] || "8755";
const BASE = `http://localhost:${PORT}`;
const OUT = require("path").join(require("os").tmpdir(), "nola_qa") + "/";   // screenshots go to the temp folder (writes into the repo tripped Windows file locks)
require("fs").mkdirSync(OUT, { recursive: true });

(async () => {
  const browser = await chromium.launch({ args: ["--autoplay-policy=no-user-gesture-required"] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  const errors = [];
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", e => errors.push("pageerror: " + e.message));
  page.on("requestfailed", r => errors.push("failed: " + r.url()));
  page.on("response", r => { if (r.status() >= 400) errors.push(r.status() + " " + r.url()); });

  await page.goto(`${BASE}/index.html?sessionID=test&rgs_url=${BASE}&lang=en&device=desktop`, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.waitForFunction(() => window.__chars && window.__chars.length, null, { timeout: 120000 }).catch(() => {});
  await page.waitForTimeout(9000);
  await page.screenshot({ path: path.join(OUT, "01_features.png") });
  await page.mouse.click(960, 1000);
  await page.waitForTimeout(5000);
  await page.screenshot({ path: path.join(OUT, "02_game.png") });

  // the live street: sample every light's opacity 12 times over 3 s
  const samples = await page.evaluate(async () => {
    const out = [];
    for (let i = 0; i < 12; i++) {
      out.push([...document.querySelectorAll("#bgscene .bgl")].map(e => +e.style.opacity || 1));
      await new Promise(r => setTimeout(r, 250));
    }
    const names = [...document.querySelectorAll("#bgscene .bgl img")].map(i => i.src.split("/").pop().replace(".webp", ""));
    return { out, names };
  });
  const span = samples.names.map((n, j) => {
    const v = samples.out.map(r => r[j]);
    return `${n} ${Math.min(...v).toFixed(2)}..${Math.max(...v).toFixed(2)}`;
  });
  const stars = await page.evaluate(async () => {
    const cv = document.querySelector("#bgscene .bgstars"), ctx = cv.getContext("2d");
    const grab = () => Array.from(ctx.getImageData(0, 0, cv.width, Math.round(cv.height * .35)).data.filter((_, i) => i % 4 === 3));
    const a = grab(); await new Promise(r => setTimeout(r, 600)); const b = grab();
    let lit = 0, diff = 0;
    for (let i = 0; i < a.length; i++) { if (a[i] > 40) lit++; if (Math.abs(a[i] - b[i]) > 20) diff++; }
    return { lit, changed: diff };
  });
  const doc = await page.evaluate(() => {
    const c = document.querySelector("#charfx canvas");
    return c ? { w: c.width, h: c.height, on: c.classList.contains("on") } : null;
  });
  // a spin, to see a board come in
  await page.keyboard.press("Space");
  await page.waitForTimeout(4500);
  await page.screenshot({ path: path.join(OUT, "03_after_spin.png") });

  // 2. the replay of a round with a Multi
  const rp = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  rp.on("pageerror", e => errors.push("replay pageerror: " + e.message));
  await rp.goto(`${BASE}/index.html?replay=true&game=smukiez&version=1&mode=base&event=9&amount=1&currency=USD&rgs_url=${BASE}&lang=en&device=desktop`);
  await rp.waitForTimeout(8000);
  for (const sel of ["text=Click to play", "text=PLAY", "button:has-text('Play')"]) {
    try { await rp.click(sel, { timeout: 1500 }); break; } catch (e) { /* not that one */ }
  }
  await rp.mouse.click(960, 1000);
  for (let i = 0; i < 26; i++) {
    await rp.waitForTimeout(450);
    await rp.screenshot({ path: path.join(OUT, `replay_${String(i).padStart(2, "0")}.png`) });
  }
  console.log(JSON.stringify({ lights: span, stars, doc, errors: [...new Set(errors)].slice(0, 25) }, null, 1));
  await browser.close();
})();
