#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - 可直接运行的多Agent协作系统
Football Lottery Multi-Agent System

这是一个完整的、可直接运行的Agent系统，不依赖Skill框架
可以直接通过 Python 或命令行使用

使用方式:
    python agent_cli.py                    # 交互模式
    python agent_cli.py --chat "分析比赛"   # 单次对话
    python agent_cli.py --analyze          # 完整分析模式
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# 设置路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Agent 基类
# ============================================================================

class AgentStatus:
    """Agent状态"""
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


class Message:
    """Agent间消息"""
    def __init__(self, sender: str, receiver: str, content: Any, msg_type: str = "task"):
        self.sender = sender
        self.receiver = receiver
        self.content = content
        self.type = msg_type
        self.timestamp = datetime.now().isoformat()


class BaseAgent:
    """Agent基类"""
    
    def __init__(self, agent_id: str, name: str, description: str = ""):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.status = AgentStatus.IDLE
        self.inbox: List[Message] = []
        self.memory: Dict[str, Any] = {}
        
        logger.info(f"Agent {self.agent_id} ({self.name}) 初始化")
    
    def receive(self, message: Message):
        """接收消息"""
        self.inbox.append(message)
        logger.debug(f"{self.agent_id} 收到来自 {message.sender} 的消息")
    
    def send(self, receiver: str, content: Any, msg_type: str = "task") -> Message:
        """发送消息"""
        return Message(self.agent_id, receiver, content, msg_type)
    
    def process(self, task: Dict) -> Dict:
        """处理任务 - 子类实现"""
        raise NotImplementedError
    
    def get_info(self) -> Dict:
        """获取Agent信息"""
        return {
            "id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "status": self.status
        }


# ============================================================================
# 专业Agent实现
# ============================================================================

class ScoutAgent(BaseAgent):
    """情报搜集Agent"""
    
    def __init__(self):
        super().__init__("scout", "情报搜集", "负责收集球队情报、阵容、伤病、历史数据")
    
    def process(self, task: Dict) -> Dict:
        """搜集情报"""
        self.status = AgentStatus.WORKING
        
        league = task.get('league', '')
        home_team = task.get('home_team', '')
        away_team = task.get('away_team', '')
        
        # 模拟情报搜集
        result = {
            "agent": self.agent_id,
            "status": "success",
            "data": {
                "home_team": {
                    "name": home_team,
                    "recent_form": ["W", "D", "W", "W", "L"],
                    "home_record": {"played": 10, "wins": 7, "draws": 2, "losses": 1},
                    "injuries": [],
                    "confidence": 0.85
                },
                "away_team": {
                    "name": away_team,
                    "recent_form": ["L", "W", "D", "W", "W"],
                    "away_record": {"played": 9, "wins": 4, "draws": 3, "losses": 2},
                    "injuries": ["主力前锋"],
                    "confidence": 0.80
                },
                "match_context": {
                    "league": league,
                    "importance": "high",
                    "weather": "晴 15°C"
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
        self.status = AgentStatus.COMPLETED
        self.memory['last_intel'] = result
        return result


class AnalystAgent(BaseAgent):
    """赔率分析Agent"""
    
    def __init__(self):
        super().__init__("analyst", "赔率分析", "负责赔率分析、价值识别、异常检测")
        self._init_analyzer()
    
    def _init_analyzer(self):
        """初始化分析器"""
        try:
            from data_fetch.odds_analyzer_tool import OddsAnalyzer
            self.analyzer = OddsAnalyzer()
        except ImportError:
            self.analyzer = None
            logger.warning("OddsAnalyzer 未找到，使用内置分析")
    
    def process(self, task: Dict) -> Dict:
        """分析赔率"""
        self.status = AgentStatus.WORKING
        
        odds = task.get('odds', {})
        intel = task.get('intel', {})  # 从Scout获取的情报
        
        if not odds:
            # 使用示例赔率
            odds = {'home': 1.85, 'draw': 3.40, 'away': 4.20}
        
        # 赔率分析
        if self.analyzer:
            analysis = self.analyzer.analyze_odds(odds)
        else:
            # 内置分析
            analysis = self._simple_analyze(odds)
        
        result = {
            "agent": self.agent_id,
            "status": "success",
            "data": {
                "odds": odds,
                "probabilities": analysis.get('probabilities', {}),
                "juice": analysis.get('juice_analysis', {}),
                "value_analysis": analysis.get('value_analysis', {}),
                "recommendation": analysis.get('recommendation', {}),
                "confidence": 0.75
            },
            "timestamp": datetime.now().isoformat()
        }
        
        self.status = AgentStatus.COMPLETED
        self.memory['last_analysis'] = result
        return result
    
    def _simple_analyze(self, odds: Dict) -> Dict:
        """简化分析"""
        home = odds.get('home', 0)
        draw = odds.get('draw', 0)
        away = odds.get('away', 0)
        
        total = (1/home + 1/draw + 1/away) if home > 0 and draw > 0 and away > 0 else 0
        
        return {
            'probabilities': {
                'home': (1/home)/total if total > 0 else 0,
                'draw': (1/draw)/total if total > 0 else 0,
                'away': (1/away)/total if total > 0 else 0
            },
            'juice_analysis': {'juice_percentage': (1-1/total)*100 if total > 1 else 0},
            'value_analysis': {},
            'recommendation': {}
        }


class StrategistAgent(BaseAgent):
    """策略制定Agent"""
    
    def __init__(self):
        super().__init__("strategist", "策略制定", "负责投注策略、M串N方案、资金分配")
    
    def process(self, task: Dict) -> Dict:
        """制定策略"""
        self.status = AgentStatus.WORKING
        
        budget = task.get('budget', 100)
        risk_level = task.get('risk_level', 'medium')
        analysis = task.get('analysis', {})
        
        # 根据分析结果生成策略
        recommendation = analysis.get('data', {}).get('recommendation', {})
        value_analysis = analysis.get('data', {}).get('value_analysis', {})
        
        # 找出有价值的选择
        valuable = []
        for outcome, data in value_analysis.items():
            if isinstance(data, dict) and data.get('has_value'):
                valuable.append({
                    'outcome': outcome,
                    'odds': data.get('odds', 0),
                    'value_pct': data.get('value_percentage', 0)
                })
        
        strategies = []
        
        # 策略1: 单关
        if valuable:
            best = max(valuable, key=lambda x: x['value_pct'])
            strategies.append({
                "type": "单关",
                "selection": best['outcome'],
                "odds": best['odds'],
                "stake": budget * 0.3,
                "expected_return": budget * 0.3 * best['odds'],
                "risk": "low"
            })
        
        # 策略2: 2串1
        if len(valuable) >= 2:
            strategies.append({
                "type": "2串1",
                "selections": [v['outcome'] for v in valuable[:2]],
                "combined_odds": valuable[0]['odds'] * valuable[1]['odds'],
                "stake": budget * 0.4,
                "expected_return": budget * 0.4 * valuable[0]['odds'] * valuable[1]['odds'],
                "risk": "medium"
            })
        
        # 策略3: 自由过关
        if len(valuable) >= 3:
            strategies.append({
                "type": "自由过关(2串1+3串1)",
                "selections": [v['outcome'] for v in valuable[:3]],
                "stake": budget * 0.3,
                "max_return": budget * 0.3 * valuable[0]['odds'] * valuable[1]['odds'] * valuable[2]['odds'],
                "risk": "high"
            })
        
        result = {
            "agent": self.agent_id,
            "status": "success",
            "data": {
                "budget": budget,
                "risk_level": risk_level,
                "strategies": strategies,
                "recommended": strategies[0] if strategies else None,
                "confidence": 0.70
            },
            "timestamp": datetime.now().isoformat()
        }
        
        self.status = AgentStatus.COMPLETED
        self.memory['last_strategy'] = result
        return result


class RiskManagerAgent(BaseAgent):
    """风险管理Agent"""
    
    def __init__(self):
        super().__init__("risk_manager", "风险管理", "负责仓位控制、止损检查、风险评估")
        self.max_stake_ratio = 0.1
        self.max_daily_loss = 0.2
    
    def process(self, task: Dict) -> Dict:
        """风控评估"""
        self.status = AgentStatus.WORKING
        
        strategy = task.get('strategy', {})
        bankroll = task.get('bankroll', 1000)
        
        stake = strategy.get('stake', 0)
        odds = strategy.get('odds', strategy.get('combined_odds', 0))
        
        # 风控检查
        checks = {
            "stake_ratio_check": {
                "passed": stake <= bankroll * self.max_stake_ratio,
                "actual_ratio": stake / bankroll if bankroll > 0 else 1,
                "max_ratio": self.max_stake_ratio
            },
            "odds_range_check": {
                "passed": 1.3 <= odds <= 10.0,
                "actual_odds": odds
            }
        }
        
        # 计算凯利
        if odds > 1:
            # 假设胜率50%
            probability = 0.5
            kelly = (odds - 1) * probability - (1 - probability)
            kelly = max(0, kelly * 0.25)  # 半凯利
        else:
            kelly = 0
        
        risk_score = sum(1 for c in checks.values() if not c['passed']) / len(checks)
        
        result = {
            "agent": self.agent_id,
            "status": "success",
            "data": {
                "checks": checks,
                "kelly_fraction": kelly,
                "risk_score": risk_score,
                "approved": risk_score < 0.5,
                "adjustments": self._generate_adjustments(checks, kelly, stake)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        self.status = AgentStatus.COMPLETED
        return result
    
    def _generate_adjustments(self, checks: Dict, kelly: float, original_stake: float) -> Dict:
        """生成调整建议"""
        adjustments = {}
        
        if not checks['stake_ratio_check']['passed']:
            max_allowed = original_stake * 0.8  # 降低20%
            adjustments['reduce_stake'] = max_allowed
        
        if kelly > 0.25:
            adjustments['reduce_kelly'] = 0.25
        
        return adjustments


# ============================================================================
# Orchestrator - 调度中心
# ============================================================================

class Orchestrator:
    """任务调度器"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.task_queue: List[Dict] = []
        self.task_history: List[Dict] = []
        
        # 注册Agent
        self.register_agent(ScoutAgent())
        self.register_agent(AnalystAgent())
        self.register_agent(StrategistAgent())
        self.register_agent(RiskManagerAgent())
        
        logger.info(f"Orchestrator 初始化，{len(self.agents)} 个Agent")
    
    def register_agent(self, agent: BaseAgent):
        """注册Agent"""
        self.agents[agent.agent_id] = agent
        logger.info(f"注册Agent: {agent.name}")
    
    def run_workflow(self, workflow: str, params: Dict) -> Dict:
        """执行工作流"""
        logger.info(f"启动工作流: {workflow}")
        
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        if workflow == "full_analysis":
            result = self._full_analysis_workflow(task_id, params)
        elif workflow == "quick_analysis":
            result = self._quick_analysis_workflow(task_id, params)
        elif workflow == "odds_analysis":
            result = self._odds_analysis_workflow(task_id, params)
        else:
            result = {"error": f"未知工作流: {workflow}"}
        
        self.task_history.append({
            "task_id": task_id,
            "workflow": workflow,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
        return result
    
    def _full_analysis_workflow(self, task_id: str, params: Dict) -> Dict:
        """完整分析工作流"""
        results = {}
        
        # 阶段1: 情报搜集 (并行)
        scout_result = self.agents['scout'].process({
            'league': params.get('league', '英超'),
            'home_team': params.get('home_team', '曼联'),
            'away_team': params.get('away_team', '利物浦')
        })
        results['scout'] = scout_result
        
        # 阶段2: 赔率分析 (需要情报)
        analyst_result = self.agents['analyst'].process({
            'odds': params.get('odds', {}),
            'intel': scout_result
        })
        results['analyst'] = analyst_result
        
        # 阶段3: 策略制定 (需要分析)
        strategist_result = self.agents['strategist'].process({
            'budget': params.get('budget', 100),
            'risk_level': params.get('risk_level', 'medium'),
            'analysis': analyst_result
        })
        results['strategist'] = strategist_result
        
        # 阶段4: 风控审核 (需要策略)
        recommended_strategy = strategist_result.get('data', {}).get('recommended') or {}
        risk_result = self.agents['risk_manager'].process({
            'strategy': recommended_strategy,
            'bankroll': params.get('bankroll', 1000)
        })
        results['risk_manager'] = risk_result
        
        return {
            "task_id": task_id,
            "workflow": "full_analysis",
            "status": "completed",
            "results": results,
            "final_recommendation": self._generate_final_recommendation(results),
            "timestamp": datetime.now().isoformat()
        }
    
    def _quick_analysis_workflow(self, task_id: str, params: Dict) -> Dict:
        """快速分析"""
        analyst_result = self.agents['analyst'].process({
            'odds': params.get('odds', {})
        })
        
        strategist_result = self.agents['strategist'].process({
            'budget': params.get('budget', 100),
            'risk_level': 'low',
            'analysis': analyst_result
        })
        
        return {
            "task_id": task_id,
            "workflow": "quick_analysis",
            "status": "completed",
            "results": {
                'analyst': analyst_result,
                'strategist': strategist_result
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _odds_analysis_workflow(self, task_id: str, params: Dict) -> Dict:
        """赔率分析"""
        analyst_result = self.agents['analyst'].process({
            'odds': params.get('odds', {})
        })
        
        return {
            "task_id": task_id,
            "workflow": "odds_analysis",
            "status": "completed",
            "results": {'analyst': analyst_result},
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_final_recommendation(self, results: Dict) -> Dict:
        """生成最终建议"""
        risk = results.get('risk_manager', {}).get('data', {})
        
        if risk.get('approved'):
            strategy = results.get('strategist', {}).get('data', {}).get('recommended', {})
            return {
                "approved": True,
                "action": "可以投注",
                "strategy": strategy,
                "adjustments": risk.get('adjustments', {})
            }
        else:
            return {
                "approved": False,
                "action": "建议观望",
                "reason": "风控检查未通过"
            }
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        return {
            "orchestrator": "running",
            "agents": [agent.get_info() for agent in self.agents.values()],
            "total_tasks": len(self.task_history),
            "active_agents": sum(1 for a in self.agents.values() if a.status == AgentStatus.WORKING)
        }


# ============================================================================
# 主CLI界面
# ============================================================================

class FootballLotteryAgentCLI:
    """命令行界面"""
    
    def __init__(self):
        self.orchestrator = Orchestrator()
        self.running = True
    
    def print_header(self):
        """打印标题"""
        print("\n" + "=" * 60)
        print("⚽ 足球彩票分析Agent系统 ⚽")
        print("=" * 60)
        print("多Agent协作: Scout + Analyst + Strategist + RiskManager")
        print("-" * 60)
    
    def print_menu(self):
        """打印菜单"""
        print("\n可用命令:")
        print("  1. 分析比赛 - 完整分析工作流")
        print("  2. 快速分析 - 赔率+策略")
        print("  3. 赔率分析 - 仅赔率分析")
        print("  4. 系统状态 - 查看Agent状态")
        print("  5. 帮助 - 显示帮助")
        print("  0. 退出 - 退出系统")
    
    def cmd_full_analysis(self):
        """完整分析"""
        print("\n--- 完整分析 ---")
        
        league = input("联赛 (默认: 英超): ").strip() or "英超"
        home = input("主队 (默认: 曼联): ").strip() or "曼联"
        away = input("客队 (默认: 利物浦): ").strip() or "利物浦"
        budget = float(input("预算 (默认: 100): ").strip() or "100")
        
        # 可选赔率
        odds_input = input("赔率 (格式: 主胜,平局,客胜, 默认使用示例): ").strip()
        odds = {}
        if odds_input:
            parts = odds_input.split(',')
            if len(parts) >= 3:
                odds = {'home': float(parts[0]), 'draw': float(parts[1]), 'away': float(parts[2])}
        
        result = self.orchestrator.run_workflow("full_analysis", {
            'league': league,
            'home_team': home,
            'away_team': away,
            'budget': budget,
            'odds': odds
        })
        
        self._print_result(result)
    
    def cmd_quick_analysis(self):
        """快速分析"""
        print("\n--- 快速分析 ---")
        
        odds_input = input("赔率 (格式: 主胜,平局,客胜): ").strip()
        odds = {}
        if odds_input:
            parts = odds_input.split(',')
            if len(parts) >= 3:
                odds = {'home': float(parts[0]), 'draw': float(parts[1]), 'away': float(parts[2])}
        
        budget = float(input("预算 (默认: 100): ").strip() or "100")
        
        result = self.orchestrator.run_workflow("quick_analysis", {
            'odds': odds,
            'budget': budget
        })
        
        self._print_result(result)
    
    def cmd_odds_analysis(self):
        """赔率分析"""
        print("\n--- 赔率分析 ---")
        
        odds_input = input("赔率 (格式: 主胜,平局,客胜): ").strip()
        odds = {}
        if odds_input:
            parts = odds_input.split(',')
            if len(parts) >= 3:
                odds = {'home': float(parts[0]), 'draw': float(parts[1]), 'away': float(parts[2])}
        
        result = self.orchestrator.run_workflow("odds_analysis", {
            'odds': odds
        })
        
        self._print_result(result)
    
    def cmd_system_status(self):
        """系统状态"""
        status = self.orchestrator.get_system_status()
        print("\n--- 系统状态 ---")
        print(f"调度器: {status['orchestrator']}")
        print(f"Agent数量: {len(status['agents'])}")
        print(f"总任务数: {status['total_tasks']}")
        print("\nAgent列表:")
        for agent in status['agents']:
            print(f"  - {agent['name']} ({agent['id']}): {agent['status']}")
    
    def _print_result(self, result: Dict):
        """打印结果"""
        print("\n" + "=" * 60)
        print("📊 分析结果")
        print("=" * 60)
        
        # 赔率分析
        analyst = result.get('results', {}).get('analyst', {}).get('data', {})
        probs = analyst.get('probabilities', {})
        juice = analyst.get('juice', {}) or analyst.get('juice_analysis', {})
        
        print("\n📈 赔率分析:")
        if probs:
            print(f"   主胜概率: {probs.get('home', 0)*100:.1f}%")
            print(f"   平局概率: {probs.get('draw', 0)*100:.1f}%")
            print(f"   客胜概率: {probs.get('away', 0)*100:.1f}%")
        if juice:
            print(f"   庄家抽水: {juice.get('juice_percentage', 0):.2f}%")
        
        # 策略
        strategist = result.get('results', {}).get('strategist', {}).get('data', {})
        strategies = strategist.get('strategies', [])
        
        if strategies:
            print("\n📋 推荐策略:")
            for i, s in enumerate(strategies[:3], 1):
                print(f"   {i}. {s.get('type', 'N/A')}")
                if 'stake' in s:
                    print(f"      投注: {s['stake']:.0f}元")
                if 'expected_return' in s:
                    print(f"      预期收益: {s['expected_return']:.0f}元")
        
        # 最终建议
        final = result.get('final_recommendation', {})
        print("\n" + "-" * 40)
        if final.get('approved'):
            print(f"✅ {final.get('action')}")
            if final.get('strategy'):
                s = final['strategy']
                print(f"   类型: {s.get('type')}")
                print(f"   投注: {s.get('stake', 0):.0f}元")
        else:
            print(f"⚠️ {final.get('action')}: {final.get('reason', '')}")
        
        print("=" * 60)
    
    def run_interactive(self):
        """交互模式"""
        self.print_header()
        self.print_menu()
        
        while self.running:
            try:
                choice = input("\n请选择 (0-5): ").strip()
                
                if choice == '1':
                    self.cmd_full_analysis()
                elif choice == '2':
                    self.cmd_quick_analysis()
                elif choice == '3':
                    self.cmd_odds_analysis()
                elif choice == '4':
                    self.cmd_system_status()
                elif choice == '5':
                    self.print_menu()
                elif choice == '0':
                    print("\n感谢使用！再见！👋")
                    self.running = False
                else:
                    print("无效选择，请重试")
            
            except KeyboardInterrupt:
                print("\n\n使用 '0' 退出")
            except Exception as e:
                print(f"\n错误: {e}")


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description="足球彩票分析Agent系统")
    parser.add_argument('--chat', '-c', type=str, help='单次对话模式')
    parser.add_argument('--analyze', '-a', action='store_true', help='完整分析模式')
    parser.add_argument('--status', '-s', action='store_true', help='显示系统状态')
    
    args = parser.parse_args()
    
    cli = FootballLotteryAgentCLI()
    
    if args.chat:
        # 单次对话
        print(f"\n分析: {args.chat}")
        result = cli.orchestrator.run_workflow("full_analysis", {
            'home_team': '曼联',
            'away_team': '利物浦',
            'budget': 100
        })
        cli._print_result(result)
    
    elif args.analyze:
        # 完整分析
        result = cli.orchestrator.run_workflow("full_analysis", {
            'league': '英超',
            'home_team': '曼联',
            'away_team': '利物浦',
            'budget': 100
        })
        cli._print_result(result)
    
    elif args.status:
        # 状态
        cli.cmd_system_status()
    
    else:
        # 交互模式
        cli.run_interactive()


if __name__ == "__main__":
    main()
