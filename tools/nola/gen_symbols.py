"""Generate the fall symbols (art/nola-src/symbols.json) with H1 as the style reference, 6 at a time.
usage: python tools/fall/gen_symbols.py [ID,ID..] [--suffix _v1]"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orimg

ROOT = orimg.ROOT
P = os.path.join(ROOT, "art", "nola-src", "prompts")
SYMS = json.load(open(os.path.join(ROOT, "art", "nola-src", "symbols.json"), encoding="utf-8"))


def prompt(desc):
    base = open(os.path.join(P, "icon_base.txt"), encoding="utf-8").read().strip()
    style = open(os.path.join(P, "style.txt"), encoding="utf-8").read().strip()
    return (f"{base}\nThe symbol: {desc}.\nMatch the attached reference symbol exactly in drawing style, outline weight, "
            f"shading, sticker border and scale on the canvas (it is another symbol from the same set).\n\n{style}\n")


def one(sid, suffix):
    out = os.path.join(ROOT, "art", "nola-src", f"{sid}{suffix}.png")
    ref = os.path.join(ROOT, "art", "nola-src", "H1_v1.png")
    try:
        _, cost = orimg.generate(out, prompt(SYMS[sid]), refs=[ref])
        return f"OK {sid} {cost}"
    except RuntimeError as e:
        return f"FAIL {sid} {e}"


if __name__ == "__main__":
    ids = sys.argv[1].split(",") if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else list(SYMS)
    suffix = sys.argv[sys.argv.index("--suffix") + 1] if "--suffix" in sys.argv else "_v1"
    with ThreadPoolExecutor(6) as ex:
        for r in ex.map(lambda s: one(s, suffix), ids):
            print(r, flush=True)
