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

    async def analyze_and_trade(self, lottery_type: str, date_str: str, home_team: str = "未知主队", away_team: str = "未知客队") -> Dict[str, Any]:
        """
        触发核心分析引擎
        """
        logger.info(f"Starting analysis for {lottery_type} on {date_str} ({home_team} vs {away_team})")
        
        try:
            state = {
                "current_match": {"home_team": home_team, "away_team": away_team},
                "task": f"Please run a full EV and portfolio analysis for {lottery_type} on {date_str}. The target match is {home_team} vs {away_team}.",
                "params": {"lottery_type": lottery_type.lower(), "lottery_desc": lottery_type},
                "messages": []
            }
            if getattr(self, "use_graph", False):
                result = await self.brain.process_graph(state)
            else:
                result = await self.brain.process(state)
            return {"ok": True, "data": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def post_match_review(self, home_team: str, away_team: str, home_score: int, away_score: int, prediction_file: str = None) -> Dict[str, Any]:
        """触发赛后复盘与强化学习"""
        logger.info(f"Starting post-match review for {home_team} vs {away_team}")
        try:
            from agents.after_action_review import AfterActionReviewAgent
            aar_agent = AfterActionReviewAgent()
            
            match_data = {"home_team": home_team, "away_team": away_team, "home_score": home_score, "away_score": away_score}
            
            # In a real system, load prediction from DB. For now, mock it.
            prediction = {"predicted_winner": home_team, "confidence": 0.8}
            
            result = await aar_agent.generate_reflection(match_data, prediction)
            if result.get("lesson"):
                await aar_agent.save_lesson_to_doc(result["lesson"])
                
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
    parser.add_argument("--action", default="analyze", choices=["analyze", "query", "review"])
    parser.add_argument("--lottery", default="JINGCAI", choices=["JINGCAI", "BEIDAN", "ZUCAI"])
    parser.add_argument("--date", default="2026-04-16", help="YYYY-MM-DD")
    parser.add_argument("--home", default="曼城", help="主队名称")
    parser.add_argument("--away", default="阿森纳", help="客队名称")
    parser.add_argument("--home_score", type=int, default=0)
    parser.add_argument("--away_score", type=int, default=0)
    parser.add_argument("--use_graph", action="store_true", help="使用最新的 StateGraph 架构而不是传统的 ReAct 循环")
    parser.add_argument("--online", action="store_true")
    
    args = parser.parse_args()
    
    agent = OpenClawMainAgent(online=args.online)
    agent.use_graph = args.use_graph
    
    if args.action == "analyze":
        result = asyncio.run(agent.analyze_and_trade(args.lottery, args.date, args.home, args.away))
    elif args.action == "review":
        result = asyncio.run(agent.post_match_review(args.home, args.away, args.home_score, args.away_score))
    elif args.action == "query":
        result = asyncio.run(agent.query_intelligence(f"{args.home} vs {args.away}情报"))
        
    print(json.dumps(result, indent=2, ensure_ascii=False))
