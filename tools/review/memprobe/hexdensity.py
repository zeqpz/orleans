"""The burst canvas at the density a phone shows it vs the old 2 px per layout px (iOS memory, 2026-11-16).

One hex (a tile dissolving, with its ghost, smoke and motes) is started on the board of the current build at a phone
profile; the burst loop is stopped and the same burst is drawn at the same moments (performance.now pinned) twice: on
the canvas as the mobile tier now sizes it (screen density, capped at 2) and on the canvas as it was (2 px per layout
px, ~2-3x the screen each way, scaled down by the compositor). Screenshot crops round the tile, side by side, and
the pixel difference.
usage: hexdensity.py OUTDIR [--base URL] [--w 390 --h 844]
"""
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, MOCK, game_url, enter_game

a = sys.argv[1:]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
out = Path(a[0]); out.mkdir(parents=True, exist_ok=True)
base = opt("--base", MOCK)
w, h = int(opt("--w", 390)), int(opt("--h", 844))
SEED = """(() => { let s = 0x2F6E2B1; Math.random = () => { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return ((s >>> 0) % 1e9) / 1e9; }; })();"""
b = Browser(w, h, 3, ua=IPHONE_UA, mobile=True)
res = []
try:
    from PIL import Image
    import numpy as np
    b.ws.call("Page.addScriptToEvaluateOnNewDocument", source=SEED)
    b.open(game_url(base), .5)
    enter_game(b); time.sleep(4)
    info = json.loads(b.js("""JSON.stringify((() => {
      document.getAnimations().forEach(x => x.pause());
      const m = burstMeasure(2, 2, shownSym[2] && shownSym[2][2]);
      window.__realNow = performance.now.bind(performance);
      window.__t0 = __realNow();
      hexIcon(m);
      cancelAnimationFrame(burstRaf); burstRaf = 0;
      const r = cellEls[2][2].getBoundingClientRect();
      return { ok: !!m, x: r.left, y: r.top, w: r.width, h: r.height, n: bursts.length, d: burstDpr, cw: shardCanvas.width, ch: shardCanvas.height };
    })())"""))
    print("hex", info)
    pad = info["w"] * 1.2
    clip = {"x": max(0, info["x"] - pad), "y": max(0, info["y"] - pad * 1.6), "width": info["w"] + 2 * pad, "height": info["h"] + 2.6 * pad, "scale": 1}
    import base64
    for age in (120, 300, 500, 750):
        shots = []
        for mob in (True, False):
            st = json.loads(b.js(f"""JSON.stringify((() => {{
              window.MOBILE = {str(mob).lower()};
              shardLayer();
              window.MOBILE = true;
              const T = __t0 + {age} * bursts[0].t;
              performance.now = () => T; burstLast = 0;
              burstStep();
              cancelAnimationFrame(burstRaf); burstRaf = 0;
              performance.now = __realNow;
              return {{ d: burstDpr, cw: shardCanvas.width, ch: shardCanvas.height }};
            }})())"""))
            time.sleep(.35)
            d = b.ws.call("Page.captureScreenshot", format="png", clip=clip)
            p = out / f"hex_{age}_{'now' if mob else 'was'}.png"
            p.write_bytes(base64.b64decode(d["data"]))
            shots.append((p, st))
        A = np.asarray(Image.open(shots[1][0]).convert("RGB")).astype(int)   # was
        B = np.asarray(Image.open(shots[0][0]).convert("RGB")).astype(int)   # now
        dd = np.abs(A - B).max(axis=2)
        r = {"age_ms": age, "was": shots[1][1], "now": shots[0][1], "max": int(dd.max()), "mean": round(float(np.abs(A - B).mean()), 3),
             "over16_pct": round(float((dd > 16).mean()) * 100, 3), "over4_pct": round(float((dd > 4).mean()) * 100, 3)}
        Image.fromarray(np.concatenate([A, B, np.minimum(255, dd[..., None].repeat(3, 2) * 4)], axis=1).astype("uint8")).save(out / f"hex_ab_{age}.png")
        res.append(r)
        print(json.dumps(r), flush=True)
finally:
    b.close()
json.dump(res, open(out / "hexdensity.json", "w"), indent=1)
