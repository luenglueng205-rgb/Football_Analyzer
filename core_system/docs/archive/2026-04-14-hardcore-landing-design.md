# 2026-04-14 Hardcore Landing Design: Real Execution Engine

## Overview
The system currently suffers from "hollowness" (虚) because it relies on mock APIs for data (like `get_live_odds`), uses overly academic models (Poisson), and outputs text rather than executable betting slips. This design lands the system into reality by introducing MCP Browser automation for real-time data scraping, Asian Handicap logic for professional analysis, and a local SQLite ledger for execution tracking.

## 1. Data Landing Layer (The Eyes & Hands)
- **Technology**: `integrated_browser` MCP Server.
- **Workflow**: 
  - Delete dummy API tools (`get_live_odds`, `get_live_injuries`, `get_team_stats`).
  - Introduce `scrape_live_odds_with_browser(match_url)` tool.
  - The AI will navigate to real portals (e.g., 500.com, Okooo) via `browser_navigate` and `browser_get_attribute` or inject JS to extract real-time European 1x2 odds, Asian Handicap lines, and Over/Under lines.
  - *Fallback/Alternative*: If navigating a specific site is too slow, we provide a Python-based headless scraper wrapper using Playwright (or similar) wrapped as an MCP tool to fetch the JSON/DOM of the match directly. Since `integrated_browser` is already configured, we will use it directly.

## 2. Professional Logic Layer (The Quant Brain)
- **New Tool**: `tools/asian_handicap_analyzer.py`
- **Core Logic**:
  - **Water Drop Analysis**: Calculates the change in implied probability and payout ratios (返还率) from opening (初盘) to live (即时盘). Detects whether a drop in odds is a genuine risk mitigation by the bookmaker or a "high-water trap" (高水阻筹).
  - **Euro-Asian Divergence (欧亚转换偏差)**: Takes the standard European odds (e.g., 1.50) and converts them to a theoretical Asian Handicap (e.g., -1.0). If the actual Asian Handicap is -0.75, the system flags it as a "shallow trap" (盘口偏浅), indicating lack of confidence in the favorite.

## 3. Execution Landing Layer (The Ledger)
- **New Tool**: `tools/betting_ledger.py`
- **Database**: `data/ledger.db` (SQLite).
- **Core Functions**:
  - `execute_bet(match_id, lottery_type, selection, odds, stake)`: Logs the bet into the SQLite database and deducts from the virtual bankroll. Generates a standard Chinese Sports Lottery ticket string (e.g., `竞彩|001|主胜@2.80|100元`).
  - `check_bankroll()`: Returns the current available capital, historical ROI, and recent bet history. This forces the AI to manage risk based on *real* past performance, not just a static $100 budget.

## Architecture Updates
- Update `tools/mcp_tools.py` to expose the new tools.
- Update `agents/ai_native_core.py` prompt to mandate using the ledger and browser scraping.
- Remove deprecated mock tools.

## Error Handling & Edge Cases
- **Browser Lock/Unlock**: Ensure the `integrated_browser` is properly locked before use and unlocked after.
- **Scraping Failures**: If DOM structure changes, the AI should retry with visual methods or fall back to conservative bankroll management.
- **Ledger Concurrency**: SQLite must use WAL mode or proper locking if multiple agents access it simultaneously.

## Testing Strategy
- Run a live match analysis using a real URL from 500.com.
- Verify that `ledger.db` correctly records the bet and updates the bankroll.
- Assert that Euro-Asian Divergence calculations mathematically match standard bookmaker conversion tables.
