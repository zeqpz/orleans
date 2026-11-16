"""Peak graphics memory of one replayed round, as WebKit on an iPhone would hold it (iOS crash review 2, 2026-11-16).

Plays a book in replay mode (?replay=true ... &event=<id>) in headless Chrome with iPhone emulation and samples, every
~0.6 s while it plays: live canvases (count, pixels), WebGL contexts (and lost ones), and the composited layer tree.
Layers are summed two ways:
  chrome  - layout size x the transforms above it (squared) x DPR^2 x 4: what Chrome rasterises
  webkit  - layout size x DPR^2 x 4: what WebKit/CoreAnimation allocates. WebKit does NOT scale a layer's backing
            store down for a scaled-down ancestor (GraphicsLayerCA::updateRootRelativeScale is off except for
            LBSE SVG), and #app is laid out at window/fit and scaled by --fit (~0.38 on a portrait iPhone), so every
            layer inside it costs ~1/fit^2 (~7x) what Chrome shows. Layers over 1280 px a side are tiled on iOS and
            capped at 156 MB each (cMaxScaledTiledLayerMemorySize), as WebKit does.
Canvas layers are not counted as layers (their pixels are the canvas's, counted once).
  swFilter - WebKit's software filters: a filter list CoreAnimation cannot take (a drop-shadow that is not last) is
            painted into buffers at layout size x DPR^2 (+60 px of shadow reach), a source and two per drop-shadow.
  wkLayers - the layers WebKit is certain to make (running transform/opacity/filter animations, 3D transforms,
            will-change, the log frame over the canvases), each at its layout box x DPR^2 x 4: a lower bound.
webkitTotal = every live 2D canvas (in the page or not) + wkLayers + swFilter. (The Chrome-tree columns are kept for
reference; Chrome squashes layers WebKit does not, so they are not used in the total.)

usage: iosprobe.py OUTJSON --mode corkstorm --event 43029 [--base URL] [--w 390 --h 844 --dpr 3] [--ua ios|crios]
                   [--throttle 4] [--shots DIR/prefix] [--extra "&lite=1"]
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, CRIOS_UA, MOCK
a = sys.argv[1:]
out = a[0]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base = opt("--base", MOCK)
mode, event = opt("--mode", "corkstorm"), int(opt("--event", 43029))
w, h, dpr = int(opt("--w", 390)), int(opt("--h", 844)), float(opt("--dpr", 3))
ua = CRIOS_UA if opt("--ua", "ios") == "crios" else IPHONE_UA
thr = float(opt("--throttle", 1))
shots = opt("--shots", "")
extra = opt("--extra", "")
MB = 1e6
TILE_CAP = 156 * 1024 * 1024

CENSUS = """JSON.stringify((() => {
  const q = __mem.quick();
  const cv = [...document.querySelectorAll('canvas')];
  let px = 0, big = 0; for (const c of cv) { px += c.width * c.height; big = Math.max(big, c.width * c.height); }
  const fit = parseFloat(document.documentElement.style.getPropertyValue('--fit')) || 1;
  let cork = 0, pops = 0;
  try { cork = FXS.parts.filter(p => p.kind === 'cork').length; } catch (e) {}
  try { pops = bursts.filter(b => b.pieces).length; } catch (e) {}
  // WebKit's software filters: a filter list it cannot hand to CoreAnimation (a drop-shadow that is not the last entry)
  // is painted on the CPU/GPU into buffers at LAYOUT size x DPR (the #app scale is not applied), a source plus two
  // per drop-shadow, over the element and whatever overflows it (a symbol's canvas), plus the shadows' reach
  let swf = 0, swn = 0;
  for (const el of document.querySelectorAll('#app *')) {
    const f = getComputedStyle(el).filter;
    if (!f || f === 'none') continue;
    const ds = (f.match(/drop-shadow/g) || []).length;
    if (!ds || (ds === 1 && /drop-shadow\\((?:[^()]|\\([^()]*\\))*\\)\\s*$/.test(f))) continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    let w = r.width, h = r.height;
    for (const c of el.querySelectorAll('canvas')) { const b = c.getBoundingClientRect(); w = Math.max(w, b.width); h = Math.max(h, b.height); }
    swn++;
    swf += (w / fit + 60) * (h / fit + 60) * devicePixelRatio * devicePixelRatio * 4 * (1 + 2 * ds);
  }
  // The layers WebKit is certain to make (independent of Chrome's own layerisation and squashing): every element with
  // a running transform/opacity/filter animation, a 3D transform or will-change, and the log frame (it sits over the
  // symbols' canvases, so it is always overlap-composited); each backed at its LAYOUT box x DPR^2 x 4 (canvases are
  // their own pixels, counted as canvases). Overlap layers beyond the frame are not modelled: a lower bound.
  const lay = new Map();
  const want = el => { if (el && el.isConnected && el.tagName !== 'CANVAS' && !lay.has(el)) lay.set(el, 1); };
  for (const an of document.getAnimations()) {
    if (an.playState !== 'running') continue;
    const ef = an.effect, t = ef && ef.target;
    if (!t || !(t instanceof Element)) continue;
    let props = [];
    try { props = ef.getKeyframes().flatMap(k => Object.keys(k)); } catch (e) {}
    if (props.some(p => /^(transform|opacity|filter|translate|rotate|scale)$/.test(p))) want(t);
  }
  for (const el of document.querySelectorAll('.stage, .spincol, .winpop, [style*="will-change"], #fgwall img')) {
    const cs = getComputedStyle(el);
    if (/matrix3d|perspective/.test(cs.transform) || /transform|opacity/.test(cs.willChange)) want(el);
  }
  want(document.getElementById('paintframe'));
  let wkl = 0, wkn = 0;
  for (const el of lay.keys()) {
    if (getComputedStyle(el).display === 'none' || !el.getClientRects().length) continue;
    const w = el.offsetWidth || el.getBoundingClientRect().width / fit, h = el.offsetHeight || el.getBoundingClientRect().height / fit;
    if (!w || !h) continue;
    wkn++;
    wkl += Math.min(w * h * devicePixelRatio * devicePixelRatio * 4, 156 * 1048576);
  }
  return { n2d: q.n2d, c2d: q.c2d, ngl: q.ngl, nlost: q.nlost, cgl: q.cgl, heap: q.heap, domCanvases: cv.length, domPx: px, bigPx: big, swf, swn, wkl, wkn,
           fit, cork, pops, phase: (document.getElementById('replayPlay') || { dataset: {} }).dataset.phase || '',
           anims: document.getAnimations().length, lite: !!window.LITE, ios: !!window.IOS_WEBKIT };
})())"""

b = Browser(w, h, dpr, ua=ua, mobile=True)
names = {}


def node_name(bid):
    if bid in names:
        return names[bid]
    try:
        n = b.ws.call("DOM.describeNode", backendNodeId=bid)["node"]
        at = dict(zip(n.get("attributes", [])[::2], n.get("attributes", [])[1::2]))
        s = n["nodeName"].lower() + ("#" + at["id"] if at.get("id") else "") + ("." + at["class"].split(" ")[0] if at.get("class") else "")
    except Exception:
        s = "?"
    names[bid] = s
    return s


def layer_sum(ls):
    byid = {l["layerId"]: l for l in ls}
    import math

    def scale(l):
        s = 1.0
        while l:
            t = l.get("transform")
            if t:
                s *= math.sqrt(abs(t[0] * t[5] - t[1] * t[4])) or 1
            l = byid.get(l.get("parentLayerId"))
        return s
    chrome = webkit = 0.0
    n = nd = 0
    top = []
    for l in ls:
        n += 1
        if not l.get("drawsContent"):
            continue
        nm = node_name(l["backendNodeId"]) if l.get("backendNodeId") else ""
        if nm.startswith("canvas"):
            continue
        nd += 1
        k = scale(l)
        c = l["width"] * l["height"] * k * k * dpr * dpr * 4
        wk = min(l["width"] * l["height"] * dpr * dpr * 4, TILE_CAP)
        chrome += c; webkit += wk
        top.append((round(wk / MB, 1), round(c / MB, 1), l["width"], l["height"], nm[:50]))
    top.sort(reverse=True)
    return {"layers": n, "draw": nd, "chrome": chrome / MB, "webkit": webkit / MB, "top": top[:10]}


res = {"profile": f"{w}x{h}@{dpr} {opt('--ua', 'ios')} x{thr}", "base": base, "mode": mode, "event": event, "samples": []}
try:
    b.ws.call("DOM.enable")
    url = f"{base}/?replay=true&game=test&version=1&mode={mode}&event={event}&amount=1000000&rgs_url={base}{extra}"
    b.open(url, 2)
    if not b.wait("(document.getElementById('replayPlay') || {dataset: {}}).dataset.phase === 'ready'", 120):
        raise RuntimeError("replay never ready")
    time.sleep(2.5)
    b.ws.call("DOM.getDocument", depth=-1)
    b.ws.call("LayerTree.enable")
    if thr > 1:
        b.ws.call("Emulation.setCPUThrottlingRate", rate=thr)
    b.js("document.getElementById('replayPlay').click(); 1")
    t0 = time.time(); last_layers = None; took = set(); peak = {}
    while time.time() - t0 < 400:
        time.sleep(.6)
        c = json.loads(b.js(CENSUS))   # (any call drains the socket: the layer trees sent meanwhile land in ws.events)
        for m in b.ws.events:
            if m.get("method") == "LayerTree.layerTreeDidChange" and m["params"].get("layers"):
                last_layers = m["params"]["layers"]
        b.ws.events = [m for m in b.ws.events if m.get("method") != "LayerTree.layerTreeDidChange"]
        L =layer_sum(last_layers or [])
        s = {"t": round(time.time() - t0, 1), "canvasN": c["domCanvases"], "canvasMB": round(c["domPx"] * 4 / MB, 1),
             "allCanvasMB": round(c["c2d"] / MB, 1), "bigCanvasMB": round(c["bigPx"] * 4 / MB, 1), "gl": c["ngl"], "glLost": c["nlost"],
             "layers": L["layers"], "drawLayers": L["draw"], "layersChromeMB": round(L["chrome"], 1), "layersWebkitMB": round(L["webkit"], 1),
             "swFilterMB": round(c["swf"] / MB, 1), "swFilterN": c["swn"], "wkLayersMB": round(c["wkl"] / MB, 1), "wkLayersN": c["wkn"],
             "cork": c["cork"], "pops": c["pops"], "anims": c["anims"], "fit": c["fit"], "lite": c["lite"], "ios": c["ios"]}
        s["webkitTotalMB"] = round(s["allCanvasMB"] + s["wkLayersMB"] + s["swFilterMB"], 1)
        res["samples"].append(s)
        for k in ("canvasN", "canvasMB", "allCanvasMB", "bigCanvasMB", "gl", "glLost", "layers", "drawLayers", "layersChromeMB", "layersWebkitMB", "swFilterMB", "swFilterN", "wkLayersMB", "wkLayersN", "webkitTotalMB", "anims"):
            if s[k] > peak.get(k, -1):
                peak[k] = s[k]
                if k == "webkitTotalMB":
                    peak["webkitTop"] = L["top"]; peak["webkitAt"] = s["t"]
        if shots:
            if c["cork"] and "cork" not in took:
                took.add("cork"); b.shot(f"{shots}_cork.png")
            if c["pops"] and "pop" not in took:
                took.add("pop"); b.shot(f"{shots}_pop.png")
        if c["phase"] == "done":
            break
    res["peak"] = peak
    cp = [x for x in res["samples"] if x["cork"] or x["pops"]]
    res["peak_corkpop"] = {k: max(x[k] for x in cp) for k in ("webkitTotalMB", "wkLayersMB", "wkLayersN", "allCanvasMB", "canvasN", "gl", "swFilterMB")} if cp else {}
    res["secs"] = round(time.time() - t0, 1)
    res["console"] = b.console()
    print(json.dumps({k: v for k, v in peak.items() if k != "webkitTop"}), flush=True)
    print("cork/pop moments:", json.dumps(res["peak_corkpop"]), flush=True)
    for r in peak.get("webkitTop", [])[:8]:
        print("   ", r)
    print("secs", res["secs"], "console:", res["console"][:6])
finally:
    try:
        b.ws.call("Emulation.setCPUThrottlingRate", rate=1)
    except Exception:
        pass
    b.close()
    json.dump(res, open(out, "w"), indent=1)
