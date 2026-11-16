"""Each phone copy (assets/mobile/lite/, tools/nola/make_mobile_art.py) against its full picture, drawn by the browser
at the sizes a phone shows it (iOS memory, 2026-11-16).

Headless Chrome at DPR 3: a page with the full picture and its copy side by side, each in a box the size a phone draws
it (the device px picfit.py measured, / 3) with the same fit as the game (stretch / cover / contain), over black and
over white (so an edge of the alpha shows too). Screenshot, crop, compare: the largest difference of any channel, the
mean, and the share of pixels off by more than 4/255 and 16/255. Writes OUTDIR/litediff.json and the crops.
usage: litediff.py OUTDIR [--base URL]
"""
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, MOCK

a = sys.argv[1:]
out = Path(a[0]); out.mkdir(parents=True, exist_ok=True)
base = (a[a.index("--base") + 1] if "--base" in a else MOCK)
# (file, fit, [device px boxes w x h: the phone sizes picfit.py measured])
CASES = [
    ("frame.webp", "fill", [(1140, 1125), (902, 885), (1281, 1268), (1097, 1081)]),
    ("board_back.webp", "fill", [(1140, 1125), (902, 885), (1281, 1268)]),
    ("title_logo.webp", "contain", [(1076, 574), (417, 222), (1214, 647), (957, 510)]),
    # (review 3: copies at about twice the biggest a phone draws them; the first round's copies of these, at 1.1x, were
    # dropped as softer)
    ("bonus/banner_fs.webp", "cover", [(279, 258), (445, 247), (317, 294), (506, 281)]),
    ("bonus/banner_xfs.webp", "cover", [(279, 258), (506, 281)]),
    ("bonus/banner_boost.webp", "cover", [(279, 258), (506, 281)]),
    ("feature_box.webp", "fill", [(479, 607), (494, 626), (571, 723)]),
    ("flat/BS.webp", "contain", [(201, 201), (240, 240), (179, 179)]),
    ("flat/ES.webp", "contain", [(201, 201), (240, 240)]),
    # review 3 (tools/nola/make_mobile_art.py JOBS3; the boxes from picfit.py / picmax at rest, device px)
    ("bonus_btn_bg.webp", "contain", [(225, 115), (201, 102)]),
    ("bonus_btn_text.webp", "contain", [(197, 102), (660, 439)]),
    ("xbonus_text.webp", "contain", [(660, 556)]),
    ("tier_bg.webp", "fill", [(1158, 327), (921, 260)]),
    ("total_bg.webp", "fill", [(1270, 580), (1000, 460)]),
    ("big_win.webp", "contain", [(1030, 212)]), ("mega_win.webp", "contain", [(1030, 214)]),
    ("xtreme_win.webp", "contain", [(1030, 230)]), ("total_win.webp", "contain", [(1199, 338)]),
    ("vnum/border.webp", "fill", [(235, 201), (160, 140)]),
]
DPR = 3
b = Browser(1400, 900, DPR, ua=None, mobile=False)
res = []
try:
    from PIL import Image, ImageChops
    import numpy as np
    for name, fit, boxes in CASES:
        for (dw, dh) in boxes:
            cw, ch = dw / DPR, dh / DPR
            for bg in ("#000", "#fff"):
                html = f"""<body style="margin:0;background:{bg}">
<div style="position:absolute;left:0;top:0;width:{cw}px;height:{ch}px"><img id=a src="{base}/assets/{name}" style="width:100%;height:100%;object-fit:{fit};display:block"></div>
<div style="position:absolute;left:{cw + 4}px;top:0;width:{cw}px;height:{ch}px"><img id=b src="{base}/assets/mobile/lite/{name}" style="width:100%;height:100%;object-fit:{fit};display:block"></div>
</body>"""
                b.size(max(800, int(2 * cw + 20)), max(600, int(ch + 10)), DPR, False)
                # (drawn on the game's own origin: a data: page may not load its pictures)
                if not b.js("location.origin === " + json.dumps(base)):
                    b.open(base + "/assets/sym/manifest.json", 1.0)
                b.js("document.documentElement.innerHTML = " + json.dumps(html) + "; 1")
                b.wait("document.getElementById('a') && document.getElementById('a').complete && document.getElementById('b').complete && document.getElementById('a').naturalWidth > 0 && document.getElementById('b').naturalWidth > 0", 20)
                time.sleep(.4)
                p = b.shot(out / "_tmp.png")
                im = Image.open(p).convert("RGB")
                x0, x1, w, h = 0, round((cw + 4) * DPR), round(cw * DPR), round(ch * DPR)
                A = np.asarray(im.crop((x0, 0, x0 + w, h))).astype(int)
                B = np.asarray(im.crop((x1, 0, x1 + w, h))).astype(int)
                d = np.abs(A - B).max(axis=2)
                tag = f"{name.replace('/', '_')}_{dw}x{dh}_{'k' if bg == '#000' else 'w'}"
                if bg == "#000":
                    Image.fromarray(np.concatenate([A, B, np.minimum(255, d[..., None].repeat(3, 2) * 8)], axis=1).astype("uint8")).save(out / f"{tag}.png")
                r = {"file": name, "box": [dw, dh], "bg": bg, "max": int(d.max()), "mean": round(float(np.abs(A - B).mean()), 3),
                     "over4": round(float((d > 4).mean()) * 100, 3), "over16": round(float((d > 16).mean()) * 100, 3),
                     "psnr": round(float(10 * np.log10(255 ** 2 / max(1e-9, ((A - B) ** 2).mean()))), 1)}
                res.append(r)
                print(json.dumps(r), flush=True)
finally:
    b.close()
json.dump(res, open(out / "litediff.json", "w"), indent=1)
