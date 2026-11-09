"""OpenRouter image generation for the fall reskin.
The key is read from %USERPROFILE%\\.fallslots\\openrouter-key.txt and never printed.

usage: python tools/fall/orimg.py <out.png> "<prompt>" [--aspect 1:1] [--opaque] [--ref a.png --ref b.png]
                                  [--model openai/gpt-image-2.5-sunburst] [--quality high]
Writes <out.png> and appends the call (prompt, refs, cost) to art/nola-src/log.jsonl."""
import argparse, base64, json, os, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KEY_FILE = os.path.join(os.path.expanduser("~"), "Documents", "gamdevkey.txt")
LOG = os.path.join(ROOT, "art", "nola-src", "log.jsonl")


def key():
    with open(KEY_FILE, encoding="utf-8") as fh:
        return fh.read().strip()


def data_url(path):
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = {"jpg": "jpeg"}.get(ext, ext)
    with open(path, "rb") as fh:
        return f"data:image/{mime};base64," + base64.b64encode(fh.read()).decode()


def generate(out, prompt, aspect="1:1", transparent=True, refs=(), model="openai/gpt-image-2.5-sunburst",
             quality="high", tries=3):
    body = {"model": model, "prompt": prompt, "aspect_ratio": aspect, "quality": quality, "n": 1}
    if transparent:
        body["background"] = "transparent"
    if refs:
        body["input_references"] = [{"type": "image_url", "image_url": {"url": data_url(r)}} for r in refs]
    last = None
    for attempt in range(tries):
        req = urllib.request.Request("https://openrouter.ai/api/v1/images", data=json.dumps(body).encode(),
                                     headers={"Authorization": "Bearer " + key(),
                                              "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            item = d["data"][0]
            if item.get("b64_json"):
                raw = base64.b64decode(item["b64_json"])
            else:
                raw = urllib.request.urlopen(item["url"], timeout=120).read()
            os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
            with open(out, "wb") as fh:
                fh.write(raw)
            cost = (d.get("usage") or {}).get("cost")
            os.makedirs(os.path.dirname(LOG), exist_ok=True)
            with open(LOG, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "out": os.path.relpath(out, ROOT),
                                     "model": model, "aspect": aspect, "refs": [os.path.relpath(r, ROOT) for r in refs],
                                     "prompt": prompt, "cost": cost}) + "\n")
            return out, cost
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:400].decode(errors='replace')}"
        except Exception as e:                      # network hiccup, bad JSON
            last = repr(e)
        time.sleep(3 + attempt * 4)
    raise RuntimeError(last)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("prompt")
    ap.add_argument("--aspect", default="1:1")
    ap.add_argument("--opaque", action="store_true")
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--model", default="openai/gpt-image-2.5-sunburst")
    ap.add_argument("--quality", default="high")
    a = ap.parse_args()
    p = a.prompt
    if p.startswith("@"):
        with open(p[1:], encoding="utf-8") as fh:
            p = fh.read()
    try:
        out, cost = generate(a.out, p, a.aspect, not a.opaque, a.ref, a.model, a.quality)
        print("OK", out, "cost", cost)
    except RuntimeError as e:
        print("FAIL", a.out, e)
        sys.exit(1)
