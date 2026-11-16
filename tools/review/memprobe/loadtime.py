"""How long the loading screen takes on a real connection (2026-11-16: "the loading screen ... takes forever").
A cold load (fresh profile) in headless Chrome over a throttled link: the loading bar's percentage over time, when
the features screen comes up, and the megabytes fetched by then by kind.
usage: loadtime.py [--mbps 20] [--rtt 60] [--desktop] [--extra "&x=1"] [--page index.html]"""
import json, sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, game_url, INTRO_GONE
DESK_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
a = sys.argv[1:]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
mbps, rtt, desk = float(opt("--mbps", 20)), float(opt("--rtt", 60)), "--desktop" in a
b = Browser(1920 if desk else 390, 1080 if desk else 844, 1 if desk else 3, ua=(DESK_UA if desk else IPHONE_UA), mobile=not desk)
try:
    b.ws.call("Network.enable")
    b.ws.call("Network.setCacheDisabled", cacheDisabled=True)
    b.ws.call("Network.emulateNetworkConditions", offline=False, latency=rtt, downloadThroughput=mbps * 125000, uploadThroughput=mbps * 31250)
    t0 = time.time()
    b.open(game_url(extra=opt("--extra", "")).replace("/?", "/" + opt("--page", "index.html") + "?"), .2)
    trace, last = [], None
    while time.time() - t0 < 400:
        r = json.loads(b.js("JSON.stringify([(document.getElementById('introFill') || {style: {}}).style.width, !!(document.body && (" + INTRO_GONE + "))])", await_=False) or '["",false]')
        if r[0] != last:
            trace.append((round(time.time() - t0, 1), r[0])); last = r[0]
        if r[1]:
            break
        time.sleep(.25)
    secs = round(time.time() - t0, 1)
    kinds = json.loads(b.js("""JSON.stringify((() => { const o = {}; for (const r of performance.getEntriesByType('resource')) {
      const m = r.name.match(/assets\/(sym\/d\d+\/[A-Za-z0-9]+_([a-z]+)|[^/?]+)/); let k = m ? (m[2] ? 'sym_' + m[2] : (m[1].includes('.') ? m[1].split('.').pop() : m[1])) : 'other';
      o[k] = o[k] || [0, 0]; o[k][0]++; o[k][1] = +(o[k][1] + (r.encodedBodySize || 0) / 1e6).toFixed(2); } return o; })())""", await_=False))
    print(json.dumps({"mbps": mbps, "desktop": desk, "features_at_s": secs, "bar": trace[::max(1, len(trace) // 14)] + trace[-3:], "MB": round(sum(v[1] for v in kinds.values()), 1), "kinds": kinds}))
finally:
    b.close()
