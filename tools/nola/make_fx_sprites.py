"""Voodoo on Bourbon: cartoon effect sprites for the Blender symbol and character clips -> art/nola-src/fx/<name>.png (RGBA, 256 px).
Flat colour, black ink outline, one hard shade on the lower right - the same look as the symbols.
Kind names are the fall build's (symanim.py's FX_SPEC); the pictures are New Orleans ones."""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "art", "nola-src", "fx")
INK = (30, 18, 12, 255)
S = 256
SS = 4                                      # supersampling


def canvas():
    return Image.new("RGBA", (S * SS, S * SS), (0, 0, 0, 0))


def done(im, name):
    im.resize((S, S), Image.LANCZOS).save(os.path.join(OUT, name + ".png"))


def poly_star(cx, cy, r0, r1, n, rot=0):
    pts = []
    for i in range(n * 2):
        r = r1 if i % 2 == 0 else r0
        a = rot + math.pi * i / n
        pts.append((cx + r * math.sin(a), cy - r * math.cos(a)))
    return pts


def inked_poly(pts, fill, shade=None, w=9):
    im = canvas()
    d = ImageDraw.Draw(im)
    d.polygon(pts, fill=INK)
    # the fill is the outline shrunk: draw the poly again with a thick ink line round it
    d.line(pts + [pts[0]], fill=INK, width=w * SS, joint="curve")
    inner = Image.new("L", im.size, 0)
    ImageDraw.Draw(inner).polygon(pts, fill=255)
    inner = inner.filter(ImageFilter.MinFilter(2 * w * SS // 2 * 2 + 1)) if w else inner
    col = Image.new("RGBA", im.size, fill)
    im.paste(col, (0, 0), inner)
    if shade:
        sh = inner.copy()
        off = Image.new("L", im.size, 0)
        off.paste(inner, (-int(S * SS * .06), -int(S * SS * .06)))
        sh = Image.fromarray(np.minimum(np.asarray(inner), 255 - np.asarray(off)).astype(np.uint8))
        im.paste(Image.new("RGBA", im.size, shade), (0, 0), sh)
    return im


def circle_pts(cx, cy, r, n=64, wob=0.0, seed=0):
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.3, 3)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r * (1 + wob * (math.sin(3 * a + ph[0]) * .5 + math.sin(5 * a + ph[1]) * .3 + math.sin(2 * a + ph[2]) * .2))
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def main():
    os.makedirs(OUT, exist_ok=True)
    C = S * SS / 2
    # sparkle: four-point gold star
    done(inked_poly(poly_star(C, C, C * .22, C * .92, 4), (255, 214, 92, 255), (238, 160, 40, 255), 7), "sparkle")
    done(inked_poly(poly_star(C, C, C * .3, C * .92, 4), (255, 255, 240, 255), (255, 226, 150, 255), 6), "sparkle_w")
    # five-point star
    done(inked_poly(poly_star(C, C, C * .42, C * .92, 5), (255, 200, 70, 255), (232, 140, 36, 255), 8), "star")
    # steam puff: soft white lumpy blob (no ink - steam is see-through), alpha .75
    im = canvas()
    d = ImageDraw.Draw(im)
    for (x, y, r) in [(.5, .55, .32), (.33, .5, .22), (.67, .48, .24), (.5, .35, .25)]:
        d.ellipse([C * 2 * x - C * 2 * r, C * 2 * y - C * 2 * r, C * 2 * x + C * 2 * r, C * 2 * y + C * 2 * r],
                  fill=(150, 255, 130, 210))
    done(im.filter(ImageFilter.GaussianBlur(12)), "steam")   # a green voodoo spirit wisp
    # dust / straw cloud puff: inked cream lumps
    done(inked_poly(circle_pts(C, C, C * .7, 80, .14, 3), (250, 248, 242, 255), (214, 206, 224, 255), 8), "puff")   # powdered sugar / fog puff
    # bubble: inked ring with a highlight
    im = canvas()
    d = ImageDraw.Draw(im)
    d.ellipse([C * .2, C * .2, C * 1.8, C * 1.8], fill=(124, 255, 107, 110), outline=INK, width=9 * SS)
    d.ellipse([C * .55, C * .5, C * .9, C * .8], fill=(255, 255, 255, 230))
    done(im, "bubble")
    # fizz drop: golden cider drop
    pts = [(C + C * .5 * math.sin(a) * (1 - .7 * max(0, -math.cos(a))) , C + C * .62 * -math.cos(a) * .9 + C * .1)
           for a in np.linspace(0, 2 * math.pi, 80, endpoint=False)]
    done(inked_poly(pts, (124, 255, 107, 255), (46, 158, 79, 255), 8), "drop")   # potion drop
    # popcorn kind -> a gold eighth-note
    im = canvas()
    d = ImageDraw.Draw(im)
    for w, col in ((30, INK), (14, (255, 214, 92, 255))):
        d.ellipse([C * .35 - w, C * 1.25 - w, C * .95 + w, C * 1.7 + w], fill=col)
        d.line([(C * .92, C * 1.45), (C * .92, C * .3)], fill=col, width=(14 + w // 2) * SS // 2)
        d.line([(C * .92, C * .32), (C * 1.55, C * .75)], fill=col, width=(18 + w // 2) * SS // 2)
    done(im, "popcorn")
    # straw kind -> a voodoo pin with a red head
    im = canvas()
    d = ImageDraw.Draw(im)
    d.line([(C * .35, C * 1.65), (C * 1.5, C * .5)], fill=INK, width=20 * SS)
    d.line([(C * .35, C * 1.65), (C * 1.5, C * .5)], fill=(210, 210, 220, 255), width=8 * SS)
    d.ellipse([C * 1.3, C * .2, C * 1.8, C * .7], fill=INK)
    d.ellipse([C * 1.36, C * .26, C * 1.74, C * .64], fill=(179, 38, 58, 255))
    done(im, "straw")
    # shock ring: inked warm ring (scaled up in Blender)
    im = canvas()
    d = ImageDraw.Draw(im)
    d.ellipse([C * .08, C * .08, C * 1.92, C * 1.92], outline=INK, width=26 * SS)
    d.ellipse([C * .12, C * .12, C * 1.88, C * 1.88], outline=(124, 255, 107, 255), width=14 * SS)
    done(im, "ring")
    # rays: a burst of 12 warm wedges, soft, for behind big hits
    im = canvas()
    d = ImageDraw.Draw(im)
    for i in range(12):
        a0, a1 = 2 * math.pi * i / 12, 2 * math.pi * (i + .45) / 12
        d.polygon([(C, C), (C + C * math.cos(a0) * 1.4, C + C * math.sin(a0) * 1.4),
                   (C + C * math.cos(a1) * 1.4, C + C * math.sin(a1) * 1.4)], fill=(196, 140, 255, 150) if i % 2 else (255, 214, 92, 150))
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).ellipse([0, 0, C * 2, C * 2], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(C * .35))
    yy, xx = np.mgrid[0:S * SS, 0:S * SS]
    rr = np.hypot(xx - C, yy - C) / C                           # 0 at the centre, 1 at the sprite's edge
    fall = np.clip((0.97 - rr) / 0.45, 0, 1) ** 1.5                # gone before the edge: no square corners
    im.putalpha(Image.fromarray((np.asarray(im.getchannel("A")) * (np.asarray(m) / 255.) * fall).astype(np.uint8)))
    done(im, "rays")
    # feather: black crow feather
    pts = [(C + C * .28 * math.sin(a) * (1 - .55 * max(0, math.cos(a))), C - C * .85 * math.cos(a))
           for a in np.linspace(0, 2 * math.pi, 80, endpoint=False)]
    done(inked_poly(pts, (126, 63, 176, 255), (91, 42, 134, 255), 7), "feather")   # purple plume
    # crumb: pie crust crumb
    done(inked_poly(circle_pts(C, C, C * .55, 7, .25, 5), (255, 255, 255, 255), (226, 222, 236, 255), 9), "crumb")   # sugar crumb
    # leaf kind -> Mardi Gras beads (purple, green, gold) under the old file names symanim.py asks for
    for name, fill, shade in (("leaf_red", (126, 63, 176, 255), (91, 42, 134, 255)),
                              ("leaf_orange", (46, 158, 79, 255), (26, 110, 52, 255)),
                              ("leaf_gold", (242, 178, 48, 255), (201, 149, 46, 255))):
        im = inked_poly(circle_pts(C, C, C * .62, 96, 0, 1), fill, shade, 8)
        ImageDraw.Draw(im).ellipse([C * .62, C * .55, C * .95, C * .85], fill=(255, 255, 255, 220))
        done(im, name)
    print("fx sprites ->", OUT)


if __name__ == "__main__":
    main()
