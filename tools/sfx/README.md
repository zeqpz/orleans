# Sound effects pipeline (2026-11-03 pass)

How the 47 sound sets (`frontend/assets/sfx_<stem>_<n>.wav` + `.ogg`) were made. Kept here so the pass can be re-run;
the raw generations and review spectrograms were left out (rebuildable, ~140 MB).

- `gen.py` / `orapi.py` - generate takes with OpenRouter's Seed Audio model (key read from
  `Documents/gamdevkey.txt`; never printed). `newlist.txt` / `cand.json` - the prompts and the takes made.
- `clean3.py` (+ `report3.json`) - the final clean (2026-11-03, after the owner still heard hiss): noise profile from
  the take's own bed (not its silent padding), per-type high-pass, noisereduce stationary (+ non-stationary on
  transients), a hard gate to exact digital zero, trims at the gate, damage checks with gentler retries.
- `process.py`, `process2.py`, `audiolib.py` - the first clean: DC + high-pass, spectral gate from the take's own quiet
  stretches, cut into single events, tight start / natural tail, expander, slow-attack compression, loudness match,
  a -1.5 dBFS limiter, end fades.
- `pick_takes.py` (+ `picks.json`, `manual_picks.json`) - choose the best, most alike takes per set.
- `synth.py` - the sets made in numpy instead (paint drips, sparkles, glow, shine).
- `assemble.py` -> `final.json`, then `encode_new.js` (the same settings as `tools/encode_sfx.js`) for the Opus copies.
- `an_existing.py`, `spec.py` - loudness/noise analysis of the existing set, spectrograms for review.

Run with the venv at `ClaudeRoblox/smukiez-slot/.venv` (numpy, scipy, soundfile, noisereduce). The sets are registered
in `SFX_SETS` / `SFX_VOL` in `frontend/index.html`; `sfx(name)` picks a take other than the last and nudges its pitch.

## Fall / Thanksgiving pass (2026-11-03)

The reskin's sounds, made on the same tools: `fall_spec.py` (prompts, kinds, caps, where each sound goes) and
`fall.py` (`gen` / `cand` / `pick` / `build` / `all`: Seed Audio takes -> process2's events -> pick_takes' scoring ->
clean3's strict clean and master, written straight into `frontend/assets/`). Work files live in `%TEMP%/fall_sfx/`
(raw takes, candidates, picks, `written.txt`, and a backup of every street-pass `sfx_*`/`music_*` file in
`old_assets/`). Opus copies: `node tools/sfx/encode_new.js <ClaudeRoblox>/.tools/pw/node_modules/playwright
%TEMP%/fall_sfx/written.txt` (its DIR now points at this repo's assets).

- `orapi.py` now reads the key from `%USERPROFILE%\Documents\gamdevkey.txt`.
- Replaced in place (same names, same roles): `can_shake` (corn-husk/straw shake), `spray_short` / `spray_long`
  (straw broom swish), `paint_drip` (gravy plop), `paint_burst` (pumpkin squelch), `cap_pop` (cider cork),
  `cascade` (acorns and apples tumbling), `drip_a..f` (soft plops), `scatter_land` (golden chime + turkey gobble),
  `bonus_start` (fiddle flourish), `bust_a/b` (sad jug wah-wah).
- New: 18 `land_<material>` sets for the fall symbols, the scarecrow's `hiccup`, `straw_rustle`, `crow_caw`,
  `jug_slosh`, `rope_creak`, `wing_flap`, `crow_peck`, and an optional `rooster` (not wired).
- Kept: the UI, counters, bells, coins, glints / sparkles / shine / glow, slam, whooshes, intro ident and the
  Casino Machines singles (spin, bet, reels, line, pop, multi hit, alerts, win text, trophy, coins rain, ...).
- What the cleaning taught: a deep thud (pumpkin) kept failing clean3's guard after denoising, so `fall.py` adds a last
  pass that reduces nothing and leaves it to the gate (only taken when the take's own bed is already under -72 dBFS); a
  broom swish is itself noise, so its bed limit is -56 (`BED`); the jug wah-wahs came back ~4 s, so they are
  time-compressed 2x with pitch kept (`wsola`) and re-levelled; the "fiddle + rooster" takes put the rooster ~2.5 s in,
  so the bonus start keeps only the fiddle (1.7 s cap) and the rooster got its own prompt.
