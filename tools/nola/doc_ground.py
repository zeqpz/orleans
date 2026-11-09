"""Set Doc's ground line (renders/meta.json ground_y) to the true bottom of his soles: the lowest opaque row of the
idle's rest frame, plus 2 px. The game stands ground_y on the bottom edge of his canvas, so a ground line above the
shoe tips slices them off. Run after rendering, before tools/blender/pack_chars.py doc.
usage: python tools/nola/doc_ground.py"""
import json, os
import numpy as np
from PIL import Image
R = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "art", "blender", "chars", "doc", "renders")
a = np.asarray(Image.open(os.path.join(R, "idle", "0000.png")).getchannel("A"))
low = int(np.nonzero(a.max(1) > 8)[0].max()) + 2
m = json.load(open(os.path.join(R, "meta.json")))
print("ground_y", m["ground_y"], "->", low, "of", a.shape[0])
m["ground_y"] = float(low)
json.dump(m, open(os.path.join(R, "meta.json"), "w"), indent=1)
