# Chinese Lottery Risk & Tax Evolution Spec

## Goal
Fix 3 critical mathematical/regulatory flaws in the current lottery analytics engine to accurately reflect the real-world operational constraints and taxation models of Chinese sports lotteries (Jingcai, Beidan, Zucai).

## Architecture
1. **Jingcai Smart Splitter & Ceiling Interceptor**: Create an optimizer in `advanced_lottery_math.py` that intercepts high-payout parlays. It will enforce the statutory payout ceilings (2-3 legs: 200k, 4-5 legs: 500k, 6+ legs: 1000k) and automatically suggest splitting tickets (倍投拆单) to avoid the 20% tax on single-bet payouts over 10,000 RMB.
2. **Beidan Exponential Vig Fix**: Modify `calculate_parlay_kelly` to accept a `lottery_type` parameter. For `BEIDAN`, ensure the 65% return rate is applied exactly once to the final combined odds, not to each individual leg's odds.
3. **Zucai Anti-Hotpot Detector**: Create an information entropy-based tool that calculates the "Value Index" of a Zucai pick by comparing the Poisson-derived true probability against the public betting consensus distribution. This guides the AI to find high-EV blind spots rather than just picking chalk favorites.

## Tech Stack
- Python 3.10+
- Existing `advanced_lottery_math.py` module

## Implementation Plan
See `docs/superpowers/plans/2026-04-22-risk-tax-evolution.md`
