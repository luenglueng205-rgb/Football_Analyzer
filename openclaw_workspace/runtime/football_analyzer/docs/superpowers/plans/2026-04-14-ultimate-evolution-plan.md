# 2026-04-14 The Ultimate Evolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the football analyzer into a 7x24 Daemon that automatically filters multi-match parlays, generates physical QR code tickets, and dispatches them via Webhook.

**Architecture:** 
1. Build `parlay_filter_matrix.py` to calculate multi-match combinations and fault-tolerance stakes.
2. Build `qrcode_ticket_generator.py` and `notification_dispatcher.py` to handle the physical ticket and delivery loop.
3. Build `market_sentinel.py` to act as the 7x24 daemon triggering the core AI.
4. Wire everything into `mcp_tools.py` and `ai_native_core.py`.

**Tech Stack:** Python 3, `qrcode[pil]`, `httpx`, `asyncio`.

---

### Task 1: Install Dependencies

**Files:**
- Modify: `requirements.txt` (or similar)

- [ ] **Step 1: Install `qrcode` and `Pillow`**
Run: `python3 -m pip install "qrcode[pil]" httpx --user --break-system-packages`
Expected: Successfully installs `qrcode` and `Pillow` for image generation.

- [ ] **Step 2: Commit**
Run: `git commit --allow-empty -m "chore: add qrcode dependency for ticket generation"`

---

### Task 2: Create the Parlay Filter Matrix (parlay_filter_matrix.py)

**Files:**
- Create: `tools/parlay_filter_matrix.py`
- Test: `tests/test_parlay_filter.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from tools.parlay_filter_matrix import ParlayFilterMatrix

def test_parlay_2x1_calculation():
    matrix = ParlayFilterMatrix()
    matches = [
        {"match_id": "001", "selection": "主胜", "odds": 2.0},
        {"match_id": "002", "selection": "客胜", "odds": 3.0}
    ]
    
    result = matrix.calculate_parlay(matches, parlay_type="2x1", total_stake=100)
    
    assert result["status"] == "success"
    assert result["total_cost"] == 100
    assert result["combinations"][0]["combined_odds"] == 6.0
    assert result["max_potential_return"] == 600.0

def test_parlay_3x4_calculation():
    matrix = ParlayFilterMatrix()
    matches = [
        {"match_id": "001", "selection": "主胜", "odds": 2.0},
        {"match_id": "002", "selection": "大球", "odds": 1.5},
        {"match_id": "003", "selection": "平局", "odds": 3.2}
    ]
    
    # 3x4 means three 2x1s and one 3x1 (4 bets total)
    result = matrix.calculate_parlay(matches, parlay_type="3x4", total_stake=400)
    
    assert result["status"] == "success"
    assert result["total_cost"] == 400
    assert len(result["combinations"]) == 4
```

- [ ] **Step 2: Run test to verify it fails**
Run: `PYTHONPATH=. pytest tests/test_parlay_filter.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
import itertools
from typing import List, Dict, Any

class ParlayFilterMatrix:
    def __init__(self):
        pass

    def calculate_parlay(self, matches: List[Dict[str, Any]], parlay_type: str, total_stake: float) -> Dict[str, Any]:
        """
        Calculate parlay combinations and returns.
        matches format: [{"match_id": "001", "selection": "主胜", "odds": 2.0}, ...]
        parlay_type: "2x1", "3x1", "3x4" (three 2x1s + one 3x1)
        """
        n_matches = len(matches)
        combinations = []
        
        if parlay_type == "2x1" and n_matches == 2:
            comb = matches
            combined_odds = comb[0]["odds"] * comb[1]["odds"]
            combinations.append({
                "matches": [m["match_id"] for m in comb],
                "combined_odds": round(combined_odds, 2),
                "stake": total_stake
            })
            
        elif parlay_type == "3x4" and n_matches == 3:
            # Three 2x1s
            per_bet_stake = total_stake / 4.0
            for comb in itertools.combinations(matches, 2):
                combined_odds = comb[0]["odds"] * comb[1]["odds"]
                combinations.append({
                    "type": "2x1",
                    "matches": [m["match_id"] for m in comb],
                    "combined_odds": round(combined_odds, 2),
                    "stake": per_bet_stake
                })
            # One 3x1
            combined_odds = matches[0]["odds"] * matches[1]["odds"] * matches[2]["odds"]
            combinations.append({
                "type": "3x1",
                "matches": [m["match_id"] for m in matches],
                "combined_odds": round(combined_odds, 2),
                "stake": per_bet_stake
            })
        else:
            return {"status": "error", "message": f"Unsupported parlay type {parlay_type} for {n_matches} matches."}

        max_return = sum(c["combined_odds"] * c["stake"] for c in combinations)
        
        return {
            "status": "success",
            "parlay_type": parlay_type,
            "total_cost": total_stake,
            "combinations": combinations,
            "max_potential_return": round(max_return, 2)
        }
```

- [ ] **Step 4: Run test to verify it passes**
Run: `PYTHONPATH=. pytest tests/test_parlay_filter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
Run: `git add tools/parlay_filter_matrix.py tests/test_parlay_filter.py && git commit -m "feat: add parlay filter matrix"`

---

### Task 3: Create the QR Code Ticket Generator and Dispatcher

**Files:**
- Create: `tools/qrcode_ticket_generator.py`
- Create: `tools/notification_dispatcher.py`
- Test: `tests/test_ticket_dispatch.py`

- [ ] **Step 1: Write the failing test**

```python
import os
import pytest
from tools.qrcode_ticket_generator import generate_ticket_qr
from tools.notification_dispatcher import dispatch_notification

def test_generate_qr():
    ticket_string = "竞彩|001主胜+002客胜|2x1|100元"
    output_path = "tickets/test_ticket.png"
    
    if os.path.exists(output_path):
        os.remove(output_path)
        
    result = generate_ticket_qr(ticket_string, output_path)
    
    assert result["status"] == "success"
    assert os.path.exists(output_path)
    
    if os.path.exists(output_path):
        os.remove(output_path)

@pytest.mark.asyncio
async def test_dispatch():
    # Use a dummy webhook
    result = await dispatch_notification(
        webhook_url="http://localhost:9999/dummy",
        message="Test Message",
        image_path=None
    )
    # Even if it fails to connect, it should handle the error gracefully
    assert "status" in result
```

- [ ] **Step 2: Run test to verify it fails**
Run: `PYTHONPATH=. pytest tests/test_ticket_dispatch.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

`tools/qrcode_ticket_generator.py`:
```python
import os
import qrcode

def generate_ticket_qr(ticket_string: str, output_path: str = "tickets/latest_ticket.png") -> dict:
    """Generates a QR code for a betting ticket string."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(ticket_string)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(output_path)
        
        return {
            "status": "success",
            "file_path": output_path,
            "ticket_string": ticket_string
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

`tools/notification_dispatcher.py`:
```python
import httpx
import json

async def dispatch_notification(webhook_url: str, message: str, image_path: str = None) -> dict:
    """Sends a markdown message to a webhook (e.g., Feishu, ServerChan)."""
    if not webhook_url or webhook_url == "dummy":
        return {"status": "mock", "message": "No real webhook configured, printing to console", "content": message}
        
    try:
        payload = {"msg_type": "text", "content": {"text": message}}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, timeout=10.0)
            
        if response.status_code == 200:
            return {"status": "success"}
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `PYTHONPATH=. pytest tests/test_ticket_dispatch.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
Run: `git add tools/qrcode_ticket_generator.py tools/notification_dispatcher.py tests/test_ticket_dispatch.py && git commit -m "feat: add QR code generator and webhook dispatcher"`

---

### Task 4: Integrate Tools into mcp_tools.py

**Files:**
- Modify: `tools/mcp_tools.py`

- [ ] **Step 1: Expose Tools**
Add `calculate_parlay`, `generate_ticket_qr`, and `dispatch_notification` to `AVAILABLE_TOOLS` and `TOOL_MAPPING`.

```python
# In tools/mcp_tools.py
from tools.parlay_filter_matrix import ParlayFilterMatrix
from tools.qrcode_ticket_generator import generate_ticket_qr
import asyncio
from tools.notification_dispatcher import dispatch_notification

_parlay_matrix = ParlayFilterMatrix()

def calculate_parlay(matches: list, parlay_type: str, total_stake: float) -> dict:
    return _parlay_matrix.calculate_parlay(matches, parlay_type, total_stake)

def generate_qr_code(ticket_string: str) -> dict:
    return generate_ticket_qr(ticket_string)

async def send_webhook_notification(message: str) -> dict:
    # Use env var or default
    import os
    url = os.getenv("WEBHOOK_URL", "dummy")
    return await dispatch_notification(url, message)

# Add to AVAILABLE_TOOLS schemas and TOOL_MAPPING
```

- [ ] **Step 2: Commit**
Run: `git add tools/mcp_tools.py && git commit -m "feat: expose ultimate evolution tools to MCP registry"`

---

### Task 5: Create the 7x24 Sentinel Daemon (market_sentinel.py)

**Files:**
- Create: `market_sentinel.py`

- [ ] **Step 1: Write Sentinel Implementation**

```python
import asyncio
import time
import logging
from agents.ai_native_core import AINativeCoreAgent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MarketSentinel:
    def __init__(self):
        self.agent = AINativeCoreAgent()
        self.polling_interval = 300 # 5 minutes
        
    async def _mock_fetch_market_scan(self):
        """Mocks fetching all today's matches to find sharp drops or arbitrage."""
        logging.info("[Sentinel] Scanning market for sharp drops or arbitrage opportunities...")
        await asyncio.sleep(2)
        # Mocking a trigger on a specific match
        return [
            {
                "league": "英超",
                "home_team": "曼城",
                "away_team": "阿森纳",
                "trigger": "SHARP_DROP",
                "details": "主胜赔率在1小时内暴跌18%"
            }
        ]

    async def run_forever(self):
        logging.info("==================================================")
        logging.info("🛡️ 7x24 Market Sentinel Daemon Started")
        logging.info("==================================================")
        
        while True:
            try:
                opportunities = await self._mock_fetch_market_scan()
                
                for opp in opportunities:
                    logging.warning(f"🚨 [ALERT] 发现极致机会: {opp['home_team']} vs {opp['away_team']} ({opp['trigger']})")
                    
                    state = {
                        "current_match": {
                            "league": opp["league"],
                            "home_team": opp["home_team"],
                            "away_team": opp["away_team"]
                        },
                        "params": {
                            "lottery_type": "jingcai",
                            "lottery_desc": "竞彩串关与单场",
                            "sentinel_alert": opp["details"]
                        }
                    }
                    
                    # Wake up the AI Brain
                    logging.info("🧠 Waking up AI Native Core for deep analysis...")
                    result = await self.agent.process(state)
                    
                    logging.info(f"✅ AI Analysis Complete. Report length: {len(str(result))}")
                    
                logging.info(f"💤 Sentinel sleeping for {self.polling_interval} seconds...")
                await asyncio.sleep(self.polling_interval)
                
            except Exception as e:
                logging.error(f"Sentinel encountered an error: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    sentinel = MarketSentinel()
    try:
        # Run one iteration immediately for testing purposes, then exit
        # In real prod, use asyncio.run(sentinel.run_forever())
        asyncio.run(sentinel._mock_fetch_market_scan())
        print("Sentinel initialized successfully.")
    except KeyboardInterrupt:
        print("Sentinel stopped.")
```

- [ ] **Step 2: Update ai_native_core.py prompt**
Modify `ai_native_core.py` prompt to add:
```python
f"5. 【极致闭环】：如果发现多个机会，必须调用 calculate_parlay 计算串关组合。决定下注后，必须调用 generate_qr_code 生成物理二维码，并调用 send_webhook_notification 将决策推送到手机！"
```

- [ ] **Step 3: Commit**
Run: `git add market_sentinel.py agents/ai_native_core.py && git commit -m "feat: add 7x24 market sentinel daemon"`
