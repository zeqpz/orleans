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
    '  wander(() => [frame, $("paintback"), document.querySelector("#board .sprayrim")].filter(Boolean), t => ({   // the velvet backing drifts with its frame')

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
    width: calc((100% - 36px) / .8291); height: calc((100% - 36px) / .6847);
    left: calc(18px - (100% - 36px) * .10144); top: calc(18px - (100% - 36px) * .22404);
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
    print(re.findall(r'H1: "[^"]*".*', rs)[:2])
