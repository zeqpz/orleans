"""Phone screenshots of the moments of a replayed round, before | after side by side (review 3).
usage: moments.py OUTDIR BEFORE_URL AFTER_URL W H"""
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA
from PIL import Image
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
A, B, w, h = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
SEED = """(() => { let s = 0x2F6E2B1; Math.random = () => { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return ((s >>> 0) % 1e9) / 1e9; }; })();"""
MOMENTS = {   # name: JS that is true at the moment
  "spin": "document.querySelector('.reel.spinning') !== null",
  "win": "document.querySelectorAll('.cell.winhit').length > 0 && document.querySelector('.winline, .winpop') !== null",
  "hex": "(() => { try { return bursts.some(x => performance.now() - x.born > 250); } catch (e) { return false; } })()",
  "bigwin": "(() => { const t = document.querySelector('.totalwin.up .twhead:not(.blank)'); return !!t; })()",
  "bonusintro": "(() => { const b = document.querySelector('.bonusintro.up'); return !!b && performance.now() - (window.__bi || (window.__bi = performance.now())) > 2200; })()",
  "freespin": "(() => { const f = document.getElementById('fsCard'); return !!(f && f.getBoundingClientRect().width > 0 && document.querySelector('.reel.spinning') === null && document.querySelectorAll('.cell.winhit').length > 0); })()",
}
def run(base, tag, mode, ev):
    b = Browser(w, h, 3, ua=IPHONE_UA)
    shots = {}
    try:
        b.ws.call("Page.addScriptToEvaluateOnNewDocument", source=SEED)
        b.open(f"{base}/?replay=true&game=test&version=1&mode={mode}&event={ev}&amount=1000000&rgs_url={base}", .5)
        b.wait("(document.getElementById('replayPlay')||{dataset:{}}).dataset.phase === 'ready'", 120); time.sleep(2)
        b.js("""(() => { clearInterval(window.__clk); const seen = {};
          window.__clk = setInterval(() => { for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s);
          if (e && e.getBoundingClientRect().width > 0) { seen[s] = (seen[s] || 0) + 1; if (seen[s] > 12) { e.click(); seen[s] = 0; } } } }, 400); })()""")
        b.js("document.getElementById('replayPlay').click(); 1")
        t0 = time.time()
        while time.time() - t0 < 300:
            for k, js in MOMENTS.items():
                if k in shots: continue
                try:
                    if b.js(js): shots[k] = b.shot(out / f"{tag}_{k}.png")
                except Exception: pass
            if b.js("document.getElementById('replayPlay').dataset.phase") == "done": break
            time.sleep(.05)
        print(tag, sorted(shots), b.console()[:3], flush=True)
    finally:
        b.close()
    return shots
for mode, ev in (("base", 94), ("base", 8)):
    sa = run(A, f"before_{w}x{h}_{ev}", mode, ev); sb = run(B, f"after_{w}x{h}_{ev}", mode, ev)
    for k in sb:
        if k not in sa: continue
        ia, ib = Image.open(sa[k]).convert("RGB"), Image.open(sb[k]).convert("RGB")
        sheet = Image.new("RGB", (ia.width + ib.width + 20, max(ia.height, ib.height)), (40, 40, 40))
        sheet.paste(ia, (0, 0)); sheet.paste(ib, (ia.width + 20, 0))
        sheet = sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS)
        sheet.save(out / f"moment_{w}x{h}_{ev}_{k}.png")
