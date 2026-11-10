"""Voodoo on Bourbon 5x5 (voodoo_5x5, 2026-11-09; copied from Tipsy Harvest's tipsy_5x5) - game configuration: symbols, cluster paytable,
bet modes. A copy of smukiez_tag_run (the 7x7 live game) cut to a 5x5 board and ten paying
symbols; every mechanic and mode is unchanged.

Symbol legend (Tipsy Harvest art):
    M   Potion Multi      the booster (1.25x .. 1000x). It lands, blows out itself and the four cells that
                          share an edge with it, leaves its multiplier on each of those
                          five cells, and new symbols drop in. A cluster covering
                          multiplied cells is multiplied by the SUM of the values on those
                          cells. Two Multis reaching the same cell add. Pays nothing itself.
    BS  FS scatter        bonus scatter: 3/4/5 -> 10/12/15 free spins
    ES  XFS scatter       extreme scatter: 2 = direct Extreme Bonus (17 spins), 1 + standard trigger = upgrade
    H1  Mardi Gras Mask  H2  Voodoo Doll  H3  Jazz Trumpet  H4  Candle Skull  H5  Gris-Gris Bag
    H6  Bayou Gator      H7  Beignets
    L1  Fleur-de-lis     L3  Crawfish     L4  King Cake     (L2, L5-L10 are not in the 5x5 game)

Wall events (v5, owner 2026-10-25): far more Multis (walls) land, most of them teasers; now
and then a straight line of 3 or 4 walls drops in together, and very rarely - an outcome of
its own that the optimiser places - the whole board is covered in walls. Every winning
cluster also drops small multipliers (x1.25-x2) on some of its own cells. Max win 10,000x.

Gone since v2: the Paint Drip wild and the painted-reel colour bonus, the Full Wall mural
award, and the C1/C2/C3 characters with their spin multipliers. Gone in v5: the Tag Meter
and its extra spins - the bonus drops more walls instead.
"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode

# Bonus Boost (bet mode "boost"): the bonus - free game, extreme and the wincap that only comes
# through them - lands this many times as often as in base.
BOOST_BONUS = 1.6
BOOSTED_CRITERIA = ("wincap", "extremegame", "freegame")
# Its price. In base 0.389 of the 0.967 return (40%) comes from the bonus criteria, so 1.6x the
# bonus is worth 0.967 + 0.6 x 0.389 = 1.200 base bets: at RTP 0.967 that costs 1.241. Rounded to
# the tidy 1.25, the base game's own winning spins make up the 0.008 left over.
BOOST_COST = 1.25
# Cork Storm (bet mode "corkstorm", owner 2026-11-04): the drop is as designed - four 2,500x Multis
# on random cells, no win promised - and the optimiser shapes how often each outcome is drawn. Left
# alone the 5x5 pool caps at 10,000x about 1 spin in 5 (mean ~4,000x; 7x7 was 1 in 22); the SDK's 3-star limits
# (rgs_verification) allow the cap at most 1 play in 12,500 (etl10k <= 0.8) and wins of 5,000x+ at
# most 1.25% of plays at this price (prob5k x 0.8 <= 0.01), so those are drawn rarely
# (game_optimization: fences "wincap" and "big") and the rest of the pool keeps its own shape.
# The price is 250 and not ~230: from 250 up, 40 x cost reaches the 10,000x cap, so the etl40b
# limit (return from wins of 40x cost or more <= 0.9) counts only the capped books; at 230 it would
# also count every 9,200-9,999x win and those would have to vanish too.
ENABLE_CORKSTORM = False   # Voodoo on Bourbon sells no Cork Storm: base, bonus, extremebonus and boost only
CORKSTORM_COST = 250.0
CORKSTORM_BIG = 5000.0   # a win this size (below the cap) is recorded as "corkstorm_big"
# 5x5 (2026-11-08): with four corks on 25 cells nearly every cluster that forms covers one, so a
# win is either a bare cluster (under 10x) or 1,000x+ (0.4 x 2,500). The 1,000-4,999x wins are
# recorded "corkstorm_mid" and drawn as a group of their own, apart from the small wins.
CORKSTORM_MID = 100.0


# 5x5 paytable (2026-11-08): every value a multiple of 0.4
PAYTABLE = {
    "H1": (4.0, 8.0, 16.0, 40.0, 100.0, 400.0),
    "H2": (3.2, 6.0, 12.0, 30.0, 80.0, 300.0),
    "H3": (2.4, 4.8, 10.0, 24.0, 60.0, 200.0),
    "H4": (2.0, 4.0, 8.0, 20.0, 48.0, 160.0),
    "H5": (1.6, 3.2, 6.4, 16.0, 40.0, 120.0),
    "H6": (1.6, 3.2, 6.4, 16.0, 40.0, 120.0),
    "H7": (1.2, 2.4, 4.8, 12.0, 32.0, 100.0),
    "L1": (0.4, 0.8, 1.6, 4.0, 10.0, 32.0),
    "L3": (0.4, 0.8, 1.2, 3.2, 8.0, 24.0),
    "L4": (0.4, 0.4, 1.2, 2.8, 6.0, 20.0),
}


class GameConfig(Config):
    """Smukiez Tag Run configuration class."""

    def __init__(self):
        super().__init__()
        self.game_id = "voodoo_5x5"
        self.game_name = "voodoo_5x5"
        self.provider_numer = 0
        self.provider_number = 0
        self.provider_name = "smukiez"
        self.working_name = "Voodoo on Bourbon 5x5"
        self.wincap = 10000.0
        self.win_type = "cluster"
        self.rtp = 0.967   # the top of the SDK's 3-star volatility band (rgs_verification: rtp <= 0.967)
        self.construct_paths()

        # Game dimensions: a 5x5 cluster board (owner 2026-11-08; was 7x7)
        self.num_reels = 5
        self.num_rows = [5] * self.num_reels

        # Max board changes (cascades) within a single spin. Each pass of the cascade loop is
        # one: a board's paid clusters and any Multi blow-outs on it leave in the same tumble.
        # Without a cap a spin can chain for a very long time
        # toward the wincap, which bloats the book past what the RGS will ingest and buries
        # the player in an endless tumble.
        self.max_tumbles_per_spin = 12

        # Paytable: (cluster size, symbol) -> payout in total-bet multiples, per cluster.
        # Six size tiers: 5 | 6 | 7-8 | 9-11 | 12-15 | 16+ (up to the whole 25-cell board).
        # Every value is a multiple of 0.4: a cluster times any SUM of Multi values (multiples
        # of 0.25) then lands exactly on a tenth of the bet, the only granularity the RGS
        # accepts. 5x5 (2026-11-08): ten symbols - the seven premiums and three lows (L1 maple
        # leaf, L3 green apple, L4 grape bunch; L2, L5-L10 are gone).
        t5, t6, t7, t9, t12, t16 = (5, 5), (6, 6), (7, 8), (9, 11), (12, 15), (16, 25)
        tiers = (t5, t6, t7, t9, t12, t16)
        cluster_pays = PAYTABLE
        pay_group = {}
        for sym, pays in cluster_pays.items():
            for tier, pay in zip(tiers, pays):
                pay_group[(tier, sym)] = pay
        self.paytable = self.convert_range_table(pay_group)

        self.include_padding = True
        # Wins are clusters: five or more of a kind touching side to side, anywhere on the
        # 5x5 board (win_type "cluster"; there are no paylines).
        # "multiplier" gives the Multi its value slot (rolled when it lands) and puts that
        # value into every reveal/tumble event, so the client can show it on the tile.
        # "booster" is what the game logic looks for. There is no wild in this game.
        self.special_symbols = {
            "wild": [],
            "scatter": ["BS"],
            "scatter_extreme": ["ES"],
            "booster": ["M"],
            "multiplier": ["M"],
        }

        self.freespin_triggers = {self.basegame_type: {3: 10, 4: 12, 5: 15}}
        self.anticipation_triggers = {
            self.basegame_type: min(self.freespin_triggers[self.basegame_type].keys()) - 1,
        }

        # Smukiez feature constants
        self.extreme_direct_count = 2  # ES symbols needed to trigger Extreme Bonus directly
        self.extreme_direct_spins = 17

        # Wall events. A wall line: a straight row or column of 3 or 4 walls landing together,
        # a chance on every reveal - rarely in the base game, often in a bonus, which drops
        # walls where it used to give spins. Adjacent walls' blasts overlap, so a line leaves
        # a strip of stacked values behind it.
        self.wall_line_chance = {self.basegame_type: 1 / 40, self.freegame_type: 1 / 6}
        self.wall_line_lengths = {3: 70, 4: 30}
        # The board cover: every cell but a scatter turns to a wall at once - each cell ends up
        # the sum of its own value and up to four neighbours', and the whole board refills on
        # top of them: the base game's jackpot, a four-figure win on average. Only in the base
        # game, and only in the outcomes forced for it (criteria "wallcover"), so the optimiser
        # sets how rare it is.
        self.cover_mult_values = {5: 30, 10: 30, 20: 25, 50: 12, 100: 3}
        # Line drops: every winning cluster leaves small multipliers on some of its own cells -
        # one per five symbols it held - under the tiles, for the refill to land on. They add to
        # whatever the cell holds, like a wall's, and last as a wall's do (the spin in the base
        # game, the whole bonus in free spins).
        self.line_drop_per = 5
        self.line_drop_values = {1.25: 60, 1.5: 25, 2: 15}

        # Reels
        reels = {
            "BR0": "BR0.csv",  # base game
            "BRE": "BRE.csv",  # base game with Phantom (extreme) scatters present
            "FR0": "FR0.csv",  # standard bonus free spins
            "FRE": "FRE.csv",  # extreme bonus free spins
            "FRWCAP": "FRWCAP.csv",  # Multi-rich free-spin strip for wincap simulations
        }
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))

        # Cork Storm (the one-spin buy "corkstorm"): exactly cork_storm_count Multis land on the
        # revealed board, each worth cork_storm_value (together the 10,000x max win), on cells
        # picked at random - nothing steers a cluster onto them. The rest of the spin is an
        # ordinary base spin on BR0 with its Multis taken out ("BRC"), so the refills never bring
        # a fifth one, and no wall line drops.
        self.cork_storm_count = 4
        self.cork_storm_value = self.wincap / self.cork_storm_count
        self.reels["BRC"] = [[s for s in reel if s != "M"] for reel in self.reels["BR0"]]

        self.padding_reels = {
            "basegame": self.reels["BR0"],
            "freegame": self.reels["FR0"],
        }

        # The Multi's value, rolled the moment it lands. Heavy at the bottom with a long,
        # thin tail up to 1000x: most Multis are a nudge, and once in a long while one is the
        # whole game. The optimiser decides how often Multi outcomes appear at all; these
        # tables only shape what a Multi is worth when it does.
        # Every value is a multiple of 0.25 and every paytable entry a multiple of 0.4, so a
        # cluster times any SUM of values lands exactly on a tenth of the bet - the only
        # granularity the RGS accepts - with nothing rounded and nothing shown that is not
        # exactly what was paid. That is why the floor is 1.25x and not 1.2x.
        # v5: three times the walls, so a wall is mostly a small teaser while the 500x and 1000x
        # keep turning up - a sight far more often than a win. The 1000x is one wall in ~1,800
        # (owner, 2026-10-25: about one base spin in 1,500 once the books are weighted;
        # tools/finish_luts.py holds it there and keeps any one such board from repeating), and
        # it is nearly always a teaser: the books where it pays are the ones the optimiser keeps
        # rarest.
        booster_mults_base = {
            1.25: 480, 1.5: 280, 2: 150, 3: 60, 5: 22, 10: 7, 20: 3,
            50: 1.2, 100: 0.5, 250: 0.22, 500: 0.12, 1000: 0.55,
        }
        # in a bonus the values persist and stack across spins, with the line drops on top of
        # them: the standard bonus averages ~3.4x a wall, the extreme ~5.7x, every one 2x or more
        booster_mults_free = {
            1.25: 300, 1.5: 240, 2: 220, 3: 150, 5: 80, 10: 35, 20: 14,
            50: 5, 100: 2, 250: 0.7, 500: 0.3, 1000: 0.15,
        }
        booster_mults_extreme = {
            2: 320, 3: 260, 5: 160, 10: 70, 20: 25, 50: 8,
            100: 3, 250: 1, 500: 0.45, 1000: 0.22,
        }
        # wincap simulations only: the strip is dense with Multis and every one is huge, so
        # the 10,000x is reached in a handful of cascades instead of a thousand resimulations
        booster_mults_rich = {1000: 100}

        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.0002,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BRE": 1},
                                self.freegame_type: {"FRWCAP": 1},
                            },
                            "booster_mult_values": {
                                self.basegame_type: booster_mults_base,
                                self.freegame_type: booster_mults_rich,
                            },
                            "scatter_triggers": {3: 1, 4: 2},
                            "extreme_trigger_style": {"direct": 50, "upgrade": 50},
                            "force_wincap": True,
                            "force_freegame": True,
                            "force_extreme": True,
                        },
                    ),
                    Distribution(
                        criteria="extremegame",
                        quota=0.02,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BRE": 1},
                                self.freegame_type: {"FRE": 1},
                            },
                            "booster_mult_values": {
                                self.basegame_type: booster_mults_base,
                                self.freegame_type: booster_mults_extreme,
                            },
                            "scatter_triggers": {3: 75, 4: 25},
                            "extreme_trigger_style": {"direct": 60, "upgrade": 40},
                            "force_wincap": False,
                            "force_freegame": True,
                            "force_extreme": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.07,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1},
                            },
                            "booster_mult_values": {
                                self.basegame_type: booster_mults_base,
                                self.freegame_type: booster_mults_free,
                            },
                            "scatter_triggers": {3: 80, 4: 15, 5: 5},
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        # the board cover: forced on the reveal, so how often a player sees one
                        # is the optimiser's call (game_optimization: hr for "wallcover")
                        criteria="wallcover",
                        quota=0.002,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "booster_mult_values": {self.basegame_type: booster_mults_base},
                            "force_wincap": False,
                            "force_freegame": False,
                            "force_cover": True,
                        },
                    ),
                    Distribution(
                        criteria="0",
                        quota=0.35,
                        win_criteria=0.0,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "booster_mult_values": {self.basegame_type: booster_mults_base},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.5578,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "booster_mult_values": {self.basegame_type: booster_mults_base},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
            BetMode(
                name="bonus",
                cost=100.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.0005,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FRWCAP": 1},
                            },
                            "booster_mult_values": {
                                self.basegame_type: booster_mults_base,
                                self.freegame_type: booster_mults_rich,
                            },
                            "scatter_triggers": {3: 1, 4: 2, 5: 1},
                            "force_wincap": True,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.998,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1},
                            },
                            "booster_mult_values": {
                                self.basegame_type: booster_mults_base,
                                self.freegame_type: booster_mults_free,
                            },
                            "scatter_triggers": {3: 70, 4: 20, 5: 10},
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                ],
            ),
            BetMode(
                name="extremebonus",
                cost=400.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BRE": 1},
                                self.freegame_type: {"FRWCAP": 1},
                            },
                            "booster_mult_values": {
                                self.basegame_type: booster_mults_base,
                                self.freegame_type: booster_mults_rich,
                            },
                            "scatter_triggers": {3: 1, 4: 2},
                            "extreme_trigger_style": {"direct": 50, "upgrade": 50},
                            "force_wincap": True,
                            "force_freegame": True,
                            "force_extreme": True,
                        },
                    ),
                    Distribution(
                        criteria="extremegame",
                        quota=0.995,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BRE": 1},
                                self.freegame_type: {"FRE": 1},
                            },
                            "booster_mult_values": {
                                self.basegame_type: booster_mults_base,
                                self.freegame_type: booster_mults_extreme,
                            },
                            "scatter_triggers": {3: 75, 4: 25},
                            "extreme_trigger_style": {"direct": 60, "upgrade": 40},
                            "force_wincap": False,
                            "force_freegame": True,
                            "force_extreme": True,
                        },
                    ),
                ],
            ),
            # Bonus Boost (owner 2026-11-04): the base spin, but the bonus (free game and extreme,
            # and the wincap that only comes through them) lands BOOST_BONUS x as often. Same
            # reels, same everything; only the optimiser's targets for those criteria and their
            # sim quotas are scaled (game_optimization). Not a buy: an ante-style spin at a higher
            # price - see BOOST_COST at the top of this file.
            BetMode(
                name="boost",
                cost=BOOST_COST,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[],   # filled below from base's
            ),
        ]
        base_mode = self.bet_modes[0]
        boost_mode = next(bm for bm in self.bet_modes if bm.get_name() == "boost")
        boost_mode._distributions = self.boosted_distributions(base_mode.get_distributions())
        if ENABLE_CORKSTORM:
            self.bet_modes.append(
                # Cork Storm (owner 2026-11-04): a one-spin buy. Exactly four Multis worth 2,500x each
                # land at random on the base board and nothing else is forced: the spin pays only if
                # clusters form on the values they leave behind (game_executables.drop_corks).
                BetMode(
                    name="corkstorm",
                    cost=CORKSTORM_COST,
                    rtp=self.rtp,
                    max_win=self.wincap,
                    auto_close_disabled=False,
                    is_feature=False,
                    is_buybonus=True,
                    distributions=[
                        Distribution(
                            criteria="wincap",
                            quota=0.002,
                            win_criteria=self.wincap,
                            conditions=self._cork_conditions(),
                        ),
                        Distribution(
                            criteria="0",
                            quota=0.25,
                            win_criteria=0.0,
                            conditions=self._cork_conditions(),
                        ),
                        Distribution(
                            criteria="corkstorm",
                            quota=0.748,
                            conditions=self._cork_conditions(),
                        ),
                    ],
                )
            )

    def boosted_distributions(self, base_distributions: list) -> list:
        """Base's distributions, with the bonus criteria's sim quotas BOOST_BONUS x larger and the
        ordinary base-game criteria taking up the difference (the quotas still sum to 1)."""
        out = []
        for d in base_distributions:
            quota = round(d.get_quota() * (BOOST_BONUS if d.get_criteria() in BOOSTED_CRITERIA else 1), 6)
            out.append(Distribution(criteria=d.get_criteria(), quota=quota,
                                    win_criteria=d.get_win_criteria(), conditions=d._conditions))
        extra = sum(d.get_quota() for d in out) - 1
        for d in out:
            if d.get_criteria() == "basegame":
                d._quota = round(d._quota - extra, 6)
        return out

    def _cork_conditions(self) -> dict:
        return {
            "reel_weights": {self.basegame_type: {"BRC": 1}},
            "booster_mult_values": {self.basegame_type: {self.cork_storm_value: 1}},
            "force_wincap": False,
            "force_freegame": False,
            "force_corks": True,
            "cork_big": CORKSTORM_BIG,
            "cork_mid": CORKSTORM_MID,
        }
