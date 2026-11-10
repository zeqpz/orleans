"""Optimise only the given modes from the books already simulated (no sims, no full config
rewrite): builds the optimisation setup, writes the temp math config, runs the Rust optimiser.

    python opt_modes.py <mode> [<mode> ...] [--threads N]
"""
import argparse

from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from src.write_data.write_configs import make_temp_math_config

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("modes", nargs="+")
    ap.add_argument("--threads", type=int, default=12)
    args = ap.parse_args()
    config = GameConfig()
    gamestate = GameState(config)
    OptimizationSetup(config)
    make_temp_math_config(gamestate)
    from optimization_program.run_script import OptimizationExecution

    OptimizationExecution().run_all_modes(config, args.modes, args.threads)
