"""Phone screenshots of a cork in flight and of a pop at the same moments of a replayed round, for a before/after look
(iOS crash review 2, 2026-11-16). The cork: its flight 0.35 s in; the pop: 0.2 s after the first tile blows.
usage: fxshots.py PREFIX [--base URL] [--mode corkstorm --event 43029] [--w 390 --h 844] [--ua ios|crios]
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, CRIOS_UA, MOCK

a = sys.argv[1:]
prefix = a[0]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base, mode, event = opt("--base", MOCK), opt("--mode", "corkstorm"), opt("--event", "43029")
w, h = int(opt("--w", 390)), int(opt("--h", 844))
b = Browser(w, h, 3, ua=CRIOS_UA if opt("--ua", "ios") == "crios" else IPHONE_UA, mobile=True)
try:
    b.open(f"{base}/?replay=true&game=test&version=1&mode={mode}&event={event}&amount=1000000&rgs_url={base}", 2)
    b.wait("(document.getElementById('replayPlay') || {dataset: {}}).dataset.phase === 'ready'", 120)
    time.sleep(2.5)
    # pause the page's clock at the moment: freeze rAF-driven loops by holding the main thread is not possible over
    # CDP, so the shot is taken as soon as the moment is seen (polled every 20 ms in the page)
    b.js("""(() => { window.__m = {};
      const look = () => {
        try {
          const c = FXS.parts.find(p => p.kind === 'cork');
          if (c && c.t > .35 && !window.__m.cork) window.__m.cork = performance.now();
          const bl = bursts.find(x => x.pieces && performance.now() - x.born > 200);
          if (bl && !window.__m.pop) window.__m.pop = performance.now();
        } catch (e) {}
        if (!(window.__m.cork && window.__m.pop)) setTimeout(look, 20);
      };
      look(); document.getElementById('replayPlay').click(); })()""")
    took = set(); t0 = time.time()
    while time.time() - t0 < 120 and len(took) < 2:
        m = b.js("JSON.stringify(window.__m)")
        for k in ("cork", "pop"):
            if k not in took and f'"{k}"' in m:
                took.add(k); b.shot(f"{prefix}_{k}.png")
        time.sleep(.02)
    print("shots", sorted(took), "console", b.console()[:4])
finally:
    b.close()
