import os
import sqlite3
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
                      status TEXT, timestamp DATETIME,
                      closing_odds REAL, result TEXT, pnl REAL)''')
        
        # Add new columns if they don't exist (for existing databases)
        try:
            c.execute("ALTER TABLE bets ADD COLUMN closing_odds REAL")
            c.execute("ALTER TABLE bets ADD COLUMN result TEXT")
            c.execute("ALTER TABLE bets ADD COLUMN pnl REAL")
        except sqlite3.OperationalError:
            pass # Columns already exist
        
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
                     (match_id, lottery_type, selection, odds, stake, ticket_code, status, timestamp, closing_odds, result, pnl)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)''',
                  (match_id, lottery_type, selection, odds, stake, ticket_code, "PENDING", now))
                  
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "ticket_code": ticket_code,
            "remaining_balance": new_balance
        }

    def record_closing_odds(self, match_id: str, closing_odds: float) -> dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "UPDATE bets SET closing_odds=? WHERE id=(SELECT id FROM bets WHERE match_id=? ORDER BY id DESC LIMIT 1)",
            (closing_odds, match_id),
        )
        conn.commit()
        updated = c.rowcount
        conn.close()
        if updated < 1:
            return {"status": "error", "message": "Bet not found"}
        return {"status": "success", "match_id": match_id, "closing_odds": closing_odds}

    def record_result(self, match_id: str, result: str, pnl: float) -> dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "UPDATE bets SET result=?, pnl=?, status=? WHERE id=(SELECT id FROM bets WHERE match_id=? ORDER BY id DESC LIMIT 1)",
            (result, pnl, "RESOLVED", match_id),
        )
        conn.commit()
        updated = c.rowcount
        conn.close()
        if updated < 1:
            return {"status": "error", "message": "Bet not found"}
        return {"status": "success", "match_id": match_id, "result": result, "pnl": pnl}
