# 2026-04-14 The Ultimate Evolution: 7x24 Sentinel & Ticket Generator

## Overview
The system is currently limited by its passive, single-match nature and text-only outputs. To reach the "Ultimate AI-Native Form" (极致), we must transform it into a 7x24 background Daemon that actively monitors the market, applies complex filtering matrices for parlay (串关) and 14-match (传足) games, and generates physical, scannable QR code tickets delivered directly to the user's phone via Webhook.

## 1. 7x24 Sentinel Daemon (`market_sentinel.py`)
- **Role**: A continuous background process.
- **Mechanism**:
  - Runs a loop every 5 minutes (configurable).
  - Fetches a list of today's matches.
  - Monitors for two primary triggers:
    1. **Sharp Drop (聪明资金跳水)**: If a team's odds drop by >15% within a short window.
    2. **Arbitrage (打水套利)**: If Beidan SP values (after 65% return rate conversion) present a risk-free arbitrage opportunity against Jingcai odds.
  - When a trigger fires, it wakes up the `AINativeCoreAgent` to perform a deep analysis on the flagged matches.

## 2. Master Filter Matrix (`tools/parlay_filter_matrix.py`)
- **Role**: Mathematical engine for multi-match combinations and fault-tolerance.
- **Mechanism**:
  - Instead of betting single matches, the system combines 2-3 high EV matches into a parlay (e.g., 2串1, 3串1, or 3串4 with 1-match fault tolerance).
  - Calculates the optimal stake distribution across the combinations to ensure capital protection (保本) if one leg fails.
  - Supports 14-match (传足) and RenJiu (任九) 310 filtering logic (e.g., filtering out combinations with too many away wins or extreme longshots).

## 3. Physical Ticket Generator (`tools/qrcode_ticket_generator.py`)
- **Role**: The bridge between the digital AI and the physical lottery shop.
- **Mechanism**:
  - Takes the final parlay or single bet string (e.g., `竞彩|001主胜+002大球|50倍`).
  - Uses the `qrcode` library to generate a standard QR code image (`.png`).
  - Saves the image to a local `tickets/` directory.

## 4. Mobile Dispatcher (`tools/notification_dispatcher.py`)
- **Role**: Delivers the analysis and the ticket to the user.
- **Mechanism**:
  - Reads `WEBHOOK_URL` from `.env` (e.g., Server酱, PushPlus, Feishu).
  - Sends a Markdown-formatted summary of the AI's debate/decision and the URL/Base64 of the generated QR code ticket.
  - Incorporates the user's `RISK_PROFILE` (conservative/aggressive) to dynamically adjust the Kelly fraction before generating the ticket.

## Architecture Updates
- Update `tools/mcp_tools.py` to expose the new matrix, ticket, and dispatcher tools to the AI Brain.
- Modify `agents/ai_native_core.py` prompt to encourage parlay combinations and require generating a QR code ticket.
- Ensure `market_sentinel.py` can be launched independently as a long-running daemon.

## Dependencies
- `qrcode[pil]` for generating images.
- `requests` or `httpx` for Webhook dispatch.

## Testing Strategy
- Mock a sharp odds drop to trigger the Sentinel.
- Verify the AI Brain correctly calls the Parlay Filter Matrix.
- Ensure a valid QR code image is generated in the `tickets/` folder.
- Test the Webhook dispatcher with a dummy URL.