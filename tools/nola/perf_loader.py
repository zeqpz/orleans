"""Perf pass 2026-11-09 (board fps during spins and wins): what a round cuts or uploads for the first time is made
while the loading screen is up (or before a replay's Play shows), not during play.
  step 1
  - every symbol clip's board atlas (hit, idle, multi followed the landings in the background, after Play)
  - every Multi dissolve kit (hexKit), cut back to back instead of in idle moments from 2.5 s on
  - every motion-blur smear (makeSmears), likewise
  - warmBursts skipped in the voodoo build: no icon bursts there (burstIcon hexes them), its pieces went unused
  step 2
  - the loader waits for the clips a round needs within seconds (landings, hits, Multis); the idles - the biggest
    clip, and a resting symbol simply holds its rest pose until its idle is in - follow in boardgl.js's workers
Run each step once, in order: python tools/nola/perf_loader.py 1, then 2 (edits recorded in reskin_frontend.py by edit.py)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edit import ed

STEP1 = [
# the rest of the clips: kept as a promise the loader can wait on
('''    await Promise.all(ids.map(id => symSheet(id, "land")));
    (async () => {
      for (const clip of ["hit", "idle", "multi"]) await Promise.all(ids.map(id => symSheet(id, clip).catch(() => {})));
    })();
    return ids.length > 0;
  })().catch(e => { console.warn("animated symbols unavailable:", e); return false; });
  return symReady;
}''', '''    await Promise.all(ids.map(id => symSheet(id, "land")));
    SYMF.rest = (async () => {
      for (const clip of ["hit", "idle", "multi"]) await Promise.all(ids.map(id => symSheet(id, clip).catch(() => {})));
    })();
    return ids.length > 0;
  })().catch(e => { console.warn("animated symbols unavailable:", e); return false; });
  return symReady;
}
// Every clip in, cut and on the GPU (perf, 2026-11-09): the loading screen and a replay's Play wait on this.
// The landings alone used to let the game in, and the hit, idle and Multi clips were decoded, resized and
// uploaded while the first round was already playing (~2.5 s of a slow phone's main thread).
const symAllReady = () => loadSymFrames().then(ok => (SYMF.rest || Promise.resolve()).then(() => symHoldQ).then(() => ok));'''),

# the dissolve kits: one after another from the loader, each in a task of its own
('''function warmHexKits() {
  const imgs = Object.values(FLAT).filter(Boolean), step = () => {
    const im = imgs.shift();
    if (!im) return;
    if (im.complete && im.naturalWidth) hexKit(im); else imgs.push(im);
    (window.requestIdleCallback || (f => setTimeout(f, 60)))(step);
  };
  setTimeout(step, 2500);
}
if (VOODOO) warmHexKits();''', '''// a picture that has arrived (true) or failed (false)
const picReady = img => img.complete ? Promise.resolve(img.naturalWidth > 0) : new Promise(r => {
  img.addEventListener("load", () => r(true), { once: true }); img.addEventListener("error", () => r(false), { once: true });
});
const nextTask = () => new Promise(r => setTimeout(r, 0));
// Every kit cut while the loading screen is up, one per task (perf, 2026-11-09): they used to wait for idle
// moments, which a busy board seldom has, so the first Multi's hex cut its kit mid-round
function warmHexKits() {
  return Object.values(FLAT).filter(Boolean).reduce((p, im) => p.then(() => picReady(im)).then(ok => { if (ok) hexKit(im); return nextTask(); }), Promise.resolve());
}
// what the round draws for the first time - the dissolves and the motion blur - made once, before play
let fxReady = null;
const warmFX = () => fxReady || (fxReady = Promise.all([VOODOO ? warmHexKits() : null, makeSmears()]).catch(() => {}));'''),

# the smears: back to back, and the loader waits for them
('''function makeSmears() {
  if (REDUCED_MOTION) return;
  const names = Object.keys(FLAT), tries = {};
  // one symbol a turn - a few ms of pixel work - close behind one another: the first spin wants them
  // all, and a page drawing every frame has little idle time to wait for
  const idle = window.requestIdleCallback ? f => requestIdleCallback(f, { timeout: 200 }) : f => setTimeout(f, 40);
  const next = () => {
    const name = names.shift();
    if (!name) return;
    const img = FLAT[name];
    if (img.complete && img.naturalWidth) {
      makeSmear(img).then(url => {''', '''function makeSmears() {
  if (REDUCED_MOTION) return Promise.resolve();
  const names = Object.keys(FLAT), made = [];
  // one symbol a task - a few ms of pixel work - close behind one another, while the loading screen is up:
  // the first spin wants them all (perf, 2026-11-09: in idle moments after the loader, a replay or a quick
  // first spin cut them mid-round). Settles once every one is made and decoded.
  return names.reduce((p, name) => p.then(() => picReady(FLAT[name])).then(ok => {
    const img = FLAT[name];
    if (ok) {
      made.push(makeSmear(img).then(url => {'''),
('''          eachCell((el, r, y) => { if (shownSym[r] && shownSym[r][y] && shownSym[r][y].name === name) smearOn(el, name); });
        });
      }).catch(() => { /* that symbol falls without a blur */ });
    } else if ((tries[name] = (tries[name] || 0) + 1) < 20) names.push(name);   // its picture is still on its way
    idle(next);
  };
  idle(next);
}''', '''          eachCell((el, r, y) => { if (shownSym[r] && shownSym[r][y] && shownSym[r][y].name === name) smearOn(el, name); });
        });
      }).catch(() => { /* that symbol falls without a blur */ }));
    }
    return nextTask();
  }), Promise.resolve()).then(() => Promise.all(made));
}'''),

# the loading screen waits for all of it
('''  waits.push(one(loadSymFrames()));  // the animated symbols: Blender's frames (the landings; the rest follows)''',
 '''  waits.push(one(symAllReady()));    // the animated symbols: Blender's frames, every clip cut and uploaded
  waits.push(one(warmFX()));         // the dissolves and the motion blur, cut before the first round'''),
('''  loaded.then(() => { if (fill) fill.style.width = "100%"; warmBursts(); makeSmears(); });''',
 '''  loaded.then(() => { if (fill) fill.style.width = "100%"; if (!VOODOO) warmBursts(); });   // (no icon bursts in the voodoo build: each is hexed)'''),
# and so does a replay's Play
('''  await Promise.race([Promise.all([loadSymFrames(), prepareSpray(), charsLoaded]).catch(() => {}), new Promise(r => setTimeout(r, 15000))]);''',
 '''  await Promise.race([Promise.all([symAllReady(), prepareSpray(), charsLoaded, warmFX()]).catch(() => {}), new Promise(r => setTimeout(r, 15000))]);'''),
]

STEP2 = [
('''    SYMF.rest = (async () => {
      for (const clip of ["hit", "idle", "multi"]) await Promise.all(ids.map(id => symSheet(id, clip).catch(() => {})));
    })();''', '''    SYMF.rest = (async () => {
      for (const clip of ["hit", "multi"]) await Promise.all(ids.map(id => symSheet(id, clip).catch(() => {})));
    })();
    SYMF.rest.then(() => Promise.all(ids.map(id => symSheet(id, "idle").catch(() => {}))));'''),
('''// Every clip in, cut and on the GPU (perf, 2026-11-09): the loading screen and a replay's Play wait on this.
// The landings alone used to let the game in, and the hit, idle and Multi clips were decoded, resized and
// uploaded while the first round was already playing (~2.5 s of a slow phone's main thread).''', '''// The clips a round plays within seconds, cut and on the GPU (perf, 2026-11-09): the loading screen and a
// replay's Play wait on this. The landings alone used to let the game in, and the hit, idle and Multi clips were
// resized on the page while the first round was playing (~2.5 s of a slow phone's main thread). Now every sheet
// is resized in the board's workers (boardgl.js), and only the idles - the biggest clip, which a resting symbol
// can do without for a moment (it holds its rest pose) - are still arriving once the game is up.'''),
]

if __name__ == "__main__":
    for old, new in {"1": STEP1, "2": STEP2}[sys.argv[1]]:
        ed(old, new)
    print("step", sys.argv[1], "ok")
