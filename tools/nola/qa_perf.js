// Board frame-rate benchmark: a Bet Replay of one book event, timed frame by frame, in headless Chrome on the
// real GPU (the installed Chrome, not Playwright's software-GL shell). Interleaved A/B: with --base <dir>, the
// "A" runs are served the files in <dir> (index.html, boardgl.js, ...) in place of frontend/'s own, so both
// sides share one server, one set of assets and one machine state; A and B alternate, the order flipping
// each run. Reports per-run numbers and the medians.
//   node tools/nola/qa_perf.js [--runs 5] [--profiles desktop,phone] [--base DIR] [--event 9] [--port 8755]
//                              [--cpu out.json]   (one B run with a CPU profile: top self time by function)
//                              [--trace out.json] (one B run with a timeline trace: main-thread time by event)
//                              [--q "&glcheck=1"] (more query: glcheck = boardgl's sampled cells checked against CSS)
// Profiles: desktop = 1920x1080 at DPR 1; phone = 390x844 at DPR 3 with a 4x CPU slowdown (from Play on).
const path = require("path"), fs = require("fs");
const { chromium } = require(path.join(__dirname, "..", "..", "..", ".tools", "pw", "node_modules", "playwright"));
const arg = (k, d) => { const i = process.argv.indexOf("--" + k); return i > 0 ? process.argv[i + 1] : d; };
const RUNS = +arg("runs", 5), PORT = arg("port", "8755"), EVENT = arg("event", "9"), BASE = arg("base", "");
const PROFILES = arg("profiles", "desktop,phone").split(",");
const EXTRA = arg("q", "");   // more query, e.g. --q "&glcheck=1"
const CPU_OUT = arg("cpu", ""), TRACE_OUT = arg("trace", ""), ONLY = arg("only", "");   // --only A|B: one side
const CHROME = arg("chrome", "C:/Program Files/Google/Chrome/Application/chrome.exe");
const PROF = {
  desktop: { viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1, cpu: 1, device: "desktop" },
  phone: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true, cpu: 4, device: "mobile" },
};

// every animation frame from Play to the round's end, and the long tasks in between
const PROBE = `(() => {
  window.__ft = []; window.__lt = []; window.__rec = false;
  const loop = t => { if (window.__rec) window.__ft.push(t); requestAnimationFrame(loop); };
  requestAnimationFrame(loop);
  try { new PerformanceObserver(l => { if (window.__rec) for (const e of l.getEntries()) window.__lt.push(e.duration); }).observe({ type: "longtask" }); } catch (e) {}
})();`;

const q = (a, p) => { if (!a.length) return NaN; const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * (s.length - 1) + .5))]; };
const med = a => q(a, .5);

async function run(browser, prof, side, opts = {}) {
  const P = PROF[prof];
  const ctx = await browser.newContext({ viewport: P.viewport, deviceScaleFactor: P.deviceScaleFactor, isMobile: !!P.isMobile, hasTouch: !!P.hasTouch });
  if (side === "A" && BASE) {
    for (const f of fs.readdirSync(BASE)) {
      const body = fs.readFileSync(path.join(BASE, f));
      const type = f.endsWith(".html") ? "text/html; charset=utf-8" : "application/javascript; charset=utf-8";
      await ctx.route(u => new URL(u).pathname === "/" + f, r => r.fulfill({ status: 200, contentType: type, body }));
    }
  }
  await ctx.addInitScript(PROBE);
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", e => errors.push("pageerror: " + e.message));
  page.on("requestfailed", r => errors.push("failed " + r.url().replace(/^https?:\/\/[^/]+/, "") + " " + (r.failure() || {}).errorText));
  const cdp = await ctx.newCDPSession(page);
  const url = `http://localhost:${PORT}/index.html?replay=true&game=smukiez&version=1&mode=base&event=${EVENT}&amount=1&currency=USD&rgs_url=http://localhost:${PORT}&lang=en&device=${P.device}${EXTRA}`;
  const t0 = Date.now();
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.waitForSelector("#replayPlay:not([hidden])", { timeout: 60000 });
  const loadMs = Date.now() - t0;
  const gpu = await page.evaluate(() => {
    const gl = document.createElement("canvas").getContext("webgl"), x = gl && gl.getExtension("WEBGL_debug_renderer_info");
    return x ? gl.getParameter(x.UNMASKED_RENDERER_WEBGL) : "?";
  });
  if (P.cpu > 1) await cdp.send("Emulation.setCPUThrottlingRate", { rate: P.cpu });
  await page.waitForTimeout(500);   // a player's moment before pressing Play
  if (opts.cpu) { await cdp.send("Profiler.enable"); await cdp.send("Profiler.setSamplingInterval", { interval: 200 }); await cdp.send("Profiler.start"); }
  let traceDone = null;
  if (opts.trace) {
    const chunks = [];
    cdp.on("Tracing.dataCollected", e => chunks.push(...e.value));
    traceDone = new Promise(r => cdp.once("Tracing.tracingComplete", () => r(chunks)));
    await cdp.send("Tracing.start", { categories: "devtools.timeline,disabled-by-default-devtools.timeline,v8,blink.user_timing", transferMode: "ReportEvents" });
  }
  await page.evaluate(() => { window.__rec = true; document.getElementById("replayPlay").click(); });
  const tPlay = Date.now();
  await page.waitForFunction(() => !state.playing, null, { timeout: 180000, polling: 200 });
  const wall = Date.now() - tPlay;
  const { ft, lt, gc } = await page.evaluate(() => { window.__rec = false; return { ft: window.__ft, lt: window.__lt, gc: window.__glcheck || null }; });
  if (gc) console.log("  glcheck: cells sampled", gc.cells, " worst px", gc.px.toFixed(4), " worst opacity", gc.op.toFixed(5), " (" + gc.worst + ")");
  if (opts.cpu) { const { profile } = await cdp.send("Profiler.stop"); fs.writeFileSync(opts.cpu, JSON.stringify(profile)); }
  if (opts.trace) { await cdp.send("Tracing.end"); fs.writeFileSync(opts.trace, JSON.stringify(await traceDone)); }
  await ctx.close();
  const d = []; for (let i = 1; i < ft.length; i++) d.push(ft[i] - ft[i - 1]);
  const dur = (ft[ft.length - 1] - ft[0]) / 1000;
  return {
    prof, side, gpu, loadMs, wall, frames: d.length, fps: d.length / dur,
    p50: q(d, .5), p95: q(d, .95), p99: q(d, .99), worst: Math.max(...d),
    over33: d.filter(x => x > 33.4).length, over50: d.filter(x => x > 50).length,
    longN: lt.length, longMs: lt.reduce((a, b) => a + b, 0), errors,
  };
}

// a CPU profile -> self time per function@file:line, the biggest first
function topSelf(file, n = 25) {
  const p = JSON.parse(fs.readFileSync(file, "utf8")), byId = new Map(p.nodes.map(x => [x.id, x])), self = new Map();
  const dt = p.timeDeltas;
  for (let i = 0; i < p.samples.length; i++) {
    const nd = byId.get(p.samples[i]), cf = nd.callFrame;
    const key = `${cf.functionName || "(anon)"} ${cf.url.split("/").pop()}:${cf.lineNumber + 1}`;
    self.set(key, (self.get(key) || 0) + (dt[i] || 0) / 1000);
  }
  return [...self].sort((a, b) => b[1] - a[1]).slice(0, n).map(([k, v]) => `${v.toFixed(0).padStart(7)} ms  ${k}`).join("\n");
}
// a trace -> main-thread time by top-level event name
function traceSummary(file) {
  const ev = JSON.parse(fs.readFileSync(file, "utf8"));
  const main = ev.find(e => e.name === "thread_name" && e.args && e.args.name === "CrRendererMain");
  const tot = new Map();
  for (const e of ev) {
    if (!main || e.pid !== main.pid || e.tid !== main.tid || e.ph !== "X" || !e.dur) continue;
    tot.set(e.name, (tot.get(e.name) || 0) + e.dur / 1000);
  }
  return [...tot].sort((a, b) => b[1] - a[1]).slice(0, 18).map(([k, v]) => `${v.toFixed(0).padStart(7)} ms  ${k}`).join("\n");
}

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ["--autoplay-policy=no-user-gesture-required", "--enable-gpu-rasterization", "--ignore-gpu-blocklist"] });
  const rows = [];
  try {
    if (CPU_OUT || TRACE_OUT) {
      for (const prof of PROFILES) {
        const side = ONLY || "B";
        if (CPU_OUT) { const f = CPU_OUT.replace(/\.json$/, `_${prof}_${side}.json`); const r = await run(browser, prof, side, { cpu: f }); console.log(prof, side, "fps", r.fps.toFixed(1), "worst", r.worst.toFixed(0)); console.log(topSelf(f)); }
        if (TRACE_OUT) { const f = TRACE_OUT.replace(/\.json$/, `_${prof}_${side}.json`); const r = await run(browser, prof, side, { trace: f }); console.log(prof, side, "fps", r.fps.toFixed(1), "worst", r.worst.toFixed(0)); console.log(traceSummary(f)); }
      }
      return;
    }
    for (let i = 0; i < RUNS; i++) {
      for (const prof of PROFILES) {
        const order = ONLY ? [ONLY] : !BASE ? ["B"] : i % 2 ? ["B", "A"] : ["A", "B"];
        for (const side of order) {
          // the mock RGS (one Python process) refuses connections now and then on a busy machine: a run that lost
          // a request did not load what the round draws, so it is run again (up to 3 times) rather than counted
          let r, tries = 0;
          do { r = await run(browser, prof, side); tries++; } while (tries < 3 && r.errors.some(e => e.startsWith("failed ")));
          r.retries = tries - 1;
          rows.push(r);
          console.log(`run ${i + 1} ${prof.padEnd(7)} ${side}  fps ${r.fps.toFixed(1).padStart(5)}  p50 ${r.p50.toFixed(1).padStart(5)}  p95 ${r.p95.toFixed(1).padStart(5)}  p99 ${r.p99.toFixed(1).padStart(5)}  worst ${r.worst.toFixed(0).padStart(4)}  >33ms ${String(r.over33).padStart(3)}  >50ms ${String(r.over50).padStart(3)}  long ${r.longN}/${r.longMs.toFixed(0)}ms  round ${(r.wall / 1000).toFixed(1)}s  load ${(r.loadMs / 1000).toFixed(1)}s${r.retries ? "  (retried " + r.retries + ")" : ""}${r.errors.length ? "  ERR " + r.errors.length : ""}`);
          if (i === 0 && side === order[0] && prof === PROFILES[0]) console.log("  gpu:", r.gpu);
          if (r.errors.length) console.log("  errors:", [...new Set(r.errors)].slice(0, 5).join(" | "));
        }
      }
    }
    console.log("\nmedians");
    for (const prof of PROFILES) for (const side of ["A", "B"]) {
      const s = rows.filter(r => r.prof === prof && r.side === side);
      if (!s.length) continue;
      const m = k => med(s.map(r => r[k]));
      console.log(`${prof.padEnd(7)} ${side}  n=${s.length}  fps ${m("fps").toFixed(1)}  p50 ${m("p50").toFixed(1)}  p95 ${m("p95").toFixed(1)}  p99 ${m("p99").toFixed(1)}  worst ${m("worst").toFixed(0)}  >33ms ${m("over33")}  >50ms ${m("over50")}  long ${m("longMs").toFixed(0)}ms  round ${(m("wall") / 1000).toFixed(1)}s  load ${(m("loadMs") / 1000).toFixed(1)}s`);
    }
    const out = arg("json", "");
    if (out) fs.writeFileSync(out, JSON.stringify(rows, null, 1));
  } finally { await browser.close(); }
})().catch(e => { console.log("FAIL", e.stack || e.message); process.exit(1); });
