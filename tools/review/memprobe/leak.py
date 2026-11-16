"""100+ live base spins (fast-forwarded), memory every N spins: must plateau.
usage: leak.py OUTJSON [--base URL] [--spins 100] [--every 20] [--noskip]
"""
import json, sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import IPHONE_UA, Browser, game_url, enter_game, MOCK, procmem

a = sys.argv[1:]
out = a[0]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base = opt("--base", MOCK)
N, EVERY = int(opt("--spins", 100)), int(opt("--every", 20))
skip = "--noskip" not in a
MB = 1e6
ROUND = """(async () => {
  const skipper = setInterval(() => { if (%s && !state.noSkip) state.skip = true;
    for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s); if (e) e.click(); } }, 300);
  let ok; try { ok = await playRound('base'); } catch (e) { ok = String(e); }
  clearInterval(skipper);
  return ok;
})()""" % ("true" if skip else "false")
rows = []
b = Browser(390, 844, 3, ua=IPHONE_UA, mobile=True)
try:
    b.open(game_url(base), 2)
    enter_game(b)
    time.sleep(3)

    def sample(i):
        b.gc(); time.sleep(.4)
        q = json.loads(b.js("JSON.stringify(__mem.quick())"))
        dom = b.ws.call("Memory.getDOMCounters")
        anims = b.js("document.getAnimations().length")
        r = {"spin": i, **{k: round(v / MB, 1) if k in ("c2d", "cgl", "tex", "bmp", "aud", "heap") else v for k, v in q.items()},
             "nodes": dom["nodes"], "listeners": dom["jsEventListeners"], "anims": anims, "proc": procmem(b)}
        rows.append(r)
        print(r, flush=True)
    sample(0)
    fails = 0
    for i in range(1, N + 1):
        time.sleep(.3)
        ok = b.js(ROUND)
        if ok is not True:
            fails += 1
        if i % EVERY == 0:
            sample(i)
    # bought rounds too, and the shown balance must be the RGS's after each
    for mode in ("bonus", "extremebonus"):
        time.sleep(.4)
        ok = b.js(ROUND.replace("playRound('base')", "playRound('%s')" % mode))
        bal = b.js("JSON.stringify([state.balance, RGS.state.balance, state.playing])")
        print(mode, "ok", ok, "balance shown/rgs/playing", bal, flush=True)
        if ok is not True:
            fails += 1
    sample(N + 2)
    res = {"rows": rows, "fails": fails, "console": b.console()[:20]}
    print("fails", fails, "console", res["console"][:5])
finally:
    b.close()
    json.dump({"rows": rows}, open(out, "w"), indent=1)
