"""
OpenClaw Market Sentinel & Daemon
Runs the continuous real-time market monitoring processes.
This relies on OpenClaw's internal scheduler or acts as a background process.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = WORKSPACE_ROOT / "runtime" / "football_analyzer"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

from core.event_bus import EventBus
from agents.daemon_monitor import RealTimeOddsDaemon

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OpenClawDaemon")

async def run_market_sentinel(match_id: str, home_team: str, away_team: str, online: bool = False):
    """
    Spins up the RealTimeOddsDaemon for a specific match, configured for OpenClaw.
    """
    logger.info(f"Starting OpenClaw Sentinel for {home_team} vs {away_team} (Online={online})")
    
    bus = EventBus()
    
    async def alert_handler(event: Dict[str, Any]):
        # In a real OpenClaw integration, this would push to an OpenClaw notification API
        # or trigger the Main Agent's workflow directly.
        logger.warning(f"🚨 [OpenClaw Alert] Anomaly detected: {event}")
        
    bus.subscribe("ODDS_ALERT", alert_handler)
    
    daemon = RealTimeOddsDaemon(
        match_id=match_id,
        home_team=home_team,
        away_team=away_team,
        bus=bus,
        online=online,
        polling_interval_s=5.0, # Less aggressive polling for OpenClaw
        water_drop_threshold=0.08
    )
    
    await daemon.run(max_ticks=None) # Run forever or until match starts

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-id", required=True)
    parser.add_argument("--home-team", required=True)
    parser.add_argument("--away-team", required=True)
    parser.add_argument("--online", action="store_true")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_market_sentinel(args.match_id, args.home_team, args.away_team, args.online))
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user.")
