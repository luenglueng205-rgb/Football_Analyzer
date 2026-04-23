# Chinese Lottery Analytics Evolution Spec

## Goal
Evolve the system's core mathematical and analytics capabilities to be deeply customized for Chinese lotteries (JINGCAI, BEIDAN, ZUCAI). Replace generic international betting models (like back/lay hedging) with specialized structural models (Parlay Kelly, Last-Leg Hedging, Tail-Probability Poisson).

## Architecture
1. **Parlay Kelly Calculator (Jingcai)**: Introduce a specialized Kelly Criterion calculator that evaluates EV and bankroll sizing for multi-leg parlay (M串N) combinations rather than just single events.
2. **Dynamic SP Estimator (Beidan)**: Create a regression tool to estimate the final SP (Starting Price) for Beidan based on current volume and time to kickoff, solving the "blind Kelly" problem.
3. **Poisson Tail-Probability Mapper (Jingcai)**: Refactor the Poisson engine to correctly aggregate tail probabilities (e.g., 5-0, 4-3, 5-1) into Jingcai's specific "胜其他", "平其他", "负其他" (Win/Draw/Loss Other) buckets.
4. **Last-Leg Parlay Hedger (Jingcai)**: Replace international exchange-style cashout logic with a strict Chinese lottery "Last Leg Hedge" calculator. This tool calculates exactly how much to bet on the opposite outcomes of the final leg to lock in profit for an already 3-of-4 winning parlay ticket.

## Tech Stack
- Python 3.10+
- `scipy.stats`
- `itertools`, `math`

## Implementation Plan
See `docs/superpowers/plans/2026-04-22-analytics-evolution.md`
