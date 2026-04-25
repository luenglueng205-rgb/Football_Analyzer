# Ultimate Chinese Lottery Arbitrage Modules Spec

## Goal
Implement the 3 missing "Holy Grail" arbitrage modules specifically designed to exploit Chinese lottery inefficiencies: 1. Latency Arbitrage Monitor, 2. Betfair Volume Anomaly Detector, 3. Low Odds Trap Identifier.

## Architecture
1. **Low Odds Trap Identifier (`trap_identifier.py`)**: A skill that takes Poisson true probabilities and compares them against Jingcai odds. If Jingcai's implied probability (1/odds * 0.89) is vastly higher than the true Poisson probability, it flags the bet as a "Trap" (Mosquito Meat) to prevent parlays from dying to fake favorites.
2. **Latency Arbitrage Monitor (`latency_arbitrage.py`)**: A skill that takes Pinnacle/Bet365 live odds and compares them against Jingcai's fixed odds. If Jingcai's odds for an outcome are actually *higher* than Pinnacle's zero-vig true odds, it triggers an immediate "Latency Arbitrage" alert.
3. **Betfair Volume Anomaly Detector (`betfair_anomaly.py`)**: A mockable skill that analyzes Betfair matched volume distribution versus actual odds probability. If 90% of money is on the Home team but the odds are drifting up, it flags a "Smart Money Lay" anomaly, perfect for fading the public in Beidan/Zucai.

## Tech Stack
- Python 3.10+
- `skills/` directory expansion

## Implementation Plan
See `docs/superpowers/plans/2026-04-22-arbitrage-modules.md`
