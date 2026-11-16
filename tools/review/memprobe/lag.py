"""Frame times per scenario at 390x844 @3 with CPU throttling, plus a CPU profile's top self-time functions.
usage: lag.py OUTJSON [--base URL] [--throttle 4] [--profile] [--runs 1] [--only pops,bigwin,...]
"""
import json, sys, time, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import IPHONE_UA, Browser, FORCE, game_url, enter_game, MOCK

a = sys.argv[1:]
out = a[0]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base = opt("--base", MOCK)
thr = float(opt("--throttle", 4))
prof = "--profile" in a
only = opt("--only", "")
SCEN = [("spin_0", "base", 0), ("pops_844", "base", 844), ("cork_1", "base", 1), ("bigwin_94", "base", 94), ("bonus_8", "base", 8)]
if only:
    SCEN = [s for s in SCEN if s[0].split("_")[0] in only.split(",")]

CLICKER = """(() => { clearInterval(window.__clk); const seen = {};
  window.__clk = setInterval(() => { for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s);
    if (e && e.getBoundingClientRect().width > 0) { seen[s] = (seen[s] || 0) + 1; if (seen[s] > 8) { e.click(); seen[s] = 0; } } } }, 400); })()"""

res = {"throttle": thr, "base": base, "scen": {}}
b = Browser(390, 844, 3, ua=IPHONE_UA, mobile=True)
try:
    b.ws.call("Page.addScriptToEvaluateOnNewDocument", source=FORCE)
    b.open(game_url(base), 2)
    enter_game(b)
    time.sleep(3)
    if opt("--eval", ""):
        print("eval", b.js(opt("--eval", "")))
    # idle board
    b.ws.call("Emulation.setCPUThrottlingRate", rate=thr)
    b.js("__mem.startFrames()"); time.sleep(5)
    res["scen"]["idle"] = json.loads(b.js("JSON.stringify(__mem.stopFrames())"))
    print("idle", res["scen"]["idle"], flush=True)
    for tag, mode, ev in SCEN:
        b.js(f"__force.push([{json.dumps(mode)}, {ev}])")
        b.js(CLICKER)
        if prof:
            b.ws.call("Profiler.enable"); b.ws.call("Profiler.setSamplingInterval", interval=200); b.ws.call("Profiler.start")
        b.js("__mem.startFrames(); window.__done = false; playRound('base').then(() => window.__done = true, () => window.__done = true); 1", await_=False)
        t0 = time.time()
        while time.time() - t0 < 200 and not b.js("window.__done"):
            time.sleep(.5)
        r = json.loads(b.js("JSON.stringify(__mem.stopFrames())"))
        r["secs"] = round(time.time() - t0, 1)
        if prof:
            p = b.ws.call("Profiler.stop")["profile"]
            b.ws.call("Profiler.disable")
            nodes = {n["id"]: n for n in p["nodes"]}
            dts = p.get("timeDeltas", [])
            self_t = collections.Counter()
            for sid, dt in zip(p["samples"], dts):
                n = nodes[sid]["callFrame"]
                key = f'{n["functionName"] or "(anon)"} {n["url"].split("/")[-1].split("?")[0]}:{n["lineNumber"] + 1}'
                self_t[key] += dt / 1000
            r["top"] = [(k, round(v, 1)) for k, v in self_t.most_common(25)]
        b.js("clearInterval(window.__clk)")
        res["scen"][tag] = r
        print(tag, {k: v for k, v in r.items() if k != "top"}, flush=True)
        if prof:
            for k, v in r["top"][:14]:
                print("     ", v, k)
        time.sleep(2)
    b.ws.call("Emulation.setCPUThrottlingRate", rate=1)
    res["console"] = b.console()
    print("console:", res["console"][:5])
finally:
    b.close()
    json.dump(res, open(out, "w"), indent=1)
