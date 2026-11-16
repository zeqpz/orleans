"""Trace one forced round (renderer main thread): time per event type, the biggest Layout/RecalcStyle/Paint,
and which JS function forced layout/style (stack of the forcing call).
usage: trace.py OUTJSON --base URL --ev 94 [--throttle 4]
"""
import base64, collections, json, sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import IPHONE_UA, Browser, FORCE, game_url, enter_game, MOCK

a = sys.argv[1:]
out = a[0]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base = opt("--base", MOCK); ev = int(opt("--ev", 94)); thr = float(opt("--throttle", 4))
CLICKER = """(() => { clearInterval(window.__clk); const seen = {};
  window.__clk = setInterval(() => { for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s);
    if (e && e.getBoundingClientRect().width > 0) { seen[s] = (seen[s] || 0) + 1; if (seen[s] > 8) { e.click(); seen[s] = 0; } } } }, 400); })()"""
b = Browser(390, 844, 3, ua=IPHONE_UA, mobile=True)
try:
    b.ws.call("Page.addScriptToEvaluateOnNewDocument", source=FORCE)
    b.open(game_url(base), 2); enter_game(b); time.sleep(3)
    if opt("--eval", ""): print("eval", b.js(opt("--eval", "")))
    b.ws.call("Emulation.setCPUThrottlingRate", rate=thr)
    b.js(f"__force.push(['base', {ev}])"); b.js(CLICKER)
    b.ws.call("Tracing.start", transferMode="ReturnAsStream", traceConfig={
        "recordMode": "recordContinuously",
        "includedCategories": ["devtools.timeline", "disabled-by-default-devtools.timeline", "disabled-by-default-devtools.timeline.stack", "blink", "v8.execute"],
        "excludedCategories": ["*"]})
    b.js("window.__done=false; playRound('base').then(()=>window.__done=true); 1", await_=False)
    t0 = time.time()
    while time.time() - t0 < 120 and not b.js("window.__done"):
        time.sleep(.5)
    b.ws.call("Tracing.end")
    e = b.wait_event("Tracing.tracingComplete", 120)
    h = e["params"]["stream"]; buf = []
    while True:
        d = b.ws.call("IO.read", handle=h, size=1 << 22)
        buf.append(base64.b64decode(d["data"]) if d.get("base64Encoded") else d["data"].encode())
        if d.get("eof"): break
    b.ws.call("Emulation.setCPUThrottlingRate", rate=1)
finally:
    b.close()
tr = json.loads(b"".join(buf))
evs = tr["traceEvents"] if isinstance(tr, dict) else tr
# the renderer main thread: the one with the most RunTask / FunctionCall
main = collections.Counter((x["pid"], x["tid"]) for x in evs if x.get("name") in ("FunctionCall", "UpdateLayoutTree", "Layout"))
pid, tid = main.most_common(1)[0][0]
tot = collections.Counter(); cnt = collections.Counter(); forced = collections.Counter(); big = []
for x in evs:
    if x.get("pid") != pid or x.get("tid") != tid or x.get("ph") != "X":
        continue
    n, dur = x["name"], x.get("dur", 0) / 1000
    if n in ("UpdateLayoutTree", "Layout", "Paint", "PrePaint", "Layerize", "UpdateLayer", "PaintImage", "Decode Image", "Commit",
             "FunctionCall", "TimerFire", "FireAnimationFrame", "EventDispatch", "HitTest", "ScheduleStyleRecalculation", "ParseHTML",
             "ImageDecodeTask", "GPUTask", "CompositeLayers", "UpdateLayerTree", "IntersectionObserverController::computeIntersections",
             "Animation", "v8.run", "RunMicrotasks", "Document::updateStyle", "LocalFrameView::RunPrePaintLifecyclePhase"):
        tot[n] += dur; cnt[n] += 1
    if n in ("UpdateLayoutTree", "Layout"):
        st = (x.get("args", {}).get("beginData", {}) or {}).get("stackTrace") or (x.get("args", {}).get("data", {}) or {}).get("stackTrace")
        if st:
            f = st[0]
            forced[f'{n} <- {f.get("functionName") or "(anon)"}:{f.get("lineNumber", 0) + 1}'] += dur
        big.append((round(dur, 1), n, (x.get("args", {}).get("beginData", {}) or {}).get("frame", ""), x.get("args", {}).get("elementCount") or (x.get("args", {}).get("beginData", {}) or {}).get("dirtyObjects")))
res = {"tot": {k: round(v, 1) for k, v in tot.most_common()}, "cnt": dict(cnt), "forced": [(k, round(v, 1)) for k, v in forced.most_common(25)], "big": sorted(big, key=lambda x: -x[0])[:15]}
json.dump(res, open(out, "w"), indent=1)
print("time per event (ms):", json.dumps(res["tot"]))
print("count:", json.dumps({k: cnt[k] for k in res["tot"]}))
print("forced by JS:")
for k, v in res["forced"]:
    print("   ", v, k)
print("biggest:", res["big"][:10])
