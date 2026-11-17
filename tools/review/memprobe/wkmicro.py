"""Micro tests in Playwright's WebKit (iPhone 12 profile): does WebKit's page process give memory back after a
pattern the game repeats every free spin? (iOS review 4, 2026-11-17.) A blank page on the mock's origin runs one pattern
N times in batches; the WebContent process's private bytes are read after each batch.
  fetch    fetch a 200 KB sheet and take its blob (dropped)
  fetchkeep  the same file fetched once, held, blob sliced (control)
  worker   a Worker made, fetches + decodes the sheet, terminated
  workernop a Worker made and terminated (no work)
  canvas   a 132 px canvas + getImageData + createImageData + putImageData (hexKit's pattern), dropped
  decode   createImageBitmap of a held blob, closed
  gltex    that bitmap uploaded to a WebGL texture, drawn, the texture deleted
usage: wkmicro.py OUTJSON --base URL --test fetch --n 400 --batch 20
"""
import json, sys, time
import psutil
from playwright.sync_api import sync_playwright

a = sys.argv[1:]
out = a[0]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base = opt("--base", "http://localhost:8781")
test, N, B = opt("--test", "fetch"), int(opt("--n", 400)), int(opt("--batch", 20))
SHEET = "assets/sym/d8/H1_hit.webp"
JS = {
    "fetch": "async () => { const b = await (await fetch('%s')).blob(); return b.size; }" % SHEET,
    "fetchkeep": "async () => { if (!window.__b) window.__b = await (await fetch('%s')).blob(); return window.__b.slice(0).size; }" % SHEET,
    "worker": """async () => { const src = "onmessage = async e => { const b = await (await fetch(e.data)).blob(); const m = await createImageBitmap(b); m.close(); postMessage(1); }";
       const w = new Worker(URL.createObjectURL(new Blob([src], { type: 'text/javascript' })));
       await new Promise(ok => { w.onmessage = ok; w.postMessage(new URL('%s', location.href).href); }); w.terminate(); return 1; }""" % SHEET,
    "workernop": """async () => { const w = new Worker(URL.createObjectURL(new Blob(["onmessage = () => postMessage(1)"], { type: 'text/javascript' })));
       await new Promise(ok => { w.onmessage = ok; w.postMessage(0); }); w.terminate(); return 1; }""",
    "canvas": """async () => { const c = document.createElement('canvas'); c.width = 132; c.height = 132; const x = c.getContext('2d', { willReadFrequently: true });
       x.fillStyle = '#4a4'; x.fillRect(10, 10, 100, 100); const d = x.getImageData(0, 0, 132, 132); const o = x.createImageData(132, 132); o.data.set(d.data); x.putImageData(o, 0, 0);
       const fr = []; for (let k = 0; k < 12; k++) { const f = document.createElement('canvas'); f.width = 132; f.height = 132; f.getContext('2d').putImageData(o, 0, 0); fr.push(f); }
       return fr.length; }""",
    "gltex": """async () => { if (!window.__b) window.__b = await (await fetch('%s')).blob();
       if (!window.__gl) { const c = document.createElement('canvas'); c.width = 64; c.height = 64; document.body.append(c); window.__gl = c.getContext('webgl2') || c.getContext('webgl'); }
       const gl = window.__gl, m = await createImageBitmap(window.__b), t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
       gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, m); gl.drawArrays(gl.POINTS, 0, 1); gl.finish(); gl.deleteTexture(t); m.close(); return 1; }""" % SHEET,
    "decode": "async () => { if (!window.__b) window.__b = await (await fetch('%s')).blob(); const m = await createImageBitmap(window.__b); m.close(); return 1; }" % SHEET,
}
res = {"test": test, "n": N, "rows": []}
with sync_playwright() as pw:
    br = pw.webkit.launch()
    root = max((p for p in psutil.process_iter(["name", "create_time"]) if (p.info["name"] or "").lower() == "playwright.exe"),
               key=lambda p: p.info["create_time"])
    pg = br.new_context(**pw.devices["iPhone 12"]).new_page()
    pg.goto(base + "/rgs.js")   # any page on the origin: a blank document, same-origin fetches
    web = lambda: sum(c.memory_info().private for c in root.children(recursive=True) if "webprocess" in c.name().lower()) / 1e6
    time.sleep(2)
    res["rows"].append({"i": 0, "web": round(web(), 1)})
    for i in range(B, N + 1, B):
        pg.evaluate("async () => { const f = %s; for (let k = 0; k < %d; k++) await f(); }" % (JS[test], B))
        time.sleep(.3)
        res["rows"].append({"i": i, "web": round(web(), 1)})
        print(i, res["rows"][-1]["web"], flush=True)
    time.sleep(5)
    res["rows"].append({"i": "settled", "web": round(web(), 1)})
    br.close()
json.dump(res, open(out, "w"), indent=1)
print(test, " ".join(f"{r['i']}:{r['web']:.0f}" for r in res["rows"]))
