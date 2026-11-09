"""The game's five music cues: where each plays, what Lyria is asked for, and how build.py cuts it.

Voodoo on Bourbon (2026-11-08): the game is Bourbon Street at night with a voodoo showman. Every cue is an
instrumental New Orleans street brass band, the way the buskers play it on Bourbon Street: bucket drums (upturned
plastic buckets and pans played with sticks) driving a second-line groove, a tenor saxophone, a slide trombone, a
trumpet and a sousaphone on the bass line, with handclaps and a tambourine. F major for the base game, the menu and
the TOTAL WIN, C major (its dominant) for the free spins' intro and the free spins, so every crossfade sits in
related keys. Lyria takes the tempo but not the key: keep takes for their key (chroma readout).

  bars       the loop's length in bars (4/4)
  head       None: the cue is only the loop. A number: the take's opening plays once and the loop
             starts that many seconds in (snapped to the take's beat), cut from wherever after
             loop_from fits best; the opening keeps ringing under it for `tail` seconds (default 2)
  start      seconds cut off the take's front before anything else (head and loop_from count from there)
  loop_from  seconds into the take before which no loop may start (past its intro)
  game_lufs  how loud the cue should sit in the game (the music bar at 100); sets its MUSIC level.
             The street loops sat at -24.5 (base) and -22 (bonus)
"""

NO_VOX = ("Strictly instrumental: no vocals, no singing, no humming, no shouts, no chants, no spoken words. ")
BAND = ("a New Orleans street brass band busking on Bourbon Street: bucket drums - upturned plastic buckets, pans and "
        "a cowbell played with drumsticks - laying down a syncopated second-line street beat, a fat sousaphone on the "
        "bass line, a gritty tenor saxophone, a sliding, growling trombone and a bright trumpet, with handclaps and a "
        "tambourine")

CUES = {
    "base": {
        "where": "the base game",
        "bpm": 100, "bars": 32, "head": None, "loop_from": 0, "game_lufs": -24.5,
        "prompt": (
            "Instrumental only. Key: F major. Tempo: 100 BPM. " + NO_VOX +
            "A strutting, good-time groove for a cartoon slot game, 100 BPM, F major, 4/4: " + BAND + ". Laid-back "
            "second-line swagger, a little spooky and mischievous like a voodoo party at midnight, but warm and "
            "friendly; the saxophone and trombone trade a catchy riff over the sousaphone, the trumpet answers. "
            "Background music that can play for a long time: never busy or fatiguing, the bucket-drum groove steady "
            "throughout. Structure: [Short drum intro] -> [Main groove] -> [Main groove, sax and trombone trading the "
            "riff] -> [Main groove]. No breakdown, no big ending, no fade-out."),
    },
    "menu": {
        "where": "the bonus buy menu",
        "bpm": 92, "bars": 16, "head": None, "loop_from": 0, "game_lufs": -27,
        "prompt": (
            "Instrumental only. Key: F major (F, A, C). Tempo: 92 BPM. " + NO_VOX +
            "A slow, sultry late-night Bourbon Street vamp while deciding something: " + BAND + ", playing softly. "
            "92 BPM, F major, 4/4. Lazy brushed bucket-drum shuffle, a soft sousaphone walking on every beat, a "
            "breathy tenor saxophone and a muted trombone playing a smoky, mysterious little tune, a muted trumpet "
            "now and then. Calm and low energy at a rock-steady tempo: the sousaphone on every beat and a rim click on "
            "2 and 4 keep strict time. The same relaxed groove from start to finish: no build-ups, no rubato, no "
            "solo, no big ending, no fade-out."),
    },
    "intro": {
        "where": "the YOU WON n FREE SPINS screen (waits for a click)",
        "bpm": 130, "bars": 8, "head": 5.5, "tail": .6, "loop_from": 9, "game_lufs": -23.5,
        "prompt": (
            "Instrumental only. Key: C major. Tempo: 130 BPM. " + NO_VOX +
            "A brass-band announcement for a bonus round: 130 BPM, C major, 4/4. It opens instantly with a big hit - "
            "a crash, a rattling bucket-drum roll, the whole brass section blasting a rising fanfare chord with a "
            "trombone glissando up - then settles into an excited, pumping second-line vamp that holds steady and "
            "keeps repeating: driving bucket drums and cowbell, a bouncing sousaphone, short punchy sax and trumpet "
            "stabs, the trombone sliding between them, handclaps. The excited feeling just before the parade takes "
            "off. Structure: [Fanfare hit] -> [Steady pumping vamp, repeating]. No big drop, no ending, no fade-out."),
    },
    "bonus": {
        "where": "the free spins",
        "bpm": 130, "bars": 32, "head": None, "loop_from": 0, "game_lufs": -22,
        "prompt": (
            "Instrumental only. Key: C major. Tempo: 130 BPM. " + NO_VOX +
            "A fast, rowdy, joyful street parade for a slot game's free spins: 130 BPM, C major, 4/4: " + BAND +
            " at full tilt. Hard-driving bucket drums and cowbell, a pumping sousaphone line, the tenor sax and "
            "trumpet blowing a catchy hook in unison, the trombone growling and sliding underneath, handclaps and "
            "tambourine. A Mardi Gras second line with a spooky voodoo swagger. Energetic and fun from the first bar: "
            "[Main section] -> [Main section, sax and trumpet trading licks] -> [Main section with variations] -> "
            "[Main section]. No intro, no breakdown, no ending, no fade-out."),
    },
    "total": {
        "where": "the bonus's TOTAL WIN screen (waits for a click)",
        "bpm": 120, "bars": 8, "start": 0, "head": 4.4, "tail": 1.2, "loop_from": 9, "game_lufs": -22.5,
        "prompt": (
            "Instrumental only. Key: F major. Tempo: 120 BPM. " + NO_VOX +
            "A triumphant brass-band finale celebrating a huge win: 120 BPM, F major, 4/4. It opens with a big "
            "celebratory hit - a crash, a bucket-drum roll and the whole horn section holding a bright major chord "
            "with a trumpet shake on top - then a joyful, strutting victory second line: " + BAND + ", the horns "
            "playing a big happy tune over F - C - B-flat - F. Uplifting, victorious and a little goofy, like the "
            "whole of Bourbon Street dancing. Structure: [Celebration hit] -> [Joyful groove, steady and repeating]. "
            "No breakdown, no ending, no fade-out."),
    },
}
