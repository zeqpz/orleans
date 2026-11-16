"""Who owns the 2D canvases and the WebGL textures on the mobile tier at boot (2026-11-16)."""
import json, sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, game_url, enter_game
b = Browser(390, 844, 3, ua=IPHONE_UA, mobile=True)
try:
    b.open(game_url(extra=(sys.argv[1] if len(sys.argv) > 1 else "")), 2)
    enter_game(b)
    time.sleep(4)
    print(b.js("""JSON.stringify((() => {
      const by = {};
      for (const r of __mem.canvases) { const c = r.deref(); if (!c || !c.__mt) continue;
        const k = c.__mt.type + ' ' + c.__mt.stack.replace(/https?:\/\/[^ ]*\//g, '').slice(0, 120);
        by[k] = by[k] || [0, 0]; by[k][0]++; by[k][1] += c.width * c.height * 4 / 1e6; }
      const tex = []; for (const r of __mem.textures) { const t = r.deref(); if (!t) continue; const b = Object.values(t.__lv).reduce((a, v) => a + v, 0); if (b) tex.push(b); }
      tex.sort((a, b) => b - a);
      return { canv: Object.entries(by).sort((a, b) => b[1][1] - a[1][1]).slice(0, 12).map(([k, v]) => [v[0], +v[1].toFixed(1), k]),
               texN: tex.length, texMB: +(tex.reduce((a, v) => a + v, 0) / 1e6).toFixed(1), texTop: tex.slice(0, 8).map(v => +(v / 1e6).toFixed(1)),
               symd: SYMF.density, symk: SYMF.k, sheets: SYMF.sheets.size };
    })())"""))
finally:
    b.close()
