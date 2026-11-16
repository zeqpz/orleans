"""The before/after table (markdown) from iosprobe3.py results (iOS crash review 3, 2026-11-16).

usage: table3.py DIR [rep]   (DIR holds before_<scenario>_r<rep>.json and after_<scenario>_r<rep>.json; with several
                              reps the median of each number is shown)
"""
import glob, json, os, statistics, sys

d = sys.argv[1]
NAMES = {"p_boot": "boot (live: load, intro, features, first touch, a spin), portrait", "p_43029": "Cork Storm 43029, portrait",
         "p_117426": "base 117426, portrait", "p_95017": "base 95017, portrait", "p_94": "648x big win (base 94), portrait",
         "l_boot": "boot, landscape 844x390", "l_43029": "Cork Storm 43029, landscape", "l_94": "648x big win, landscape",
         "c_boot": "boot, Chrome for iOS UA", "c_117426": "base 117426, Chrome for iOS UA", "c_43029": "Cork Storm 43029, Chrome for iOS UA"}


def load(tag, sc):
    out = []
    for f in sorted(glob.glob(os.path.join(d, f"{tag}_{sc}_r*.json"))):
        try:
            out.append(json.load(open(f)))
        except Exception:
            pass
    return out


def med(rs, path):
    vals = []
    for r in rs:
        v = r
        for k in path:
            v = (v or {}).get(k) if isinstance(v, dict) else None
        if isinstance(v, (int, float)):
            vals.append(v)
    return statistics.median(vals) if vals else None


def fmt(a, b):
    if a is None or b is None:
        return "-"
    return f"{a:.0f} -> **{b:.0f}** ({a / b:.1f}x)" if b else f"{a:.0f} -> 0"


rows = ["| scenario | whole run: WebKit model | at the cork/pop moments | + decoded audio (whole run) | canvases (2D, MB) | layers (MB) | decoded pictures (MB) | WebGL contexts |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
for sc, name in NAMES.items():
    B, A = load("before", sc), load("after", sc)
    if not B or not A:
        continue
    cpk = "peak_corkpop"
    rows.append(f"| {name} | {fmt(med(B, ['peak', 'total']), med(A, ['peak', 'total']))} | "
                f"{fmt(med(B, [cpk, 'total']), med(A, [cpk, 'total'])) if not sc.endswith('boot') else '-'} | "
                f"{fmt(med(B, ['peak', 'totalAudio']), med(A, ['peak', 'totalAudio']))} | "
                f"{med(B, ['peak', 'canvas2d']):.0f} -> {med(A, ['peak', 'canvas2d']):.0f} | "
                f"{med(B, ['peak', 'layers']):.0f} -> {med(A, ['peak', 'layers']):.0f} | "
                f"{med(B, ['peak', 'pics']):.0f} -> {med(A, ['peak', 'pics']):.0f} | "
                f"{med(B, ['peak', 'glN']):.0f} -> {med(A, ['peak', 'glN']):.0f} |")
print("\n".join(rows))
print()
print("Parts at the heaviest moment of each run (after build): canvas2d / gl / tex / bitmaps / pictures / layers / audio")
for sc in NAMES:
    for tag in ("before", "after"):
        rs = load(tag, sc)
        if rs:
            p = rs[0]["peak_at"]
            print(f"  {tag:6s} {sc:9s} t={p['t']:5.1f} {p['tag']:8s} total {p['total']:6.1f}: cv {p['canvas2d']:5.1f} gl {p['gl']:4.1f} tex {p['tex']:4.1f} "
                  f"bmp {p['bmp']:4.1f} pics {p['pics']:5.1f} layers {p['layers']:5.1f} audio {p['audio']:5.1f}  top {p['topLayers'][:3]}")
