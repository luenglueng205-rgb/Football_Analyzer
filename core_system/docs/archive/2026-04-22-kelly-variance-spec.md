# Match Fixing & Consensus Detection Spec (Kelly Variance)

## Goal
Implement the final "Bookmaker's Mindset" puzzle piece: a Kelly Index Variance Analyzer to detect match-fixing, deep consensus, or orchestrated traps across dozens of global bookmakers. 

## Architecture
1. **Kelly Variance Analyzer (`kelly_variance_analyzer.py`)**: A skill module that takes an array of odds from various bookmakers (e.g., Bet365, William Hill, Pinnacle, Macauslot) for a specific outcome.
2. **Variance Calculation**: It calculates the implied probability and Kelly Index for each bookmaker. Then it computes the statistical variance/standard deviation of these indices.
3. **Anomaly Detection**: 
   - **Low Variance + Dropping Odds**: Global consensus (Strong trend, safe to follow).
   - **High Variance**: Bookmakers are divided (High risk, observe).
   - **Extremely Low Variance + Asian Handicap Divergence**: The classic "Match Fixing" or "Deep Trap" signature. If all European books agree on a probability, but Asian books are stubbornly holding a different line with massive water drops, it signals manipulated money.

## Tech Stack
- Python 3.10+
- `statistics` or `numpy` (if available, otherwise standard library `math`)

## Implementation Plan
See `docs/superpowers/plans/2026-04-22-kelly-variance.md`
