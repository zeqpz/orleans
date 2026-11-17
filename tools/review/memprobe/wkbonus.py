"""Bonus rounds in a real WebKit engine (Playwright WebKit for Windows, iPhone 12 profile, Safari UA): the WebContent and
GPU processes' private bytes every 100 ms, and every second, inside the page, counts of everything a free spin could make
and fail to let go (iOS review 4, 2026-11-17: "the game crashes during Bonus Mode ... persists after reloading"):
blob URLs, ImageBitmaps, workers, WebGL textures/buffers/framebuffers and their bytes, canvases and images made, DOM
nodes, running animations, live intervals, listeners, Audio elements, fetches - plus the free spin the round is on.

Two ways in:
  replay (default): the replay of --mode/--event, pressed --rounds times back to back in one page (PLAY AGAIN)
  --live: a session on the mock: the mock is told to deal --event in --mode (/mock/force), the round is bought with
          playRound(mode); with --reload N the page is reloaded after the N-th reveal and the round resumes from the
          RGS's open round (authenticate) and plays to its end-round.
Needs the throwaway venv with playwright + psutil + WebKit (see wkprobe.py).
usage: wkbonus.py OUTJSON --base URL --mode extremebonus --event 3111 [--extra "&symdemand=0"] [--rounds 1] [--live]
                   [--reload 6] [--crios] [--land] [--tail 15] [--init JS]
"""
import json, sys, threading, time, random
import psutil
from playwright.sync_api import sync_playwright

a = sys.argv[1:]
out = a[0]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base = opt("--base", "http://localhost:8781")
mode, event = opt("--mode", "extremebonus"), int(opt("--event", "3111"))
extra = opt("--extra", "")
rounds = int(opt("--rounds", 1))
live, reload_at = "--live" in a, int(opt("--reload", 0))
land, crios = "--land" in a, "--crios" in a
tail = float(opt("--tail", 15))
skip = "--skip" in a
gcpress = "--gc" in a
poll = float(opt("--poll", 1))   # seconds between the page reads (each page.evaluate costs WebKit's process a little under Playwright)
user_init = opt("--init", "")
CRIOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
         "CriOS/141.0.7390.96 Mobile/15E148 Safari/604.1")

INSTR = r"""
(() => {
  const C = window.__ct = { url: 0, urlRev: 0, bmp: 0, bmpClose: 0, wk: 0, wkTerm: 0, tex: 0, texDel: 0, texB: 0, buf: 0, bufDel: 0,
    fb: 0, fbDel: 0, cv: 0, img: 0, div: 0, aud: 0, iv: 0, ivClr: 0, ael: 0, rel: 0, anim: 0, fetch: 0, spin: 0, tumble: 0, ev: '' };
  const w = (o, k, f) => { const d = o && Object.getOwnPropertyDescriptor(o, k); if (d && typeof d.value === 'function') { const r = d.value; o[k] = function (...x) { return f.call(this, r, x); }; } };
  w(URL, 'createObjectURL', function (r, x) { C.url++; return r.apply(this, x); });
  w(URL, 'revokeObjectURL', function (r, x) { C.urlRev++; return r.apply(this, x); });
  w(window, 'createImageBitmap', function (r, x) { C.bmp++; return r.apply(this, x); });
  if (window.ImageBitmap) w(ImageBitmap.prototype, 'close', function (r, x) { C.bmpClose++; return r.apply(this, x); });
  if (window.Worker) { const W = window.Worker; window.Worker = function (...x) { C.wk++; return new W(...x); }; window.Worker.prototype = W.prototype;
    w(W.prototype, 'terminate', function (r, x) { C.wkTerm++; return r.apply(this, x); }); }
  // what is made and later collected (FinalizationRegistry): made - fin = still alive (or not yet collected)
  const FR = window.FinalizationRegistry ? new FinalizationRegistry(k => { C['fin_' + k] = (C['fin_' + k] || 0) + 1; }) : null;
  const reg = (o, k) => { if (FR && o && typeof o === 'object') { C['made_' + k] = (C['made_' + k] || 0) + 1; FR.register(o, k); } return o; };
  window.__reg = reg;
  w(Document.prototype, 'createElement', function (r, x) { const t = String(x[0]).toLowerCase(); if (t === 'canvas') C.cv++; else if (t === 'img') C.img++; else if (t === 'div') C.div++; else if (t === 'audio') C.aud++; return reg(r.apply(this, x), t === 'canvas' || t === 'img' ? t : 'el'); });
  w(CanvasRenderingContext2D.prototype, 'getImageData', function (r, x) { return reg(r.apply(this, x), 'imgdata'); });
  w(CanvasRenderingContext2D.prototype, 'createImageData', function (r, x) { return reg(r.apply(this, x), 'imgdata'); });
  if (window.Image) { const I = window.Image; window.Image = function (...x) { C.img++; return new I(...x); }; window.Image.prototype = I.prototype; }
  if (window.Audio) { const A = window.Audio; window.Audio = function (...x) { C.aud++; return new A(...x); }; window.Audio.prototype = A.prototype; }
  const live = new Set();
  w(window, 'setInterval', function (r, x) { const id = r.apply(this, x); live.add(id); C.iv = live.size; return id; });
  w(window, 'clearInterval', function (r, x) { live.delete(x[0]); C.iv = live.size; C.ivClr++; return r.apply(this, x); });
  w(EventTarget.prototype, 'addEventListener', function (r, x) { C.ael++; return r.apply(this, x); });
  w(EventTarget.prototype, 'removeEventListener', function (r, x) { C.rel++; return r.apply(this, x); });
  w(Element.prototype, 'animate', function (r, x) { C.anim++; return r.apply(this, x); });
  w(window, 'fetch', function (r, x) { C.fetch++; return r.apply(this, x); });
  const texBytes = new Map();
  for (const G of [window.WebGLRenderingContext, window.WebGL2RenderingContext]) {
    if (!G) continue; const P = G.prototype; const bound = new WeakMap();
    w(P, 'createTexture', function (r, x) { C.tex++; return r.apply(this, x); });
    w(P, 'deleteTexture', function (r, x) { C.texDel++; if (texBytes.has(x[0])) { C.texB -= texBytes.get(x[0]); texBytes.delete(x[0]); } return r.apply(this, x); });
    w(P, 'createBuffer', function (r, x) { C.buf++; return r.apply(this, x); });
    w(P, 'deleteBuffer', function (r, x) { C.bufDel++; return r.apply(this, x); });
    w(P, 'createFramebuffer', function (r, x) { C.fb++; return r.apply(this, x); });
    w(P, 'deleteFramebuffer', function (r, x) { C.fbDel++; return r.apply(this, x); });
    w(P, 'activeTexture', function (r, x) { this.__unit = x[0]; return r.apply(this, x); });
    w(P, 'bindTexture', function (r, x) { let m = bound.get(this); if (!m) bound.set(this, m = {}); m[this.__unit || 0] = x[1]; return r.apply(this, x); });
    const sz = (gl, wd, ht, lvl) => { if (lvl) return; const m = bound.get(gl), t = m && m[gl.__unit || 0]; if (!t) return;
      const b = wd * ht * 4; C.texB += b - (texBytes.get(t) || 0); texBytes.set(t, b); };
    w(P, 'texImage2D', function (r, x) { if (x.length >= 8) sz(this, x[3], x[4], x[1]); else { const s = x[5]; if (s) sz(this, s.width || s.videoWidth || 0, s.height || s.videoHeight || 0, x[1]); } return r.apply(this, x); });
    w(P, 'texStorage2D', function (r, x) { sz(this, x[3], x[4], 0); return r.apply(this, x); });
  }
  addEventListener('load', () => { try {
    const r = handlers.reveal, t = handlers.tumbleBoard;
    handlers.reveal = async (...x) => { C.spin++; C.ev = 'reveal'; return r(...x); };
    if (t) handlers.tumbleBoard = async (...x) => { C.tumble++; return t(...x); };
  } catch (e) { C.err = String(e); } });
})();
"""
DOMCENSUS = """(() => { const m = {}; for (const el of document.getElementsByTagName('*')) { const k = el.tagName.toLowerCase() + '.' + (typeof el.className === 'string' ? el.className.trim().split(/\s+/)[0] : '') + (el.parentElement ? '<' + el.parentElement.tagName.toLowerCase() + '.' + (typeof el.parentElement.className === 'string' ? el.parentElement.className.trim().split(/\s+/)[0] : '') : ''); m[k] = (m[k] || 0) + 1; } return m; })()"""
DOM0 = [None]
COUNTS = """JSON.stringify((() => { const C = Object.assign({}, window.__ct || {});
  C.nodes = document.getElementsByTagName('*').length; C.canvases = document.querySelectorAll('canvas').length;
  try { C.anims = document.getAnimations().length; } catch (e) {}
  try { C.symHeld = SYMF.sheets.size; } catch (e) {}
  try { C.playing = !!state.playing; C.open = !!(RGS.state.round); } catch (e) {}
  C.phase = (document.getElementById('replayPlay') || { dataset: {} }).dataset.phase || '';
  C.lite = !!(window.GFX && GFX.low);
  return C; })())"""


def kind(p):
    try:
        n = p.name().lower()
    except Exception:
        return None
    return "web" if "webprocess" in n else "gpu" if "gpuprocess" in n else None


res = {"mode": mode, "event": event, "extra": extra, "live": live, "reload": reload_at, "rounds": rounds, "crios": crios, "land": land}
with sync_playwright() as pw:
    dev = dict(pw.devices["iPhone 12 landscape" if land else "iPhone 12"])
    if crios:
        dev["user_agent"] = CRIOS
    br = pw.webkit.launch()
    root = None
    for p in psutil.process_iter(["name", "create_time"]):
        if (p.info["name"] or "").lower() == "playwright.exe":
            if not root or p.info["create_time"] > root.info["create_time"]:
                root = p
    ctx = br.new_context(**dev)
    ctx.add_init_script(INSTR + user_init)
    pg = ctx.new_page()
    log, crashed, navs = [], [], []
    pg.on("console", lambda m: log.append(f"{round(time.time() - T0, 1)} {m.type}: {m.text[:300]}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: log.append(f"{round(time.time() - T0, 1)} pageerror: {str(e)[:400]}"))
    pg.on("crash", lambda *_: crashed.append(time.time()))
    pg.on("framenavigated", lambda f: navs.append(f.url) if f == pg.main_frame else None)
    reqs = {}
    ctx.on("request", lambda r: reqs.__setitem__(r.url.split("?")[0].replace(base, ""), reqs.get(r.url.split("?")[0].replace(base, ""), 0) + 1))
    samples, counts, stop, marks = [], [], [False], []
    procs = {}
    T0 = time.time()

    def sampler():
        while not stop[0]:
            if root:
                try:
                    for c in root.children(recursive=True):
                        k = kind(c)
                        if k:
                            procs[c.pid] = (k, c)
                except Exception:
                    pass
            row = {"t": round(time.time() - T0, 2)}
            for pid, (k, pr) in list(procs.items()):
                try:
                    row[k] = round(row.get(k, 0) + pr.memory_info().private / 1e6, 1)
                except Exception:
                    pass
            samples.append(row)
            time.sleep(.1)
    th = threading.Thread(target=sampler, daemon=True); th.start()

    def mark(s):
        marks.append((round(time.time() - T0, 1), s)); print(f"[{marks[-1][0]:7.1f}] {s}", flush=True)

    def census():
        try:
            c = json.loads(pg.evaluate(COUNTS))
        except Exception as e:
            log.append("evaluate: " + str(e)[:200]); return None
        c["t"] = round(time.time() - T0, 1)
        last = samples[-1] if samples else {}
        c["web"], c["gpu"] = last.get("web"), last.get("gpu")
        counts.append(c)
        return c

    CLICKER = """() => { clearInterval(window.__clk); const seen = {};
      window.__clk = setInterval(() => { for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s);
        if (e && e.getBoundingClientRect().width > 0) { seen[s] = (seen[s] || 0) + 1; if (seen[s] > 8) { e.click(); seen[s] = 0; } } } }, 400); }"""

    def wait_for(js, secs):
        t1 = time.time()
        while time.time() - t1 < secs and not crashed:
            try:
                if pg.evaluate(js):
                    return True
            except Exception:
                pass
            time.sleep(.3)
        return False

    def enter():
        ok = wait_for("(() => { const i = document.getElementById('intro'); const f = document.querySelector('.fhit');"
                      " return (!i || i.classList.contains('gone')) && !!(f && f.getBoundingClientRect().width > 0); })()", 150)
        if not ok:
            raise RuntimeError("features screen never came up")
        time.sleep(.8)
        for _ in range(5):   # (the plate keeps moving, so Playwright's own click never finds it "stable")
            pg.evaluate("document.querySelector('.fhit') && document.querySelector('.fhit').click()")
            time.sleep(.8)
            if not pg.evaluate("document.body.classList.contains('features-up')"):
                break
        wait_for("!document.body.classList.contains('features-up') && typeof RGS !== 'undefined' && RGS.state.authenticated", 30)

    def follow(until_js, secs, stop_on_spin=0):
        t1 = time.time()
        while time.time() - t1 < secs and not crashed:
            c = census()
            if c is None:
                return False
            if stop_on_spin and c.get("spin", 0) >= stop_on_spin:
                return "spin"
            try:
                if pg.evaluate(until_js):
                    return True
            except Exception:
                pass
            time.sleep(poll)
        return False

    try:
        if live:
            sess = f"wk{random.randint(100000, 999999)}"
            url = f"{base}/?sessionID={sess}&rgs_url={base}&lang=en{extra}"
            pg.goto(url); enter(); time.sleep(2)
            mark("in game")
            for c in range(rounds):
                census()
                pg.evaluate(f"""fetch('/mock/force', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ sessionID: RGS.sessionID, mode: {json.dumps(mode)}, event: {event} }}) }}).then(r => r.json())""")
                pg.evaluate(CLICKER)
                pg.evaluate(f"""() => {{ window.__done = false; window.__err = null; playRound({json.dumps(mode)}).then(v => {{ window.__done = true; window.__ok = v; }}, e => {{ window.__done = true; window.__err = String(e && e.stack || e); }}); }}""")
                mark(f"round {c + 1} bought")
                if reload_at and c == 0:
                    r = follow("window.__done", 600, stop_on_spin=reload_at)
                    mark(f"reload at spin {reload_at} ({r})")
                    pg.reload(); enter(); pg.evaluate(CLICKER)
                    mark("resumed (features passed)")
                    r = follow("!!(window.__ct.spin > 0 && !state.playing && !RGS.state.round)", 600)
                    mark(f"resumed round over: {r}")
                else:
                    r = follow("window.__done", 600)
                    mark(f"round {c + 1} over: {r} err={pg.evaluate('window.__err')}")
                time.sleep(2)
        else:
            url = f"{base}/?replay=true&game=test&version=1&mode={mode}&event={event}&amount=1000000&rgs_url={base}{extra}"
            pg.goto(url)
            wait_for("(document.getElementById('replayPlay')||{dataset:{}}).dataset.phase === 'ready'", 120)
            time.sleep(3)
            mark("replay ready")
            pg.evaluate(CLICKER)
            for c in range(rounds):
                census()
                if c == 0:
                    DOM0[0] = pg.evaluate(DOMCENSUS)
                s0 = pg.evaluate("window.__ct.spin")
                pg.evaluate("document.getElementById('replayPlay').click()")
                wait_for(f"window.__ct.spin > {s0}", 30)
                mark(f"round {c + 1} started")
                if skip:
                    pg.evaluate("() => { clearInterval(window.__skp); window.__skp = setInterval(() => { if (state.playing) state.skip = true; }, 250); }")
                time.sleep(2)
                r = follow("!state.playing && (document.getElementById('replayPlay')||{dataset:{}}).dataset.phase === 'done'", 600)
                mark(f"round {c + 1} over: {r}")
                time.sleep(2)
        if gcpress:
            census(); mark("before GC pressure")
            for k in range(4):
                pg.evaluate("() => { let keep = 0; for (let i = 0; i < 60; i++) { const a = []; for (let j = 0; j < 100000; j++) a.push({ j, s: 'x' + j }); keep += a.length; } return keep; }")
                time.sleep(2); census()
            mark("after GC pressure")
        t1 = time.time()
        while time.time() - t1 < tail and not crashed:
            census(); time.sleep(poll)
        mark("tail done")
        if DOM0[0] is not None:
            d1 = pg.evaluate(DOMCENSUS)
            res["domdiff"] = {k: d1.get(k, 0) - DOM0[0].get(k, 0) for k in set(d1) | set(DOM0[0]) if d1.get(k, 0) != DOM0[0].get(k, 0)}
    except Exception as e:
        log.append("probe: " + str(e)[:300])
    stop[0] = True; th.join()
    if crashed:
        mark("CRASHED")
    for x in samples:
        x["s"] = 0
    # the free spin each sample belongs to
    ci = 0
    for x in samples:
        while ci + 1 < len(counts) and counts[ci + 1]["t"] <= x["t"]:
            ci += 1
        if counts:
            x["s"] = counts[ci].get("spin", 0)
    web = [x.get("web", 0) for x in samples]
    res["requests"] = reqs
    res.update({"crashed": bool(crashed), "navigations": len(navs), "marks": marks, "console": log[:40],
                "peak_web": round(max(web, default=0), 1), "peak_gpu": round(max((x.get("gpu", 0) for x in samples), default=0), 1),
                "counts": counts, "series": samples[::5]})
    try:
        br.close()
    except Exception:
        pass
json.dump(res, open(out, "w"), indent=1)
# per free spin: the WebContent median over its samples
by = {}
for x in samples:
    by.setdefault(x["s"], []).append(x.get("web", 0))
med = lambda v: sorted(v)[len(v) // 2]
print("peak web", res["peak_web"], "gpu", res["peak_gpu"], "crashed", res["crashed"], "navs", len(navs))
print("per spin web median:", " ".join(f"{k}:{med(v):.0f}" for k, v in sorted(by.items())))
if counts:
    f, l = counts[0], counts[-1]
    keys = [k for k in l if isinstance(l.get(k), (int, float)) and not isinstance(l.get(k), bool) and k not in ("t",)]
    print("counts first->last:", " ".join(f"{k}={f.get(k)}->{l.get(k)}" for k in keys))
print("console:", log[:8])
rq = res.get("requests") or {}
print("requests:", sum(rq.values()), "repeated:", sorted(((k, v) for k, v in rq.items() if v > 1), key=lambda kv: -kv[1])[:15])
if res.get("domdiff"):
    print("dom diff:", sorted(res["domdiff"].items(), key=lambda kv: -abs(kv[1]))[:25])
