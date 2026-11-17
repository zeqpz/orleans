"""A bonus resumed after a reload, in desktop Chrome (iOS review 4, 2026-11-17: the resume is round handling, on every
device). A session on the mock: the mock deals --event in --mode (/mock/force), the round is bought, the page is
reloaded after the --reload-th reveal; the open round comes back from authenticate with its marker (round.event) and
must carry on from that free spin to end-round. Prints the free spin it resumed at, the reveals played after the
reload, the mock's own count of end-rounds and markers, the payout against what the page shows, and the console.
usage: chresume.py --mode extremebonus --event 3111 --reload 6 [--base URL] [--w 1600 --h 900] [--phone]
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memlib import Browser, IPHONE_UA, game_url, enter_game, MOCK

a = sys.argv[1:]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
base = opt("--base", MOCK)
mode, event, at = opt("--mode", "extremebonus"), int(opt("--event", 3111)), int(opt("--reload", 6))
phone = "--phone" in a
DESK = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
b = Browser(390, 844, 3, ua=IPHONE_UA, mobile=True) if phone else Browser(int(opt("--w", 1600)), int(opt("--h", 900)), 1, ua=DESK, mobile=False)
HOOK = """(() => { window.__sp = 0; const r = handlers.reveal; handlers.reveal = async (...x) => { window.__sp++; return r(...x); };
  const seen = {}; setInterval(() => { for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s);
    if (e && e.getBoundingClientRect().width > 0) { seen[s] = (seen[s] || 0) + 1; if (seen[s] > 6) { e.click(); seen[s] = 0; } } }
    if (state.playing && !state.noSkip) state.skip = true; }, 400); return 1; })()"""
try:
    url = game_url(base)
    b.open(url, 2); enter_game(b); time.sleep(1.5)
    b.js(HOOK)
    b.js(f"fetch('/mock/force', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ sessionID: RGS.sessionID, mode: {json.dumps(mode)}, event: {event} }}) }}).then(r => r.json())")
    b.js(f"(() => {{ playRound({json.dumps(mode)}); return 1; }})()")
    ok = b.wait(f"window.__sp >= {at}", 400)
    marks_before = b.js("fetch('/mock/state', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionID: RGS.sessionID }) }).then(r => r.json()).then(m => JSON.stringify(m.marks))")
    b.open(url, 2); enter_game(b)
    b.js(HOOK)
    b.wait("state.playing", 30)
    first = b.js("JSON.stringify({ fs: state.fsShown, card: document.getElementById('fsCard').classList.contains('on'), intro: !!document.querySelector('.bonusintro'), total: state.totalWin })")
    done = b.wait("!state.playing && !RGS.state.round", 600)
    time.sleep(1.5)
    res = json.loads(b.js("""fetch('/mock/state', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionID: RGS.sessionID }) }).then(r => r.json())
      .then(m => JSON.stringify(Object.assign(m, { reveals: window.__sp, roundPayout: state.roundPayout, shownWin: document.getElementById('roundWin').textContent, rgsBalance: RGS.state.balance })))"""))
    print(json.dumps({"mode": mode, "event": event, "reload_at_reveal": at, "reached": ok, "marks_before_reload": json.loads(marks_before or "[]"),
                      "on_resume": json.loads(first), "done": done, "after": res, "console": b.console()[:8]}, indent=1))
finally:
    b.close()
