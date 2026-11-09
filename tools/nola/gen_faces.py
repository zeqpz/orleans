"""Face reactions for the voodoo showman (Doc): the head crop (art/nola-src/head_crop.png) redrawn with a new expression,
everything else identical. -> art/nola-src/faces/<name>.png"""
import os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orimg

FACES = {
    "blink": "both eyes fully CLOSED in a slow smug blink (curved closed eyelid lines), the same sly grin with the gold tooth",
    "laugh": "a big villainous LAUGH: mouth wide open showing teeth and the gold tooth, eyes squeezed into happy crescents, eyebrows up",
    "smug": "a smug sly SMIRK to one side, one eyebrow raised high, eyes half-lidded and scheming",
    "cheer": "ecstatic and amazed: huge toothy grin with the gold tooth, eyes wide open with tiny glowing green dot pupils, eyebrows raised high",
    "shock": "SHOCKED: eyes popped wide open and bulging, tiny pupils, mouth a small round O, eyebrows raised high, moustache ends sprung up",
    "sad": "SULKING and annoyed: droopy half-closed eyes looking down to the side, mouth a wobbly frown, moustache drooping",
    "wink": "a cheeky WINK: his right eye (on the viewer's left) closed in a curved line, the other eye open, a confident lopsided grin with the gold tooth",
}
SRC = os.path.join(orimg.ROOT, "art", "nola-src", "head_crop.png")


def one(name):
    out = os.path.join(orimg.ROOT, "art", "nola-src", "faces", name + ".png")
    p = (f"Redraw the attached image EXACTLY - same cartoon man's head, same long narrow face, same top hat with the "
         f"purple band, bone and feather, same curled pencil moustache, same collar and cravat, same outlines, same "
         f"colours, same framing, same position and size on the canvas, transparent background - changing ONLY the "
         f"facial expression (eyes, eyebrows, mouth) to: {orimg_face(name)}. Rick and Morty cartoon style, flat cel shading.")
    try:
        _, c = orimg.generate(out, p, refs=[SRC])
        return f"OK {name} {c}"
    except RuntimeError as e:
        return f"FAIL {name} {e}"


def orimg_face(n):
    return FACES[n]


if __name__ == "__main__":
    names = sys.argv[1].split(",") if len(sys.argv) > 1 else list(FACES)
    with ThreadPoolExecutor(7) as ex:
        for r in ex.map(one, names):
            print(r, flush=True)
