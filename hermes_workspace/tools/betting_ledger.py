import os
import sqlite3
import datetime
from typing import Optional

from hermes_workspace.tools.paths import data_dir

class InsufficientFundsError(Exception):
    pass

class BettingLedger:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(data_dir(), "ledger.db")
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()
        
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            # 开启 WAL 模式支持高并发
            c.execute("PRAGMA journal_mode=WAL;")
            
            # 支持多 Agent 隔离的资金池
            c.execute('''CREATE TABLE IF NOT EXISTS bankroll
                         (agent_id TEXT PRIMARY KEY, balance REAL)''')
                         
            c.execute('''CREATE TABLE IF NOT EXISTS bets
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          agent_id TEXT,
                          match_id TEXT, lottery_type TEXT, selection TEXT,
                          odds REAL, stake REAL, ticket_code TEXT,
                          status TEXT, timestamp DATETIME,
                          closing_odds REAL, result TEXT, pnl REAL)''')
            
            # 资金流水表，用于复盘和对账
            c.execute('''CREATE TABLE IF NOT EXISTS transactions
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          agent_id TEXT, amount REAL, type TEXT, ref_id INTEGER, timestamp DATETIME)''')
            
            # Add new columns if they don't exist (for existing databases)
            try:
                c.execute("ALTER TABLE bets ADD COLUMN agent_id TEXT")
            except sqlite3.OperationalError:
                pass
                
            conn.commit()

    def reset_economy(self, agent_id: str = "default_agent", initial_balance: float = 10000.0):
        """为 Agent 重置或初始化经济环境"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO bankroll (agent_id, balance) VALUES (?, ?)", (agent_id, initial_balance))
            now = datetime.datetime.now().isoformat()
            c.execute("INSERT INTO transactions (agent_id, amount, type, timestamp) VALUES (?, ?, 'DEPOSIT', ?)", 
                      (agent_id, initial_balance, now))
            conn.commit()

    def check_bankroll(self, agent_id: str = "default_agent") -> dict:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT balance FROM bankroll WHERE agent_id=?", (agent_id,))
            row = c.fetchone()
            balance = row[0] if row else 0.0
            
            if not row:
                # 自动初始化默认资金
                self.reset_economy(agent_id)
                balance = 10000.0
                
            c.execute("SELECT COUNT(*) FROM bets WHERE agent_id=?", (agent_id,))
            total_bets = c.fetchone()[0]
            
        return {
            "current_bankroll": balance,
            "total_bets": total_bets,
            "currency": "USDC"
        }

    def get_recent_resolved_bets(self, agent_id: str, limit: int = 10, only_losses: bool = False) -> list:
        """为 RLEF 提取最近已结算的订单"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            query = "SELECT * FROM bets WHERE agent_id=? AND status='RESOLVED'"
            if only_losses:
                query += " AND pnl < 0"
            query += " ORDER BY timestamp DESC LIMIT ?"
            
            c.execute(query, (agent_id, limit))
            rows = c.fetchall()
            return [dict(r) for r in rows]

    def get_agent_metrics(self, agent_id: str) -> dict:
        """获取指定 Agent 的真实历史盈亏指标"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*), SUM(stake), SUM(pnl) FROM bets WHERE agent_id=? AND status='RESOLVED'", (agent_id,))
            row = c.fetchone()
            total_resolved = row[0] or 0
            total_stake = row[1] or 0.0
            total_pnl = row[2] or 0.0
            
            c.execute("SELECT COUNT(*) FROM bets WHERE agent_id=? AND status='RESOLVED' AND pnl > 0", (agent_id,))
            row_wins = c.fetchone()
            wins = row_wins[0] if row_wins else 0
            
            win_rate = (wins / total_resolved) if total_resolved > 0 else 0.0
            roi = (total_pnl / total_stake) if total_stake > 0 else 0.0
            
            return {
                "total_resolved": total_resolved,
                "win_rate": round(win_rate, 4),
                "roi": round(roi, 4),
                "total_pnl": round(total_pnl, 2)
            }

    def execute_bet(self, agent_id: str, match_id: str, lottery_type: str, selection: str, odds: float, stake: float) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("BEGIN TRANSACTION")
            try:
                c.execute("SELECT balance FROM bankroll WHERE agent_id=?", (agent_id,))
                row = c.fetchone()
                if not row:
                    self.reset_economy(agent_id)
                    balance = 10000.0
                else:
                    balance = row[0]
                    
                # 风控: 检查余额是否充足
                if balance < stake:
                    raise InsufficientFundsError(f"余额不足: 当前 ${balance:.2f}, 需要 ${stake:.2f}")
                
                # 扣款
                new_balance = balance - stake
                c.execute("UPDATE bankroll SET balance=? WHERE agent_id=?", (new_balance, agent_id))
                
                ticket_code = f"{lottery_type}|{match_id}|{selection}@{odds}|{stake}U"
                now = datetime.datetime.now().isoformat()
                
                # 记录订单
                c.execute('''INSERT INTO bets 
                             (agent_id, match_id, lottery_type, selection, odds, stake, ticket_code, status, timestamp)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (agent_id, match_id, lottery_type, selection, odds, stake, ticket_code, "PENDING", now))
                bet_id = c.lastrowid
                
                # 记录流水
                c.execute('''INSERT INTO transactions (agent_id, amount, type, ref_id, timestamp)
                             VALUES (?, ?, 'BET_PLACED', ?, ?)''', (agent_id, -stake, bet_id, now))
                
                conn.commit()
                return {
                    "status": "success",
                    "bet_id": bet_id,
                    "ticket_code": ticket_code,
                    "remaining_balance": new_balance
                }
            except Exception as e:
                conn.rollback()
                if isinstance(e, InsufficientFundsError):
                    return {"status": "error", "message": str(e)}
                raise e

    def record_result(self, bet_id: int, result: str, pnl: float) -> dict:
        """结算订单，并将盈利加回资金池 (真正的经济闭环)"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("BEGIN TRANSACTION")
            try:
                # 获取订单信息
                c.execute("SELECT agent_id, stake, status FROM bets WHERE id=?", (bet_id,))
                row = c.fetchone()
                if not row:
                    return {"status": "error", "message": "Bet not found"}
                    
                agent_id, stake, status = row
                if status == "RESOLVED":
                    return {"status": "error", "message": "Bet already resolved"}
                
                # 更新订单状态
                c.execute("UPDATE bets SET result=?, pnl=?, status='RESOLVED' WHERE id=?", (result, pnl, bet_id))
                
                # 【关键修复】如果本金+盈亏 > 0，说明有钱进账，加回余额
                total_return = stake + pnl
                if total_return > 0:
                    c.execute("UPDATE bankroll SET balance = balance + ? WHERE agent_id=?", (total_return, agent_id))
                    now = datetime.datetime.now().isoformat()
                    c.execute('''INSERT INTO transactions (agent_id, amount, type, ref_id, timestamp)
                                 VALUES (?, ?, 'BET_SETTLED', ?, ?)''', (agent_id, total_return, bet_id, now))
                                 
                conn.commit()
                return {"status": "success", "bet_id": bet_id, "result": result, "pnl": pnl, "total_return": total_return}
            except Exception as e:
                conn.rollback()
                raise e
