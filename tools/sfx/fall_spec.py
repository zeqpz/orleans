"""The fall / Thanksgiving sound pass (2026-11-03): what Seed Audio is asked for and where each sound goes.

name -> (prompt, takes, kind, (min s, max s, keep, mode override), out)
  kind  drives the trim/clean rules (process2.K, clean3.HP); "sting" is added here: a short musical or
        animal flourish kept whole (activity merged over 0.6 s gaps)
  out   ("set", stem, target momentary-max LUFS, SFX_SETS key, level, what) -> sfx_<stem>_1..keep.wav
        ("files", [file names], target, what)                            -> those single files, in place
fall.py runs it: generate -> candidates -> pick -> clean (clean3) -> frontend/assets/*.wav (+ .ogg via
encode_new.js)."""

PRE = "[Sound effect only. No voice, no speech, no music.] "
PRE_ANIMAL = "[Sound effect only. No human voice, no speech, no words, no music.] "
PRE_STING = "[Sound effect only. No voice, no speech, no singing.] "
CLOSE = " Close-up, dry, clean studio foley recording, crisp and punchy, no background noise, no room hiss."

S = {
    # ---------------- in place of the street sounds (same files, same roles) ----------------
    "f_shake": (PRE + "Shaking a bundle of dry corn husks and straw quickly twice in one hand: a crisp, crackly, "
                "papery rustling shake, shk-shk.", 6, "foley", (.3, .8, 2, "gesture"),
                ("set", "can_shake", -23, "canShake", .34, "spin pressed: a corn-husk / straw shake")),
    "f_sweep_short": (PRE + "One quick stroke of a stiff straw broom sweeping across a dry wooden barn floor: a crisp, "
                      "airy, scratchy swish lasting half a second.", 6, "whoosh", (.35, .55, 3, "sustain"),
                      ("set", "spray_short", -22, "sprayLineShort", .36, "straw broom swish, short line")),
    "f_sweep_long": (PRE + "One long smooth stroke of a stiff straw broom sweeping steadily across a dry wooden barn "
                     "floor: a crisp, airy, scratchy swish that keeps going evenly for about one and a half seconds "
                     "and stops cleanly.", 10, "whoosh", (.9, 1.5, 2, "sustain"),
                     ("set", "spray_long", -22, "sprayLineLong", .32, "straw broom swish, long line")),
    "f_gravy_drop": (PRE + "A single fat drop of thick warm gravy falling into a full gravy boat: one tiny, soft, wet, "
                     "round plop.", 8, "drop", (.06, .3, 5, None),
                     ("set", "paint_drip", -24, "paintDrip", .3, "one gravy drop plop")),
    "f_squash": (PRE + "A small ripe pumpkin squashing open: a juicy, pulpy, wet squelch pop with a short splat.",
                 6, "hit", (.12, .7, 3, None),
                 ("set", "paint_burst", -22, "paintBurst", .4, "pumpkin squelch pop, icon burst")),
    "f_cork": (PRE + "Pulling a cork out of a cider bottle: one crisp, satisfying, hollow cork pop.", 6, "click",
               (.03, .2, 2, None), ("set", "cap_pop", -24, "capPop", .38, "cider cork pop (bonus open)")),
    "f_tumble": (PRE + "A handful of acorns and small apples tumbling and rolling down onto a wooden table in a "
                 "quick short clatter of woody knocks and soft thuds.", 6, "hit", (.3, 1.0, 2, "gesture"),
                 ("set", "cascade", -23, "cascade", .3, "acorns and apples tumbling")),
    "f_plop": (PRE + "One soft, round, muffled, cartoony plop, like a spoonful of mashed potato dropped onto a plate: "
               "a gentle, short bloop.", 8, "drop", (.08, .6, 6, None),
               ("files", ["sfx_drip_a.wav", "sfx_drip_b.wav", "sfx_drip_c.wav", "sfx_drip_d.wav", "sfx_drip_e.wav",
                          "sfx_drip_f.wav"], -24.5, "soft plops (dripLand = drip_b on every icon landing)")),
    "f_scatter": (PRE_ANIMAL + "A magical golden chime ringing out bright and sparkling, followed right away by a "
                  "short comical turkey gobble-gobble.", 6, "sting", (1.2, 3.0, 1, None),
                  ("files", ["sfx_scatter_land.wav"], -21.5, "golden chime + turkey gobble (bonus symbol lands)")),
    "f_bonus": (PRE_STING + "A quick, bright, cheerful cartoon fiddle flourish running up to a high note, followed "
                "immediately by a short rooster crow, cock-a-doodle-doo.", 6, "sting", (1.0, 1.7, 1, None),
                ("files", ["sfx_bonus_start.wav"], -23, "fiddle flourish up to a high note (free spins start); the "
                 "takes' rooster comes later in them, so the 1.7 s cap keeps only the fiddle")),
    "f_rooster": (PRE_ANIMAL + "A rooster crowing once: one loud, proud cock-a-doodle-doo, close.", 5, "sting",
                  (.9, 2.2, 2, None), ("set", "rooster", -23, "rooster", .3, "rooster crow (optional, see README)")),
    "f_bust": (PRE_STING + "A comical sad 'wah-wah-wah-waaah' made by blowing into an empty clay jug: four "
               "descending hollow hooting tones, the last one sliding down and fading, like a sad trombone.",
               6, "sting", (2.5, 4.8, 2, None),
               ("files", ["sfx_bust_a.wav", "sfx_bust_b.wav"], -16.5, "sad jug wah-wah (Multis landed, nothing used them)")),

    # ---------------- board foley: what each symbol is made of, as it lands ----------------
    "land_platter": (PRE + "A heavy porcelain serving platter with a roast turkey on it set down on a wooden table: a "
                     "solid low ceramic clunk with a soft meaty thud.", 5, "hit", (.08, .45, 3, None),
                     ("set", "land_platter", -24, "landPlatter", .28, "H1 turkey platter: ceramic clunk + thud")),
    "land_pie": (PRE + "A pie in a thin metal pie tin set down on a wooden table: a soft muffled thud with a light "
                 "tinny tick.", 5, "hit", (.06, .4, 3, None),
                 ("set", "land_pie", -24, "landPie", .26, "H2 pumpkin pie: soft thud + tin tick")),
    "land_wicker": (PRE + "A wicker basket dropped onto a wooden table: a short dry crunchy wicker creak and thump.",
                    5, "hit", (.08, .45, 3, None),
                    ("set", "land_wicker", -24, "landWicker", .28, "H3 cornucopia: wicker creak + thump")),
    "land_hat": (PRE + "A stiff felt hat dropped onto a wooden table: a soft muffled flop with a tiny metal buckle "
                 "tick.", 5, "hit", (.06, .35, 2, None),
                 ("set", "land_hat", -24, "landHat", .28, "H4 pilgrim hat: felt flop + buckle tick")),
    "land_jug": (PRE + "A heavy clay jug set down on a wooden table: a hollow ceramic clunk with a little liquid "
                 "slosh inside.", 5, "hit", (.1, .5, 3, None),
                 ("set", "land_jug", -24, "landJug", .28, "H5 moonshine jug: hollow clay clunk + slosh")),
    "land_corn": (PRE + "An ear of corn in its dry husk dropped onto a wooden table: a short dull knock with a crisp "
                  "papery husk crackle.", 5, "hit", (.08, .4, 3, None),
                  ("set", "land_corn", -24, "landCorn", .26, "H6 ear of corn: knock + husk crackle")),
    "land_pumpkin": (PRE + "A small pumpkin set down on a wooden table: one soft, hollow, round, deep thud.", 5, "hit",
                     (.06, .4, 3, None), ("set", "land_pumpkin", -24, "landPumpkin", .3, "H7 pumpkin: hollow soft thud")),
    "land_leaf": (PRE + "A dry autumn maple leaf landing on a small pile of dry leaves: a short light crisp crinkle.",
                  5, "hit", (.06, .35, 3, None), ("set", "land_leaf", -25, "landLeaf", .24, "L1 maple leaf: crisp crinkle")),
    "land_acorn": (PRE + "An acorn dropped onto a wooden table: one short light woody tick with a tiny bounce.", 5,
                   "hit", (.04, .3, 3, None), ("set", "land_acorn", -25, "landAcorn", .24, "L2 acorn: woody tick")),
    "land_apple": (PRE + "A firm apple dropped onto a wooden table: one short solid soft thud.", 5, "hit",
                   (.05, .3, 3, None), ("set", "land_apple", -24, "landApple", .26, "L3 green apple: solid soft thud")),
    "land_grapes": (PRE + "A bunch of grapes dropped onto a wooden table: a soft, squishy, bumpy thud.", 5, "hit",
                    (.06, .35, 2, None), ("set", "land_grapes", -24, "landGrapes", .26, "L4 grapes: squishy bumpy thud")),
    "land_sunflower": (PRE + "A big dried sunflower head dropped onto a wooden table: a soft papery thump with a "
                       "quick little rattle of seeds.", 5, "hit", (.08, .45, 2, None),
                       ("set", "land_sunflower", -25, "landSunflower", .24, "L5 sunflower: papery thump + seed rattle")),
    "land_candy": (PRE + "A few small hard candy pieces dropped onto a wooden table: a short light clicky clatter.",
                   5, "hit", (.1, .5, 3, "gesture"),
                   ("set", "land_candy", -25, "landCandy", .24, "L6 candy corn: light clicky clatter")),
    "land_feather": (PRE + "A large feather landing on a table: one very soft, quick, airy feathery swish.", 5, "foley",
                     (.08, .4, 2, None), ("set", "land_feather", -26, "landFeather", .22, "L7 turkey feather: airy swish")),
    "land_jelly": (PRE + "A wobbly jellied cranberry sauce dropped onto a plate: a short wet jiggly squelch and wobble.",
                   5, "hit", (.1, .5, 3, None),
                   ("set", "land_jelly", -24, "landJelly", .26, "L8 cranberry sauce: wet jelly wobble")),
    "land_porcelain": (PRE + "A small porcelain gravy boat set down on a porcelain saucer: one short bright delicate "
                       "ceramic clink.", 5, "hit", (.08, .5, 3, None),
                       ("set", "land_porcelain", -25, "landPorcelain", .24, "L9 gravy boat: porcelain clink")),
    "land_hay": (PRE + "A small bale of hay dropped onto a wooden floor: a soft heavy crunchy thump of packed dry "
                 "straw.", 5, "hit", (.1, .5, 3, None),
                 ("set", "land_hay", -24, "landHay", .28, "L10 hay bale: crunchy straw thump")),
    "land_bottle": (PRE + "A thick glass cider bottle set down hard on a wooden table: one solid glassy clunk with a "
                    "short ring.", 5, "hit", (.08, .5, 3, None),
                    ("set", "land_bottle", -21, "landBottle", .34, "M cider bottle: glassy clunk (the Multi)")),

    # ---------------- the scarecrow's foley ----------------
    "hiccup": (PRE_ANIMAL + "One single cartoon hiccup: a short, comical, squeaky 'hic' gulp from a cartoon "
               "character's throat. Just one hiccup, no words.", 6, "foley", (.08, .45, 3, None),
               ("set", "hiccup", -25, "hiccup", .12, "cartoon hiccup")),
    "straw_rustle": (PRE + "Dry straw stuffing rustling inside an old burlap shirt as a scarecrow shifts on his pole: a "
                     "short crisp crackly rustle.", 5, "foley", (.3, .8, 3, None),
                     ("set", "straw_rustle", -26, "strawRustle", .08, "straw stuffing rustle")),
    "crow_caw": (PRE_ANIMAL + "One single crow caw: a harsh, loud, raspy caw from a black crow, close.", 6, "foley",
                 (.25, .8, 3, None), ("set", "crow_caw", -24, "crowCaw", .12, "one crow caw (2 of the 3 asked for came out clean)")),
    "jug_slosh": (PRE + "Liquid sloshing and glugging inside a heavy clay jug as it swings: a short hollow glug-glug "
                  "slosh.", 5, "foley", (.3, 1.0, 2, None),
                  ("set", "jug_slosh", -26, "jugSlosh", .1, "moonshine jug glug / slosh")),
    "rope_creak": (PRE + "An old rope creaking as it tightens against a wooden post: a short dry woody creak.", 5,
                   "foley", (.3, 1.0, 2, None), ("set", "rope_creak", -26, "ropeCreak", .08, "rope creak on the pole")),
    "wing_flap": (PRE + "A crow flapping its wings hard to take off: a quick burst of four feathery wing flaps.", 5,
                  "foley", (.4, 1.2, 2, None), ("set", "wing_flap", -25, "wingFlap", .1, "crow wing flaps, taking off")),
    "crow_peck": (PRE + "A bird's beak pecking once on a stiff felt hat: one short soft woody tock.", 6, "hit",
                  (.03, .25, 3, None), ("set", "crow_peck", -25, "crowPeck", .1, "crow beak peck on the hat")),
}

# one event per take for these (no second hit inside the event)
SINGLE = {"land_platter", "land_pie", "land_hat", "land_jug", "land_corn", "land_pumpkin", "land_leaf", "land_acorn",
          "land_apple", "land_grapes", "land_sunflower", "land_feather", "land_jelly", "land_porcelain", "land_hay",
          "land_bottle", "crow_peck", "f_cork", "f_gravy_drop", "f_plop", "f_squash"}
TONAL = {"land_porcelain", "land_bottle", "f_scatter", "f_bonus", "f_bust", "land_pie"}
FOUT = {"f_scatter": 400, "f_bonus": 250, "f_bust": 250, "jug_slosh": 120, "straw_rustle": 90, "rope_creak": 90,
        "wing_flap": 90, "f_sweep_long": 120, "crow_caw": 60}


# the bed allowed under a sound that is itself a noise (a broom swish fills its whole take; outside the
# sound the gate leaves exact zero anyway); everything else keeps clean3's -72 dBFS
BED = {"f_sweep_long": -56}
# hand picks (take files from cand/) where the scoring can't hear the difference
MANUAL = {"f_bonus": ["5_0.wav"]}      # take 5: a clean fiddle run up to a high note in its first 1.45 s
# time-compressed (WSOLA, pitch kept) after cleaning: the jug's four wah-wahs came back ~4 s long
STRETCH = {"f_bust": 2.0}


def jobs():
    for name, (prompt, takes, kind, _, _) in S.items():
        yield name, prompt + CLOSE, takes, kind
