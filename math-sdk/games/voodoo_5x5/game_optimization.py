"""Optimization parameters for the Tipsy Harvest 5x5 bet modes (tipsy_5x5, 2026-11-08).

RTP allocation (total 0.967 per mode - the top of the 3-star volatility band; tools/finish_luts.py
trims each table 1e-10 under it):
    base:         wincap 0.002 | freegame 0.340 (hr 260) | extremegame 0.052 (hr 8000)
                  | wallcover 0.0105 (hr 40000) | basegame 0.5625 (hr 2.5)
    bonus:        wincap 0.004 | freegame 0.963
    extremebonus: wincap 0.0018 | extremegame 0.9652
    boost:        base's, the bonus criteria 1.6x as frequent, priced 1.25
    corkstorm:    wincap / 0 / big / corkstorm (see the CORK_* constants)

The av_win each criteria is asked for (rtp x hr) sits near the 5x5 simulated pool's own mean, so the
optimiser weights the pool rather than fighting it (scratchpad tune5.py, 2,000-8,000 sims each):
natural free game ~88x (asked 88.4x), extreme ~416x (asked 416x), board cover ~423x (asked 420x),
base winning spins ~2.55x in the pool against 1.41x asked (the optimiser keeps the big ones rare).
The extreme's cap share is small on purpose: the 3-star band asks etl10k <= 0.8.

The base game's winning spins are weighted per BOOK, not per payout (see base_book_scaling): the
optimiser on its own weights payout values and splits each one evenly over the books that pay it.
"""

import json
import os
from collections import Counter

from game_config import BOOST_BONUS, BOOST_COST, ENABLE_CORKSTORM, CORKSTORM_COST

# Base-game targets: criteria -> (rtp, hr). basegame's rtp is what is left of the mode's.
BASE_TARGETS = {
    "wincap": 0.002,
    "freegame": (0.34, 245),
    "extremegame": (0.052, 7700),
    "wallcover": (0.011, 40000),
    "basegame_hr": 2.5,
}
from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructConditions,
    ConstructFenceBias,
    verify_optimization_input,
)

# The base game's winning spins as a player should meet them once the table is weighted: how
# often (1 in N base spins) a win lands in each band above 5x. The wins below 5x take the rest of
# the criteria's hit rate and RTP, leaning toward the bottom (a v^-a tilt, a solved to fit).
# The old value-weighted table had 5-20x 1 in 167, 20-100x 1 in 143, 100x+ 1 in 12,555: keeping
# all of that leaves the small wins averaging 0.5x, which can only be paid by drawing each 0.4x
# book about 1 in 10,000 spins, so the tail gives up about a third of its RTP (0.373 -> ~0.25).
BASE_TAIL = ((5, 20, 100), (20, 100, 250), (100, None, 15000))
# The tail is asked for at 80% of that. The table's own mean then sits a little under the
# criteria's and the optimiser lands the RTP by mixing in a few more high wins (measured: 5-20x
# 1 in 92-127, 20-100x 1 in 181-204); asked for in full, two runs in six instead piled the
# difference onto the 0.4x books (1 in ~13,000 each), while at 80% all three runs kept every
# board rarer than 1 in 20,000.
BASE_TAIL_ASK = 0.8
# Over 100x the optimiser's own curves thin the pool's few books (38 of them) to a third or less
# of what is asked, so they are asked for three times as much.
BASE_TOP_LIFT = 3.0

# Cork Storm (cost CORKSTORM_COST = 250). The 3-star limits set the shape: the cap at most 1 play in
# 12,500 (etl10k <= 0.8; asked 1 in ~15,000 -> 0.667) and every win of 5,000x or more at most 1.25%
# of plays (prob5k, x0.8 leniency at this price; asked 1 in CORK_BIG_HR). On the 5x5 board four corks
# cover up to 20 of the 25 cells, so nearly every cluster that forms touches one: a win is either a
# bare cluster (0.4x-10x) or 1,000x+ (the 100k pool: 26,035 wins under 10x, one at 10x, nothing from
# 10x to 1,000x). Fences: "big" = books recorded "corkstorm_big" (5,000x up to the cap), "mid" =
# recorded "corkstorm_mid" (100x-4,999x, in practice 1,000x-4,010x), "corkstorm" = the small wins,
# the zero books fill the rest. Each group is asked for its pool's own mean, so its inner shape is the
# drop's own (cork_book_scaling); hr/rtp only set how often each group comes. av_wins in bet
# multiples, measured on the 100,000-book pool (2026-11-08).
CORK_CAP_RTP = 0.00267          # x 250 / 10,000 -> the cap 1 in 14,981 plays
CORK_BIG_HR = 90                # 5,000x+ wins (below the cap) 1 in 90 plays
CORK_BIG_AV = 6450.0            # the pool: 15,382 books, 5,000x-9,9xx x
CORK_MID_AV = 2822.6            # the pool: 18,601 books, 1,000x-4,010x
CORK_SMALL_HR = 3.0             # a bare cluster (no cork under it) 1 in 3 plays
CORK_SMALL_AV = 0.65            # the pool: 26,035 books, 0.4x-10x


def base_book_scaling(game_config, conditions, criteria="basegame", mode="base"):
    """One scaling entry per payout of the `criteria` fence, read off the simulated pool.

    The optimiser builds each criteria's distribution as smooth curves over its PAYOUT VALUES and
    splits each value's weight evenly over the books that pay it, so a payout few books reach is
    drawn as often as one thousands reach: 0.5x (165 books) and 0.6x (112) each took ~12% of all
    rounds while 0.8x (22,000 books) got 0.004%. Scaling each payout by its book count makes the
    curves weigh BOOKS instead - every board of a payout drawn about as often as its neighbours'.
    On top of that sits the win profile above (BASE_TAIL), so the curves start from the shape
    wanted and the optimiser only has to fit the RTP and pick the best-scoring variation.

    Returns [] when there is no pool yet, which is why run.py builds the setup after the sims.
    """
    lut = os.path.join(game_config.library_path, "lookup_tables", f"lookUpTable_{mode}.csv")
    forces = os.path.join(game_config.library_path, "forces", f"force_record_{mode}.json")
    if not (os.path.exists(lut) and os.path.exists(forces)):
        return []

    # the books the optimiser hands to earlier criteria: exact payouts (wincap, 0) and searches
    names = list(conditions)
    fixed, searches = set(), []
    for name in names[: names.index(criteria)]:
        cond = conditions[name]
        if cond["force_search"]:
            searches.append(cond["force_search"])
        elif cond["search_range"][0] == cond["search_range"][1] != -1:
            fixed.add(round(cond["search_range"][0] * 100))
    taken = set()
    for option in json.load(open(forces, encoding="UTF-8")):
        keys = {(k["name"], k["value"]) for k in option["search"]}
        if any(all((str(n), str(v)) in keys for n, v in s.items()) for s in searches):
            taken.update(option["bookIds"])
    counts = Counter()
    with open(lut, encoding="UTF-8") as f:
        for line in f:
            book, _, payout = (int(x) for x in line.split(","))
            if book not in taken and payout not in fixed:
                counts[payout / 100] += 1

    share = 1 / conditions[criteria]["hr"]    # the criteria's share of all rounds
    mean = conditions[criteria]["rtp"] * conditions[criteria]["hr"]
    split = BASE_TAIL[0][0]
    bands = []
    for lo, hi, one_in in BASE_TAIL:
        books = {v: n for v, n in counts.items() if lo < v <= (hi or float("inf"))}
        size = sum(books.values())
        bands.append((lo, hi or float("inf"), (1 / one_in) / share, size, sum(v * n for v, n in books.items()) / size))
    tail_mass = sum(m for _, _, m, _, _ in bands)
    small_mean = (mean - sum(m * avg for _, _, m, _, avg in bands)) / (1 - tail_mass)
    small = {v: n for v, n in counts.items() if v <= split}
    lo_a, hi_a = -5.0, 10.0
    for _ in range(100):
        a = (lo_a + hi_a) / 2
        tilted = sum(n * v**-a for v, n in small.items())
        if sum(n * v**-a * v for v, n in small.items()) / tilted > small_mean:
            lo_a = a
        else:
            hi_a = a
    assert abs(sum(n * v**-a * v for v, n in small.items()) / tilted - small_mean) < 1e-6, (
        f"BASE_TAIL leaves the small wins a {small_mean:.3f}x mean the pool cannot tilt to")
    total = tilted / (1 - tail_mass)          # the per-book weights' sum, small part included
    levels = [(lo, hi, BASE_TAIL_ASK * m * total / size * (BASE_TOP_LIFT if lo >= 100 else 1.0))
              for lo, hi, m, size, _ in bands]

    most = max(counts.values())
    scaling = []
    for v, n in sorted(counts.items()):
        per_book = v**-a if v <= split else next(level for lo, hi, level in levels if lo < v <= hi)
        scaling.append({
            "criteria": criteria,
            "scale_factor": n / most * per_book,
            "win_range": (round(v - 0.005, 3), round(v + 0.005, 3)),
            "probability": 1.0,
        })
    return scaling


def cork_book_scaling(game_config, mode="corkstorm"):
    """Cork Storm: weigh BOOKS, not payout values, inside the "big" and "corkstorm" fences.

    Left to itself the optimiser spreads each fence's weight over its distinct payouts and splits
    a payout's share evenly over the books paying it, so the 7 books paying 10-1,000x took 4% of
    all buys between them (one 28.4x board came 1 in 59). One scaling entry per payout, its book
    count over the commonest payout's, makes every board in a fence about as likely as any other
    - the drop's own shape - and the fence's hr/rtp only set how often the group comes.
    Returns [] when there is no pool yet (run.py builds the setup after the sims)."""
    lut = os.path.join(game_config.library_path, "lookup_tables", f"lookUpTable_{mode}.csv")
    forces = os.path.join(game_config.library_path, "forces", f"force_record_{mode}.json")
    if not (os.path.exists(lut) and os.path.exists(forces)):
        return []
    group = {}
    for option in json.load(open(forces, encoding="UTF-8")):
        for key, fence in (("corkstorm_big", "big"), ("corkstorm_mid", "mid")):
            if {"name": "symbol", "value": key} in option["search"]:
                group.update(dict.fromkeys(option["bookIds"], fence))
    counts = {"big": Counter(), "mid": Counter(), "corkstorm": Counter()}
    with open(lut, encoding="UTF-8") as f:
        for line in f:
            book, _, payout = (int(x) for x in line.split(","))
            if 0 < payout < game_config.wincap * 100:
                counts[group.get(book, "corkstorm")][payout / 100] += 1
    scaling = []
    for criteria, c in counts.items():
        if not c:
            continue
        most = max(c.values())
        for v, n in sorted(c.items()):
            scaling.append({
                "criteria": criteria,
                "scale_factor": n / most,
                "win_range": (round(v - 0.005, 3), round(v + 0.005, 3)),
                "probability": 1.0,
            })
    return scaling


class OptimizationSetup:
    """Handle all game mode optimization parameters."""

    def __init__(self, game_config):
        self.game_config = game_config
        wincaps = {}
        for bm in game_config.bet_modes:
            wincaps[bm.get_name()] = bm.get_wincap()
        # Targets for the v5 wall economy (av_win = rtp*hr must be reachable from each criteria's
        # simulated distribution - see the pool means above).
        T = BASE_TARGETS
        base_rest = round(game_config.rtp - T["wincap"] - T["freegame"][0] - T["extremegame"][0] - T["wallcover"][0], 6)
        base_conditions = {
            "wincap": ConstructConditions(
                rtp=T["wincap"], av_win=wincaps["base"], search_conditions=wincaps["base"]
            ).return_dict(),
            "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
            "freegame": ConstructConditions(
                rtp=T["freegame"][0], hr=T["freegame"][1], search_conditions={"symbol": "scatter"}
            ).return_dict(),
            "extremegame": ConstructConditions(
                rtp=T["extremegame"][0], hr=T["extremegame"][1], search_conditions={"symbol": "scatter_extreme"}
            ).return_dict(),
            # the whole board covered in walls: the base game's jackpot
            "wallcover": ConstructConditions(
                rtp=T["wallcover"][0], hr=T["wallcover"][1], search_conditions={"symbol": "wallcover"}
            ).return_dict(),
            "basegame": ConstructConditions(hr=T["basegame_hr"], rtp=base_rest).return_dict(),
        }
        # Bonus Boost: base's targets with the bonus criteria BOOST_BONUS x as frequent (hr / 1.6)
        # at the same average win, priced at BOOST_COST. Every rtp here is a share of the boost's
        # cost (1.25 base bets), so a return of R base bets is asked as R / 1.25. The bonus brings
        # 1.6 x 0.389 = 0.622 base bets and the base game's own spins 0.578; the 0.008 still
        # missing to 0.967 x 1.25 = 1.209 goes on the ordinary winning spins (av_win 1.415x ->
        # 1.436x a win), so wallcover and the 0 criteria are untouched.
        k, c = BOOST_BONUS, BOOST_COST
        boost_bonus_rtp = {
            "wincap": round(T["wincap"] * k / c, 6),
            "freegame": round(T["freegame"][0] * k / c, 6),
            "extremegame": round(T["extremegame"][0] * k / c, 6),
            "wallcover": round(T["wallcover"][0] / c, 6),
        }
        boost_conditions = {
            "wincap": ConstructConditions(
                rtp=boost_bonus_rtp["wincap"], av_win=wincaps["boost"], search_conditions=wincaps["boost"]
            ).return_dict(),
            "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
            "freegame": ConstructConditions(
                rtp=boost_bonus_rtp["freegame"], hr=T["freegame"][1] / k, search_conditions={"symbol": "scatter"}
            ).return_dict(),
            "extremegame": ConstructConditions(
                rtp=boost_bonus_rtp["extremegame"], hr=T["extremegame"][1] / k, search_conditions={"symbol": "scatter_extreme"}
            ).return_dict(),
            "wallcover": ConstructConditions(
                rtp=boost_bonus_rtp["wallcover"], hr=T["wallcover"][1], search_conditions={"symbol": "wallcover"}
            ).return_dict(),
            "basegame": ConstructConditions(
                hr=T["basegame_hr"], rtp=round(game_config.rtp - sum(boost_bonus_rtp.values()), 6)
            ).return_dict(),
        }
        self.game_config.opt_params = {
            "base": {
                "conditions": base_conditions,
                "scaling": ConstructScaling(base_book_scaling(game_config, base_conditions)).return_dict(),
                "parameters": ConstructParameters(
                    num_show=1500,
                    num_per_fence=2000,
                    min_m2m=1,
                    max_m2m=400,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[50, 100, 200],
                    test_weights=[0.3, 0.4, 0.3],
                    score_type="rtp",
                ).return_dict(),
            },
            "bonus": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.004, av_win=wincaps["bonus"], search_conditions=wincaps["bonus"]
                    ).return_dict(),
                    "freegame": ConstructConditions(rtp=0.963, hr="x").return_dict(),
                },
                "scaling": ConstructScaling([]).return_dict(),
                "parameters": ConstructParameters(
                    num_show=1500,
                    num_per_fence=2000,
                    min_m2m=1,
                    max_m2m=400,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[10, 20, 50],
                    test_weights=[0.6, 0.2, 0.2],
                    score_type="rtp",
                ).return_dict(),
            },
            "extremebonus": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.0018, av_win=wincaps["extremebonus"], search_conditions=wincaps["extremebonus"]
                    ).return_dict(),
                    "extremegame": ConstructConditions(rtp=0.9652, hr="x").return_dict(),
                },
                "scaling": ConstructScaling([]).return_dict(),
                "parameters": ConstructParameters(
                    num_show=1500,
                    num_per_fence=2000,
                    min_m2m=1,
                    max_m2m=400,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[10, 20, 50],
                    test_weights=[0.6, 0.2, 0.2],
                    score_type="rtp",
                ).return_dict(),
            },
            "boost": {
                "conditions": boost_conditions,
                "scaling": ConstructScaling(
                    base_book_scaling(game_config, boost_conditions, mode="boost")
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=1500,
                    num_per_fence=2000,
                    min_m2m=1,
                    max_m2m=400,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[50, 100, 200],
                    test_weights=[0.3, 0.4, 0.3],
                    score_type="rtp",
                ).return_dict(),
            },
        }
        if ENABLE_CORKSTORM:
            big_rtp = round(CORK_BIG_AV / CORK_BIG_HR / CORKSTORM_COST, 6)
            small_rtp = round(CORK_SMALL_AV / CORK_SMALL_HR / CORKSTORM_COST, 6)
            mid_rtp = round(game_config.rtp - CORK_CAP_RTP - big_rtp - small_rtp, 6)
            mid_hr = round(CORK_MID_AV / (mid_rtp * CORKSTORM_COST), 4)
            self.game_config.opt_params["corkstorm"] = {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=CORK_CAP_RTP, av_win=wincaps["corkstorm"], search_conditions=wincaps["corkstorm"]
                    ).return_dict(),
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    "big": ConstructConditions(
                        rtp=big_rtp, hr=CORK_BIG_HR, search_conditions={"symbol": "corkstorm_big"}
                    ).return_dict(),
                    "mid": ConstructConditions(
                        rtp=mid_rtp, hr=mid_hr, search_conditions={"symbol": "corkstorm_mid"}
                    ).return_dict(),
                    # the bare clusters: 0.4x-10x, mean/median ~1.5, inside the default band
                    "corkstorm": ConstructConditions(rtp=small_rtp, hr=CORK_SMALL_HR).return_dict(),
                },
                "scaling": ConstructScaling(cork_book_scaling(game_config)).return_dict(),
                "parameters": ConstructParameters(
                    num_show=1500,
                    num_per_fence=2000,
                    min_m2m=1,
                    max_m2m=400,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[10, 20, 50],
                    test_weights=[0.6, 0.2, 0.2],
                    score_type="rtp",
                ).return_dict(),
            }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
