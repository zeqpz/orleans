"""Pack Doc's live rig for the game: art/blender/chars/doc_rig/rig/ (from tools/nola/blender/doc_rig.py, export step)
-> frontend/assets/chars/doc/rig/:
  rig.json        the rig: bones, parts (mesh offsets into geo.bin), faces, fx kinds, shoes, clips (face track, wisp
                  alpha, fx draws, offset into clips.bin) and, per density, its atlas pages and where each texture sits
  geo.bin         every part's mesh (as exported)
  clips.bin       every clip's bone transforms, back to back (float32: frames x bones x 6)
  d<NNN>/p<k>.webp the atlas pages at each density (texels per art px: .5, .75, 1, 1.5), parts + reaction faces +
                  fx sprites, shelf-packed with a gutter so mipmaps never bleed one into the next
The game picks the smallest density that draws the standing figure at a texel per screen pixel.
usage: python tools/nola/pack_rig.py"""
import json, os, shutil
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, "art", "blender", "chars", "doc_rig", "rig")
PARTS = os.path.join(ROOT, "art", "nola-src", "doc_parts")
FX = os.path.join(ROOT, "art", "nola-src", "fx")
DST = os.path.join(ROOT, "frontend", "assets", "chars", "doc", "rig")
DENSITIES = [.5, .75, 1.0, 1.5]
FX_PX = {"steam": 160, "sparkle": 90, "sparkle_w": 80, "leaf_red": 70, "leaf_orange": 70, "leaf_gold": 70,
         "ring": 200, "star": 80}          # each sprite's size in art px (doc_rig.FX_KINDS) ...
FX_GROW = 1.6                               # ... times the most it grows
GUTTER = 6


def shelf_pack(rects, width):
    """rects: [(key, w, h)] -> {key: (x, y)}, height used; tallest first, shelves left to right."""
    out, x, y, shelf = {}, 0, 0, 0
    for key, w, h in sorted(rects, key=lambda r: -r[2]):
        if x + w > width:
            x, y, shelf = 0, y + shelf + GUTTER, 0
        out[key] = (x, y)
        x += w + GUTTER
        shelf = max(shelf, h)
    return out, y + shelf


def pages_for(rects):
    """Pack onto as few pages as needed, each at most 4096 square; a page only as big as it has to be."""
    left = list(rects)
    pages = []
    while left:
        for size in (1024, 2048, 4096):
            pos, h = shelf_pack(left, size)
            if h <= size:
                pages.append((size, 1 << max(0, (h - 1)).bit_length(), pos))
                left = []
                break
        else:                                  # does not fit one 4096 page: fill one, carry the rest over
            pos, h = shelf_pack(left, 4096)
            keep = {k: p for k, p in pos.items() if p[1] + dict((r[0], r[2]) for r in left)[k] <= 4096}
            pages.append((4096, 4096, keep))
            left = [r for r in left if r[0] not in keep]
    return pages


def main():
    rig = json.load(open(os.path.join(SRC, "rig.json")))
    if os.path.isdir(DST):
        shutil.rmtree(DST)
    os.makedirs(DST)
    shutil.copyfile(os.path.join(SRC, "geo.bin"), os.path.join(DST, "geo.bin"))
    blob = bytearray()
    for c, C in rig["clips"].items():
        C["o"] = len(blob)
        blob.extend(open(os.path.join(SRC, f"{c}.bin"), "rb").read())
        assert len(blob) - C["o"] == C["frames"] * len(rig["bones"]) * 24, c
    open(os.path.join(DST, "clips.bin"), "wb").write(bytes(blob))
    rig["geo"], rig["clips_bin"] = "geo.bin", "clips.bin"
    # the source pictures: each part's / face's 4K plate (its box in art px), each fx sprite
    srcs = {}
    for p in rig["parts"]:
        srcs[p["tex"]] = (os.path.join(PARTS, p["tex"] + ".png"), p["box"][2], p["box"][3])
    for k in rig["fx"]:
        srcs["fx_" + k] = (os.path.join(FX, k + ".png"), FX_PX[k] * FX_GROW, FX_PX[k] * FX_GROW)
    ims = {k: Image.open(path).convert("RGBA") for k, (path, _, _) in srcs.items()}
    rig["densities"] = []
    for d in DENSITIES:
        tag = f"d{int(round(d * 100)):03d}"
        os.makedirs(os.path.join(DST, tag))
        sized = {}
        for k, (path, w, h) in srcs.items():
            im = ims[k]
            tw, th = max(2, round(w * d)), max(2, round(h * d))
            if k.startswith("fx_"):                # a sprite keeps its aspect, never upscaled past its source
                s = min(tw / im.width, th / im.height, 1.0)
                tw, th = max(2, round(im.width * s)), max(2, round(im.height * s))
            sized[k] = im.resize((tw, th), Image.LANCZOS)
        pages = pages_for([(k, im.width, im.height) for k, im in sized.items()])
        frames, files, total = {}, [], 0
        for pi, (pw, ph, pos) in enumerate(pages):
            page = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
            for k, (x, y) in pos.items():
                page.paste(sized[k], (x, y))
                frames[k] = [pi, x, y, sized[k].width, sized[k].height]
            name = f"{tag}/p{pi}.webp"
            page.save(os.path.join(DST, name), "WEBP", quality=90, alpha_quality=100, method=6)
            files.append(name)
            total += os.path.getsize(os.path.join(DST, name))
        rig["densities"].append({"d": d, "pages": files, "frames": frames})
        print(tag, [f"{pw}x{ph}" for pw, ph, _ in pages], f"{total / 1e6:.2f} MB", flush=True)
    json.dump(rig, open(os.path.join(DST, "rig.json"), "w"), separators=(",", ":"))
    verts = sum(p["verts"] for p in rig["parts"])
    print("rig.json", os.path.getsize(os.path.join(DST, "rig.json")), "geo", os.path.getsize(os.path.join(DST, "geo.bin")),
          "clips", len(blob), "verts", verts, "bones", len(rig["bones"]))


if __name__ == "__main__":
    main()
