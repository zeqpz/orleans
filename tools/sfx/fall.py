"""The fall / Thanksgiving sound pass (2026-11-03), end to end, on the street pass's own tools.

  python tools/sfx/fall.py gen   [name ...]   # Seed Audio takes -> %TEMP%/fall_sfx/raw/<name>_<t>.pcm (resumable)
  python tools/sfx/fall.py cand  [name ...]   # every take cleaned whole and cut into events (process2) -> cand/
  python tools/sfx/fall.py pick  [name ...]   # best + most alike `keep` per sound (pick_takes' scoring) -> picks.json
  python tools/sfx/fall.py build [name ...]   # clean3's strict clean + master from the raw take -> frontend/assets
  python tools/sfx/fall.py all   [name ...]

The prompts and where each sound goes are in fall_spec.py. The work files stay in %TEMP%/fall_sfx (rebuildable);
build writes the WAVs into frontend/assets and the list of them to %TEMP%/fall_sfx/written.txt, which
encode_new.js takes for the Opus copies:
  node tools/sfx/encode_new.js <ClaudeRoblox>/.tools/pw/node_modules/playwright %TEMP%/fall_sfx/written.txt
"""
import os, sys, json, glob, shutil, itertools, time, urllib.error, concurrent.futures as cf
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import orapi, fall_spec as FS
import process2 as P
import clean3 as C
from audiolib import write_wav, lufs, analyze, noise_floor
from pick_takes import penalty

ROOT = os.path.dirname(os.path.dirname(HERE))
ASSETS = os.path.join(ROOT, "frontend", "assets")
W = os.path.join(os.environ.get("TEMP", "/tmp"), "fall_sfx")
RAW, CAND = os.path.join(W, "raw"), os.path.join(W, "cand")
SR0, SR = 24000, 44100

# the street tools read their tables from module globals: hand them the fall sounds
P.K["sting"] = dict(P.K["tone"], gap=.6, hp=70, fout=200, exp=-56, tail=-56)
C.HP["sting"] = 70
for name, (_, _, kind, t, _) in FS.S.items():
    P.T[name] = t
    C.KIND[name] = kind
P.FOUT.update(FS.FOUT)
C.TONAL |= FS.TONAL
P.RAW = RAW


# ------------------------------------------------------------------ generate
def speech(prompt):
    last = None
    for a in range(4):                 # Seed Audio turns ~1% of requests away with a 400 at random: ask again
        try:
            return orapi.speech(prompt, fmt="pcm")
        except RuntimeError as e:
            last = e
            time.sleep(2 + 3 * a)
    raise last


def gen_one(name, prompt, take):
    out = os.path.join(RAW, f"{name}_{take}.pcm")
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        return name, take, "kept", 0
    try:
        b, ct = speech(prompt)
    except Exception as e:
        return name, take, f"ERR {str(e)[:160]}", 0
    if "rate=24000" not in ct or "channels=2" not in ct:
        return name, take, f"ERR content type {ct}", 0
    open(out + ".part", "wb").write(b)
    os.replace(out + ".part", out)
    return name, take, f"{len(b) / 4 / SR0:.2f}s", len(b) / 4 / SR0


def gen(names):
    os.makedirs(RAW, exist_ok=True)
    work = [(n, p, t) for n, p, takes, _ in FS.jobs() if n in names for t in range(1, takes + 1)
            if not os.path.exists(os.path.join(RAW, f"{n}_{t}.pcm"))]
    c0 = orapi.credits()
    print(f"{len(work)} takes; credits {c0:.4f}", flush=True)
    secs = errs = 0
    with cf.ThreadPoolExecutor(6) as ex:
        for i, (n, t, r, d) in enumerate(ex.map(lambda w: gen_one(*w), work)):
            secs += d
            errs += r.startswith("ERR")
            if r.startswith("ERR"):
                print(f"[{i + 1}/{len(work)}] {n}_{t}: {r}", flush=True)
    c1 = orapi.credits()
    print(f"{errs} errors, {secs:.1f}s of audio (~${secs / 60 * .15:.3f} at $0.15/min); credits {c1:.4f} "
          f"(account moved {c0 - c1:.4f} meanwhile, other work included)", flush=True)


# ------------------------------------------------------------------ candidates (process2.main, per fall sound)
def cand(names):
    path = os.path.join(W, "cand.json")
    db = json.load(open(path)) if os.path.exists(path) else {}
    for name, prompt, takes, kind in FS.jobs():
        if name not in names:
            continue
        kd = dict(P.K[kind])
        mn, mx, keep, mode = P.T[name]
        mode = mode or kd["mode"]
        d = os.path.join(CAND, name)
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        db[name] = []
        raws = sorted(glob.glob(os.path.join(RAW, f"{name}_*.pcm")), key=lambda p: int(p.rsplit("_", 1)[1][:-4]))
        for p in raws:
            t = int(p.rsplit("_", 1)[1][:-4])
            st = np.frombuffer(open(p, "rb").read(), "<i2").reshape(-1, 2).astype(np.float64) / 32768
            if len(st) < 2048 or np.abs(st).max() < 1e-3:
                continue
            st = st - st.mean(0)
            nf_raw = noise_floor(st, SR0) - 20 * np.log10(np.abs(st).max())
            st = signal.sosfiltfilt(signal.butter(4, kd["hp"], "highpass", fs=SR0, output="sos"), st, axis=0)
            g, Nn, Gg = P.gate(st, *kd["gate"])
            cal = (np.abs(P.stft(np.random.default_rng(0).standard_normal(SR0))) ** 2).mean(1).sum()
            m = g.mean(1)
            if mode == "hit":
                evs = P.ev_hits(m, mn, mx, kd["tail"], single=kind in ("click", "drop") or name in FS.SINGLE)
            elif mode == "gesture":
                evs = P.ev_gesture(m, kd.get("gap", .15), kd["tail"], mx)
            else:
                evs = P.ev_sustain(m, mx)
            evs = [e for e in evs if e["pk"] > -14][:24]
            for i, ev in enumerate(evs):
                seg = g[ev["a"]:ev["b"]]
                raw_len = len(seg) / SR0
                if raw_len < mn * .8:
                    continue
                y = P.finish(seg, kd, mx, kind, name)
                if len(y) < int(mn * .8 * SR):
                    continue
                a = analyze(y, SR)
                f0, f1 = ev["a"] // P.HOP, max(ev["a"] // P.HOP + 1, min(Gg.shape[1], ev["b"] // P.HOP))
                pk_in = np.abs(seg.mean(1)).max() + 1e-12
                hiss_raw = 10 * np.log10(Nn.sum() / cal + 1e-20) - 20 * np.log10(pk_in)
                hiss = 10 * np.log10((Nn[:, None] * Gg[:, f0:f1] ** 2).sum(0).mean() / cal + 1e-20) - 20 * np.log10(pk_in)
                fn = f"{t}_{i}.wav"
                write_wav(os.path.join(d, fn), y, SR)
                db[name].append(dict(file=fn, take=t, ev=i, a=int(ev["a"]), b=int(ev["b"]), dur=a["dur"], peak=a["peak_db"],
                                     mmax=lufs(y, SR)[1], I=a["lufs"], cen=a["centroid"], nf_raw=nf_raw,
                                     nf_out=noise_floor(y, SR), ev_pk=ev["pk"], cut=bool(ev["cut"] or raw_len > mx),
                                     raw_len=raw_len, hiss_raw=hiss_raw, hiss=hiss, bands=P.bands(y)))
        print(f"{name:16s} {len(raws)} takes -> {len(db[name])} candidates", flush=True)
    json.dump(db, open(path, "w"), indent=0)


# ------------------------------------------------------------------ pick (pick_takes' scoring, no review sheets)
def pick(names):
    db = json.load(open(os.path.join(W, "cand.json")))
    path = os.path.join(W, "picks.json")
    picks = json.load(open(path)) if os.path.exists(path) else {}
    for name in names:
        cs = db.get(name) or []
        if not cs:
            print(f"{name:16s} NO CANDIDATES"); continue
        mn, mx, keep, _ = P.T[name]
        for c in cs:
            c["pen"] = penalty(c, mn, mx)
        cs.sort(key=lambda c: c["pen"])
        if name in FS.MANUAL:
            picks[name] = FS.MANUAL[name]
            print(f"{name:16s} keep {picks[name]} (by hand)"); continue
        top = cs[:max(keep, min(9 if keep > 3 else 8, len(cs)))]
        best, bestv = None, 1e9
        for combo in itertools.combinations(range(len(top)), min(keep, len(top))):
            B = [np.array(top[i]["bands"]) for i in combo]
            dist = np.mean([np.abs(a - b).mean() for a, b in itertools.combinations(B, 2)]) if len(B) > 1 else 0
            same = len(combo) - len({top[i]["take"] for i in combo})      # a little variety: takes, not one take's echoes
            v = dist * 2 + np.mean([top[i]["pen"] for i in combo]) + 1.5 * same
            if v < bestv:
                best, bestv = combo, v
        picks[name] = [top[i]["file"] for i in best]
        print(f"{name:16s} keep {picks[name]}  " + "  ".join(f"{top[i]['dur']:.2f}s pen{top[i]['pen']:.1f}" for i in best))
    json.dump(db, open(os.path.join(W, "cand.json"), "w"), indent=0)
    json.dump(picks, open(path, "w"), indent=1)


def wsola(x, rate, sr, frame=.04, tol=.012):
    """Time-compress by `rate` keeping the pitch: waveform-similarity overlap-add (Hann frames, 50 %
    overlap out, each next frame taken where it best continues the last one within +-tol)."""
    N = int(frame * sr) // 2 * 2; Ho = N // 2; Hi = Ho * rate; T = int(tol * sr)
    win = np.hanning(N)[:, None]
    n_out = int((len(x) - N - T) / Hi)
    out = np.zeros((n_out * Ho + N, x.shape[1])); norm = np.zeros(n_out * Ho + N)
    pos = 0
    for k in range(n_out):
        c = int(round(k * Hi))
        if k:
            want = x[pos + Ho:pos + Ho + N].mean(1)            # what would naturally follow the last frame
            lo, hi = max(0, c - T), min(len(x) - N, c + T)
            seg = x[lo:hi + N].mean(1)
            cc = signal.correlate(seg, want, mode="valid")
            c = lo + int(np.argmax(cc))
        out[k * Ho:k * Ho + N] += x[c:c + N] * win
        norm[k * Ho:k * Ho + N] += win[:, 0]
        pos = c
    return out / np.maximum(norm, 1e-3)[:, None]


# ------------------------------------------------------------------ build (clean3) -> frontend/assets
def build(names):
    db = json.load(open(os.path.join(W, "cand.json")))
    picks = json.load(open(os.path.join(W, "picks.json")))
    written = []
    wl = os.path.join(W, "written.txt")
    if os.path.exists(wl):
        written = [l.strip() for l in open(wl) if l.strip()]
    for name in names:
        _, _, kind, (mn, mx, keep, _), out = FS.S[name]
        tgt = out[2]
        fns = [f"sfx_{out[1]}_{i}.wav" for i in range(1, keep + 1)] if out[0] == "set" else out[1]
        ranked = sorted(db[name], key=lambda c: c.get("pen", 99))
        want = [next(c for c in db[name] if c["file"] == f) for f in picks[name]]
        res = []
        for c in want + [c for c in ranked if c not in want]:
            if len(res) == len(fns):
                break
            y = None
            # gentler and gentler; the last pass reduces nothing (the gate alone), for a take whose sound
            # the denoiser keeps changing (a deep pumpkin thud) but whose own bed is already low
            for j, (prop, ns) in enumerate(((1.0, True), (1.0, False), (.85, False), (.6, False), (0.0, False))):
                yy, info = C.build_one(name, c, tgt, prop=prop, nonstat=ns)
                bed = info["n_after"] + info["gain"]
                if info["guard"]["ok"] and bed <= FS.BED.get(name, C.BED_MAX) and len(yy) >= int(max(.012, mn * .6) * SR):
                    y = yy; info["pass"] = j; break
            if y is None:
                print(f"  {name} {c['file']}: rejected (bed {bed:.1f}, guard {info['guard']['ok']})")
                continue
            res.append((c, y, info))
        for fn, (c, y, info) in zip(fns, res):
            if name in FS.STRETCH:
                y = wsola(y, FS.STRETCH[name], SR)
                _, M = lufs(y, SR)                      # back to the loudness target, never over -1.5 dBFS
                y *= 10 ** (min(tgt - M, -1.5 - 20 * np.log10(np.abs(y).max() + 1e-12)) / 20)
                n = int(.06 * SR)
                y[-n:] *= (.5 + .5 * np.cos(np.linspace(0, np.pi, n)))[:, None]
                y[0] = 0; y[-1] = 0
            write_wav(os.path.join(ASSETS, fn), y, SR)
            if fn not in written:
                written.append(fn)
            I, M = lufs(y, SR)
            g = info["guard"]
            print(f"{fn:28s} {name}:{c['file']:7s} dur {len(y) / SR:5.2f}s pk {20 * np.log10(np.abs(y).max() + 1e-12):5.1f} "
                  f"M {M:6.1f} I {I:6.1f} bed {info['n_after'] + info['gain']:6.1f} pass {info['pass']} "
                  f"guard lvl {g['dlvl']:+.1f} cen {g['dcen'] * 100:+.0f}%", flush=True)
        if len(res) < len(fns):
            print(f"  !! {name}: {len(res)} of {len(fns)} files")
    open(wl, "w").write("\n".join(written) + "\n")


def main():
    step, names = sys.argv[1], [a for a in sys.argv[2:]] or list(FS.S)
    for s in (("gen", "cand", "pick", "build") if step == "all" else (step,)):
        globals()[s](names)


if __name__ == "__main__":
    main()
