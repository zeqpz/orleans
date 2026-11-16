"""Phone copies of the pictures a phone shows at well under their pixels (iOS memory, 2026-11-16).

    ..\\fallslotsga\\.venv\\Scripts\\python.exe -I tools/nola/make_mobile_art.py

A picture costs width x height x 4 bytes once decoded, whatever its file size, and WebKit decodes the whole file to
draw it however small it is shown. On a phone (index.html: window.MOBILE and a screen no wider than 500 CSS px on its
short side, html.mobart) these copies are used instead; a tablet and the desktop keep the full ones. Each is sized to
the biggest it is ever drawn on a phone - measured at 375x667, 390x844, 844x390, 440x956 and 956x440 @3
(tools/review/memprobe/picfit.py) - plus about 10% headroom, so the browser still draws it by scaling DOWN, as it did
the full picture:

  frame.webp, board_back.webp  2200x1982 -> 1400x1261   drawn at most 1281x1268 device px (440x956 portrait)
                                                        (sized by CSS width and height, so the box is the same)
  title_logo.webp              2400x1279 -> 1340x714    drawn at most 1214x647 (the features screen, 440x956);
                                                        html.mobart .ftitle keeps the full file's aspect ratio
  feature_box.webp             840x1074  -> 630x806     drawn at most 571x723 (stretched to its box: 100% 100%)

Tried and left out: the bonus shop's banners (1440x810, drawn at most ~523x294) and the scatters' flat icons (800 px,
drawn at most 240): drawn 3-5x smaller than their files, a copy came out visibly softer than the browser's own scaling
of the full picture (litediff.py: PSNR 18-25 dB, edges throughout), so they would have changed the look.

Written to frontend/assets/mobile/lite/ under the same names. Lanczos, WebP at quality 94 (alpha lossless).
Checked with tools/review/memprobe/litediff.py: each copy against the full picture, drawn by the browser at the size
a phone shows it.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "assets"
OUT = SRC / "mobile" / "lite"
OPTS = dict(quality=94, method=6, alpha_quality=100)
JOBS = [   # (file under assets/, new width, new height)
    ("frame.webp", 1400, 1261),
    ("board_back.webp", 1400, 1261),
    ("title_logo.webp", 1340, 714),
    ("feature_box.webp", 630, 806),
]


def main():
    for name, w, h in JOBS:
        im = Image.open(SRC / name)
        im.load()
        im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") or "transparency" in im.info else "RGB")
        out = OUT / name
        out.parent.mkdir(parents=True, exist_ok=True)
        im.resize((w, h), Image.LANCZOS).save(out, "WEBP", **OPTS)
        print(f"{name}: {im.size[0]}x{im.size[1]} -> {w}x{h}  {(SRC / name).stat().st_size // 1024} KB -> {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
