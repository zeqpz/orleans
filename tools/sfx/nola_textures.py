"""The two continuous textures the event cutter can't split (Voodoo on Bourbon pass): the reels' tambourine/shaker
rattle and the doubloon rain. Each is cut by hand from its raw Seed Audio take: the steadiest window of the wanted
length (least loudness wobble), high-passed, resampled to 44.1 kHz, levelled to its LUFS target, faded at both ends
(the reels with a longer fade so the game's looping pitch-bend never clicks).
usage: python tools/sfx/nola_textures.py"""
import glob, os, sys
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from audiolib import write_wav, lufs

ROOT = os.path.dirname(os.path.dirname(HERE))
W = os.path.join(os.environ.get("TEMP", "/tmp"), "nola_sfx", "raw")
JOBS = {"n_reels": ("sfx_reels.wav", 1.6, -24, .08), "n_rain": ("sfx_coins_rain.wav", 2.2, -23, .25)}


def load(p):
    a = np.frombuffer(open(p, "rb").read(), np.int16).astype(np.float32) / 32768
    return a.reshape(-1, 2) if a.size % 2 == 0 else np.stack([a, a], 1)


for name, (fn, secs, tgt, fade) in JOBS.items():
    best = None
    for p in sorted(glob.glob(os.path.join(W, name + "_*.pcm"))):
        x = load(p)
        sos = signal.butter(4, 120, "hp", fs=24000, output="sos")
        x = signal.sosfilt(sos, x, axis=0)
        n = int(secs * 24000)
        if len(x) < n:
            continue
        env = np.sqrt(signal.convolve(x.mean(1) ** 2, np.ones(1200) / 1200, "same")) + 1e-6
        db = 20 * np.log10(env)
        for s0 in range(0, len(x) - n, 2400):
            w = db[s0:s0 + n]
            score = w.std() - .2 * w.mean()          # steady, and not the quiet tail
            if w.mean() > -40 and (best is None or score < best[0]):
                best = (score, p, x[s0:s0 + n])
    if not best:
        print("no take for", name); continue
    y = signal.resample_poly(best[2], 147, 80, axis=0)       # 24 kHz -> 44.1 kHz
    _, M = lufs(y, 44100)
    y *= 10 ** (min(tgt - M, -1.5 - 20 * np.log10(np.abs(y).max() + 1e-12)) / 20)
    k = int(fade * 44100)
    ramp = (.5 - .5 * np.cos(np.linspace(0, np.pi, k)))[:, None]
    y[:k] *= ramp; y[-k:] *= ramp[::-1]
    write_wav(os.path.join(ROOT, "frontend", "assets", fn), y, 44100)
    wl = os.path.join(os.path.dirname(W), "written.txt")
    lines = [l.strip() for l in open(wl) if l.strip()]
    if fn not in lines:
        open(wl, "a").write(fn + "\n")
    print(fn, os.path.basename(best[1]), f"{len(y) / 44100:.2f}s", "steadiness", round(best[0], 2))
