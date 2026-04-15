# 2026-04-14 P2 Data Fabric Design (Browser/Search First, API Optional)

## Goal
Build a **non-fragile real-data layer** for the AI-native football lottery system that:

- Does **not** depend on a single overseas data API (rate limits, region blocks, language mapping issues).
- Uses **Chinese sites as primary sources**: 500.com / 澳客 / 懂球帝 / 捷报比分.
- Supports **multi-source fallback** and never “silently returns empty data”.
- Stores **snapshots** so every run is reproducible and can power P2 KPIs (CLV/ROI calibration).

## Non-Goals
- Not attempting any “bypass anti-bot” behavior. When sites require CAPTCHA, the system pauses and asks for **one-time manual verification**, then continues.
- Not building a full UI/dashboard in P2.

## Data Scope (A/B/C/D)
- **A Odds/Markets**: 欧赔/亚盘/大小球、北单 SP、初盘/即时/收盘。
- **B Injuries/Lineups**: 伤停、停赛、预计首发、临场首发确认（尽可能）。
- **C Fixtures/Results/Standings**: 今日在售赛事池、赛果、积分/排名、近期战绩。
- **D News/Sentiment**: 懂球帝等新闻摘要（用于“变量”，不直接决定大额下注）。

## Architecture Overview
### 1) MultiSourceFetcher (Provider Pipeline)
Introduce a provider pipeline per data category:

- `OddsProvider`
- `InjuryProvider`
- `FixturesProvider`
- `NewsProvider`
- `ScoreProvider`

Each provider is implemented as a **chain**:
1. **Browser Scrape (Primary)**: headless browser automation (DOM + text extraction).
2. **Web Search (Secondary)**: search + extraction as a resilience layer.
3. **Optional API (Tertiary)**: only as fallback, always normalized by EntityResolver.
4. **Snapshot Cache (Last Resort)**: return latest known snapshot (marked stale).

All fetch operations MUST return the unified protocol:
```json
{
  "ok": true,
  "data": {},
  "error": null,
  "meta": {
    "source": "500.com",
    "mock": false,
    "timestamp": "2026-04-14T12:34:56+08:00",
    "confidence": 0.0,
    "stale": false
  }
}
```

### 2) EntityResolver (Language/Identity Normalization)
To prevent multilingual breakage:

- Normalize everything into stable identifiers:
  - `team_id`, `league_id`, `match_id`
- Maintain an alias map:
  - Chinese name (primary), English name, short names, historic names
- Output a canonical structure consumed by downstream tools.

This ensures:
- Chinese sites → no mapping needed.
- Optional overseas APIs → only one centralized mapping step; no scattered “中文映射脚本” across tools.

### 3) SnapshotStore (Reproducibility + CLV)
Persist all fetched data as immutable snapshots to support:
- Re-run and audit (why the agent decided X)
- CLV & ROI calibration (placed vs closing)
- Auto-tuning training signals (later)

Storage: SQLite (consistent with existing ledger).

Tables (minimum):
- `matches(match_id, league_id, home_team_id, away_team_id, kickoff_time, source, created_at)`
- `odds_snapshots(id, match_id, captured_at, source, payload_json, confidence, stale)`
- `injury_snapshots(id, match_id, captured_at, source, payload_json, confidence, stale)`
- `news_snapshots(id, match_id, captured_at, source, payload_json, confidence, stale)`
- `score_snapshots(id, match_id, captured_at, source, payload_json, confidence, stale)`

### 4) Integration Points (Minimum Code Surface)
We integrate at the most leveraged chokepoints:

1. **AnalyzerAPI enhancement**: upgrade `get_live_*` to call MultiSourceFetcher (HTTP backend becomes just one provider).
2. **Tool layer**: expose real-data tools for the LLM via tool registry (SSOT), e.g.:
   - `get_live_odds`
   - `get_live_injuries`
   - `get_today_fixtures`
   - `get_match_result`
   - `search_news`

### 5) CAPTCHA Handling
If a site triggers CAPTCHA:
- The system returns `ok=false` with `error.code="CAPTCHA_REQUIRED"` and `meta.source` set.
- The daemon pauses that source and requests manual verification.
- After user verification, resume pipeline; also store `meta.confidence` improvement.

## Provider Plan (Chosen Sites)
### Primary Sources
- 500.com: fixtures pool + odds/SP pages
- 澳客: odds comparison (cross-validate) + Asian handicap detail pages
- 懂球帝: injuries + lineup + news
- 捷报比分: results/scores + match events (where available)

### Optional API Sources (Fallback Only)
- The Odds API
- api-football
- football-data.org
- TheSportsDB
- Odds-API.io

All optional APIs must be isolated behind EntityResolver and MUST NOT be required for system health.

## Acceptance Criteria (P2)
- **No single point of failure**: any one provider fails → system still returns a structured response with fallback source and `confidence`.
- **No silent empty**: no `{}` on failure; all failures are explicit `{ok:false, error:{...}}`.
- **Snapshot reproducibility**: every analysis run stores snapshots for odds/injuries/news/scores (even if stale).
- **CLV ready**: odds snapshots include timestamped “closing odds” candidate; ledger can link bet → closing odds later.

