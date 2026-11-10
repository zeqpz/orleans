"""Voodoo on Bourbon: reskin the newest Smukiez engine.io front end (frontend/index.html + rules.js) in place.
Every edit is an exact (old -> new) replacement and must match exactly once (or `n` times), so a changed base
fails loudly instead of half-applying. Run once on a fresh copy of the base build.
usage: python tools/nola/reskin_frontend.py"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FE = os.path.join(ROOT, "frontend")

GOLD, GOLD_RGB = "#F2B230", "242, 178, 48"         # Mardi Gras gold: the bonus scatter's paint, UI accents
GREEN, GREEN_RGB = "#7CFF6B", "124, 255, 107"      # voodoo green: the Extreme / skull, magic
VIOLET, VIOLET_RGB = "#9B5CF0", "155, 92, 240"     # Mardi Gras violet

ED = []   # (old, new, count)


def rep(old, new, n=1):
    ED.append((old, new, n))


def apply(path, edits):
    s = open(path, encoding="utf-8").read()
    for old, new, n in edits:
        c = s.count(old)
        if c != n and not (n == 0 and c > 0):
            sys.exit(f"{os.path.basename(path)}: expected {n} of {old[:90]!r}, found {c}")
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8", newline="\n").write(s)


# ------------------------------------------------------------------ head, fonts
rep("<title>Smukiez's City</title>", "<title>Voodoo on Bourbon</title>")
for fam, src in (("Jraot Hollow", 'url("assets/jraot-hollow.ttf") format("truetype")'),
                 ("Timegoing", 'url("assets/timegoing.ttf") format("truetype")'),
                 ("BROMO", 'url("assets/bromo.otf") format("opentype")'),
                 ("LLambozy", 'url("assets/llambozy.ttf") format("truetype")'),
                 ("Apocalypse Grunge", 'url("assets/apocalypse_grunge.ttf") format("truetype")'),
                 ("aaaiight", 'url("assets/aaaiight.ttf") format("truetype")'),
                 ("aaaiight fat", 'url("assets/aaaiight-fat.ttf") format("truetype")'),
                 ("Smashed Graffiti", 'url("assets/smashed_graffiti_fill.otf") format("opentype")'),
                 ("Smashed Graffiti Outline", 'url("assets/smashed_graffiti_outline.otf") format("opentype")')):
    rep(f'font-family: "{fam}";\n    src: {src};', f'font-family: "{fam}";\n    src: url("assets/fredoka.ttf") format("truetype"); font-weight: 300 700;')

# ------------------------------------------------------------------ one character, on the left
rep('  #charfx  { right: var(--char-inset); --char-shift: 40%; --char-lift: 5%; --char-depth: calc(1 - sin(var(--scene-yaw)) * .3); }   /* the skull stands 5% lower than the boy */\n'
    '  #charfx2 { left: var(--char-inset);  --char-shift: 49.7%; --char-lift: 7%; --char-depth: calc(1 + sin(var(--scene-yaw)) * .3); }   /* the boy a little lower (owner, 2026-11-03) */',
    '  #charfx  { left: var(--char-inset); --char-lift: 7%; --char-depth: 1; }   /* Doc, the voodoo showman, on the left of the board */')
rep('    #charfx2 { left: calc(var(--char-inset) + 6vw); --char-lift: 10%; }',
    '    #charfx { left: calc(var(--char-inset) + 6vw); --char-lift: 10%; }')
rep('<div id="charfx" class="charfx" aria-hidden="true"></div>\n<div id="charfx2" class="charfx" aria-hidden="true"></div></div>',
    '<div id="charfx" class="charfx" aria-hidden="true"></div></div>')
rep('const root = document.documentElement.style, chars = [$("charfx"), $("charfx2")].filter(Boolean);',
    'const root = document.documentElement.style, chars = [$("charfx")].filter(Boolean);')
rep('''const CHARACTERS = [
  // #charfx is the right-hand slot, #charfx2 the left
  {
    el: "charfx", name: "skull",
    flavour: [["ash_break"]],
    swap: { big_win: "win" },   // the skull's big-win clip is retired: its normal win plays for both
    shadow: false,              // no shadow under his shoes (owner, 2026-11-03)
  },
  {
    el: "charfx2", name: "boy",
    flavour: [["cash_show"], ["cash_count"]],
  },
];''', '''const CHARACTERS = [
  // Doc, the voodoo showman with his skull cane, beside the board (#charfx; CSS stands him on the left)
  {
    el: "charfx", name: "doc",
    flavour: [["cane_twirl"], ["hat_tip"], ["conjure"]],   // idle breaks: twirls the cane, tips his hat, conjures a wisp
  },
];''')

rep('<div class="boardplate" aria-hidden="true"></div><img id="paintframe" src="assets/frame.webp" alt="" draggable="false">',
    '<div class="boardplate" aria-hidden="true"></div><img id="paintback" src="assets/board_back.webp" alt="" draggable="false" aria-hidden="true"><img id="paintframe" src="assets/frame.webp" alt="" draggable="false">')

rep('  wander(() => [frame, document.querySelector("#board .sprayrim")].filter(Boolean), t => ({',
    '  wander(() => [frame, $("paintback"), $("candleflame"), document.querySelector("#board .sprayrim")].filter(Boolean), t => ({   // the velvet backing drifts with its frame')

# ------------------------------------------------------------------ the living street (bgscene.js) in place of the wall
rep('<script src="wallfx.js"></script>\n', '<script src="bgscene.js"></script>\n')

# ------------------------------------------------------------------ symbols
rep('''  M:  { label: "MULTI", sub: "",           cls: "booster", img: "assets/flat/M.webp" },   // the brick chunk, its value over it
  BS: { label: "CREW",  sub: "BONUS",      cls: "scat",  img: "assets/flat/BS.webp" },
  ES: { label: "PHNTM", sub: "EXTREME",    cls: "escat", img: "assets/flat/ES.webp" },
  H1: { label: "CASH",  sub: "BAG",        cls: "high", img: "assets/flat/H1.webp" },
  H2: { label: "GLOCK", sub: "CARTOON",    cls: "high", img: "assets/flat/H2.webp" },
  H3: { label: "CHAIN", sub: "GOLD",       cls: "high", img: "assets/flat/H3.webp" },
  H4: { label: "KICKS", sub: "FRESH",      cls: "high", img: "assets/flat/H4.webp" },
  H5: { label: "BOOM",  sub: "BOX",        cls: "high", img: "assets/flat/H5.webp" },
  L1: { label: "SPRAY", sub: "CAN",        cls: "low",  img: "assets/flat/L1.webp" },
  L2: { label: "MRKR",  sub: "MARKERS",    cls: "low",  img: "assets/flat/L2.webp" },
  L3: { label: "BEANIE",sub: "SMUKIEZ",    cls: "low",  img: "assets/flat/L3.webp" },
  L4: { label: "TAG",   sub: "HANGTAG",    cls: "low",  img: "assets/flat/L4.webp" },
  L5: { label: "DICE",  sub: "PAIR",       cls: "low",  img: "assets/flat/L5.webp" },
  H6: { label: "SK8",   sub: "BOARD",      cls: "high", img: "assets/flat/H6.webp" },
  H7: { label: "DROP",  sub: "LIMITED",    cls: "high", img: "assets/flat/H7.webp" },
  L6: { label: "SHIRT", sub: "SMUKIEZ",    cls: "low",  img: "assets/flat/L6.webp" },
  L7: { label: "HOODIE",sub: "SMUKIEZ",    cls: "low",  img: "assets/flat/L7.webp" },
  L8: { label: "WEED",  sub: "BAG",        cls: "low",  img: "assets/flat/L8.webp" },
  L9: { label: "TRAIN", sub: "FREIGHT",    cls: "low",  img: "assets/flat/L9.webp" },
  L10:{ label: "LOW",   sub: "RIDER",      cls: "low",  img: "assets/flat/L10.webp" },''',
'''  M:  { label: "POTION",sub: "MULTI",      cls: "booster", img: "assets/flat/M.webp" },   // the voodoo potion, its value over it
  BS: { label: "FS",    sub: "BONUS",      cls: "scat",  img: "assets/flat/BS.webp" },
  ES: { label: "XFS",   sub: "EXTREME",    cls: "escat", img: "assets/flat/ES.webp" },
  H1: { label: "MASK",  sub: "MARDI GRAS", cls: "high", img: "assets/flat/H1.webp" },
  H2: { label: "DOLL",  sub: "VOODOO",     cls: "high", img: "assets/flat/H2.webp" },
  H3: { label: "HORN",  sub: "TRUMPET",    cls: "high", img: "assets/flat/H3.webp" },
  H4: { label: "SKULL", sub: "CANDLE",     cls: "high", img: "assets/flat/H4.webp" },
  H5: { label: "GRIS",  sub: "GRIS-GRIS",  cls: "high", img: "assets/flat/H5.webp" },
  L1: { label: "FLEUR", sub: "DE-LIS",     cls: "low",  img: "assets/flat/L1.webp" },
  L2: { label: "BEADS", sub: "PURPLE",     cls: "low",  img: "assets/flat/L2.webp" },
  L3: { label: "CRAW",  sub: "FISH",       cls: "low",  img: "assets/flat/L3.webp" },
  L4: { label: "KING",  sub: "CAKE",       cls: "low",  img: "assets/flat/L4.webp" },
  L5: { label: "CANDLE",sub: "",           cls: "low",  img: "assets/flat/L5.webp" },
  H6: { label: "GATOR", sub: "BAYOU",      cls: "high", img: "assets/flat/H6.webp" },
  H7: { label: "BEIGNT",sub: "BEIGNETS",   cls: "high", img: "assets/flat/H7.webp" },
  L6: { label: "KEY",   sub: "SKELETON",   cls: "low",  img: "assets/flat/L6.webp" },
  L7: { label: "COIN",  sub: "DOUBLOON",   cls: "low",  img: "assets/flat/L7.webp" },
  L8: { label: "TAROT", sub: "CARD",       cls: "low",  img: "assets/flat/L8.webp" },
  L9: { label: "BONE",  sub: "",           cls: "low",  img: "assets/flat/L9.webp" },
  L10:{ label: "LAMP",  sub: "GAS",        cls: "low",  img: "assets/flat/L10.webp" },''')
rep('''  H1: "#45c46a", H2: "#6CFC54", H3: "#F5C518", H4: "#C77DFF", H5: "#C77DFF", H6: "#c8e83c", H7: "#C77DFF",
  L1: "#3dff5a", L2: "#ff8a1c", L3: "#eeeeee", L4: "#eeeeee", L5: "#ff5a2a", L6: "#86a548", L7: "#d0d0d0",
  L8: "#8bbf4a", L9: "#f2e34a", L10: "#7ec8f2", M: "#e07a4a", BS: "#9CE424", ES: "#B454E4",''',
'''  H1: "#F2B230", H2: "#c9a26a", H3: "#e8b84a", H4: "#b98cff", H5: "#7CFF6B", H6: "#5fd36a", H7: "#fff3dc",   // voodoo: each symbol's own colour
  L1: "#F2B230", L2: "#9B5CF0", L3: "#ff5a3a", L4: "#a86cff", L5: "#ffd27a", L6: "#9aa0b8", L7: "#ffd24a",
  L8: "#9B5CF0", L9: "#efe6cc", L10: "#ffc95a", M: "#7CFF6B", BS: "#b07cff", ES: "#7CFF6B",''')
rep("const FIRE_WIN = [[.72, .95, .23], [.62, .33, .98], [.98, .36, .62], [.3, .86, .98]];",
    "const FIRE_WIN = [[.95, .7, .19], [.61, .36, .94], [.49, 1, .42], [1, .9, .7]];   // voodoo: gold, violet, spirit green, cream")

# ------------------------------------------------------------------ names in the game's own text
for a, b in (("FULL WALL</b> \\u2014 every cell is a Multi", "VOODOO STORM</b> \\u2014 every cell is a Potion"),
             ("WALL LINE</b> \\u2014 ${cells.length} Multis in a row", "HEX LINE</b> \\u2014 ${cells.length} Potions in a row")):
    rep(a, b)
rep('aria-label="Smukiez"', 'aria-label="Voodoo on Bourbon"')
rep('T("Crew Leader \\u00b7 Bonus")', 'T("FS scatter \\u00b7 Bonus")')
rep('T("The Phantom \\u00b7 Extreme")', 'T("XFS scatter \\u00b7 Extreme")')
rep('alt="${T("Crew Leader")}"', 'alt="${T("FS scatter")}"')
rep('alt="${T("The Phantom")}"', 'alt="${T("XFS scatter")}"')
rep("A Crew Leader trigger with a Phantom on the same spin is upgraded to Extreme.",
    "A FS scatter trigger with a XFS scatter on the same spin is upgraded to Extreme.")
rep("Walls drop in lines of <b>3</b> or <b>4</b> far more often in here",
    "Potions drop in lines of <b>3</b> or <b>4</b> far more often in here")
rep('"smukiez.', '"voodoobourbon.', 0)

# ------------------------------------------------------------------ colours: lime -> Mardi Gras gold, extreme purple -> voodoo green
for a, b in (("108, 252, 84", GOLD_RGB), ("108,252,84", GOLD_RGB), ("168, 240, 0", GOLD_RGB), ("184, 242, 58", GOLD_RGB),
             ("#9CE424", GOLD), ("#E4FC84", "#FFE39A"), ("#B8F23A", GOLD), ("#A8F000", GOLD), ("#3C6C0C", "#7A4A0E"),
             ("#4a840a", "#8A5A10"), ("180, 84, 228", GREEN_RGB), ("180,84,228", GREEN_RGB), ("#B454E4", "#5FE04E"),
             ("#E4B4FC", "#C9FFC0"), ("#EBC9FF", "#D8FFCF"), ("#5a1c9c", "#1F7A2E"), ("192, 38, 216", GREEN_RGB)):
    rep(a, b, 0)

# ------------------------------------------------------------------ the Multi: no pop - it is hexed away
# its value lands with no spray can: the figure condenses out of green spirit smoke (voodooReveal)
rep('''function prepareSpray() {
  if (sprayReady) return sprayReady;''', '''const VOODOO = true;   // Voodoo on Bourbon: Multi values condense out of spirit smoke (voodooReveal), no spray can
function prepareSpray() {
  if (sprayReady) return sprayReady;
  if (VOODOO) return (sprayReady = Promise.resolve(false));''')
rep('''async function sprayRun(cell) {
  const m = cell.ico && cell.ico.querySelector(".multface"), mv = m && m.querySelector(".mv");
  const layer = $("sprayLayer");
  if (!mv || !layer || REDUCED_MOTION) return;''', '''// The value appears by conjuring: a few green spirit wisps spiral in onto the potion and the figure condenses
// out of them - blurred and glowing, tightening, settling - with a soft whoosh-chime. No pop.
async function voodooReveal(m, mv, layer) {
  const t = tempo() / MULTI_RATE, rnd = (a, b) => a + Math.random() * (b - a);
  const [fx, fy] = boardXY(mv), w = mv.offsetWidth, h = mv.offsetHeight, cx = fx + w / 2, cy = fy + h / 2;
  m.classList.remove("bare");
  const anims = [mv.animate([
    { opacity: 0, filter: "blur(7px) brightness(2.4)", transform: "scale(1.35)" },
    { offset: .55, opacity: 1, filter: "blur(1.5px) brightness(1.6)", transform: "scale(.94)" },
    { opacity: 1, filter: "blur(0) brightness(1)", transform: "scale(1)" },
  ], { duration: 620 * t, easing: "cubic-bezier(.3,.6,.3,1)" })];
  const els = [];
  for (let i = 0; i < 7; i++) {
    const e = document.createElement("i");
    e.className = "swisp"; layer.append(e); els.push(e);
    const a0 = rnd(0, 6.28), d = rnd(46, 74), turn = rnd(2.2, 3.4) * (i % 2 ? 1 : -1), k = [];
    for (let s = 0; s <= 6; s++) {
      const p = s / 6, r = d * (1 - p), a = a0 + turn * p;
      k.push({ offset: p, transform: `translate(${(cx + Math.cos(a) * r).toFixed(1)}px, ${(cy + Math.sin(a) * r * .8 - (1 - p) * 10).toFixed(1)}px) scale(${(1.3 - p * .8).toFixed(2)})`,
               opacity: p < .2 ? p * 4 : p > .85 ? (1 - p) * 6 : .85 });
    }
    anims.push(e.animate(k, { duration: 560 * t, delay: 25 * i * t, fill: "both", easing: "cubic-bezier(.4,0,.6,1)" }));
  }
  sfx("reveal", .95 + Math.random() * .1);
  await Promise.all(anims.map(a => a.finished.catch(() => {})));
  els.forEach(e => e.remove());
}
async function sprayRun(cell) {
  const m = cell.ico && cell.ico.querySelector(".multface"), mv = m && m.querySelector(".mv");
  const layer = $("sprayLayer");
  if (!mv || !layer || REDUCED_MOTION) return;
  if (VOODOO) { if (!document.hidden && cell._spray === "on") await voodooReveal(m, mv, layer); return; }''')

# the blow-out: the potion tile dissolves away into spirit smoke instead of shattering (hexIcon, drawn by burstStep)
rep('''function burstIcon(m) {
  if (!m) return;''', '''// The Multi does not pop. It is hexed away: the potion shivers and lifts, burns away from its edges inward in a
// ragged voodoo-green line (a dissolve cut once from a noise field, HEX_STEPS frames, hexKit), its spirit - a
// faint green ghost of the voodoo skull - rises out of it, green smoke curls up on a spiral and motes of
// green and violet drift away. Same canvas and clock as the bursts, so it costs a few drawImage calls a frame.
const HEX_STEPS = 16, HEX_PX = 220, HEX_MS = 900;
let hexKitCache = null;
function hexKit(img) {
  if (hexKitCache && hexKitCache.img === img) return hexKitCache;
  if (!img || !img.naturalWidth) return null;
  const S = HEX_PX, ar = img.naturalHeight / img.naturalWidth, w = S, h = Math.round(S * ar);
  const base = document.createElement("canvas"); base.width = w; base.height = h;
  const bx = base.getContext("2d", { willReadFrequently: true });
  bx.drawImage(img, 0, 0, w, h);
  const src = bx.getImageData(0, 0, w, h);
  // the burn: value noise on two scales, plus distance from the middle, so it eats in from the rim
  let s = 9173; const r = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const G = 9, g = Array.from({ length: (G + 1) * (G + 1) }, r), g2 = Array.from({ length: 33 * 33 }, r);
  const at = (arr, n, x, y) => { const x0 = Math.floor(x), y0 = Math.floor(y), fx = x - x0, fy = y - y0, i = y0 * (n + 1) + x0;
    const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
    return (arr[i] * (1 - sx) + arr[i + 1] * sx) * (1 - sy) + (arr[i + n + 1] * (1 - sx) + arr[i + n + 2] * sx) * sy; };
  const noise = new Float32Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const u = x / w, v = y / h, d = Math.hypot(u - .5, v - .5) * 1.4;
    noise[y * w + x] = Math.min(1, Math.max(0, .55 * at(g, G, u * G * .999, v * G * .999) + .25 * at(g2, 32, u * 31.9, v * 31.9) + .45 * (1 - d) - .1));
  }
  const frames = [];
  for (let k = 0; k < HEX_STEPS; k++) {
    const thr = k / (HEX_STEPS - 1) * 1.1, band = .07;
    const c = document.createElement("canvas"); c.width = w; c.height = h;
    const cx = c.getContext("2d"), out = cx.createImageData(w, h), d = out.data, sd = src.data;
    for (let i = 0; i < w * h; i++) {
      const n = noise[i], a = sd[i * 4 + 3];
      if (!a || n < thr) continue;
      const j = i * 4;
      if (k && n < thr + band) {   // the burning edge: hot voodoo green, white at its very front
        const e = (n - thr) / band;
        d[j] = e < .3 ? 230 : 124; d[j + 1] = 255; d[j + 2] = e < .3 ? 220 : 107; d[j + 3] = a;
      } else { d[j] = sd[j]; d[j + 1] = sd[j + 1]; d[j + 2] = sd[j + 2]; d[j + 3] = a; }
    }
    cx.putImageData(out, 0, 0);
    frames.push(c);
  }
  return (hexKitCache = { img, frames, w, h });
}
function hexIcon(m) {
  const { pic, img, c, drawW } = m, t = tempo(), now = performance.now();
  const kit = hexKit(img);
  if (!kit) return false;
  const W = c.w, rnd = (a, b) => a + Math.random() * (b - a);
  bursts.push({ hex: true, from: now, born: now, t, x: c.x, y: c.y, W, kit, drawW, glow: glowSprite("#7CFF6B"),
    vglow: glowSprite("#9B5CF0"), turn: rnd(-1, 1),
    wisps: [0, 1, 2, 3].map(i => ({ a: i / 4 * 6.28 + rnd(0, 1), r: W * rnd(.12, .26), sp: rnd(.004, .007) * (i % 2 ? 1 : -1), s: rnd(.5, .8) })),
    motes: Array.from({ length: bursts.length > 8 ? 6 : 14 }, () => ({ a: rnd(0, 6.28), r: W * rnd(.1, .4), up: W * rnd(.5, 1.1),
      spin: rnd(-.006, .006), s: W * rnd(.03, .06), at: rnd(80, 380), violet: Math.random() < .35 })) });
  pic.style.visibility = "hidden";   // the canvas carries the potion from its first frame (the dissolve's frame 0 is the whole icon)
  if (!burstRaf) burstRaf = requestAnimationFrame(burstStep);
  return true;
}
function drawHex(ctx, b, now) {
  const age = (now - b.born) / b.t;
  if (age > HEX_MS) return;
  const p = Math.min(1, Math.max(0, (age - 70) / 640)), e = 1 - Math.pow(1 - p, 2);
  const smoke = smokePuff();
  // green smoke first, curling up on a spiral (drawn normal, so it veils as well as glows)
  for (const w of b.wisps) {
    const a = w.a + w.sp * age, r = w.r * (1 + e * .6), rr = b.W * w.s * (.5 + e * .9);
    ctx.globalAlpha = .5 * Math.sin(Math.PI * Math.min(1, age / HEX_MS));
    ctx.drawImage(b.glow, b.x + Math.cos(a) * r - rr, b.y + Math.sin(a) * r * .6 - b.W * .55 * e - rr, rr * 2, rr * 2);
    ctx.globalAlpha *= .6;
    ctx.drawImage(smoke, b.x + Math.cos(a) * r - rr * .8, b.y + Math.sin(a) * r * .6 - b.W * .6 * e - rr * .8, rr * 1.6, rr * 1.6);
  }
  // the potion: shivers, lifts and burns away from the rim
  const f = b.kit.frames[Math.min(HEX_STEPS - 1, Math.floor(p * HEX_STEPS))];
  const dw = b.drawW * (1 + .08 * e), dh = dw * b.kit.h / b.kit.w;
  const shiver = (1 - p) * Math.sin(age / 22) * .05 * b.turn, lift = b.W * .1 * e;
  ctx.save();
  ctx.translate(b.x, b.y - lift); ctx.rotate(shiver);
  ctx.globalAlpha = 1;
  ctx.drawImage(f, -dw / 2, -dh / 2, dw, dh);
  ctx.restore();
}
function drawHexLight(ctx, b, now) {
  const age = (now - b.born) / b.t;
  if (age > HEX_MS) return;
  const p = Math.min(1, age / HEX_MS), e = 1 - Math.pow(1 - p, 2);
  // a green flare as the hex takes hold, then a soft violet bloom under the rising spirit
  if (age < 300) { const q = age / 300, s = b.W * (1 + .7 * q); ctx.globalAlpha = .55 * (1 - q); ctx.drawImage(b.glow, b.x - s / 2, b.y - s / 2, s, s); }
  const vs = b.W * (1.1 + .5 * e); ctx.globalAlpha = .35 * Math.sin(Math.PI * p);
  ctx.drawImage(b.vglow, b.x - vs / 2, b.y - vs / 2 - b.W * .2 * e, vs, vs);
  // the spirit: a ghost of the voodoo skull rising out of the potion, faint and green
  const ghost = FLAT.ES;
  if (ghost && ghost.naturalWidth && age > 160) {
    const q = Math.min(1, (age - 160) / (HEX_MS - 160)), gs = b.W * (.55 + .25 * q);
    ctx.globalAlpha = .45 * Math.sin(Math.PI * q);
    ctx.drawImage(ghost, b.x - gs / 2 + Math.sin(q * 6) * b.W * .04, b.y - gs / 2 - b.W * (.1 + .75 * q), gs, gs);
  }
  // motes: green and violet sparks drifting up on little helices
  for (const m of b.motes) {
    if (age < m.at) continue;
    const q = Math.min(1, (age - m.at) / (HEX_MS - m.at)), a = m.a + m.spin * (age - m.at);
    ctx.globalAlpha = Math.sin(Math.PI * q);
    const s = m.s * (1 - q * .5);
    ctx.drawImage(m.violet ? b.vglow : b.glow, b.x + Math.cos(a) * m.r - s, b.y + Math.sin(a) * m.r * .4 - m.up * q - s, s * 2, s * 2);
  }
}
function burstIcon(m) {
  if (!m) return;
  if (VOODOO && m.name === "M" && !REDUCED_MOTION && hexIcon(m)) return;''')
rep('''  bursts = bursts.filter(b => now - b.born < 1100 * b.t);
  const blown = bursts.filter(b => b.pieces && now >= b.born);''', '''  bursts = bursts.filter(b => now - b.born < (b.hex ? HEX_MS : 1100) * b.t);
  for (const b of bursts) if (b.hex) drawHex(ctx, b, now);   // the hexed potions, under the flying pieces
  const blown = bursts.filter(b => b.pieces && now >= b.born);''')
rep('''  for (const b of bursts) {
    if (now < b.born || !b.pieces) {   // heating up from inside as it strains''', '''  for (const b of bursts) {
    if (b.hex) { drawHexLight(ctx, b, now); continue; }
    if (now < b.born || !b.pieces) {   // heating up from inside as it strains''')
# its sound: a hex whoosh, not the pop
rep('''        setTimeout(() => { sfx("pop", rate); if (i % 3 === 0) sfxGap("paintBurst", 140, rate * .95); multEls[r][y].classList.add("bare"); }, BURST_AT * tempo());''',
    '''        const hexed = VOODOO && geo[i] && geo[i].name === "M";
        setTimeout(() => {
          if (hexed) sfx("vanish", .94 + Math.random() * .12);   // the potion is hexed away: a ghostly whoosh, no pop
          else { sfx("pop", rate); if (i % 3 === 0) sfxGap("paintBurst", 140, rate * .95); }
          multEls[r][y].classList.add("bare");
        }, hexed ? 0 : BURST_AT * tempo());''')
rep('''        burstIcon(geo[i]);   // the icon strains, then comes apart''', '''        burstIcon(geo[i]);   // the icon strains, then comes apart (a potion is hexed away instead)''')

# the Multi going off: a voodoo shudder and a green flare, not a scale pop
rep('''  @keyframes multiboom {
    0%   { transform: scale(1); }
    40%  { transform: scale(1.4) rotate(-4deg); filter: brightness(1.7); }
    100% { transform: scale(1); }
  }''', '''  @keyframes multiboom {   /* Voodoo on Bourbon: the potion shudders as the hex takes it, glowing green - no pop */
    0%   { transform: none; filter: none; }
    20%  { transform: rotate(-4deg) translateY(-2%); filter: brightness(1.35) drop-shadow(0 0 10px rgb(124 255 107)); }
    45%  { transform: rotate(3deg) translateY(-3%); filter: brightness(1.5) drop-shadow(0 0 18px rgb(124 255 107)); }
    70%  { transform: rotate(-2deg) translateY(-2%); filter: brightness(1.3) drop-shadow(0 0 14px rgb(155 92 240)); }
    100% { transform: none; filter: none; }
  }''')
# its values: they condense out of mist when they arrive, and evaporate when a spin clears them (no pop)
rep('''  @keyframes gmultIn {
    0%   { scale: .3; filter: brightness(2.2); }
    55%  { scale: 1.2; filter: brightness(1.5); }
    100% { scale: 1; filter: brightness(1); }
  }''', '''  @keyframes gmultIn {   /* condensing out of spirit mist: big, blurred and glowing, tightening into the figure */
    0%   { scale: 1.45; opacity: 0; filter: blur(8px) brightness(2.4); }
    55%  { scale: .96; opacity: 1; filter: blur(1.5px) brightness(1.5); }
    100% { scale: 1; filter: blur(0) brightness(1); }
  }''')
rep('''  .multlayer .gmult.gone { opacity: 0; scale: .72; transition: opacity .45s ease, scale .45s ease; }''',
    '''  .multlayer .gmult.gone { opacity: 0; scale: 1.18; translate: 0 -28%; filter: blur(7px) brightness(1.6);   /* it evaporates like a spirit */
    transition: opacity .6s ease, scale .6s ease, translate .6s ease, filter .6s ease; }''')

rep("  if (!window.SprayFX || /[?&]norim\b/.test(location.search)) return;   // QA: ?norim shows the painted outlines",
    "  // Voodoo on Bourbon wears its painted iron-lace frames: the graffiti build's live spray-paint rims stay off\n"
    "  // unless ?rim asks for them.\n  if (!window.SprayFX || !/[?&]rim\b/.test(location.search)) return;")

rep('function tvGlitch(el, { strength = 1, every = [1300, 3600], burst = [120, 320] } = {}) {\n  if (REDUCED_MOTION || !el) return;',
    'function tvGlitch(el, { strength = 1, every = [1300, 3600], burst = [120, 320] } = {}) {\n  if (VOODOO_NO_GLITCH || REDUCED_MOTION || !el) return;   // Voodoo on Bourbon: no TV glitch on wins or the bonus screens (owner, 2026-11-08)')

rep('const VOODOO = true;',
    'const VOODOO = true, VOODOO_NO_GLITCH = true;')

rep('    if (state.multiTotal > 0) sfx(pickSfx(["bustA", "bustB"], bustMemo));',
    '    // Voodoo on Bourbon: the sad trombone only once in a while (owner, 2026-11-08) - about one missed round in\n    // four, and never within 45 s of the last one\n    if (state.multiTotal > 0 && Math.random() < BUST_CHANCE && performance.now() - bustAt > BUST_GAP) {\n      bustAt = performance.now();\n      sfx(pickSfx(["bustA", "bustB"], bustMemo));\n    }')

rep('const bustMemo = { last: null };',
    'const bustMemo = { last: null };\nconst BUST_CHANCE = .25, BUST_GAP = 45000;\nlet bustAt = -Infinity;')

rep('    --drip: url("data:image/svg+xml,<svg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 20 24\'><path d=\'M10 1C10 1 3 10 3 15a7 7 0 0 0 14 0C17 10 10 1 10 1z\'/></svg>");',
    '    /* the volatility pips: simple voodoo skulls (cranium, jaw, two eyes and a nose cut out) - was a paint drip */\n    --drip: url("data:image/svg+xml,<svg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 20 24\'><path fill-rule=\'evenodd\' d=\'M10 1.5C5 1.5 2 5 2 9.4c0 2.6 1.2 4.6 3 5.8V18c0 .8.6 1.4 1.4 1.4H7v2.1c0 .6.4 1 1 1s1-.4 1-1v-2.1h2v2.1c0 .6.4 1 1 1s1-.4 1-1v-2.1h.6c.8 0 1.4-.6 1.4-1.4v-2.8c1.8-1.2 3-3.2 3-5.8C18 5 15 1.5 10 1.5zM6.9 8.1a2.1 2.1 0 1 0 0 4.2 2.1 2.1 0 0 0 0-4.2zm6.2 0a2.1 2.1 0 1 0 0 4.2 2.1 2.1 0 0 0 0-4.2zM10 12.6l-1.3 2.3h2.6z\'/></svg>");')

rep('  .reel.spinning { clip-path: inset(0 -60px); }   /* the spin strip stays tight top and bottom */',
    "  .reel.spinning { clip-path: inset(-20px -60px); }   /* Voodoo on Bourbon: the strip runs on to the iron frame's inner edge (18px out) and just under it */")

rep('  .reel.tumbling { clip-path: inset(-24px -60px); }',
    '  .reel.tumbling { clip-path: inset(-20px -60px); }   /* the same line as the spin: tiles show until they pass under the iron */')

rep('    cg.addColorStop(0, "rgba(255,255,255,1)"); cg.addColorStop(.6, "rgba(255,255,255,1)"); cg.addColorStop(1, "rgba(255,255,255,0)");',
    '    // Voodoo on Bourbon: a spirit thread, not paint - a white-hot core going ectoplasm green at its edge\n    cg.addColorStop(0, "rgba(245,255,235,1)"); cg.addColorStop(.45, "rgba(190,255,160,1)"); cg.addColorStop(1, "rgba(124,255,107,0)");')

rep('      g.fillStyle = `rgba(255,255,255,${(.22 + Math.random() * .45).toFixed(2)})`;',
    '      g.fillStyle = Math.random() < .3 ? `rgba(196,140,255,${(.3 + Math.random() * .5).toFixed(2)})`   // magic motes: green, some violet\n                                       : `rgba(160,255,140,${(.3 + Math.random() * .5).toFixed(2)})`;')

rep('    ug.addColorStop(0, "rgba(10,6,16,.075)"); ug.addColorStop(.5, "rgba(10,6,16,.035)"); ug.addColorStop(1, "rgba(10,6,16,0)");',
    '    ug.addColorStop(0, "rgba(124,255,107,.16)"); ug.addColorStop(.5, "rgba(124,255,107,.06)"); ug.addColorStop(1, "rgba(124,255,107,0)");   // a green aura')

rep('let hexKitCache = null;',
    'const hexKits = new Map();   // one dissolve (and green ghost) per symbol picture, cut on first use or while idle')

rep('  if (hexKitCache && hexKitCache.img === img) return hexKitCache;',
    '  if (img && hexKits.has(img.src)) return hexKits.get(img.src);')

rep('  return (hexKitCache = { img, frames, w, h });',
    '  // the icon\'s ghost: its own silhouette washed in ectoplasm green, faintly showing its drawing through\n  const ghost = document.createElement("canvas"); ghost.width = w; ghost.height = h;\n  const gx = ghost.getContext("2d");\n  gx.drawImage(img, 0, 0, w, h);\n  gx.globalCompositeOperation = "source-atop";\n  gx.fillStyle = "rgba(150, 255, 130, .78)"; gx.fillRect(0, 0, w, h);\n  const kit = { img, frames, w, h, ghost };\n  hexKits.set(img.src, kit);\n  return kit;')

rep('  bursts.push({ hex: true, from: now, born: now, t, x: c.x, y: c.y, W, kit, drawW, glow: glowSprite("#7CFF6B"),',
    '  // its spirit: the potion gives up the voodoo skull\'s ghost; every other icon its own\n  const spirit = (m.name === "M" && FLAT.ES && hexKit(FLAT.ES)) || kit;\n  bursts.push({ hex: true, from: now, born: now, t, x: c.x, y: c.y, W, kit, drawW, ghost: spirit.ghost, glow: glowSprite("#7CFF6B"),')

rep('  // the spirit: a ghost of the voodoo skull rising out of the potion, faint and green\n  const ghost = FLAT.ES;\n  if (ghost && ghost.naturalWidth && age > 160) {\n    const q = Math.min(1, (age - 160) / (HEX_MS - 160)), gs = b.W * (.55 + .25 * q);\n    ctx.globalAlpha = .45 * Math.sin(Math.PI * q);',
    "  // the spirit: the icon's green ghost (the potion's is the voodoo skull) rising out of it, swaying as it goes\n  const ghost = b.ghost;\n  if (ghost && age > 120) {\n    const q = Math.min(1, (age - 120) / (HEX_MS - 120)), gs = b.W * (.62 + .3 * q);\n    ctx.globalAlpha = .55 * Math.sin(Math.PI * q);")

rep('  if (VOODOO && m.name === "M" && !REDUCED_MOTION && hexIcon(m)) return;',
    '  // Voodoo on Bourbon: no icon pops or shatters - every one is hexed into its ghost and green mist (owner, 2026-11-08)\n  if (VOODOO && !REDUCED_MOTION && hexIcon(m)) return;')

rep('        const hexed = VOODOO && geo[i] && geo[i].name === "M";\n        setTimeout(() => {\n          if (hexed) sfx("vanish", .94 + Math.random() * .12);   // the potion is hexed away: a ghostly whoosh, no pop\n          else { sfx("pop", rate); if (i % 3 === 0) sfxGap("paintBurst", 140, rate * .95); }',
    '        const hexed = VOODOO && geo[i] && !REDUCED_MOTION, potion = hexed && geo[i].name === "M";\n        setTimeout(() => {\n          // hexed away: the potion with its full ghostly whoosh, the rest with the same whoosh thinned out (never\n          // closer than 110 ms) and a soft glassy ting each, so a big cluster is a shimmer, not a wall of noise\n          if (potion) sfx("vanish", .94 + Math.random() * .12);\n          else if (hexed) { sfxGap("vanish", 110, rate * 1.05); if (i % 2 === 0) sfxGap("glint", 60, rate); }\n          else { sfx("pop", rate); if (i % 3 === 0) sfxGap("paintBurst", 140, rate * .95); }')

rep('function hexIcon(m) {',
    'function warmHexKits() {\n  const imgs = Object.values(FLAT).filter(Boolean), step = () => {\n    const im = imgs.shift();\n    if (!im) return;\n    if (im.complete && im.naturalWidth) hexKit(im); else imgs.push(im);\n    (window.requestIdleCallback || (f => setTimeout(f, 60)))(step);\n  };\n  setTimeout(step, 2500);\n}\nif (VOODOO) warmHexKits();\nfunction hexIcon(m) {')

rep('  const rig = cell.ico ? rigEl(sym.name, def.label) : null;   // an animated symbol, once the rigs have loaded',
    '  // the potion\'s colour tells its value (potionId: green, sapphire, violet, gold, blood red)\n  const rigName = def.cls === "booster" ? potionId(sym.multiplier) : sym.name;\n  const rig = cell.ico ? (rigEl(rigName, def.label) || (rigName !== sym.name ? rigEl(sym.name, def.label) : null)) : null;')

rep('function fillCell(cell, sym) {',
    '// Voodoo on Bourbon: the potion in a colour per value (tools/nola/potion_tiers.py made M2..M5\'s frames and flat icons)\nconst POTION_TIERS = [[2, "M"], [5, "M2"], [20, "M3"], [100, "M4"], [Infinity, "M5"]];\nfunction potionId(v) {\n  if (!v) return "M";\n  for (const [top, id] of POTION_TIERS) if (v <= top + 1e-9) return id;\n  return "M";\n}\nfor (const [, id] of POTION_TIERS) if (id !== "M") { const i = new Image(); i.src = `assets/flat/${id}.webp`; FLAT[id] = i; }\nfunction fillCell(cell, sym) {')

rep('    else if (def.img) {   // the brick chunk; the value is painted over it\n      const im = document.createElement("img");\n      im.src = def.img; im.alt = def.label; im.draggable = false;',
    '    else if (def.img) {   // the potion; the value is painted over it\n      const im = document.createElement("img");\n      im.src = FLAT[rigName] ? FLAT[rigName].src : def.img; im.alt = def.label; im.draggable = false;')

rep('  const spirit = (m.name === "M" && FLAT.ES && hexKit(FLAT.ES)) || kit;',
    '  const spirit = (/^M\\d?$/.test(m.name || "") && FLAT.ES && hexKit(FLAT.ES)) || kit;')

rep('        const hexed = VOODOO && geo[i] && !REDUCED_MOTION, potion = hexed && geo[i].name === "M";',
    '        const hexed = VOODOO && geo[i] && !REDUCED_MOTION, potion = hexed && /^M\\d?$/.test(geo[i].name || "");')

rep('<title>Voodoo on Bourbon</title>',
    '<title>Voodoo on Bourbon</title>\n<link rel="stylesheet" href="assets/vnum/glyphs.css">')

rep('// Voodoo on Bourbon: the potion in a colour per value',
    '// Voodoo on Bourbon: Multi values in the voodoo numerals (tools/nola/vnum.py): each character one glyph picture\nconst VGLYPH = { x: "x", ".": "dot" };\nfunction vNum(el, text) {\n  el.replaceChildren(...[...text].map(ch => { const i = document.createElement("i"); i.className = "vg g-" + (VGLYPH[ch] || ch); return i; }));\n  el.setAttribute("aria-label", text);\n}\n// Voodoo on Bourbon: the potion in a colour per value')

rep('      v.className = "mv"; v.textContent = "x" + fmtMult(sym.multiplier);',
    '      v.className = "mv"; vNum(v, "x" + fmtMult(sym.multiplier));')

rep('    g.textContent = t; g.hidden = false;',
    '    vNum(g, t); g.hidden = false;')

rep('    face.textContent = "x" + fmtMult(values[vi]);',
    '    vNum(face, "x" + fmtMult(values[vi]));')

rep('<div class="fmult" id="featMult">x${fmtMult(FEATURE_VALUES[0])}</div>',
    '<div class="fmult" id="featMult" aria-label="x${fmtMult(FEATURE_VALUES[0])}">${[..."x" + fmtMult(FEATURE_VALUES[0])].map(ch => `<i class="vg g-${VGLYPH[ch] || ch}"></i>`).join("")}</div>')

rep('  caneTap: ["sfx_cane_tap", 3, 0.16],',
    '  landBrick: ["sfx_land_brick", 3, 0.34],   // the SMUKIEZ ident: each letter landing (its own sounds, from zeqpz/slotsgame)\n  caneTap: ["sfx_cane_tap", 3, 0.16],')

rep('<title>Voodoo on Bourbon</title>\n<link rel="stylesheet" href="assets/vnum/glyphs.css">',
    '<title>Voodoo on Bourbon</title>')

rep('<script src="boardgl.js"></script>\n<script>\n"use strict";',
    '<script src="boardgl.js"></script>\n<script src="charrig.js"></script>\n<script>\n"use strict";')

rep('async function makeCharacter({ el, name, flavour, swap = {}, shadow = true }) {\n  const root = document.getElementById(el);\n  if (!root || typeof PIXI === "undefined") return null;',
    'async function makeCharacter({ el, name, flavour, swap = {}, shadow = true }) {\n  // a character with a live rig (charrig.js: Blender\'s bones posed on every refresh) plays that; one without\n  // falls through to its baked frames\n  if (window.CharRig) {\n    const rigged = await CharRig.make({ el, name, flavour, swap, shadow });\n    if (rigged !== undefined) return rigged;\n  }\n  const root = document.getElementById(el);\n  if (!root || typeof PIXI === "undefined") return null;')

rep('function placeScenery() {\n  const root = document.documentElement.style, chars = [$("charfx")].filter(Boolean);\n  root.removeProperty("--char-height");   // the stylesheet\'s size first (an upright screen may cap it below)\n  if (!matchMedia("(max-width: 1100px) and (orientation: portrait)").matches) {\n    root.removeProperty("--char-drop"); root.removeProperty("--tag-top");\n    for (const el of chars) el.style.removeProperty("--char-cut");\n    return;\n  }\n  const stage = document.querySelector(".stage"), board = $("board");\n  if (!stage || !board || !chars.length) return;\n  // two invisible specks on the line through the middle of the frame\'s top band (the band runs\n  // 1% to 4% of the frame art in from its edge, and the art hangs 10px past the board), one at\n  // each end of the stage: placed in its own coordinates, read back on screen with the lean and\n  // the fit applied\n  if (!sceneryProbes) {\n    sceneryProbes = ["left", "right"].map(side => {\n      const p = document.createElement("i");\n      p.setAttribute("aria-hidden", "true");\n      p.style.cssText = `position:absolute;${side}:0;width:1px;height:1px;visibility:hidden;pointer-events:none`;\n      stage.appendChild(p);\n      return p;\n    });\n  }\n  const band = -10 + .025 * (board.offsetHeight + 20);\n  for (const p of sceneryProbes) p.style.top = band.toFixed(1) + "px";\n  const [a, b] = sceneryProbes.map(p => p.getBoundingClientRect());\n  const lineAt = x => a.top + (b.left === a.left ? 0 : (x - a.left) / (b.left - a.left) * (b.top - a.top));\n  const ref = lineAt(innerWidth / 2);\n  // A tablet\'s board fills most of an upright screen, so the room over it is short: there the\n  // pair is sized down until their heads clear the top (their box shows about .58 of its height\n  // over the board: .65 above the line, less the lift and the canvas headroom). The box is\n  // --char-height x 1.3 x 1.2 tall. (2026-11-03 QA: 768x1024 had their heads cut off at the top.)\n  const fitsH = (ref - 22) / .6;\n  if (chars[0].offsetHeight > fitsH && fitsH > 40) root.setProperty("--char-height", (fitsH / 1.56).toFixed(1) + "px");\n  const feet = ref + .35 * chars[0].offsetHeight;                 // the character boxes\' bottom edge\n  root.setProperty("--char-drop", (feet - innerHeight).toFixed(1) + "px");   // bottom = screen bottom - feet\n  // #walltag\'s top is its centre (it is moved up half its height), measured inside #bgwall,\n  // which starts 4% of the screen above the screen\'s top\n  root.setProperty("--tag-top", (ref - .08 * innerHeight + .04 * innerHeight).toFixed(1) + "px");\n  // each figure\'s cut, in its own box: worked out down its centre column, where the lean (a\n  // turn about that column) moves nothing up or down, from its lift and its depth scale (both\n  // taken about its bottom edge)\n  for (const el of chars) {\n    const cs = getComputedStyle(el), h = el.offsetHeight;\n    const lift = (parseFloat(cs.getPropertyValue("--char-lift")) || 0) / 100 * h;\n    const depth = parseFloat(cs.scale) || 1;\n    const r = el.getBoundingClientRect();\n    const cut = (feet - lift - lineAt(r.left + r.width / 2)) / depth;\n    el.style.setProperty("--char-cut", Math.max(0, Math.min(h, cut)).toFixed(1) + "px");\n  }\n}\naddEventListener("resize", fitToScreen);\n',
    '// Doc stands on the left sidewalk of the street (owner, 2026-11-09: "always standing on the sidewalk"), wherever the\n// screen puts the painting. WALK is that sidewalk on the plate (assets/bonus_wall.webp) as fractions of it, read off\n// the painting: its back edge along the shop fronts and its front edge along the curb\'s top, each a line over x; he\n// stands DEPTH of the way out from the shops toward the curb (near the curb: he is big, so he is near us).\nconst WALK = { back: [[0, .745], [.2, .73], [.3, .705], [.37, .69]],\n               front: [[0, .925], [.1, .9], [.2, .852], [.3, .81], [.37, .796]], depth: .7, x: [.07, .33] };\nconst walkEdge = (fx, edge) => {\n  const e = WALK[edge];\n  if (fx <= e[0][0]) return e[0][1];\n  for (let i = 1; i < e.length; i++) {\n    if (fx <= e[i][0]) { const [x0, y0] = e[i - 1], [x1, y1] = e[i]; return y0 + (y1 - y0) * (fx - x0) / (x1 - x0); }\n  }\n  return e[e.length - 1][1];\n};\nconst walkAt = fx => walkEdge(fx, "back") + (walkEdge(fx, "front") - walkEdge(fx, "back")) * WALK.depth;\n// A landscape screen: the painting covers the window as it always has; Doc\'s box is moved up or down (--char-walk)\n// until his soles - the box\'s bottom edge, where his canvas stands them - are on the sidewalk under his shoes.\nfunction standOnWalk(el) {\n  const scene = $("bgscene");\n  if (!scene || el.classList.contains("bounce")) return;\n  el.style.setProperty("--char-walk", "0px");\n  const s = scene.getBoundingClientRect(), r = el.getBoundingClientRect();\n  if (!s.width || !r.height) return;\n  const fx = Math.max(WALK.x[0], Math.min(WALK.x[1], (r.left + r.width * .5 - s.left) / s.width));\n  const target = Math.min(innerHeight - 4, s.top + walkAt(fx) * s.height);\n  el.style.setProperty("--char-walk", (r.bottom - target).toFixed(1) + "px");\n}\nconst sceneStyle = ["width", "height", "left", "top", "translate"];\nfunction placeScenery() {\n  const root = document.documentElement.style, chars = [$("charfx")].filter(Boolean), scene = $("bgscene");\n  root.removeProperty("--char-height");   // the stylesheet\'s size first (an upright screen may cap it below)\n  if (!matchMedia("(max-width: 1100px) and (orientation: portrait)").matches) {\n    root.removeProperty("--char-drop"); root.removeProperty("--tag-top");\n    if (scene) for (const k of sceneStyle) scene.style.removeProperty(k);\n    for (const el of chars) { el.style.removeProperty("--char-cut"); standOnWalk(el); }\n    return;\n  }\n  // An upright phone or tablet: the board fills the bottom of the screen, and the street is framed above it - the\n  // painting scaled and moved so its left sidewalk runs just over the iron frame\'s spikes, sky, moon and spires above\n  // - and Doc stands on that sidewalk, whole, his shoes just clear of the iron (no longer half behind the board).\n  const frame = $("paintframe"), wall = $("bgwall");\n  if (!frame || !scene || !wall || !chars.length) return;\n  const el = chars[0], cs = getComputedStyle(el);\n  for (const e of chars) { e.style.removeProperty("--char-cut"); e.style.setProperty("--char-walk", "0px"); }\n  const fr = frame.getBoundingClientRect();\n  const sole = fr.top + .004 * fr.height - 2;                     // just over the spike tips\n  // his standing height (1.3 x --char-height; the box is 1.56 x) fits between the top of the screen and the sole\n  const room = (sole - 10) / 1.3;\n  if (el.offsetHeight / 1.56 > room && room > 30) root.setProperty("--char-height", room.toFixed(1) + "px");\n  const h = el.offsetHeight, lift = (parseFloat(cs.getPropertyValue("--char-lift")) || 0) / 100 * h;\n  root.setProperty("--char-drop", (sole + lift - innerHeight).toFixed(1) + "px");   // bottom edge = sole + lift\n  root.removeProperty("--tag-top");\n  // the painting: its sidewalk (a fifth of the way along it, between the lamp post and the corner) under his shoes,\n  // at the sole line; big enough that it still reaches the top of the screen and both its sides\n  const r = el.getBoundingClientRect(), footX = r.left + r.width * .5, fx = .2, wy = walkAt(fx);\n  const Hp = Math.max(sole / wy, (innerWidth - footX) / ((1 - fx) * 16 / 9), Math.max(0, footX) / (fx * 16 / 9));\n  const Wp = Hp * 16 / 9, ox = footX - fx * Wp, oy = sole - wy * Hp, wr = wall.getBoundingClientRect();\n  Object.assign(scene.style, { width: Wp.toFixed(1) + "px", height: Hp.toFixed(1) + "px",\n    left: (ox - wr.left).toFixed(1) + "px", top: (oy - wr.top).toFixed(1) + "px", translate: "none" });\n}\naddEventListener("resize", fitToScreen);')

rep('  const fromOgg = () => fetchMusic(name).then(b => actx.decodeAudioData(b)).then(buf => ({ buf, at: 0 }));\n  const fromAac = () => (OPUS_OK ? fetch(m.aac).then(r => r.arrayBuffer()) : fetchMusic(name)).then(b => actx.decodeAudioData(b))',
    '  // (decodeAudioData empties the bytes it is handed: the cached copy is kept whole for the next decode)\n  const fromOgg = () => fetchMusic(name).then(b => actx.decodeAudioData(b.slice(0))).then(buf => ({ buf, at: 0 }));\n  const fromAac = () => (OPUS_OK ? fetch(m.aac).then(r => r.arrayBuffer()) : fetchMusic(name).then(b => b.slice(0))).then(b => actx.decodeAudioData(b))')

rep('  for (const sheet of document.styleSheets) {\n    try { walk(sheet.cssRules); } catch (err) { /* a sheet from elsewhere: nothing to read */ }\n  }',
    "  for (const sheet of document.styleSheets) {\n    try { walk(sheet.cssRules); } catch (err) { /* a sheet from elsewhere: nothing to read */ }\n  }\n  // art the voodoo build never shows, though the base build's rules still name it: not fetched, not held\n  if (VOODOO) for (const u of [...urls]) if (UNSHOWN_ART.test(u)) urls.delete(u);")

rep('function assetUrls() {',
    'const UNSHOWN_ART = /assets\\/(wall_tag|plate_grey|brickwall|spin_plate|spin_btn_arrows)\\.webp|assets\\/wallfx\\/|assets\\/rim\\//;\nfunction assetUrls() {')

rep('  urls.add("assets/wall_tag.webp");   // the tag on the wall is an <img>, so no rule names it',
    '  if (!VOODOO) urls.add("assets/wall_tag.webp");   // the tag on the wall is an <img>, so no rule names it')

rep('  if (REDUCED_MOTION) for (const id of Object.keys(TIER))',
    '  if (REDUCED_MOTION && !VOODOO) for (const id of Object.keys(TIER))')

rep('<img id="walltag" src="assets/wall_tag.webp"',
    '<img id="walltag" alt=""')

rep('<head>',
    '<head>\n<link rel="icon" href="data:,">')

rep('{ mode: "extremebonus", key: "xfs", title: "Free Spins",',
    '{ mode: "extremebonus", key: "xfs", title: "Xtreme Free Spins",')

rep('  $("betVal").textContent = fmt(shown);\n  fitFigure($("betVal"), fmt(shown));',
    '  $("betVal").textContent = fmt(shown);\n  fitFigure($("betVal"), fmt(shown));\n  if (!state.playing && !(shownWin > 0)) $("roundWin").textContent = fmt(0);   // an empty WIN, in the currency')

rep('eachCell((el, r, y) => setCell(r, y, { name: ["L1","L2","L3","L4","L5"][(r + y) % 5] }));',
    '{\n  const pool = ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "H1", "H2", "H3", "H4", "L1", "L3", "L5", "L7"];\n  let seed = 20261109;\n  const rnd = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;\n  const grid = {};\n  eachCell((el, r, y) => {\n    let name, n = 0;\n    do { name = pool[Math.floor(rnd() * pool.length)]; n++; }\n    while (n < 20 && SYM[name] === undefined || n < 20 && (grid[(r - 1) + ":" + y] === name || grid[r + ":" + (y - 1)] === name));\n    grid[r + ":" + y] = SYM[name] ? name : "L1";\n    setCell(r, y, { name: grid[r + ":" + y] });\n  });\n}')

rep('function standOnWalk(el) {\n  const scene = $("bgscene");\n  if (!scene || el.classList.contains("bounce")) return;\n  el.style.setProperty("--char-walk", "0px");\n  const s = scene.getBoundingClientRect(), r = el.getBoundingClientRect();\n  if (!s.width || !r.height) return;',
    '// Doc\'s reach in his drawing (art px): his centre line, standing height, cane tip and open fingertips\nconst DOC_ART = { cx: 512, rest: 1502, left: 150, right: 990 };\nfunction standOnWalk(el) {\n  const scene = $("bgscene"), frame = $("paintframe");\n  if (!scene || el.classList.contains("bounce")) return;\n  el.style.setProperty("--char-walk", "0px");\n  el.style.setProperty("--char-nudge", "0px");\n  let r = el.getBoundingClientRect();\n  const s = scene.getBoundingClientRect();\n  if (!s.width || !r.height) return;\n  // his open hand clear of the iron frame: the box slides left until it is, never so far the cane leaves the screen\n  if (frame) {\n    const hr = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--char-headroom")) || 1;\n    const k = r.height / hr / DOC_ART.rest, mid = r.left + r.width / 2;\n    const over = mid + (DOC_ART.right - DOC_ART.cx) * k + 6 - frame.getBoundingClientRect().left;\n    const room = mid + (DOC_ART.left - DOC_ART.cx) * k - 4;\n    const nudge = Math.max(0, Math.min(over, room));\n    if (nudge > 0) { el.style.setProperty("--char-nudge", nudge.toFixed(1) + "px"); r = el.getBoundingClientRect(); }\n  }')

rep('{ mode: "extremebonus", key: "xfs", title: "Xtreme Free Spins",',
    '{ mode: "extremebonus", key: "xfs", title: "Xtreme Spins",')

rep('    await Promise.all(ids.map(id => symSheet(id, "land")));\n    (async () => {\n      for (const clip of ["hit", "idle", "multi"]) await Promise.all(ids.map(id => symSheet(id, clip).catch(() => {})));\n    })();\n    return ids.length > 0;\n  })().catch(e => { console.warn("animated symbols unavailable:", e); return false; });\n  return symReady;\n}',
    '    await Promise.all(ids.map(id => symSheet(id, "land")));\n    SYMF.rest = (async () => {\n      for (const clip of ["hit", "idle", "multi"]) await Promise.all(ids.map(id => symSheet(id, clip).catch(() => {})));\n    })();\n    return ids.length > 0;\n  })().catch(e => { console.warn("animated symbols unavailable:", e); return false; });\n  return symReady;\n}\n// Every clip in, cut and on the GPU (perf, 2026-11-09): the loading screen and a replay\'s Play wait on this.\n// The landings alone used to let the game in, and the hit, idle and Multi clips were decoded, resized and\n// uploaded while the first round was already playing (~2.5 s of a slow phone\'s main thread).\nconst symAllReady = () => loadSymFrames().then(ok => (SYMF.rest || Promise.resolve()).then(() => symHoldQ).then(() => ok));')

rep('function warmHexKits() {\n  const imgs = Object.values(FLAT).filter(Boolean), step = () => {\n    const im = imgs.shift();\n    if (!im) return;\n    if (im.complete && im.naturalWidth) hexKit(im); else imgs.push(im);\n    (window.requestIdleCallback || (f => setTimeout(f, 60)))(step);\n  };\n  setTimeout(step, 2500);\n}\nif (VOODOO) warmHexKits();',
    '// a picture that has arrived (true) or failed (false)\nconst picReady = img => img.complete ? Promise.resolve(img.naturalWidth > 0) : new Promise(r => {\n  img.addEventListener("load", () => r(true), { once: true }); img.addEventListener("error", () => r(false), { once: true });\n});\nconst nextTask = () => new Promise(r => setTimeout(r, 0));\n// Every kit cut while the loading screen is up, one per task (perf, 2026-11-09): they used to wait for idle\n// moments, which a busy board seldom has, so the first Multi\'s hex cut its kit mid-round\nfunction warmHexKits() {\n  return Object.values(FLAT).filter(Boolean).reduce((p, im) => p.then(() => picReady(im)).then(ok => { if (ok) hexKit(im); return nextTask(); }), Promise.resolve());\n}\n// what the round draws for the first time - the dissolves and the motion blur - made once, before play\nlet fxReady = null;\nconst warmFX = () => fxReady || (fxReady = Promise.all([VOODOO ? warmHexKits() : null, makeSmears()]).catch(() => {}));')

rep('function makeSmears() {\n  if (REDUCED_MOTION) return;\n  const names = Object.keys(FLAT), tries = {};\n  // one symbol a turn - a few ms of pixel work - close behind one another: the first spin wants them\n  // all, and a page drawing every frame has little idle time to wait for\n  const idle = window.requestIdleCallback ? f => requestIdleCallback(f, { timeout: 200 }) : f => setTimeout(f, 40);\n  const next = () => {\n    const name = names.shift();\n    if (!name) return;\n    const img = FLAT[name];\n    if (img.complete && img.naturalWidth) {\n      makeSmear(img).then(url => {',
    'function makeSmears() {\n  if (REDUCED_MOTION) return Promise.resolve();\n  const names = Object.keys(FLAT), made = [];\n  // one symbol a task - a few ms of pixel work - close behind one another, while the loading screen is up:\n  // the first spin wants them all (perf, 2026-11-09: in idle moments after the loader, a replay or a quick\n  // first spin cut them mid-round). Settles once every one is made and decoded.\n  return names.reduce((p, name) => p.then(() => picReady(FLAT[name])).then(ok => {\n    const img = FLAT[name];\n    if (ok) {\n      made.push(makeSmear(img).then(url => {')

rep('          eachCell((el, r, y) => { if (shownSym[r] && shownSym[r][y] && shownSym[r][y].name === name) smearOn(el, name); });\n        });\n      }).catch(() => { /* that symbol falls without a blur */ });\n    } else if ((tries[name] = (tries[name] || 0) + 1) < 20) names.push(name);   // its picture is still on its way\n    idle(next);\n  };\n  idle(next);\n}',
    '          eachCell((el, r, y) => { if (shownSym[r] && shownSym[r][y] && shownSym[r][y].name === name) smearOn(el, name); });\n        });\n      }).catch(() => { /* that symbol falls without a blur */ }));\n    }\n    return nextTask();\n  }), Promise.resolve()).then(() => Promise.all(made));\n}')

rep("  waits.push(one(loadSymFrames()));  // the animated symbols: Blender's frames (the landings; the rest follows)",
    "  waits.push(one(symAllReady()));    // the animated symbols: Blender's frames, every clip cut and uploaded\n  waits.push(one(warmFX()));         // the dissolves and the motion blur, cut before the first round")

rep('  loaded.then(() => { if (fill) fill.style.width = "100%"; warmBursts(); makeSmears(); });',
    '  loaded.then(() => { if (fill) fill.style.width = "100%"; if (!VOODOO) warmBursts(); });   // (no icon bursts in the voodoo build: each is hexed)')

rep('  await Promise.race([Promise.all([loadSymFrames(), prepareSpray(), charsLoaded]).catch(() => {}), new Promise(r => setTimeout(r, 15000))]);',
    '  await Promise.race([Promise.all([symAllReady(), prepareSpray(), charsLoaded, warmFX()]).catch(() => {}), new Promise(r => setTimeout(r, 15000))]);')

rep('    SYMF.rest = (async () => {\n      for (const clip of ["hit", "idle", "multi"]) await Promise.all(ids.map(id => symSheet(id, clip).catch(() => {})));\n    })();',
    '    SYMF.rest = (async () => {\n      for (const clip of ["hit", "multi"]) await Promise.all(ids.map(id => symSheet(id, clip).catch(() => {})));\n    })();\n    SYMF.rest.then(() => Promise.all(ids.map(id => symSheet(id, "idle").catch(() => {}))));')

rep("// Every clip in, cut and on the GPU (perf, 2026-11-09): the loading screen and a replay's Play wait on this.\n// The landings alone used to let the game in, and the hit, idle and Multi clips were decoded, resized and\n// uploaded while the first round was already playing (~2.5 s of a slow phone's main thread).",
    "// The clips a round plays within seconds, cut and on the GPU (perf, 2026-11-09): the loading screen and a\n// replay's Play wait on this. The landings alone used to let the game in, and the hit, idle and Multi clips were\n// resized on the page while the first round was playing (~2.5 s of a slow phone's main thread). Now every sheet\n// is resized in the board's workers (boardgl.js), and only the idles - the biggest clip, which a resting symbol\n// can do without for a moment (it holds its rest pose) - are still arriving once the game is up.")

rep('for (const [, id] of POTION_TIERS) if (id !== "M") { const i = new Image(); i.src = `assets/flat/${id}.webp`; FLAT[id] = i; }',
    'for (const [, id] of POTION_TIERS) if (id !== "M") { const i = new Image(); i.src = `assets/flat/${id}.webp`; FLAT[id] = i; }\n// the potions\' liquid colours (sampled from assets/flat/M..M5, lifted a touch to read as glowing text): the win\n// figure and its "x" wear the colour of the bottle their value comes in (owner, 2026-11-09)\nconst POTION_INK = { M: [157, 255, 110], M2: [104, 212, 255], M3: [184, 132, 255], M4: [255, 170, 64], M5: [255, 66, 102] };\nconst potionInk = v => POTION_INK[potionId(v)];\nconst rgbCss = c => `rgb(${c.map(Math.round).join(", ")})`;')

rep('  const final = amount, m = mult > 1 ? mult : 1, base = final / m;\n  const paint = (v, exact) => {\n    const t = winFigure(v, exact);\n    if (t === num.textContent) return;   // only a new figure is drawn (and its new colour)\n    num.textContent = t;\n    chip.style.color = `hsl(${(100 + 185 * Math.min(1, v / Math.max(1e-9, final))).toFixed(0)} 90% 64%)`;   // green -> purple\n  };\n  const slamTag = () => {\n    const tag = document.createElement("span");\n    tag.className = "wpx";\n    tag.textContent = "x" + fmtMult(m);',
    '  const final = amount, m = mult > 1 ? mult : 1, base = final / m;\n  // its colour is a potion\'s (POTION_INK): the plain potion\'s green while it counts what the cluster is worth; when\n  // Multis pay in, it runs on into the colour of the bottle their total comes in as it climbs to what it pays\n  const inkFrom = POTION_INK.M, inkTo = potionInk(m);\n  const paint = (v, exact) => {\n    const t = winFigure(v, exact);\n    if (t === num.textContent) return;   // only a new figure is drawn (and its new colour)\n    num.textContent = t;\n    const k = m > 1 ? Math.min(1, Math.max(0, (v - base) / Math.max(1e-9, final - base))) : 0;\n    chip.style.color = rgbCss(inkFrom.map((c, i) => c + (inkTo[i] - c) * k));\n  };\n  const slamTag = () => {\n    const tag = document.createElement("span");\n    tag.className = "wpx";\n    tag.style.color = rgbCss(inkTo);     // the "x" in the colour of the bottle that value comes in\n    tag.textContent = "x" + fmtMult(m);')

rep('  .reel.spinning { clip-path: inset(-20px -60px); }',
    '  .reel.spinning { clip-path: inset(-20px -60px calc(-1 * var(--reel-floor, 20px)) -60px); }')

rep('  .reel.tumbling { clip-path: inset(-20px -60px); }',
    '  .reel.tumbling { clip-path: inset(-20px -60px calc(-1 * var(--reel-floor, 20px)) -60px); }')

rep("// figures still on their way down: the bar's WIN counts once they have landed\nlet winGates = [];",
    '// a cluster\'s figure landing in the bar adds its amount there and then, with a quick count (owner, 2026-11-09: in a\n// normal round and in a bonus alike, never waiting for the spin to end); the board\'s tally (setRoundWin) then only\n// makes up any difference\nfunction bumpRoundWin(amount, gen) {\n  if (!(amount > 0) || gen !== hudWinGen) return;\n  const el = $("roundWin"), stat = $("winStat"), from = hudWinShown;\n  hudWinShown = from + amount;\n  if (stat) stat.classList.remove("zero");\n  if (!REDUCED_MOTION) { el.classList.remove("pop"); restyle(el); el.classList.add("pop"); }\n  countTo(el, from, hudWinShown, Math.min(countMs(), 420 * tempo()));\n}\n// figures still on their way down: the bar\'s WIN counts once they have landed\nlet winGates = [];')

rep('      if (gen !== hudWinGen || v <= hudWinShown) return;',
    '      if (gen !== hudWinGen) return;\n      if (v <= hudWinShown) {   // the figures already brought it here: only a rounding difference left to settle\n        if (v < hudWinShown) { hudWinShown = v; countTo(el, v, v, 0); }\n        return;\n      }')

rep('  const gone = () => !chip.isConnected;\n  const bye = () => chip.remove();',
    '  const gone = () => !chip.isConnected;\n  const bye = () => chip.remove();\n  const hudGen = hudWinGen;   // the round this figure belongs to (bumpRoundWin)')

rep("    await flyWinToHud(chip);                  // pulled down into the bar's WIN, which pops and counts up\n    landed();",
    "    await flyWinToHud(chip);                  // pulled down into the bar's WIN, which pops and counts up\n    bumpRoundWin(final, hudGen);              // ...at once, by this cluster's amount\n    landed();")

rep('       Sized for the 7x7 cluster board: seven of these, gaps included, take about the room\n       the old 5x4 board did. */\n    --cell-w: 115px;   /* 20% up from 96 / 82 / 6 on 2026-10-06: the board fills more of the middle */\n    --cell-h: 98px;',
    "       Sized for the 5x5 cluster board (2026-11-09, from Tipsy Harvest): five of these, gaps included, take the\n       same 847 x 728 px the 7x7 board's 115 x 98 cells did, so the board and its iron frame keep their size and\n       every icon is 43% bigger. */\n    --cell-w: 164px;\n    --cell-h: 140px;")

rep('const FLAT = {};   // the flat icon pictures, kept: the paytable, the shards of a blown-out tile and the fallback all draw them',
    '// The 5x5 game (math voodoo_5x5, 2026-11-09) keeps three lows - fleur-de-lis, crawfish, king cake: the others never\n// land, so they are not loaded, not drawn in a celebration\'s shower and not offered anywhere (their art stays in assets/)\nfor (const k of ["L2", "L5", "L6", "L7", "L8", "L9", "L10"]) delete SYM[k];\nconst FLAT = {};   // the flat icon pictures, kept: the paytable, the shards of a blown-out tile and the fallback all draw them')

rep('const REELS = 7, ROWS = 7;   // the 7x7 cluster board; the events still pad every reel by one row top and bottom',
    'const REELS = 5, ROWS = 5;   // the 5x5 cluster board (2026-11-09, math games/voodoo_5x5; was 7x7); the events still pad every reel by one row top and bottom')

rep('const FALLBACK_STRIP = ["L1", "H4", "L3", "H1", "L5", "H3", "L2", "H5", "L4", "H2"];',
    'const FALLBACK_STRIP = ["L1", "H4", "L3", "H1", "L4", "H3", "L1", "H5", "L3", "H2"];   // 5x5 symbol set: no L2 / L5-L10')

rep('  const pool = ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "H1", "H2", "H3", "H4", "L1", "L3", "L5", "L7"];',
    '  const pool = ["L1", "L3", "L4", "H1", "H2", "H3", "H4", "H5", "H6", "H7", "L1", "L3", "L4"];   // only the 5x5 game\'s symbols')

# ------------------------------------------------------------------ the voodoo look (appended to the stylesheet)
CSS = '''
  /* ---- Voodoo on Bourbon (2026-11-08) ---------------------------------------------------------------
     The background is Bourbon Street at night: a plate with every light off (assets/bonus_wall.webp) in
     #bgscene, a 16:9 box sized to cover the window, with bgscene.js putting the lights, the moon, the
     stars and the fog back on top and keeping them alive. No graffiti tag, neon tube or drips, no lean. */
  :root {
    --scene-yaw: 0deg; --wall-scale: cover;
    --spray: #9B5CF0; --spray-deep: #5B2A86; --gold: #F2B230; --fs-green: #F2B230; --fs-purple: #7CFF6B;
    --hud-on: #F2B230; --hud-fill: rgba(28, 14, 40, .58); --hud-soft: #d6c7ea; --hud-ink: #f6f0ff;
  }
  #walltag, .tagfx, #wallpaint, #walllight { display: none !important; }
  #bgwall { background: #0d0b1c; transform: none; container-type: size; }
  #bgscene {
    position: absolute; left: 50%; top: 50%; translate: -50% -50%;
    width: max(100cqw, 177.78cqh); height: max(100cqh, 56.25cqw);
    background: url("assets/bonus_wall.webp") center / 100% 100% no-repeat; overflow: hidden;
  }
  #bgscene::after {   /* a touch darker toward the pavement, so the board reads */
    content: ""; position: absolute; inset: 0; z-index: 5; pointer-events: none;
    background: linear-gradient(rgba(12, 6, 24, .04), rgba(12, 6, 24, .26));
  }
  #bgscene .bgl { position: absolute; mix-blend-mode: plus-lighter; will-change: opacity; }
  #bgscene .bgl img { position: absolute; inset: 0; width: 100%; height: 100%; }
  #bgscene .bgl b { position: absolute; inset: -60%; border-radius: 50%; pointer-events: none; }
  #bgscene .bgl.neon b { inset: -25%; }
  #bgscene .bgl.moon b { inset: -30%; }
  #bgscene .bgl.street { z-index: 1; }
  #bgscene .bgstars { position: absolute; inset: 0; width: 100%; height: 100%; mix-blend-mode: plus-lighter; }
  #bgscene .bgmist {
    position: absolute; left: 0; width: 100%; z-index: 3; mix-blend-mode: screen; opacity: var(--op);
    background-repeat: repeat-x; background-size: auto 100%;
    animation: bgmistdrift var(--dur) linear infinite, bgmistbreathe var(--br) ease-in-out infinite alternate;
  }
  @keyframes bgmistdrift { from { background-position-x: 0; } to { background-position-x: calc(var(--dir) * 200cqh); } }
  @keyframes bgmistbreathe { from { opacity: calc(var(--op) * .55); translate: 0 1.5%; } to { opacity: var(--op); translate: 0 -1.5%; } }
  @media (prefers-reduced-motion: reduce) { #bgscene .bgmist { animation: none; } }
  /* the reels sit on a deep violet see-through shade of the street, not the graffiti build's grey plate */
  /* an opaque painted backing (assets/board_bg.webp: midnight velvet, fleur-de-lis damask) filling the frame's
     opening: the plate sits 14px in, the iron's opening 18px in, so it runs 4px under the lace all round and no
     street shows between the two; a dark inner shadow fades its edge into the black iron */
  .boardplate { display: none; }
  /* #paintback: the opaque velvet backing cut to the iron frame's own opening (tools/nola/board_back.py: flood-filled
     through every gap between the spikes and the lace up to the solid iron, grown under the metal, shadow baked in),
     drawn in exactly the frame's box and just behind it, so it fits the outline wherever the frame is placed */
  #paintback {
    position: absolute; pointer-events: none; user-select: none; z-index: -1;   /* behind the reels and their canvas, like the plate was */
  }
  /* the iron-lace frame (assets/frame.webp): its opening sized round the board (tools/nola: frame fracs) */
  /* (literal fractions: --fx/--fy are the frame's idle drift in px, set by frameIdle) */
  #paintframe, #paintback {
    width: calc((100% - 36px) / .8273); height: calc((100% - 36px) / .6816);
    left: calc(18px - (100% - 36px) * .10330); top: calc(18px - (100% - 36px) * .22724);
  }
  /* the skull candle's live flame (candleflame.js) on its wick: 95.23% across and 6.2% down the frame's box; the
     canvas is 13% x 13% of the frame (wide enough for the glow to fade inside it), its wick drawn at 50% across and 86% down it */
  #candleflame {
    position: absolute; z-index: 4; pointer-events: none;
    width: calc((100% - 36px) / .8273 * .13); height: calc((100% - 36px) / .6816 * .13);
    left: calc(18px - (100% - 36px) * .10330 + (100% - 36px) / .8273 * .8873);
    top: calc(18px - (100% - 36px) * .22724 - (100% - 36px) / .6816 * .0498);
  }
  /* The iron frame hangs past the board's own box - about 0.2 of its height above and below and 0.08 of its width at
     the sides (the fractions above). fitToScreen() sizes the page by the board's box, so the board carries that
     overhang as margin: the fit then shrinks the board until the whole frame, and the HUD under it, are on screen
     (owner, 2026-11-08: the frame ran off the top and over the bar). */
  .board { margin: calc(.205 * var(--bh, 781px)) calc(.085 * var(--bw, 963px)); }
  /* the spirit wisps that conjure a Multi's value (voodooReveal) */
  .spraylayer .swisp {
    width: 18px; height: 18px; margin: -9px 0 0 -9px; border-radius: 50%;
    background: radial-gradient(circle, rgba(220, 255, 210, .95) 0, rgba(124, 255, 107, .7) 35%, rgba(124, 255, 107, 0) 70%);
    mix-blend-mode: screen;
  }

  /* ---- owner pass 2026-11-08 ---- */
  /* no neon glow round the Bonus button, and no pulsing glow outline round the FS / XFS tiles */
  .bonusbtn .bglow, .bonuspanel h3 .bglow { display: none !important; }
  .cell.scat img, .cell.scat .rigin, .cell.escat img, .cell.escat .rigin { animation: none !important; filter: none !important; }
  /* no pink flash round the board when a spin starts (the hop stays) */
  .board.pop::after { animation: none !important; }
  .bspips i { width: 20px; height: 24px; }
  .cell.scat.scatland img, .cell.scat.scatland .rigin, .cell.escat.scatland img, .cell.escat.scatland .rigin {
    animation: scatland calc(.7s * var(--tempo, 1)) cubic-bezier(.25,.85,.35,1) !important;   /* the landing punch, no glow */
  }
  .cell .tglows { display: none !important; }   /* the graffiti build's neon tier glows were traced from the old icons */
  /* the win line's runs of paint are spirit wisps now: a small green glow that rises off the thread and fades */
  .lineLayer b {
    width: 9px !important; height: 9px !important; margin: -4.5px 0 0 -4.5px !important; border-radius: 50%;
    background: radial-gradient(circle, rgba(235,255,225,.95) 0, rgba(124,255,107,.75) 40%, rgba(124,255,107,0) 72%) !important;
    filter: none !important; mix-blend-mode: screen;
    animation: lineWisp calc(1.2s * var(--tempo, 1)) cubic-bezier(.3, .5, .4, 1) forwards !important;
  }
  @keyframes lineWisp {
    0%   { transform: translate(0, 0) scale(.4); opacity: 0; }
    25%  { opacity: 1; }
    100% { transform: translate(calc(var(--len, 16px) * .3), calc(var(--len, 16px) * -1.8)) scale(1.3); opacity: 0; }
  }
  /* Multi values in voodoo numerals (vNum: one glyph picture a character) with a stitched voodoo border */
  .vg { display: inline-block; height: 1em; background: center / contain no-repeat; vertical-align: bottom; margin: 0 -.035em; }
  .multlayer .gmult { font-size: calc(32px * var(--shrink, 1)); text-shadow: none; }
  .multlayer .gmult::before {
    inset: -4% !important; -webkit-mask: none !important; mask: none !important; filter: none !important;
    background: url("assets/vnum/border.webp") center / 100% 100% no-repeat !important;
  }
  .cell.booster .multface .mv {
    font-size: 26px; padding: .42em .5em .36em; line-height: 0; text-shadow: none;
    background: url("assets/vnum/border.webp") center / 100% 100% no-repeat;
    filter: drop-shadow(0 2px 3px rgba(0, 0, 0, .6));
  }
  .fbox .fmult { text-shadow: none; }
  /* the voodoo numerals, one class a glyph (tools/nola/vnum.py writes the aspect ratios) */
  .vg.g-x { background-image: url("assets/vnum/x.webp"); aspect-ratio: 155 / 267; }
  .vg.g-0 { background-image: url("assets/vnum/0.webp"); aspect-ratio: 162 / 269; }
  .vg.g-1 { background-image: url("assets/vnum/1.webp"); aspect-ratio: 116 / 271; }
  .vg.g-2 { background-image: url("assets/vnum/2.webp"); aspect-ratio: 161 / 273; }
  .vg.g-3 { background-image: url("assets/vnum/3.webp"); aspect-ratio: 161 / 271; }
  .vg.g-4 { background-image: url("assets/vnum/4.webp"); aspect-ratio: 172 / 267; }
  .vg.g-5 { background-image: url("assets/vnum/5.webp"); aspect-ratio: 163 / 267; }
  .vg.g-6 { background-image: url("assets/vnum/6.webp"); aspect-ratio: 155 / 267; }
  .vg.g-7 { background-image: url("assets/vnum/7.webp"); aspect-ratio: 163 / 267; }
  .vg.g-8 { background-image: url("assets/vnum/8.webp"); aspect-ratio: 169 / 267; }
  .vg.g-9 { background-image: url("assets/vnum/9.webp"); aspect-ratio: 152 / 267; }
  .vg.g-dot { background-image: url("assets/vnum/dot.webp"); aspect-ratio: 91 / 267; }
  /* the glyphs are separate pictures: one centred row, not a grid row each */
  .multlayer .gmult { display: flex !important; align-items: center; justify-content: center; }
  .cell.booster .multface .mv { display: inline-flex !important; align-items: center; font-size: 30px; }
  .fbox .fmult { display: inline-flex; align-items: center; }
  .multlayer .gmult[hidden] { display: none !important; }
  .multlayer .gmult { font-size: calc(42px * var(--shrink, 1)); }   /* the numerals fill the border's opening */

  /* Doc on the sidewalk (placeScenery): --char-walk moves his box so his soles land on the painted sidewalk */
  #charfx { bottom: calc(-1 * var(--char-drop) + var(--char-walk, 0px)); }
  /* An upright screen frames the street above the board (placeScenery sizes #bgscene there); under it, behind the
     board and round the controls, the same painting at full size shows its cobbles. Doc's shoes are on show now,
     so his shadow is too. */
  @media (max-width: 1100px) and (orientation: portrait) {
    #bgwall { background: #0d0b1c url("assets/bonus_wall.webp") 50% 100% / cover no-repeat; }
    .charshadow { display: block; }
  }
  /* A squarer desktop window (5:4, 4:3 at full size) has no more room beside the board than a small one: Doc is
     sized to that room and centred in it, as on the small landscape windows */
  @media (min-width: 1081px) and (orientation: landscape) and (max-aspect-ratio: 3/2) and (min-height: 501px) {
    :root {
      --char-height: clamp(24vh, calc((47vw - 43.5vh) / .6), 42.5vh);
      --char-inset: calc((50vw - 43.5vh - var(--char-height) * .94) / 2);
    }
    #charfx { left: var(--char-inset); }
  }

  #charfx { margin-left: calc(-1 * var(--char-nudge, 0px)); }   /* standOnWalk: the open hand clear of the frame */

  /* the multiplier on the win figure glows in its own potion colour (placeWinChip sets it), not white on green */
  .winpop .wpx { text-shadow: 0 0 6px currentColor, 0 0 16px currentColor, 0 3px 0 rgba(0, 0, 0, .5); }

  /* the 5x5 board (2026-11-09): cells 164 x 140 (were 115 x 98), so the Multi numerals grow with them (x1.43) */
  .multlayer .gmult { font-size: calc(60px * var(--shrink, 1)); }
  .cell.booster .multface .mv { font-size: 43px; }
'''
rep("</style>\n</head>", CSS + "</style>\n</head>")

# ------------------------------------------------------------------ rules.js
RULES = [
    ('H6: "Skateboard", H7: "Limited Drop Box",', 'H6: "Bayou Gator", H7: "Beignets",'),
    ('H1: "Bag of Cash", H2: "Cartoon Glock", H3: "Gold Chain", H4: "Fresh Kicks", H5: "Boombox",',
     'H1: "Mardi Gras Mask", H2: "Voodoo Doll", H3: "Jazz Trumpet", H4: "Candle Skull", H5: "Gris-Gris Bag",'),
    ('M: "Multi", BS: "Crew Leader", ES: "The Phantom",', 'M: "Multi", BS: "FS scatter", ES: "XFS scatter",'),
    ('L1: "Spray Can", L2: "Graffiti Markers", L3: "Smukiez Beanie", L4: "Custom Hangtag", L5: "Dice",',
     'L1: "Fleur-de-lis", L2: "Mardi Gras Beads", L3: "Crawfish", L4: "King Cake", L5: "Candle",'),
    ('L6: "Smukiez Shirt", L7: "Hoodie", L8: "Bag of Weed", L9: "Freight Train", L10: "Lowrider",',
     'L6: "Skeleton Key", L7: "Doubloon", L8: "Tarot Card", L9: "Bone", L10: "Gas Lamp",'),
    ("Smukiez's City is a 7-reel", "Voodoo on Bourbon is a 7-reel"),
    ("Wall Line and Full Wall", "Hex Line and Voodoo Storm"),
    ("Wall Line: a straight line", "Hex Line: a straight line"),
    ("Full Wall: very rarely", "Voodoo Storm: very rarely"),
    ("Wall Lines", "Hex Lines"),
    ("Crew Leaders", "FS scatters"), ("Crew Leader", "FS scatter"),
    ("Phantoms", "XFS scatters"), ("The Phantom", "The XFS scatter"), ("Phantom", "XFS scatter"),
    # social mode (review 2026-11-09): "costs x1.25" slipped past the "cost" swap, and "not a buy" became "not a get"
    ('    ["buy bonus", "get bonus"], ["bonus buy", "bonus"], ["total bet", "total play"],',
     '    ["not a buy", "not a one-off"], ["costs", "takes"],   // (social review 2026-11-09: "costs x1.25", "not a get")\n'
     '    ["buy bonus", "get bonus"], ["bonus buy", "bonus"], ["total bet", "total play"],'),
    # the 5x5 board (2026-11-09): math-sdk/games/voodoo_5x5's paytable, ten paying symbols
    ('const TIERS = ["5", "6", "7-8", "9-11", "12-15", "16+"];',
     'const TIERS = ["5", "6", "7-8", "9-11", "12-15", "16-25"];'),
    ('    L1: [0.8, 1.6, 3.2, 8, 20, 60],\n    L2: [0.8, 1.6, 3.2, 8, 20, 60],\n    L3: [0.8, 1.2, 2.4, 6, 16, 48],\n    L4: [0.4, 1.2, 2.4, 6, 16, 48],\n    L5: [0.4, 0.8, 2, 4.8, 12, 40],\n    L6: [0.4, 0.8, 2, 4.8, 12, 40],\n    L7: [0.4, 0.8, 1.6, 4, 10, 32],\n    L8: [0.4, 0.8, 1.6, 4, 10, 32],\n    L9: [0.4, 0.8, 1.2, 3.2, 8, 24],\n    L10: [0.4, 0.8, 1.2, 3.2, 8, 24],',
     '    L1: [0.4, 0.8, 1.6, 4, 10, 32],\n    L3: [0.4, 0.8, 1.2, 3.2, 8, 24],\n    L4: [0.4, 0.4, 1.2, 2.8, 6, 20],'),
    ('  const ORDER = ["H1", "H2", "H3", "H4", "H5", "H6", "H7",\n                 "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10"];',
     '  const ORDER = ["H1", "H2", "H3", "H4", "H5", "H6", "H7", "L1", "L3", "L4"];   // the 5x5 game\'s ten paying symbols'),
    ('is a 7-reel, 7-row video slot',
     'is a 5-reel, 5-row video slot'),
    ('Pays by cluster size: 5 / 6 / 7-8 / 9-11 / 12-15 / 16 or more matching symbols',
     'Pays by cluster size: 5 / 6 / 7-8 / 9-11 / 12-15 / 16-25 matching symbols'),
    ('Every number here mirrors math-sdk/games/smukiez_tag_run/game_config.py;',
     'Every number here mirrors math-sdk/games/voodoo_5x5/game_config.py (the 5x5 board);'),
]
# rgs.js (review 2026-11-09): an amount too small for even 4 decimals printed as a bare "0."
RGS = [
    ('        if (s.split(".")[1] && s.split(".")[1].length < meta.decimals) s = v.toFixed(meta.decimals);',
     '        // (an amount too small to show even at maxDec came out "0." - never a bare point: the usual decimals)\n'
     '        if ((s.split(".")[1] || "").length < meta.decimals) s = v.toFixed(meta.decimals);'),
]

if __name__ == "__main__":
    apply(os.path.join(FE, "index.html"), ED)
    rs = open(os.path.join(FE, "rules.js"), encoding="utf-8").read()
    s0 = rs
    for a, b in RULES:
        rs = rs.replace(a, b)
    # the H names live in the same table: print them so they can be checked
    open(os.path.join(FE, "rules.js"), "w", encoding="utf-8", newline="\n").write(rs)
    print("index.html:", len(ED), "edits; rules.js changed:", rs != s0)
    gp = os.path.join(FE, "rgs.js")
    g = open(gp, encoding="utf-8").read()
    for a, b in RGS:
        g = g.replace(a, b)
    open(gp, "w", encoding="utf-8", newline="\n").write(g)
    print(re.findall(r'H1: "[^"]*".*', rs)[:2])
