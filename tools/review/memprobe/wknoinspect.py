"""A replayed round in Playwright's WebKit build run BY ITSELF - no automation, no Web Inspector recording the page
(iOS review 4, 2026-11-17): the binary is started headless on the mock's /mock/drive.html, which plays the replay in an
iframe (as Engine's casino page holds the game) and posts its progress to the mock; this script only reads the
WebContent / GPU processes' private bytes and that progress. Tells what WebKit itself keeps apart from what the
inspector Playwright attaches keeps (it buffers network bodies, among other things).
usage: wknoinspect.py OUTJSON --base URL --mode bonus --event 62596 [--rounds 3] [--skip] [--extra "&mobile=1"]
       [--w 390 --h 844] [--webkit DIR (the folder holding Playwright.exe)] [--init JS]
"""
import json, os, subprocess, sys, tempfile, time, shutil
import urllib.parse, urllib.request
import psutil

a = sys.argv[1:]
out = a[0]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base = opt("--base", "http://localhost:8781")
mode, event = opt("--mode", "bonus"), opt("--event", "62596")
rounds, skip = int(opt("--rounds", 1)), "--skip" in a
extra = opt("--extra", "&mobile=1&mobart=1")
w, h = opt("--w", "390"), opt("--h", "844")
wk = opt("--webkit", os.environ.get("PW_WEBKIT_DIR", ""))
game = f"replay=true&game=test&version=1&mode={mode}&event={event}&amount=1000000&rgs_url={base}{extra}"
url = f"{base}/mock/drive.html?rounds={rounds}&skip={'1' if skip else '0'}&w={w}&h={h}&game={urllib.parse.quote(game)}"
if "--init" in a:   # JS run in the game once its replay is ready (an ablation)
    url += "&init=" + urllib.parse.quote(opt("--init", ""))
logs = lambda: json.loads(urllib.request.urlopen(base + "/mock/log").read())
n0 = len(logs())
prof = tempfile.mkdtemp(prefix="wkni")
p = subprocess.Popen([os.path.join(wk, "Playwright.exe"), "--headless", f"--user-data-dir={prof}", url])
root = psutil.Process(p.pid)
samples, t0, done = [], time.time(), False
try:
    while time.time() - t0 < 1800:
        row = {"t": round(time.time() - t0, 1)}
        try:
            for c in root.children(recursive=True):
                n = c.name().lower()
                k = "web" if "webprocess" in n else "gpu" if "gpuprocess" in n else None
                if k:
                    row[k] = round(row.get(k, 0) + c.memory_info().private / 1e6, 1)
        except Exception:
            pass
        ev = logs()[n0:]
        row["spin"] = max([e.get("spins", 0) for e in ev if "spins" in e] or [0])
        samples.append(row)
        if any(e.get("ev") == "done" for e in ev):
            done = True
            time.sleep(10)
            break
        time.sleep(1)
    ev = logs()[n0:]
    last = samples[-1] if samples else {}
finally:
    p.kill()
    shutil.rmtree(prof, ignore_errors=True)
by = {}
for s in samples:
    by.setdefault(s["spin"], []).append(s.get("web", 0))
med = lambda v: sorted(v)[len(v) // 2]
res = {"mode": mode, "event": event, "rounds": rounds, "skip": skip, "done": done, "events": [e for e in ev if e.get("ev") != "spin"],
       "peak_web": max((s.get("web", 0) for s in samples), default=0), "per_spin": {k: med(v) for k, v in sorted(by.items())}, "series": samples}
json.dump(res, open(out, "w"), indent=1)
print("done", done, "peak web", res["peak_web"], "errors", [e for e in ev if e.get("ev") in ("error", "rejection")][:5])
print("per spin web median:", " ".join(f"{k}:{v:.0f}" for k, v in res["per_spin"].items()))
