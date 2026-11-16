"""Budget table (markdown) from scen.py results: per item, decoded MB, before vs after, per scenario."""
import json, re, sys, collections

CV_GROUPS = [
    ("rig cell canvases (25 symbols)", r"rigEl"),
    ("burst pieces (Voronoi shards, CPU canvases)", r"burstKit"),
    ("burst layer over the board (shardLayer)", r"shardLayer"),
    ("debris: stains + flying chunks (2 canvases)", r"debrisLayers"),
    ("cork/cider particles (fxCanvas, whole screen)", r"fxCanvas"),
    ("icon sprites + shadows (26 x 208/164 px)", r"img\.onload"),
    ("icon rain / loading icons (whole screen)", r"startIconRain|startIntroIcons|draw \("),
    ("splat / glow / smoke / material sprites", r"splatSprite|glowSprite|smokePuff|matSprite"),
    ("win-line sheets", r"wipeSheet|lineSheet|make \("),
]


def cv_groups(detail):
    g = collections.OrderedDict((k, 0.0) for k, _ in CV_GROUPS)
    g["other canvases"] = 0.0
    for c in detail["cv"]:
        if "webgl" in c["type"]:
            continue   # counted with the WebGL drawing buffers
        st = c["st"]
        for k, rx in CV_GROUPS:
            if re.search(rx, st):
                g[k] += c["mb"]
                break
        else:
            g["other canvases"] += c["mb"]
    return g


def aud_groups(detail):
    music = sum(a["mb"] for a in detail["aud"] if a["s"] > 10)
    sfx = sum(a["mb"] for a in detail["aud"] if a["s"] <= 10)
    return music, sfx, sum(1 for a in detail["aud"] if a["s"] <= 10)


def row_of(s):
    """s: a snapshot (boot/after) or round best, with detail"""
    d = s["detail"]
    out = collections.OrderedDict()
    out["JS heap (used)"] = s["quick"]["heap"]
    for k, v in cv_groups(d).items():
        out[k] = round(v, 1)
    out["WebGL drawing buffers (bgfx + scarecrow)"] = s["quick"]["cgl"]
    for t in sorted(d["tex"], key=lambda t: -t["mb"]):
        if t["mb"] >= .2:
            key = "GL texture " + ("bgfx painting" if t["gl"] == "bgfx" and t["wh"] not in ("960x540", "512x128") else
                                   "bgfx wind/water mask" if t["wh"] == "960x540" else "bgfx leaves/smoke" if t["wh"] == "512x128" else
                                   "scarecrow atlas (mipmapped)")
            out[key] = round(out.get(key, 0) + t["mb"], 1)
    for b in d["bmp"]:
        w, h = map(int, b["wh"].split("x"))
        key = "ImageBitmap " + ("scarecrow atlas" if "charRig" in b["st"] else "symbol rig atlas page")
        out[key] = round(out.get(key, 0) + w * h * 4 / 1e6, 1)
    m, sfx, n = aud_groups(d)
    out["audio: music decoded"] = round(m, 1)
    out[f"audio: SFX decoded"] = round(sfx, 1)
    out["pictures on screen (decoded)"] = s["pics_visible_mb"]
    out["composited layers that paint (at 3x)"] = s["layers_paint_mb"]
    return out


def main():
    before, after = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
    for tag in sys.argv[3:]:
        sb = before["scen"][tag]; sa = after["scen"][tag]
        sb = sb.get("best", sb); sa = sa.get("best", sa)
        rb, ra = row_of(sb), row_of(sa)
        print(f"\n#### {tag}\n\n| item | before MB | after MB |\n|---|---:|---:|")
        for k in list(dict.fromkeys(list(rb) + list(ra))):
            print(f"| {k} | {rb.get(k, 0)} | {ra.get(k, 0)} |")
        print(f"| **model total** | **{sb['model']}** | **{sa['model']}** |")


if __name__ == "__main__":
    main()
