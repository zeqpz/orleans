"""Voodoo on Bourbon sound pass (2026-11-08): what Seed Audio is asked for and where each sound goes.
Every game sound is replaced with a New Orleans / voodoo one EXCEPT the HUD buttons (uiClick, uiHover, sliderTick,
swishIn/Out, menuOpen/Close, toggle, autoStart/Stop, bet, skip, hoverLoop), which keep the base build's sounds.

name -> (prompt, takes, kind, (min s, max s, keep, mode override), out)   - the same shape as fall_spec.py
  out   ("set", stem, target LUFS, SFX_SETS key, level, what) -> sfx_<stem>_1..keep.wav (nola.py registers the set)
        ("files", [file names], target LUFS, what)               -> those single files, in place
nola.py runs it: generate -> candidates -> pick -> clean (clean3) -> frontend/assets/*.wav (+ .ogg via encode_new.js)."""

PRE = "[Sound effect only. No voice, no speech, no music.] "
PRE_STING = "[Sound effect only. No voice, no speech, no singing.] "
CLOSE = " Close-up, dry, clean studio recording, crisp and punchy, no background noise, no room hiss."
BRASS = "a New Orleans street brass band"


def st(stem, key, level, what, lufs=-23):
    return ("set", stem, lufs, key, level, what)


S = {
    # ---------------- the spin and the board ----------------
    "n_spin": (PRE_STING + "A quick rattling snare roll played on an upturned plastic bucket with drumsticks, ending on one "
               "sharp cowbell clank.", 5, "hit", (.3, .9, 1, "gesture"),
               ("files", ["sfx_spin.wav"], -22, "spin: bucket-drum roll + cowbell")),
    "n_reels": (PRE + "A steady, continuous, fast rattle of a tambourine and a shaker played evenly, with no accents, for "
                "two seconds.", 5, "foley", (.7, 2.2, 1, "sustain"),
                ("files", ["sfx_reels.wav"], -24, "reels turning: even tambourine + shaker rattle (pitched by speed)")),
    "n_shake": (PRE + "Shaking a dried gourd rattle full of seeds and small bones quickly twice: a dry, clicky voodoo "
                "rattle, shk-shk.", 6, "foley", (.3, .8, 2, "gesture"),
                st("can_shake", "canShake", .34, "spin pressed: a voodoo gourd rattle")),
    "n_reelstop": (PRE + "One short solid thump of a big bass drum with a small cowbell tick on top.", 5, "hit",
                   (.12, .5, 3, None), st("reel_stop", "reelStop", .3, "a column's last tile down")),
    "n_tap": (PRE + "One soft, low, muffled tap of a felt drumstick on the bottom of a plastic bucket.", 6, "drop",
              (.06, .35, 6, None),
              ("files", ["sfx_drip_a.wav", "sfx_drip_b.wav", "sfx_drip_c.wav", "sfx_drip_d.wav", "sfx_drip_e.wav",
                         "sfx_drip_f.wav"], -25, "soft bucket taps (dripLand = drip_b on every icon landing)")),
    "n_cascade": (PRE + "A handful of plastic Mardi Gras beads and metal doubloons tumbling and clattering onto "
                  "cobblestones in one quick short shower.", 5, "hit", (.3, 1.0, 2, "gesture"),
                  st("cascade", "cascade", .3, "the refill tumbling in: beads + doubloons")),
    "n_pop": (PRE + "One short, round, hollow pop, like a cork pulled from a small glass bottle, with a tiny puff.", 6,
              "click", (.05, .3, 1, None), ("files", ["sfx_pop.wav"], -24, "one icon coming apart")),
    "n_burst": (PRE + "A short wet pop and fizz, like a bubble of potion bursting with a little sizzle.", 5, "hit",
                (.12, .6, 3, None), st("paint_burst", "paintBurst", .38, "under every third icon pop: potion bubble")),
    "n_line": (PRE_STING + "One short bright stab of a trumpet and a trombone playing a single note together.", 5,
               "sting", (.25, .9, 1, None), ("files", ["sfx_line.wav"], -23, "a cluster pays: brass stab")),
    "n_scatter": (PRE + "A magical shimmering crystal chime ringing out, with a soft ghostly rising whoosh of wind under "
                  "it, like a spirit waking.", 6, "sting", (1.0, 2.6, 1, None),
                  ("files", ["sfx_scatter_land.wav"], -21.5, "FS/XFS lands: crystal chime + spirit whoosh")),
    # ---------------- the Multi: hexed, not popped ----------------
    "n_multi": (PRE + "A spooky voodoo magic hit: one deep low drum boom with a rattle of dry bones and a short ghostly "
                "rising whoosh.", 6, "hit", (.3, 1.8, 1, "gesture"),
                ("files", ["sfx_multi_hit.wav"], -21, "a Multi going off: voodoo boom + bone rattle")),
    "n_vanish": (PRE + "A ghostly magic vanish: a soft breathy whoosh of wind sucking away upward into a faint "
                 "shimmering chime, like a spirit disappearing in a puff of smoke.", 8, "whoosh", (.5, 1.2, 3, None),
                 st("vanish", "vanish", .42, "a potion hexed away (no pop)")),
    "n_reveal": (PRE + "A soft reversed magical whoosh gathering in toward the listener and ending on one gentle glassy "
                 "chime, like smoke condensing into something.", 6, "whoosh", (.4, 1.0, 2, None),
                 st("reveal", "reveal", .36, "a Multi's value conjured out of smoke")),
    "n_slam": (PRE + "A heavy, deep voodoo drum slam, one big hit on a large hand drum with a rattle of bones.", 6,
               "hit", (.2, 1.4, 3, "gesture"), st("mult_slam", "multSlam", .6, "the x<N> slamming onto the figure")),
    "n_alert": (PRE_STING + BRASS[0].upper() + BRASS[1:] + " hitting one short loud fanfare chord, trumpet, trombone and "
                "saxophone together, with a cymbal crash.", 6, "sting", (.6, 1.6, 2, None),
                ("files", ["sfx_jackpot_alert_a.wav", "sfx_jackpot_alert_b.wav"], -21, "a run of Multis: brass hits")),
    "n_bust": (PRE_STING + "A comical sad trombone: 'wah-wah-wah-waaah', four descending notes, the last one sliding down "
               "and fading.", 6, "sting", (1.6, 3.4, 2, None),
               ("files", ["sfx_bust_a.wav", "sfx_bust_b.wav"], -17, "Multis landed, nothing used them: sad trombone")),
    # ---------------- the win presentation ----------------
    "n_sweep_short": (PRE + "A quick airy ghostly whoosh, like a spirit flying past, half a second.", 6, "whoosh",
                      (.35, .6, 3, "sustain"), st("spray_short", "sprayLineShort", .34, "the win line: spirit whoosh")),
    "n_sweep_long": (PRE + "A long smooth airy ghostly whoosh of wind sweeping past evenly for about one and a half "
                     "seconds and stopping cleanly.", 8, "whoosh", (.9, 1.5, 2, "sustain"),
                     st("spray_long", "sprayLineLong", .3, "the win line, long")),
    "n_plink": (PRE + "One tiny, bright, glassy magic plink, like a single drop falling into a crystal bowl.", 6, "drop",
                (.06, .4, 5, None), st("paint_drip", "paintDrip", .26, "drops off the win line: glassy plinks")),
    "n_glow": (PRE + "A soft low eerie magical swell, a breathy hum of rising spirit energy, about one second.", 5,
               "tone", (.4, 1.3, 2, None), st("glow_pulse", "glowPulse", .26, "a winning symbol lighting up")),
    "n_shine": (PRE + "A bright magical shimmer sweeping across with two small glassy glints at its end.", 5, "tone",
                (.25, .9, 2, None), st("shine", "shine", .3, "a shine sweeping a symbol")),
    "n_sparkle": (PRE + "A quick run of tiny magical glittering chimes, like fairy dust.", 5, "tone", (.3, 1.2, 3, None),
                  st("sparkle", "sparkle", .28, "glitter twinkles")),
    "n_glint": (PRE + "One small, bright, clear bell ting, like a tiny brass bell struck once.", 6, "click",
                (.1, .6, 3, None), st("glint", "glint", .24, "one ting a lit symbol")),
    "n_wintext": (PRE_STING + BRASS[0].upper() + BRASS[1:] + " playing a short bright 'ta-daa!' - trumpet and trombone with a "
                  "snare hit.", 6, "sting", (.6, 1.5, 1, None), ("files", ["sfx_win_text.wav"], -22, "the win amount pops up")),
    "n_tick": (PRE + "One single short dry click of a wooden drumstick on the rim of a drum.", 6, "click",
               (.015, .08, 3, None), st("count_tick", "countTick", .26, "the win figure counting")),
    "n_countend": (PRE_STING + "A big bucket-drum hit with a cowbell clank and a cymbal crash, ringing out.", 5, "impact",
                   (.4, 1.8, 1, "gesture"), st("count_end", "countEnd", .5, "the figure lands")),
    "n_rise": (PRE + "A rising magical whoosh with a shimmer, getting brighter, about one second.", 5, "whoosh",
               (.6, 1.4, 2, None), st("count_whoosh", "countWhoosh", .38, "counting up again after the slam")),
    "n_float": (PRE + "A soft airy ghostly whoosh drifting away upward and fading out.", 5, "whoosh", (.6, 1.8, 2, None),
                st("float_away", "floatAway", .34, "the figure floating away")),
    "n_tick1": (PRE + "One single tiny tick of a small shaker.", 5, "click", (.02, .12, 1, None),
                ("files", ["sfx_money_tick.wav"], -26, "the total's counter tick")),
    "n_medium": (PRE_STING + "A short cheerful saxophone riff, five quick bouncy notes ending high.", 6, "sting",
                 (.8, 2.0, 1, None), ("files", ["sfx_medium_win.wav"], -22, "a medium win: sax riff")),
    "n_trophy": (PRE_STING + BRASS[0].upper() + BRASS[1:] + " holding one big triumphant major chord with a trumpet shake on "
                 "top and a long cymbal crash.", 6, "sting", (1.2, 3.0, 1, None),
                 ("files", ["sfx_trophy.wav"], -21, "the total's arrival: big brass chord")),
    "n_rain": (PRE + "A long shower of plastic Mardi Gras beads and metal doubloons raining down and bouncing on "
               "cobblestones for two seconds.", 5, "foley", (1.2, 2.6, 1, "sustain"),
               ("files", ["sfx_coins_rain.wav"], -23, "doubloons and beads raining")),
    "n_coins": (PRE + "A handful of heavy gold doubloon coins jingling and clinking together.", 5, "foley",
                (.3, 1.2, 1, "gesture"), ("files", ["sfx_coins.wav"], -23, "doubloons jingling")),
    "n_bell": (PRE + "One single clang of an old streetcar bell, bright and ringing.", 5, "tone", (.4, 1.6, 1, None),
               ("files", ["sfx_bell.wav"], -22, "streetcar bell (spins added)")),
    "n_fstick": (PRE + "One short ding of an old brass streetcar bell.", 6, "tone", (.2, .9, 2, None),
                 st("fs_tick", "fsTick", .3, "the free spins counter turning over")),
    "n_jackpot": (PRE_STING + BRASS[0].upper() + BRASS[1:] + " big win hit: a rattling snare roll into a huge unison horn chord "
                  "and a cymbal crash.", 6, "sting", (1.0, 2.6, 2, None),
                  ("files", ["sfx_jackpot_a.wav", "sfx_jackpot_b.wav"], -20.5, "big win: drum roll + horn chord")),
    "n_bonus": (PRE_STING + "A hot trumpet flourish running quickly up to a high note with a shake, over a snare roll.", 6,
                "sting", (.9, 1.8, 1, None), ("files", ["sfx_bonus_start.wav"], -22, "free spins start: trumpet run")),
    "n_bonusend": (PRE_STING + BRASS[0].upper() + BRASS[1:] + " ending: a short drum roll and one final unison horn hit.", 5,
                   "sting", (.8, 2.0, 1, None), ("files", ["sfx_bonus_end.wav"], -22, "free spins over: brass ending")),
    # ---------------- the bonus buy (its own sounds; its buttons' clicks stay HUD) ----------------
    "n_cork": (PRE + "A cork popping out of a glass potion bottle followed by a short fizzy bubbling.", 6, "hit",
               (.1, 1.0, 2, "gesture"), st("cap_pop", "capPop", .38, "the bonus buy opening: potion cork")),
    "n_spell": (PRE + "A voodoo spell being cast: one deep hand-drum hit and a bright shimmering magical whoosh rising.",
                5, "impact", (.6, 1.6, 1, None), st("buy_confirm", "buyConfirm", .5, "a bonus bought")),
    # ---------------- the opening ident ----------------
    "n_irise": (PRE + "An eerie rising swell: a low drum roll on a big hand drum growing louder with a rising wind, "
                "about one and a half seconds, ending at its peak.", 5, "whoosh", (1.0, 1.8, 3, None),
                st("intro_rise", "introRise", .5, "ident: rising tension")),
    "n_iwhoosh": (PRE + "A fast airy swoosh, like a ghost flying past quickly.", 5, "whoosh", (.4, .9, 3, None),
                  st("intro_whoosh", "introWhoosh", .45, "ident: the light sweeping")),
    "n_ihit": (PRE + "A huge deep drum boom with a crash cymbal and a long ghostly echo decaying away.", 5, "impact",
               (1.2, 2.8, 2, None), st("intro_hit", "introHit", .7, "ident: the logo landing")),
    "n_ishimmer": (PRE + "A glassy, magical shimmer of tiny chimes, about one second.", 5, "tone", (.8, 1.5, 3, None),
                   st("intro_shimmer", "introShimmer", .42, "ident: sheen over the letters")),
    "n_iout": (PRE + "A reversed swell of wind sucking inward and stopping, about one second.", 5, "whoosh",
               (.6, 1.1, 2, None), st("intro_out", "introOut", .45, "ident: whoosh out to the next screen")),
    # ---------------- Doc's foley ----------------
    "n_cane": (PRE + "One crisp tap of a wooden walking cane's metal tip on a cobblestone.", 6, "click",
               (.05, .35, 3, None), st("cane_tap", "caneTap", .16, "Doc's cane tapping")),
    "n_poof": (PRE + "A soft magical poof of smoke with a tiny shimmer at its end.", 6, "whoosh", (.3, .9, 2, None),
               st("magic_poof", "magicPoof", .16, "Doc conjuring a wisp")),
    "n_hat": (PRE + "A short soft cloth swish, like a top hat being lifted and tipped.", 5, "foley", (.15, .5, 2, None),
              st("hat_swish", "hatSwish", .12, "Doc tipping his hat")),
    "n_cane_spin": (PRE + "A quick airy whirr of a stick being twirled fast through the air, whoo-whoo.", 5, "whoosh",
                    (.4, 1.1, 2, None), st("cane_spin", "caneSpin", .14, "Doc twirling his cane")),
    # ---------------- board foley: what each symbol is made of, as it lands ----------------
    "l_mask": (PRE + "A light hollow plastic carnival mask with feathers set down on a wooden table: a light papery "
               "tap with a soft feather rustle.", 4, "hit", (.08, .45, 2, None), st("land_mask", "landMask", .26, "H1 mask")),
    "l_doll": (PRE + "A small soft burlap doll stuffed with straw dropped onto a table: a soft cloth thump.", 4, "hit",
               (.06, .4, 2, None), st("land_doll", "landDoll", .28, "H2 voodoo doll")),
    "l_brass": (PRE + "A brass trumpet set down on a wooden table: a bright metallic clank with a short ring.", 4, "hit",
                (.1, .6, 2, None), st("land_brass", "landBrass", .24, "H3 trumpet, L10 lamp")),
    "l_bone": (PRE + "A dry skull or bone dropped onto a wooden table: a hollow, clacky, bony knock.", 4, "hit",
               (.06, .4, 3, None), st("land_bone", "landBone", .26, "H4 skull, L9 bone, ES")),
    "l_leather": (PRE + "A small leather pouch full of charms dropped onto a table: a soft leathery thud with a tiny "
                  "jingle.", 4, "hit", (.08, .45, 2, None), st("land_pouch", "landPouch", .26, "H5 gris-gris")),
    "l_gator": (PRE + "A small wet splash with a quick snap of jaws.", 4, "hit", (.1, .6, 2, None),
                st("land_gator", "landGator", .24, "H6 gator")),
    "l_pastry": (PRE + "A soft warm pastry dropped onto a plate: a muffled soft pat with a light powdery puff.", 4, "hit",
                 (.06, .4, 2, None), st("land_pastry", "landPastry", .26, "H7 beignets, L4 king cake")),
    "l_metal": (PRE + "A heavy old iron key set down on a wooden table: a short dull metallic clink.", 4, "hit",
                (.06, .45, 2, None), st("land_iron", "landIron", .24, "L1 fleur-de-lis, L6 key")),
    "l_beads": (PRE + "A string of plastic Mardi Gras beads dropped onto a table: a short clattery rattle.", 4, "foley",
                (.12, .6, 2, "gesture"), st("land_beads", "landBeads", .24, "L2 beads")),
    "l_shell": (PRE + "A boiled crawfish dropped onto a metal tray: a light crunchy shell clack.", 4, "hit",
                (.06, .4, 2, None), st("land_shell", "landShell", .24, "L3 crawfish")),
    "l_wax": (PRE + "A thick wax candle set down on a wooden table: a soft dull waxy thunk.", 4, "hit", (.06, .4, 2, None),
              st("land_wax", "landWax", .26, "L5 candle")),
    "l_doubloon": (PRE + "One gold coin dropped onto a wooden table, spinning briefly and settling.", 4, "foley",
                   (.15, .8, 2, "gesture"), st("land_doubloon", "landDoubloon", .24, "L7 doubloon")),
    "l_card": (PRE + "One stiff playing card flicked down onto a table: a crisp papery slap.", 4, "click",
               (.04, .3, 2, None), st("land_tarot", "landTarot", .24, "L8 tarot card, BS")),
    "l_glass": (PRE + "A small round glass bottle of liquid set down on a wooden table: a glassy clink with a little "
                "slosh.", 4, "hit", (.08, .5, 2, None), st("land_glass", "landGlass", .26, "M potion")),
}

FOUT = {"n_scatter": 300, "n_bust": 250, "n_trophy": 400, "n_jackpot": 350, "n_bonus": 200, "n_bonusend": 250,
        "n_alert": 200, "n_ihit": 500, "n_rain": 150, "n_sweep_long": 120, "n_reels": 60, "n_countend": 250}
TONAL = {"n_glow", "n_shine", "n_sparkle", "n_glint", "n_bell", "n_fstick", "n_ishimmer", "n_line", "n_medium", "n_wintext",
         "n_trophy", "n_jackpot", "n_bonus", "n_bonusend", "n_alert", "n_bust", "n_scatter"}
BED = {"n_sweep_long": -56, "n_sweep_short": -56, "n_reels": -56, "n_rain": -60, "n_irise": -60}
MANUAL = {}
STRETCH = {}

# which symbol makes which landing sound (LAND_FOLEY in frontend/index.html)
LAND = {"H1": "landMask", "H2": "landDoll", "H3": "landBrass", "H4": "landBone", "H5": "landPouch", "H6": "landGator",
        "H7": "landPastry", "L1": "landIron", "L2": "landBeads", "L3": "landShell", "L4": "landPastry", "L5": "landWax",
        "L6": "landIron", "L7": "landDoubloon", "L8": "landTarot", "L9": "landBone", "L10": "landBrass", "M": "landGlass"}


def jobs():
    for name, (prompt, takes, kind, _, _) in S.items():
        yield name, prompt + CLOSE, takes, kind

# one event per take: the landings, the clicks and the single hits are cut to their first event only
SINGLE = {n for n in S if n.startswith("l_")} | {"n_pop", "n_tick", "n_tick1", "n_cane", "n_reelstop"}
