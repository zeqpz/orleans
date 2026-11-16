"""The symbol clips at the density a phone shows them: assets/sym/d8 (iOS memory, review 3, 2026-11-16).

    ..\\fallslotsga\\.venv\\Scripts\\python.exe -I tools/nola/make_phone_sheets.py

A phone draws a symbol at 0.6-0.9 sheet px per rig unit (an icon is 100 units across; the board canvas at 2 device px
per CSS px): the smallest density there was, d16 (1.6), was cut down at run time to about half each way - decoded
whole first (a 1566x1376 idle sheet: 8.6 MB) in a worker, resized, and only then put on the GPU, for every clip,
every time one came in. These sheets are those same frames at 0.8 px per unit, made once here: each frame of each d16
sheet scaled to half (rounded) with its colour premultiplied (as tools/blender/pack_frames.py does, so see-through
edges pick up no dark fringe), on the same grid. A phone whose board wants at most 0.85 px per unit takes them with
no resize at all (390x844, 375x667, the Safari toolbar); one on its side resizes these instead of d16 (a quarter of the
pixels); a bigger phone (440x956: 0.88) keeps d16. Only the symbols the game lands (index.html SYM + the potions).

They are listed in assets/sym/manifest.json under "phone" (sheets.d8), not in "densities": the desktop never sees them.
"""
import json, math, os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYM = os.path.join(ROOT, "frontend", "assets", "sym")
IDS = ["M", "M2", "M3", "M4", "M5", "BS", "ES", "H1", "H2", "H3", "H4", "H5", "H6", "H7", "L1", "L3", "L4"]
SRC, DST, K = "d16", "d8", 0.5


def main():
    man_path = os.path.join(SYM, "manifest.json")
    man = json.load(open(man_path))
    os.makedirs(os.path.join(SYM, DST), exist_ok=True)
    tot_src = tot_dst = 0
    for sid in IDS:
        e = man["symbols"][sid]
        for clip, sh in e["sheets"][SRC].items():
            n = e["clips"][clip]["frames"]
            w, h, cols = sh["w"], sh["h"], sh["cols"]
            fw, fh = max(1, round(w * K)), max(1, round(h * K))
            src = Image.open(os.path.join(SYM, SRC, f"{sid}_{clip}.webp")).convert("RGBA")
            rows = math.ceil(n / cols)
            out = Image.new("RGBA", (cols * fw, rows * fh), (0, 0, 0, 0))
            for f in range(n):
                x, y = (f % cols) * w, (f // cols) * h
                fr = src.crop((x, y, x + w, y + h)).convert("RGBa").resize((fw, fh), Image.LANCZOS).convert("RGBA")
                out.paste(fr, ((f % cols) * fw, (f // cols) * fh))
            path = os.path.join(SYM, DST, f"{sid}_{clip}.webp")
            out.save(path, "WEBP", quality=82, method=6)
            e["sheets"].setdefault(DST, {})[clip] = {"w": fw, "h": fh, "cols": cols, "bytes": os.path.getsize(path)}
            tot_src += os.path.getsize(os.path.join(SYM, SRC, f"{sid}_{clip}.webp")); tot_dst += os.path.getsize(path)
        print(sid, {c: f'{s["w"]}x{s["h"]}' for c, s in e["sheets"][DST].items()}, flush=True)
    man["phone"] = {"density": 0.8, "ids": IDS}
    json.dump(man, open(man_path, "w"), indent=1)
    print(f"{SRC} {tot_src / 1e6:.1f} MB -> {DST} {tot_dst / 1e6:.1f} MB for {len(IDS)} symbols")


if __name__ == "__main__":
    main()
