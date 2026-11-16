"""Playwright WebKit (iPhone 12): the WebContent + GPU process memory through the live boot stages of a build
(load, features screen, board, one natural spin, after), peak per stage (review 3, 2026-11-16). Same throwaway venv
as wkprobe.py.  usage: wkstage.py BASE_URL [EXTRA_QUERY] [--land]"""
import sys, time, threading, json, psutil, random
import os
from playwright.sync_api import sync_playwright
base = sys.argv[1]; extra = sys.argv[2] if len(sys.argv) > 2 else ""; land = "--land" in sys.argv
def kind(p):
    try: n = p.name().lower()
    except Exception: return None
    return "web" if "webprocess" in n else "gpu" if "gpuprocess" in n else None
with sync_playwright() as pw:
    br = pw.webkit.launch()
    root = max((p for p in psutil.process_iter(["name", "create_time"]) if (p.info["name"] or "").lower() == "playwright.exe"), key=lambda p: p.info["create_time"])
    ctx = br.new_context(**pw.devices["iPhone 12 landscape" if land else "iPhone 12"]); pg = ctx.new_page()
    log = []; pg.on("console", lambda m: log.append(m.type + ": " + m.text[:200]) if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: log.append("pageerror: " + str(e)[:200]))
    stage = ["blank"]; peaks = {}; stop = [False]
    def sampler():
        while not stop[0]:
            row = {}
            try:
                for c in root.children(recursive=True):
                    k = kind(c)
                    if k: row[k] = row.get(k, 0) + c.memory_info().private / 1e6
            except Exception: pass
            p = peaks.setdefault(stage[0], {"web": 0, "gpu": 0, "sum": 0})
            for k in ("web", "gpu"): p[k] = max(p[k], row.get(k, 0))
            p["sum"] = max(p["sum"], row.get("web", 0) + row.get("gpu", 0))
            time.sleep(.1)
    th = threading.Thread(target=sampler, daemon=True); th.start()
    time.sleep(1.5)
    stage[0] = "load"
    pg.goto(f"{base}/?sessionID=wk{random.randint(1000,9999)}&rgs_url={base}{extra}")
    t0 = time.time()
    while time.time() - t0 < 120:
        if pg.evaluate("(() => { const i = document.getElementById('intro'); const f = document.querySelector('.fhit'); return (!i || i.classList.contains('gone')) && !!(f && f.getBoundingClientRect().width > 0); })()"): break
        time.sleep(.3)
    stage[0] = "features"; time.sleep(3)
    r = pg.evaluate("JSON.stringify(document.querySelector('.fhit').getBoundingClientRect())"); r = json.loads(r)
    pg.touchscreen.tap(r["x"] + r["width"] / 2, r["y"] + r["height"] / 2)
    stage[0] = "board"; time.sleep(6)
    stage[0] = "spin"
    pg.evaluate("window.__d=false; playRound('base').then(()=>window.__d=true,()=>window.__d=true); 1")
    t0 = time.time()
    while time.time() - t0 < 90 and not pg.evaluate("window.__d"): time.sleep(.3)
    stage[0] = "after"; time.sleep(8)
    stop[0] = True; th.join()
    print(extra or "(default)", json.dumps({k: {kk: round(vv) for kk, vv in v.items()} for k, v in peaks.items()}), "console", log[:4])
    br.close()
