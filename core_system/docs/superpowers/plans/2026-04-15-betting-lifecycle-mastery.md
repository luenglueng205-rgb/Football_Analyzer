# Betting Lifecycle Mastery Plan: Proactive Problem Discovery & Fail-Safes

## Background
The user explicitly pointed out a fatal flaw in the system: it acts reactively rather than proactively. While the mathematical modeling (xG, Poisson, EV) is solid, the operational betting lifecycle (Pre-Match, In-Play, Post-Match) lacks the obsessive detail required for a true "Digital Life". The system waits to be told about real-world edge cases rather than proactively discovering and handling them.

## Identified Missing Lifecycle Features
Through a deep audit of the system's lifecycle handling, four critical operational gaps were found that violate official lottery rules and professional betting practices:
1. **Pre-Match (T-30 mins):** No mechanism to verify confirmed starting lineups. A late injury to a star player invalidates the entire EV calculation.
2. **In-Play (Live Hedging):** No mechanism to monitor live matches and calculate if a cash-out or hedge bet is mathematically optimal to secure a profit or minimize a loss.
3. **Post-Match (Cancellations/Postponements):** No handling for matches that are cancelled or interrupted. Official rules dictate these must be settled at odds of `1.0`.
4. **Post-Match (Extra Time Rules):** No strict enforcement separating 90-minute scores from 120-minute/penalty scores. Official Jingcai/Beidan rules settle strictly on 90-minute results (including injury time).

## Implementation Steps

### Phase 1: Pre-Match Proactivity (T-30 Lineup Sentinel)
- **Goal:** Catch late injuries/suspensions and cancel negative EV bets before kick-off.
- **Action:** Create `standalone_workspace/tools/pre_match_sentinel.py`.
- **Details:** 
  - Expose a `check_lineups_t30(match_id)` tool.
  - If a key player (from the original Quant analysis) is missing, trigger an emergency EV recalculation.

### Phase 2: In-Play Proactivity (Live Hedging Monitor)
- **Goal:** Proactively secure profits or cut losses based on live game states.
- **Action:** Create `standalone_workspace/tools/live_match_monitor.py`.
- **Details:** 
  - Implement `evaluate_hedge_opportunity(match_id, current_score, live_odds)`.
  - Calculate Hedge EV. If `Guaranteed Profit > Threshold`, trigger a hedge alert.

### Phase 3: Post-Match Proactivity (Strict Settlement Engine)
- **Goal:** Perfectly mirror official China Sports Lottery settlement rules.
- **Action:** Create `standalone_workspace/tools/settlement_engine.py`.
- **Details:** 
  - Implement `settle_match(match_id, match_status, ft_score, aet_score)`.
  - Handle `Cancelled/Postponed` -> returns `odds = 1.0`.
  - Enforce `FT Score` (90 mins) over `AET Score` (120 mins) for standard W/D/L markets.

### Phase 4: Lifecycle Orchestration (Market Sentinel Upgrade)
- **Goal:** The system must run these checks autonomously.
- **Action:** Update `standalone_workspace/market_sentinel.py`.
- **Details:** 
  - Add asynchronous background tasks for `pre_match_loop`, `in_play_loop`, and `settlement_loop`.
  - Shift from a "one-and-done" pre-match generator to a continuous lifecycle manager.

## Evaluation
- The system will no longer just generate a ticket and forget it. It will actively monitor the ticket's lifecycle until the funds are settled in the ledger, acting as a proactive, autonomous entity.
