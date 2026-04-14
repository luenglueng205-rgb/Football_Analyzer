# 2026-04-14 Hardcore Landing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the football analyzer from a theoretical mock-data system into a hardcore execution engine using MCP Browser for real data, Asian Handicap logic for professional analysis, and a local SQLite ledger for bankroll execution.

**Architecture:** We will build three independent components: a data fetcher using `integrated_browser` MCP (or Playwright), a professional Asian Handicap mathematical model, and an SQLite-backed betting ledger. We will then integrate these into the `ai_native_core.py` prompt and tool registry.

**Tech Stack:** Python 3, SQLite (`sqlite3`), MCP (`integrated_browser`), `asyncio`.

---

### Task 1: Create the Execution Ledger (betting_ledger.py)

**Files:**
- Create: `tools/betting_ledger.py`
- Test: `tests/test_betting_ledger.py`

- [ ] **Step 1: Write the failing test**

```python
import os
import sqlite3
import pytest
from tools.betting_ledger import BettingLedger

def test_ledger_initialization_and_bet():
    db_path = "test_ledger.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    ledger = BettingLedger(db_path=db_path)
    
    # Check initial bankroll
    status = ledger.check_bankroll()
    assert status["current_bankroll"] == 10000.0
    
    # Execute a bet
    result = ledger.execute_bet(
        match_id="20260414_RM_MCI",
        lottery_type="jingcai",
        selection="主胜",
        odds=2.80,
        stake=1000.0
    )
    
    assert result["status"] == "success"
    assert "竞彩|20260414_RM_MCI|主胜@2.80|1000.0元" in result["ticket_code"]
    
    # Check updated bankroll
    status = ledger.check_bankroll()
    assert status["current_bankroll"] == 9000.0
    assert status["total_bets"] == 1
    
    if os.path.exists(db_path):
        os.remove(db_path)
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_betting_ledger.py -v`
Expected: FAIL (ModuleNotFoundError or similar)

- [ ] **Step 3: Write minimal implementation**

```python
import sqlite3
import os
import datetime

class BettingLedger:
    def __init__(self, db_path="data/ledger.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()
        
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS bankroll
                     (id INTEGER PRIMARY KEY, balance REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS bets
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      match_id TEXT, lottery_type TEXT, selection TEXT,
                      odds REAL, stake REAL, ticket_code TEXT,
                      status TEXT, timestamp DATETIME)''')
        
        # Init bankroll if empty
        c.execute("SELECT balance FROM bankroll WHERE id=1")
        if not c.fetchone():
            c.execute("INSERT INTO bankroll (id, balance) VALUES (1, 10000.0)")
        conn.commit()
        conn.close()

    def check_bankroll(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT balance FROM bankroll WHERE id=1")
        balance = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM bets")
        total_bets = c.fetchone()[0]
        conn.close()
        
        return {
            "current_bankroll": balance,
            "total_bets": total_bets,
            "currency": "CNY"
        }

    def execute_bet(self, match_id: str, lottery_type: str, selection: str, odds: float, stake: float) -> dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Check balance
        c.execute("SELECT balance FROM bankroll WHERE id=1")
        balance = c.fetchone()[0]
        if balance < stake:
            conn.close()
            return {"status": "error", "message": "Insufficient funds"}
            
        new_balance = balance - stake
        c.execute("UPDATE bankroll SET balance=? WHERE id=1", (new_balance,))
        
        ticket_code = f"{lottery_type}|{match_id}|{selection}@{odds}|{stake}元"
        now = datetime.datetime.now().isoformat()
        
        c.execute('''INSERT INTO bets 
                     (match_id, lottery_type, selection, odds, stake, ticket_code, status, timestamp)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (match_id, lottery_type, selection, odds, stake, ticket_code, "PENDING", now))
                  
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "ticket_code": ticket_code,
            "remaining_balance": new_balance
        }
```

- [ ] **Step 4: Run test to verify it passes**
Run: `PYTHONPATH=. pytest tests/test_betting_ledger.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
Run: `git add tools/betting_ledger.py tests/test_betting_ledger.py && git commit -m "feat: add SQLite betting ledger"`

---

### Task 2: Create the Asian Handicap Analyzer (asian_handicap_analyzer.py)

**Files:**
- Create: `tools/asian_handicap_analyzer.py`
- Test: `tests/test_asian_handicap.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from tools.asian_handicap_analyzer import AsianHandicapAnalyzer

def test_euro_asian_divergence():
    analyzer = AsianHandicapAnalyzer()
    
    # Euro odds 1.50 typically implies Asian Handicap -1.0
    # If actual AH is -0.75, it's a shallow trap.
    result = analyzer.analyze_divergence(
        euro_home_odds=1.50,
        actual_asian_handicap=-0.75,
        home_water=0.85
    )
    
    assert result["theoretical_handicap"] == -1.0
    assert result["divergence"] == 0.25
    assert result["conclusion"] == "Shallow Trap (诱盘/阻筹)"
    
def test_water_drop():
    analyzer = AsianHandicapAnalyzer()
    result = analyzer.analyze_water_drop(
        opening_water=1.05,
        live_water=0.80
    )
    assert result["drop_amplitude"] == 0.25
    assert result["is_sharp_drop"] == True
```

- [ ] **Step 2: Run test to verify it fails**
Run: `PYTHONPATH=. pytest tests/test_asian_handicap.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
class AsianHandicapAnalyzer:
    def __init__(self):
        # Simplified conversion table: Euro Odds -> Asian Handicap
        self.conversion_table = [
            (1.10, -2.5), (1.15, -2.0), (1.20, -1.75), (1.25, -1.5),
            (1.35, -1.25), (1.50, -1.0), (1.65, -0.75), (1.85, -0.5),
            (2.10, -0.25), (2.35, 0.0)
        ]

    def _get_theoretical_handicap(self, euro_odds: float) -> float:
        # Find closest match
        closest = min(self.conversion_table, key=lambda x: abs(x[0] - euro_odds))
        return closest[1]

    def analyze_divergence(self, euro_home_odds: float, actual_asian_handicap: float, home_water: float) -> dict:
        theoretical = self._get_theoretical_handicap(euro_home_odds)
        divergence = theoretical - actual_asian_handicap
        
        conclusion = "Normal (盘口合理)"
        if divergence > 0.1: # e.g., Theo is -1.0, Actual is -0.75. Divergence = -1.0 - (-0.75) = -0.25 (Wait, logic fix)
            pass
            
        # Correct logic:
        # Theo = -1.0. Actual = -0.75. divergence = actual - theo = -0.75 - (-1.0) = 0.25
        divergence = actual_asian_handicap - theoretical
        
        if divergence > 0.1:
            conclusion = "Shallow Trap (诱盘/阻筹)"
        elif divergence < -0.1:
            conclusion = "Deep Support (机构真实看好)"
            
        return {
            "theoretical_handicap": theoretical,
            "actual_handicap": actual_asian_handicap,
            "divergence": divergence,
            "conclusion": conclusion
        }

    def analyze_water_drop(self, opening_water: float, live_water: float) -> dict:
        drop = opening_water - live_water
        return {
            "opening_water": opening_water,
            "live_water": live_water,
            "drop_amplitude": round(drop, 2),
            "is_sharp_drop": drop >= 0.15
        }
```

- [ ] **Step 4: Run test to verify it passes**
Run: `PYTHONPATH=. pytest tests/test_asian_handicap.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
Run: `git add tools/asian_handicap_analyzer.py tests/test_asian_handicap.py && git commit -m "feat: add Asian Handicap and Euro-Asian divergence logic"`

---

### Task 3: Integrate Tools into Tool Registry and Core

**Files:**
- Modify: `tools/mcp_tools.py`
- Modify: `agents/ai_native_core.py`

- [ ] **Step 1: Expose Ledger and Asian Handicap Tools in mcp_tools.py**

Modify `tools/mcp_tools.py` to add `execute_bet`, `check_bankroll`, `analyze_asian_handicap_divergence`, and `analyze_water_drop` functions and append them to `AVAILABLE_TOOLS` and `TOOL_MAPPING`.

```python
# Add to tools/mcp_tools.py
from tools.betting_ledger import BettingLedger
from tools.asian_handicap_analyzer import AsianHandicapAnalyzer

_ledger = BettingLedger()
_ah_analyzer = AsianHandicapAnalyzer()

def execute_bet(match_id: str, lottery_type: str, selection: str, odds: float, stake: float) -> dict:
    return _ledger.execute_bet(match_id, lottery_type, selection, odds, stake)

def check_bankroll() -> dict:
    return _ledger.check_bankroll()

def analyze_asian_handicap_divergence(euro_home_odds: float, actual_asian_handicap: float, home_water: float) -> dict:
    return _ah_analyzer.analyze_divergence(euro_home_odds, actual_asian_handicap, home_water)

def analyze_water_drop(opening_water: float, live_water: float) -> dict:
    return _ah_analyzer.analyze_water_drop(opening_water, live_water)

# Add corresponding JSON schemas to AVAILABLE_TOOLS and map functions in TOOL_MAPPING.
```

- [ ] **Step 2: Update ai_native_core.py System Prompt**

Modify `agents/ai_native_core.py` (around line 80):
```python
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"请为我深度量化分析这场比赛：主队 '{home}' 对阵 客队 '{away}'。当前彩种为：'{lottery_desc}'。\n"
                                         f"【最高指令】：你是一个统治华尔街的数字博彩基金大脑。你需要自主调用所有可用工具：\n"
                                         f"1. 必须调用 check_bankroll 查看当前真实可用资金。\n"
                                         f"2. 必须分析亚盘水位异动和欧亚转换偏差（不要只用泊松）。\n"
                                         f"3. 决定投资后，必须调用 execute_bet 真正生成实单并写入账本！\n"
                                         f"4. 拒绝纸上谈兵，用真实数据和真实仓位说话。"}
        ]
```

- [ ] **Step 3: Remove Deprecated Dummy Tools**
Remove `get_live_odds` and `get_live_injuries` schemas from `AVAILABLE_TOOLS` in `tools/mcp_tools.py` since we will rely on MCP Browser or Dark Intel.

- [ ] **Step 4: Commit**
Run: `git add tools/mcp_tools.py agents/ai_native_core.py && git commit -m "feat: integrate ledger and AH analyzer into core agent"`
