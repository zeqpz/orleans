# Music

## Fall pass (2026-11-03)

The five cues were redone for the Thanksgiving harvest-farm reskin: instrumental cartoon jug-band Americana
(fiddle, banjo, acoustic guitar, upright bass, washboard and brushes, a blown jug, accordion, glockenspiel).
Prompts are in `cues.py`; the kept takes are in `art/music-src/` (the street takes are gone from this copy).

| cue   | take (art/music-src/) | key     | tempo | in the game                                              |
|-------|-----------------------|---------|-------|----------------------------------------------------------|
| base  | base.mp3              | D major | 101   | 32-bar loop (76.0 s)                                     |
| menu  | menu.mp3              | D major | 100   | 16-bar loop (38.4 s)                                     |
| intro | intro.mp3             | D major | 135.7 | fanfare head (5.76 s, once), then an 8-bar loop (14.2 s) |
| bonus | bonus.mp3             | D major | 135.6 | 32-bar loop (56.6 s), drops in on the intro's next beat  |
| total | total.mp3             | G major | 123   | swell + hit head (4.45 s, once), then an 8-bar loop      |

- The key is now read from `%USERPROFILE%\Documents\gamdevkey.txt`. Runs on the venv at
  `ClaudeRoblox/smukiez-slot/.venv` (PyAV installed into it for this).
- Lyria refused prompts with "drunk" / "tipsy" in them (`PROHIBITED_CONTENT` on 5 of 15): the prompts say
  "goofy" / "wobbly" instead. Its keys again came back anywhere (D, A, E, F, G for a G-major ask), so every
  cue was picked by key: D major for four, the total in G (the subdominant).
- Lyria's tempo drifts within a take: the 8-bar loops of the intro and the total came out 70 and 120 ms off
  the constant-tempo grid. `build.py` now finds that drift first (`coarse_lag`: the onset curve two bars
  after the loop's end against the two after its start, within half a beat, only taken where it clearly
  matches) and then lines up the transients to the sample as before.
- `cues.py` has a `start` (seconds cut off the take's front): the total's take opens on 1.3 s of silence.
- The first menu take drifted too much to loop cleanly (no clear onset match); the kept one asks for a
  "rock-steady tempo" and came back at exactly 100.000 BPM.

## The street pass (2026-10-30)

Five cues, generated with Google's Lyria 3 Pro through OpenRouter and cut into seamless loops for
the game: the base game, the bonus buy menu, the YOU WON n FREE SPINS screen, the free spins and
the bonus's TOTAL WIN. Instrumental, early-90s piano house and UK rave with heist-score tension.

| cue   | take (art/music-src/) | key       | tempo | in the game                                          |
|-------|-----------------------|-----------|-------|------------------------------------------------------|
| base  | base.mp3              | G minor   | 125   | 32-bar loop, resumes where it left off                |
| menu  | menu.mp3              | G minor   | 120   | 16-bar loop while the buy menu is open                |
| intro | intro.mp3             | C minor   | 174   | impact and build (5.6 s, once), then an 8-bar loop    |
| bonus | bonus.mp3             | C minor   | 174   | 32-bar loop, drops in on the intro's next beat        |
| total | total.mp3             | B-flat    | 120   | celebration hit (8.6 s, once), then an 8-bar loop     |

## Regenerate

```
python tools/music/lyria.py base --takes 3     # takes -> %TEMP%/music_gen/base/ (~$0.08 each)
copy %TEMP%\music_gen\base\<take>.mp3 art\music-src\base.mp3   (and its .json)
python tools/music/build.py base --wav         # cut + encode -> frontend/assets/music_base.ogg/.aac
```

`build.py` prints the cue's `MUSIC` entry; paste it over the old one in `frontend/index.html`.
`--wav` also writes `%TEMP%/music_build/<cue>.wav` (the head, then the loop twice) to listen to.
Runs on `.venv312` (numpy, scipy, PyAV). The key is read from
`%USERPROFILE%\Documents\gamdevkey.txt`.

## Things the first round taught

- Lyria follows the tempo it is asked for (within ~4%) but **not the key**: of 15 takes, the keys
  were all over. Takes were picked for their key so the cues crossfade without clashing; check
  with a chroma readout before keeping one. A prompt can come back `PROHIBITED_CONTENT` once and
  pass the next time.
- OpenRouter returns MP3 (44.1 kHz, 192 kbps) whatever format is asked for; `build.py` resamples to
  48 kHz.
- The beat grid can lock onto house's off-beat open hats: `beat_grid` moves half a beat when the
  kick lines up there clearly better. Downbeats come from the claps on 2 and 4 plus where the
  arrangement changes (not chord changes alone: house piano pushes its chords a beat early).
- Seams are chosen by the spectrum in dB and the chroma either side of the junction, then lined up
  on the drum transients. A cue with a head keeps the head's beat of the bar, so the loop carries
  on its meter.
- Opus decodes to the exact frame count in Chrome; FFmpeg's AAC puts 1024 frames of encoder delay
  in front, which `aacStart` covers (checked in Chrome: offset error 0 for every cue).
