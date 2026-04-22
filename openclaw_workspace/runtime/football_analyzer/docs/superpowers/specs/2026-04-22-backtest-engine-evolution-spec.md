# 4-Core Lottery Backtest Engine Evolution Spec

## Goal
Upgrade the backtesting framework (`run_blind_backtest.py` and `historical_database.py`) to fully support the historical simulation of the 4 core high-value play types identified: Jingcai WDL (胜平负), Jingcai Goals (总进球), Beidan SXDS (上下单双), and Zucai Renjiu (任选九).

## Architecture
1. **Data Layer Expansion**: Update `historical_database.py` to extract Half-Time scores (`ht_score` / `ht_home_score` / `ht_away_score`) and any available handicap or odds data from the JSON if present. If odds for GOALS or SXDS are missing, we will generate dynamic baseline odds based on historical payout averages to allow EV calculation.
2. **Settlement Engine Integration**: Integrate the existing `SettlementEngine` from `test_destructive_math.py` into the main `run_blind_backtest.py` loop. Instead of `if actual_h > actual_a`, the script will use the Settlement Engine to determine the exact winning options across the 4 core play types.
3. **Multi-Market EV Scanner**: In `run_blind_backtest.py`, the AI logic will call `LotteryMathEngine.calculate_all_markets()` to get the probabilities for WDL, GOALS, and SXDS. It will then evaluate the EV across all these markets simultaneously and choose the single most profitable market to bet on.

## Tech Stack
- Python 3.10+
- Existing `historical_database.py`, `run_blind_backtest.py`

## Implementation Plan
See `docs/superpowers/plans/2026-04-22-backtest-engine-evolution.md`
