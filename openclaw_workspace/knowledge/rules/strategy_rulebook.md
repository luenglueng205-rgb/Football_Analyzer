# Strategy Rulebook (System Official Standard)

This document serves as the absolute source of truth for the system's internal betting strategies. The Self-Proving QA Engine will validate system outputs against these rules.

## 1. Selection Strategy (选场策略)
- **Jingcai (Fixed Odds):** A bet is selected ONLY IF `Expected Value (EV) >= 1.05`. EV is calculated as `Odds * Win Probability`.
- **Beidan (Dynamic Pool):** A bet is selected ONLY IF `EV >= 1.05`. EV MUST be calculated with the official 35% pool deduction: `(Odds * Win Probability) * 0.65`.
- **Zucai (No Odds Pool):** A bet is selected ONLY IF `Probability Edge >= 0.15`. Edge is calculated as `True Win Probability - Public Support Rate`.

## 2. Parlay Strategy (串关策略)
- **Jingcai:** Maximum legs allowed is 8. Decimal handicaps (e.g., 0.5) are strictly prohibited.
- **Beidan:** Maximum legs allowed is 15. SFGG (胜负过关) MUST use a 0.5 decimal handicap to eliminate draws.
- **Zucai:** Must be exactly 14 matches for 14-Match, and exactly 9 matches for Renjiu. Odds parameters MUST be ignored.
- **Payout Limits:** 2-3 legs <= 200,000 RMB; 4-5 legs <= 500,000 RMB; 6+ legs <= 1,000,000 RMB.

## 3. Live-check Strategy (临场/走地对冲策略)
- **Hedge Trigger:** A hedge is triggered ONLY IF the sum of implied probabilities (`sum(1/odds)`) of all remaining complementary markets is `< 1.0`, ensuring a guaranteed risk-free arbitrage.
- **Capital Distribution:** Hedge capital MUST be distributed proportionally to `Target Payout / Live Odds` to perfectly flatten the risk curve across all remaining outcomes.

## 4. Anomaly & Wind Control (风控策略)
- **CPU Protection:** Any combination request resulting in `> 50` total selections MUST be rejected to prevent combinatorics explosion.
- **Match Cancellation:** Any match marked as CANCELLED, POSTPONED, or W/O MUST be settled with odds of `1.0`.