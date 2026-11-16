"""The biggest box (device px) each picture is drawn into on phones (440x956, 956x440, 390x844, 844x390 @3): the board,
the bonus shop, the rules, and replays of a big win (base 94) and a bonus (base 8) (review 3, 2026-11-16; picfit.py's
measure over whole rounds). Boxes include a moment's scale (a slam starts 2x+), so read the resting sizes from it.
usage: picmax.py BASE_URL OUT.json"""
import json, sys, time, re
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, DIMS, game_url, enter_game
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "picfit.py")).read()
JS = re.search(r'JS = r"""(.*?)"""', src, re.S).group(1)
base, out = sys.argv[1], sys.argv[2]
res = {}
def grab(b, tag):
    try: d = json.loads(b.js(JS))
    except Exception: return
    for u, o in d.items():
        r = res.setdefault(u, {"file": DIMS.get(u), "shown": [0, 0], "at": set()})
        if o["w"] * o["h"] > r["shown"][0] * r["shown"][1]: r["shown"] = [round(o["w"]), round(o["h"])]
        r["at"].add(tag + ":" + ",".join(o["where"][:1]))
for (w, h) in [(440, 956), (956, 440), (390, 844), (844, 390)]:
    b = Browser(w, h, 3, ua=IPHONE_UA)
    try:
        b.open(game_url(base), .3); enter_game(b); time.sleep(2); grab(b, f"{w}board")
        for sel, close in (("#bonusBtn", "closeBonus()"), ("#menuBtn", "document.getElementById('infoClose').click()")):
            b.js(f"(() => {{ const e = document.querySelector({json.dumps(sel)}); if (e) e.click(); }})(); 1"); time.sleep(1.8); grab(b, f"{w}{sel}")
            b.js(close + "; 1"); time.sleep(1)
        for mode, ev in (("base", 94), ("base", 8)):
            if w in (390, 844) and ev != 94: continue
            b.open(f"{base}/?replay=true&game=test&version=1&mode={mode}&event={ev}&amount=1000000&rgs_url={base}", .3)
            b.wait("(document.getElementById('replayPlay')||{dataset:{}}).dataset.phase === 'ready'", 120)
            b.js("""(() => { clearInterval(window.__clk); const seen = {};
              window.__clk = setInterval(() => { for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s);
              if (e && e.getBoundingClientRect().width > 0) { seen[s] = (seen[s] || 0) + 1; if (seen[s] > 8) { e.click(); seen[s] = 0; } } } }, 400); })()""")
            b.js("document.getElementById('replayPlay').click(); 1")
            t0 = time.time()
            while time.time() - t0 < 300:
                time.sleep(.7); grab(b, f"{w}r{ev}")
                if b.js("(document.getElementById('replayPlay')||{dataset:{}}).dataset.phase") == "done": break
    finally:
        b.close()
rows = []
for u, r in res.items():
    f = r["file"]
    if not f: continue
    mb = f[0] * f[1] * 4 / 1e6
    over = max(f[0] / max(1, r["shown"][0]), f[1] / max(1, r["shown"][1])) if r["shown"][0] else 0
    rows.append({"url": u, "file": f, "mb": round(mb, 2), "shown": r["shown"], "over": round(over, 2), "at": sorted(r["at"])[:6]})
rows.sort(key=lambda x: -x["mb"])
for x in rows[:45]: print(x["mb"], x["url"], x["file"], "shown", x["shown"], "over", x["over"], x["at"][:3])
json.dump(rows, open(out, "w"), indent=1)
