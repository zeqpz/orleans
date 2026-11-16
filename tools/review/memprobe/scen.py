"""Peak memory per scenario: boot, base spin with pops, big win, bonus.
usage: scen.py OUTJSON [--base URL] [--w 390 --h 844 --dpr 3] [--desktop] [--extra "&x=1"] [--ua none]
"""
import json, sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import procmem, IPHONE_UA, Browser, FORCE, game_url, enter_game, pics_bytes, MOCK, layer_list

a = sys.argv[1:]
out = a[0]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base = opt("--base", MOCK)
w, h, dpr = int(opt("--w", 390)), int(opt("--h", 844)), float(opt("--dpr", 3))
desktop = "--desktop" in a
extra = opt("--extra", "")
ua = None if desktop or opt("--ua", "") == "none" else IPHONE_UA
MB = 1e6

b = Browser(w, h, dpr, ua=ua, mobile=not desktop)
res = {"profile": f"{w}x{h}@{dpr}{' desktop' if desktop else ''}{' iPhoneUA' if ua else ''}", "base": base, "extra": extra, "scen": {}}


def quick():
    q = json.loads(b.js("JSON.stringify(__mem.quick())"))
    return {k: (round(v / MB, 1) if k in ("c2d", "cgl", "tex", "bmp", "aud", "heap", "total") else v) for k, v in q.items()}


def look(detail=True):
    s = {"quick": quick(), "proc": procmem(b)}
    tot, vis, rows = pics_bytes(json.loads(b.js("JSON.stringify(__mem.pics())")))
    s["pics_mb"] = round(tot / MB, 1); s["pics_visible_mb"] = round(vis / MB, 1)
    s["pics_top"] = [(round(x / MB, 1), u, wh) for x, u, wh in rows[:30]]
    L = layer_list(b)
    s["layers_paint_mb"] = round(sum(x["mb"] for x in L if not x["name"].startswith("canvas")), 1)
    s["layers_top"] = L[:14]
    s["dom"] = b.ws.call("Memory.getDOMCounters")
    if detail:
        s["detail"] = json.loads(b.js("JSON.stringify(__mem.detail())"))
    q = s["quick"]
    s["model"] = round(q["heap"] + q["c2d"] + q["cgl"] + q["tex"] + q["bmp"] + q["aud"] + s["pics_visible_mb"] + s["layers_paint_mb"], 1)
    return s


def snapshot(tag):
    b.gc(); time.sleep(.3)
    s = look()
    res["scen"][tag] = s
    q = s["quick"]
    print(f"{tag:10s} model {s['model']:6.1f} | heap {q['heap']} c2d {q['c2d']}({q['n2d']}) gl {q['cgl']}({q['ngl']}) tex {q['tex']} bmp {q['bmp']} aud {q['aud']}({q['naud']}) pics {s['pics_visible_mb']} layers {s['layers_paint_mb']} | proc {s['proc']}", flush=True)


CLICKER = """(() => { clearInterval(window.__clk); const seen = {};
  window.__clk = setInterval(() => { for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s);
    if (e && e.getBoundingClientRect().width > 0) { seen[s] = (seen[s] || 0) + 1; if (seen[s] > 8) { e.click(); seen[s] = 0; } } } }, 400); })()"""


def round_peak(tag, mode, ev, every=3.0, max_s=170):
    b.js(f"__force.push([{json.dumps(mode)}, {ev}])")
    b.js("__mem.startSampler(250)")
    b.js(CLICKER)
    time.sleep(.4)
    b.js("window.__done = false; playRound('base').then(() => window.__done = true, () => window.__done = true); 1", await_=False)
    t0 = time.time(); best = None
    while time.time() - t0 < max_s:
        time.sleep(every)
        if b.js("window.__done"):
            break
        s = look(detail=True)
        if not best or s["model"] > best["model"]:
            best = s; best["at_s"] = round(time.time() - t0, 1)
    b.js("__mem.stopSampler(); clearInterval(window.__clk)")
    pk = json.loads(b.js("JSON.stringify(__mem.peak)"))
    pk = {k: (round(v / MB, 1) if k in ("c2d", "cgl", "tex", "bmp", "aud", "heap", "total") else v) for k, v in pk.items() if k != "t"}
    best = best or look(detail=False)
    # the peak as the sum of each part's own peak (sampled every 250 ms) plus the pictures/layers at the heaviest look
    model_peak = round(pk.get("heap", 0) + pk.get("c2d", 0) + pk.get("cgl", 0) + pk.get("tex", 0) + pk.get("bmp", 0) + pk.get("aud", 0)
                       + best["pics_visible_mb"] + best["layers_paint_mb"], 1)
    res["scen"][tag] = {"page_peak": pk, "best": best, "model_peak": model_peak, "secs": round(time.time() - t0, 1)}
    print(f"{tag:10s} PEAK model {model_peak:6.1f} | heap {pk.get('heap')} c2d {pk.get('c2d')}({pk.get('n2d')}) gl {pk.get('cgl')} tex {pk.get('tex')} bmp {pk.get('bmp')} aud {pk.get('aud')} pics {best['pics_visible_mb']} layers {best['layers_paint_mb']} | proc@best {best['proc']} ({res['scen'][tag]['secs']} s)", flush=True)
    time.sleep(2)


try:
    b.ws.call("Page.addScriptToEvaluateOnNewDocument", source=FORCE)
    b.open(game_url(base, extra), 2)
    # the loading screen (every picture fetching) and the feature screen, before the first touch
    time.sleep(3); snapshot("loading")
    from memlib import INTRO_GONE, FEATURES_UP
    b.wait(f"({INTRO_GONE}) && {FEATURES_UP}", 150); time.sleep(1); snapshot("features")
    enter_game(b)
    time.sleep(4)
    snapshot("boot")
    round_peak("pops_844", "base", 844)
    if "--quick" not in a:
        round_peak("bigwin_94", "base", 94)
        round_peak("bonus_8", "base", 8)
    time.sleep(2)
    snapshot("after")
    res["console"] = b.console()
    b.shot(out.replace(".json", ".png"))
    print("console:", res["console"][:6])
finally:
    b.close()
    json.dump(res, open(out, "w"), indent=1)
