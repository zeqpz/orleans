"""50 live rounds on a phone profile (iOS crash review 2, 2026-11-16): the biggest tumble chains and cork storms forced
in (memlib.FORCE rewrites the round's events with a replay book), natural spins between them; most skipped (a skipped
spin still flies its corks and pops its tiles), every 5th played out. Per round: ok, ms, and the peak of live
canvases / canvas MB / WebGL contexts (lost) / the GFX safety net's counters, sampled every 200 ms in the page.
At the end: console errors, failed rounds, and the shown balance against the RGS's after the natural spins.
usage: soak.py OUTJSON [--base URL] [--rounds 50] [--ua ios|crios] [--throttle 4] [--w 390 --h 844]
"""
import json, os, random, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, CRIOS_UA, FORCE, game_url, enter_game, MOCK

a = sys.argv[1:]
out = a[0]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base = opt("--base", MOCK)
N = int(opt("--rounds", 50))
thr = float(opt("--throttle", 4))
ua = CRIOS_UA if opt("--ua", "ios") == "crios" else IPHONE_UA
w, h = int(opt("--w", 390)), int(opt("--h", 844))
BIG = [("base", 117426), ("corkstorm", 43029), ("base", 95017), ("base", 25750), ("corkstorm", 82647), ("base", 48006),
       ("corkstorm", 2), ("base", 107153), ("base", 844)]
SAMPLER = """(() => { clearInterval(window.__sm); window.__pk = {};
  window.__sm = setInterval(() => { const pk = window.__pk; const cv = [...document.querySelectorAll('canvas')]; let px = 0; for (const c of cv) px += c.width * c.height;
    const q = __mem.quick(); const v = { n: cv.length, mb: px * 4 / 1e6, all: q.c2d / 1e6, gl: q.ngl, lost: q.nlost,
      fails: (window.GFX || {}).fails || 0, glost: (window.GFX || {}).lost || 0, fx: FXS.parts.length };
    for (const k in v) pk[k] = Math.max(pk[k] || 0, v[k]); }, 200); })()"""
ROUND = """(async (skip) => {
  const t0 = performance.now();
  const skipper = setInterval(() => { if (skip && !state.noSkip) state.skip = true;
    for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s); if (e && e.getBoundingClientRect().width > 0) e.click(); } }, skip ? 300 : 2500);
  let ok, err = null;
  try { ok = await playRound('base'); } catch (e) { ok = false; err = String(e && e.stack || e); }
  clearInterval(skipper);
  return JSON.stringify({ ok, err, ms: Math.round(performance.now() - t0), pk: window.__pk });
})(%s)"""
rows, fails = [], 0
b = Browser(w, h, 3, ua=ua, mobile=True)
try:
    b.ws.call("Page.addScriptToEvaluateOnNewDocument", source=FORCE)
    b.open(game_url(base), 2)
    enter_game(b)
    time.sleep(3)
    b.ws.call("Emulation.setCPUThrottlingRate", rate=thr)
    rng = random.Random(7)
    natural = 0
    for i in range(1, N + 1):
        forced = None
        if i % 3 != 0:   # two of every three rounds a big book, the third a natural spin
            forced = BIG[(i // 3 * 2 + (i % 3) - 1) % len(BIG)]
            b.js(f"__force.push([{json.dumps(forced[0])}, {forced[1]}])")
        else:
            natural += 1
        b.js(SAMPLER)
        r = json.loads(b.js(ROUND % ("false" if i % 5 == 0 else "true")))
        r.update({"i": i, "forced": forced})
        r["pk"] = {k: round(v, 1) for k, v in (r.get("pk") or {}).items()}
        if r["ok"] is not True:
            fails += 1
        rows.append(r)
        print(json.dumps(r)[:400], flush=True)
        time.sleep(.3)
    b.js("clearInterval(window.__sm)")
    b.ws.call("Emulation.setCPUThrottlingRate", rate=1)
    time.sleep(1)
    bal = json.loads(b.js("JSON.stringify({ shown: document.getElementById('balance').textContent, state: state.balance, rgs: RGS.state.balance })"))
    con = b.console()
    pk = {}
    for r in rows:
        for k, v in (r.get("pk") or {}).items():
            pk[k] = max(pk.get(k, 0), v)
    res = {"rounds": N, "fails": fails, "peak": pk, "balance": bal, "console": con[:30], "rows": rows}
    print("fails", fails, "peak", pk, "balance", bal)
    print("console", con[:8])
finally:
    try:
        b.ws.call("Emulation.setCPUThrottlingRate", rate=1)
    except Exception:
        pass
    b.close()
    json.dump(locals().get("res", {"rows": rows}), open(out, "w"), indent=1)
