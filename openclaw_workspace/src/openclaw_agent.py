"""
OpenClaw Main Agent (AI-Native Edition)
This is the highest-privilege entry point for the OpenClaw edition of the Football Analyzer.
It relies on LLM capabilities for cognitive looping, just like the standalone AINativeCoreAgent.
"""

import asyncio
import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = WORKSPACE_ROOT / "runtime" / "football_analyzer"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))
SRC_DIR = WORKSPACE_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Use the LLM Brain from standalone to ensure cognitive parity
from agents.ai_native_core import AINativeCoreAgent
from tools.memory_manager import MemoryManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OpenClawMainAgent")

class OpenClawMainAgent:
    """
    The Supreme Agent for the OpenClaw Platform.
    It doesn't just run static workflows; it uses the LLM Brain to autonomously
    decide which mathematical tools to call based on the 16 Market Rules.
    """
    def __init__(self, online: bool = False):
        self.online = online
        self.brain = AINativeCoreAgent()
        self.memory = MemoryManager()

    async def analyze_and_trade(self, lottery_type: str, date_str: str) -> Dict[str, Any]:
        """
        触发核心分析引擎
        """
        logger.info(f"Starting analysis for {lottery_type} on {date_str}")
        
        try:
            state = {
                "current_match": {"home_team": "曼城", "away_team": "阿森纳"},
                "task": f"Please run a full EV and portfolio analysis for {lottery_type} on {date_str}.",
                "params": {"lottery_type": lottery_type.lower(), "lottery_desc": lottery_type},
                "messages": []
            }
            result = await self.brain.process(state)
            return {"ok": True, "data": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def query_intelligence(self, query: str) -> Dict[str, Any]:
        logger.info(f"Querying intelligence: {query}")
        try:
            state = {
                "task": f"Answer intelligence query: {query}",
                "messages": []
            }
            result = await self.brain.process(state)
            return {"ok": True, "data": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OpenClaw Main Agent (AI-Native)")
    parser.add_argument("--lottery", default="JINGCAI", choices=["JINGCAI", "BEIDAN", "ZUCAI"])
    parser.add_argument("--date", default="2026-04-16", help="YYYY-MM-DD")
    parser.add_argument("--online", action="store_true")
    
    args = parser.parse_args()
    
    agent = OpenClawMainAgent(online=args.online)
    result = asyncio.run(agent.analyze_and_trade(args.lottery, args.date))
    print(json.dumps(result, indent=2, ensure_ascii=False))
