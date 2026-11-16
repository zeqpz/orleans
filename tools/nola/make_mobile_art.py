"""Phone copies of the pictures a phone shows at well under their pixels (iOS memory, 2026-11-16; review 3 the same day).

    ..\\fallslotsga\\.venv\\Scripts\\python.exe -I tools/nola/make_mobile_art.py

A picture costs width x height x 4 bytes once decoded, whatever its file size, and WebKit decodes the whole file to
draw it however small it is shown. On a phone (index.html: window.MOBILE and a screen no wider than 500 CSS px on its
short side, html.mobart) these copies are used instead; a tablet and the desktop keep the full ones. Each is sized from
the biggest it is ever drawn on a phone - measured at 375x667, 390x844, 844x390, 440x956 and 956x440 @3
(tools/review/memprobe/picfit.py; review 3: through replays of a big win, a bonus and an Extreme Bonus too) - with
headroom, so the browser still draws it by scaling DOWN, as it did the full picture:

  frame.webp, board_back.webp  2200x1982 -> 1400x1261   drawn at most 1281x1268 device px (440x956 portrait)
                                                        (sized by CSS width and height, so the box is the same)
  title_logo.webp              2400x1279 -> 1340x714    drawn at most 1214x647 (the features screen, 440x956);
                                                        html.mobart .ftitle keeps the full file's aspect ratio
  feature_box.webp             840x1074  -> 630x806     drawn at most 571x723 (stretched to its box: 100% 100%)

Review 3 (the owner allowed the phone tier to change a little; these are still drawn scaled down):
  pictures drawn small (the HUD's bonus button, the shop's banners, the scatters' flat icons) at about twice the biggest
  a phone draws them - so the browser still halves them, the way it drew the full file 3-5x down; the win screens'
  lettering and splashes, the bonus intro's lettering and the panels' frames (border-image: the slices are fractions,
  so a copy draws the same edge) at 1.1-1.2x their biggest. The table is JOBS below; litediff.py checks them.

Two copies are cut down to what is drawn (same pixels, less to decode):
  board_back.webp  the lite copy cropped to its opaque box (CSS: html.mobart #paintback, the box fractions printed below)
  frame.webp       the lite copy as four bars round its clear middle (frame_top/bottom/left/right.webp; the middle is
                   half the picture and wholly transparent) - index.html lays them on the frame's box

Written to frontend/assets/mobile/lite/ under the same names. Lanczos, WebP at quality 94 (alpha lossless).
"""
from pathlib import Path
from PIL import Image
import numpy as np

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
# review 3: (file, new width) - the height keeps the file's aspect ratio. Sizes from tools/review/memprobe/picfit.py and
# research/ios_memory_3/picmax.txt (the biggest box each is drawn into on a phone, device px)
JOBS3 = [
    ("bonus_btn_text.webp", 760),   # the HUD's BONUS (<= 225 px) and the bonus intro's title (<= ~660 px)
    ("bonus_btn_bg.webp", 460),     # the HUD's bonus button (<= 225 px)
    ("xbonus_text.webp", 760),      # the Extreme Bonus intro's title (<= ~660 px)
    ("tier_bg.webp", 1360),         # BIG / MEGA / XTREME's splash (<= ~1160 px)
    ("total_bg.webp", 1360),        # the win figure's sweep (<= ~1180 px)
    ("big_win.webp", 1200), ("mega_win.webp", 1200), ("xtreme_win.webp", 1200), ("total_win.webp", 1200),   # (<= ~1030 px)
    ("info_panel.webp", 960),       # border-image (4.9% 6.25% / 20px): its 100 px slices drawn 60 px -> 60 px
    ("bonus_panel.webp", 1350),     # the shop's panel (border-image the same way)
    ("bonus/banner_fs.webp", 1020), ("bonus/banner_xfs.webp", 1020), ("bonus/banner_boost.webp", 1020),   # (<= 506 px)
    ("flat/BS.webp", 480), ("flat/ES.webp", 480),   # the scatters' flat icons (<= 240 px; the dissolves cut 132)
    ("vnum/border.webp", 480),      # the Multi values' stitched border (<= 235 px)
]


def rgba(im):
    im.load()
    return im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") or "transparency" in im.info else "RGB")


def clear_rect(a):
    """The biggest wholly transparent rectangle round the middle of an alpha plane (grown from the centre lines)."""
    op = a > 0
    H, W = op.shape
    cy, cx = H // 2, W // 2
    l = r = cx
    while l > 0 and not op[cy, l - 1]: l -= 1
    while r < W - 1 and not op[cy, r + 1]: r += 1
    t = b = cy
    while t > 0 and not op[t - 1, cx]: t -= 1
    while b < H - 1 and not op[b + 1, cx]: b += 1
    while op[t:b + 1, l:r + 1].any():
        s = {"l": op[t:b + 1, l].sum(), "r": op[t:b + 1, r].sum(), "t": op[t, l:r + 1].sum(), "b": op[b, l:r + 1].sum()}
        k = max(s, key=s.get)
        if k == "l": l += 1
        elif k == "r": r -= 1
        elif k == "t": t += 1
        else: b -= 1
    return l, t, r + 1, b + 1   # [l, r) x [t, b)


def main():
    made = {}
    for name, w, h in JOBS:
        im = rgba(Image.open(SRC / name)).resize((w, h), Image.LANCZOS)
        made[name] = im
        out = OUT / name
        out.parent.mkdir(parents=True, exist_ok=True)
        if name == "board_back.webp":   # cropped to what it draws: its opaque box
            x0, y0, x1, y1 = im.getbbox()
            im.crop((x0, y0, x1, y1)).save(out, "WEBP", **OPTS)
            print(f"  board_back crop {x0},{y0} {x1 - x0}x{y1 - y0} of {w}x{h}: left {x0 / w:.5f} top {y0 / h:.5f} "
                  f"width {(x1 - x0) / w:.5f} height {(y1 - y0) / h:.5f}")
        else:
            im.save(out, "WEBP", **OPTS)
        print(f"{name}: -> {w}x{h}  {(SRC / name).stat().st_size // 1024} KB -> {out.stat().st_size // 1024} KB")
    # the frame as four bars round its clear middle
    fr = made["frame.webp"]
    W, H = fr.size
    l, t, r, b = clear_rect(np.array(fr)[:, :, 3])
    bars = {"top": (0, 0, W, t), "bottom": (0, b, W, H), "left": (0, t, l, b), "right": (r, t, W, b)}
    for k, box in bars.items():
        fr.crop(box).save(OUT / f"frame_{k}.webp", "WEBP", **OPTS)
        x0, y0, x1, y1 = box
        print(f"  frame_{k}: {x1 - x0}x{y1 - y0} at {x0},{y0}: left {x0 / W:.5f} top {y0 / H:.5f} width {(x1 - x0) / W:.5f} height {(y1 - y0) / H:.5f}")
    print(f"  frame: the clear middle [{l},{r}) x [{t},{b}) = {(r - l) * (b - t) / (W * H):.1%} of the picture")
    for name, w in JOBS3:
        im = rgba(Image.open(SRC / name))
        h = round(im.size[1] * w / im.size[0])
        out = OUT / name
        out.parent.mkdir(parents=True, exist_ok=True)
        im.resize((w, h), Image.LANCZOS).save(out, "WEBP", **OPTS)
        print(f"{name}: {im.size[0]}x{im.size[1]} -> {w}x{h}  {im.size[0] * im.size[1] * 4 / 1e6:.1f} -> {w * h * 4 / 1e6:.1f} MB decoded")


if __name__ == "__main__":
    main()
