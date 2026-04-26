import asyncio
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from rich.live import Live
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from core.event_bus import EventBus
from agents.daemon_monitor import RealTimeOddsDaemon
from core.mentor_workflow import MentorWorkflow
from core.beidan_workflow import BeidanWorkflow
from core.zucai_workflow import ZucaiWorkflow
from tools.multisource_fetcher import MultiSourceFetcher
from tools.snapshot_store import SnapshotStore

# Disable default logging to not mess up Rich UI
logging.getLogger().setLevel(logging.CRITICAL)

class AutopilotDashboard:
    def __init__(self, lottery_type: str, match_id: str, online: bool):
        self.console = Console()
        self.lottery_type = lottery_type
        self.match_id = match_id
        self.online = online
        
        self.ticks = []
        self.alerts = []
        self.trades = []
        
    def add_tick(self, tick_data):
        self.ticks.insert(0, tick_data)
        if len(self.ticks) > 10:
            self.ticks.pop()
            
    def add_alert(self, alert_data):
        self.alerts.insert(0, alert_data)
        if len(self.alerts) > 5:
            self.alerts.pop()
            
    def add_trade(self, trade_data):
        self.trades.insert(0, trade_data)
        if len(self.trades) > 5:
            self.trades.pop()

    def generate_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main")
        )
        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1)
        )
        layout["left"].split_column(
            Layout(name="ticks", ratio=2),
            Layout(name="alerts", ratio=1)
        )
        layout["right"].split_column(
            Layout(name="trades", ratio=1)
        )
        
        # Header
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mode = "ONLINE" if self.online else "OFFLINE"
        header_text = Text(f"🤖 AI-Native Football Analyzer Autopilot | Mode: {mode} | Lottery: {self.lottery_type} | Time: {time_str}", style="bold white on blue", justify="center")
        layout["header"].update(Panel(header_text))
        
        # Ticks Table
        tick_table = Table(expand=True)
        tick_table.add_column("Time", style="cyan")
        tick_table.add_column("Home", justify="right")
        tick_table.add_column("Draw", justify="right")
        tick_table.add_column("Away", justify="right")
        for t in self.ticks:
            tick_table.add_row(t.get("time", ""), str(t.get("home_odds", "")), str(t.get("draw_odds", "")), str(t.get("away_odds", "")))
        layout["ticks"].update(Panel(tick_table, title="[green]Live Odds Stream[/green]", border_style="green"))
        
        # Alerts Table
        alert_table = Table(expand=True)
        alert_table.add_column("Time", style="cyan")
        alert_table.add_column("Reason", style="yellow")
        for a in self.alerts:
            alert_table.add_row(datetime.now().strftime("%H:%M:%S"), str(a.get("reason", "Anomaly")))
        layout["alerts"].update(Panel(alert_table, title="[yellow]Market Anomalies / Alerts[/yellow]", border_style="yellow"))
        
        # Trades Table
        trade_table = Table(expand=True)
        trade_table.add_column("Time", style="cyan")
        trade_table.add_column("Ticket / Action", style="magenta")
        for t in self.trades:
            trade_table.add_row(t.get("time", ""), t.get("summary", ""))
        layout["trades"].update(Panel(trade_table, title="[magenta]Execution & Trades[/magenta]", border_style="magenta"))
        
        return layout

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--lottery-type", default="JINGCAI", choices=["JINGCAI", "BEIDAN", "ZUCAI"])
    parser.add_argument("--match-id", default="match_1024")
    parser.add_argument("--home-team", default="曼城")
    parser.add_argument("--away-team", default="切尔西")
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--max-ticks", type=int, default=15)
    args = parser.parse_args()

    dashboard = AutopilotDashboard(args.lottery_type, args.match_id, args.online)
    bus = EventBus()
    
    # Store reference to prevent GC
    workflows = {}
    
    async def handle_tick(event):
        data = event.get("data", event)
        dashboard.add_tick({
            "time": datetime.now().strftime("%H:%M:%S"),
            "home_odds": data.get("home_odds", "-"),
            "draw_odds": data.get("draw_odds", "-"),
            "away_odds": data.get("away_odds", "-")
        })

    async def handle_alert(event):
        dashboard.add_alert({"reason": str(event.get("reason", "Odds dropped significantly"))})
        
        # Trigger workflow
        dashboard.add_trade({"time": datetime.now().strftime("%H:%M:%S"), "summary": "Triggering Workflow..."})
        try:
            store = SnapshotStore()
            fetcher = MultiSourceFetcher(store=store, online=args.online)
            
            if args.lottery_type == "JINGCAI":
                wf = MentorWorkflow(fetcher=fetcher)
            elif args.lottery_type == "BEIDAN":
                wf = BeidanWorkflow(fetcher=fetcher)
            else:
                wf = ZucaiWorkflow(fetcher=fetcher)
                
            # Run workflow in thread to avoid blocking UI
            date_str = datetime.now().strftime("%Y-%m-%d")
            out = await asyncio.to_thread(wf.run, date=date_str, stake=100.0, auto_trade=False)
            
            if out.get("ticket") and out["ticket"].get("ticket"):
                legs = len(out["ticket"]["ticket"].get("legs", []))
                dashboard.add_trade({
                    "time": datetime.now().strftime("%H:%M:%S"), 
                    "summary": f"✅ Generated Ticket ({legs} legs)"
                })
            else:
                dashboard.add_trade({
                    "time": datetime.now().strftime("%H:%M:%S"), 
                    "summary": "❌ No valid ticket generated"
                })
        except Exception as e:
            dashboard.add_trade({"time": datetime.now().strftime("%H:%M:%S"), "summary": f"⚠️ Error: {str(e)[:50]}"})

    await bus.subscribe("ODDS_TICK", handle_tick)
    await bus.subscribe("ODDS_ALERT", handle_alert)

    daemon = RealTimeOddsDaemon(
        match_id=args.match_id,
        home_team=args.home_team,
        away_team=args.away_team,
        bus=bus,
        online=args.online,
        polling_interval_s=1.0,
        water_drop_threshold=0.05
    )
    
    daemon_task = asyncio.create_task(daemon.run(max_ticks=args.max_ticks))
    
    with Live(dashboard.generate_layout(), refresh_per_second=2, screen=True) as live:
        while not daemon_task.done():
            await asyncio.sleep(0.5)
            live.update(dashboard.generate_layout())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
