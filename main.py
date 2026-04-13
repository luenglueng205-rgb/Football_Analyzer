#!/usr/bin/env python3
"""
Football Lottery Multi-Agent System
符合 OpenClaw 规范的多Agent足球彩票分析系统
直接可运行的主入口
"""

import os
import sys
import json
import argparse
from datetime import datetime

# 添加当前目录到路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from agents import (
    OrchestratorAgent,
    ScoutAgent,
    AnalystAgent,
    StrategistAgent,
    RiskManagerAgent
)

LEAGUE_MAPPING_PATH = os.path.join(BASE_DIR, "data", "league_mapping.json")
_LEAGUE_LOOKUP = None

def _load_league_lookup():
    global _LEAGUE_LOOKUP
    if _LEAGUE_LOOKUP is not None:
        return _LEAGUE_LOOKUP
    try:
        with open(LEAGUE_MAPPING_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        lookup = {}
        for group in data.values():
            leagues = group.get("leagues", {})
            for code, info in leagues.items():
                name = info.get("name")
                name_en = info.get("name_en")
                if name:
                    lookup[name] = code
                if name_en:
                    lookup[name_en] = code
                lookup[code] = code
        short = {
            "英超": "E0",
            "西甲": "SP1",
            "意甲": "I1",
            "德甲": "D1",
            "法甲": "F1",
            "中超": "CHN",
            "欧冠": "C1",
        }
        lookup.update(short)
        _LEAGUE_LOOKUP = lookup
        return lookup
    except Exception:
        _LEAGUE_LOOKUP = {}
        return _LEAGUE_LOOKUP

def _normalize_league(league: str):
    if not league:
        return league
    lookup = _load_league_lookup()
    if league in lookup:
        return lookup[league]
    for name, code in lookup.items():
        if isinstance(name, str) and isinstance(league, str) and league in name:
            return code
    return league


class FootballLotteryMultiAgentSystem:
    """
    OpenClaw 规范的多Agent足球彩票分析系统
    支持直接运行和作为模块导入
    """
    
    def __init__(self, config_path: str = None):
        """
        初始化多Agent系统
        
        Args:
            config_path: 配置文件路径，默认使用openclaw.json
        """
        self.config_path = config_path or os.path.join(BASE_DIR, "openclaw.json")
        self.config = self._load_config()
        
        # 初始化所有Agent
        self.agents = {
            "orchestrator": OrchestratorAgent(),
            "scout": ScoutAgent(),
            "analyst": AnalystAgent(),
            "strategist": StrategistAgent(),
            "risk_manager": RiskManagerAgent()
        }
        
        # 注册子Agent到Orchestrator
        self._register_agents()
        
        print(f"[系统] 足球彩票多Agent系统初始化完成")
        print(f"[系统] 已注册 {len(self.agents)} 个专业Agent")
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def _register_agents(self):
        """注册子Agent到Orchestrator"""
        orchestrator = self.agents["orchestrator"]
        for name, agent in self.agents.items():
            if name != "orchestrator":
                orchestrator.register_agent(name, agent)
    
    def analyze(
        self,
        league: str = None,
        home_team: str = None,
        away_team: str = None,
        odds: dict = None,
        markets: dict = None,
        matches: list = None,
        budget: float = 100,
        lottery_type: str = "jingcai",
        mode: str = "full"
    ) -> dict:
        """
        执行比赛分析
        
        Args:
            league: 联赛名称
            home_team: 主队名称
            away_team: 客队名称
            odds: 赔率数据 {"home": x, "draw": y, "away": z}
            matches: 批量比赛列表
            budget: 投注预算
            mode: 分析模式 "fast" | "standard" | "full"
            
        Returns:
            分析结果字典
        """
        print(f"\n{'='*60}")
        print(f"开始 {mode} 模式分析")
        print(f"{'='*60}")
        
        # 准备输入参数
        league_code = _normalize_league(league)
        params = {
            "league": league_code,
            "home_team": home_team,
            "away_team": away_team,
            "odds": odds or {"home": 2.0, "draw": 3.2, "away": 3.5},
            "matches": matches or [],
            "budget": budget,
            "bankroll": budget,
            "lottery_type": lottery_type,
            "risk_rules": {
                "max_single_stake_ratio": 0.1,
                "min_odds": 1.5,
                "max_odds": 10.0,
                "kelly_fraction": 0.25
            },
            "mode": mode
        }
        if markets:
            params["markets"] = markets
        
        # 根据模式执行分析
        if mode == "fast":
            result = self.agents["analyst"].process({"params": params})
        elif mode == "standard":
            # 并行执行 scout 和 analyst
            scout_result = self.agents["scout"].process({"params": params})
            analyst_result = self.agents["analyst"].process({"params": params})
            result = {
                "scout": scout_result,
                "analyst": analyst_result
            }
        else:  # full
            # Swarm Handoff 扁平化工作流
            print("\n[Handoff 机制启动] 抛弃中心调度，Agent 直接交接")
            
            context = {"params": params}
            results = {}
            current_agent_id = "scout"
            
            max_handoffs = 10
            handoff_count = 0
            
            while current_agent_id and handoff_count < max_handoffs:
                print(f"  -> 当前接棒 Agent: {current_agent_id}")
                agent = self.agents.get(current_agent_id)
                if not agent:
                    print(f"⚠️ 找不到 Agent: {current_agent_id}")
                    break
                
                # 执行当前 Agent
                step_result = agent.process(context)
                
                # 特殊处理：如果是辩论打回重审，我们要追加记录而不是覆盖
                if current_agent_id in results and "debate_context" in step_result:
                    results[f"{current_agent_id}_retry_{handoff_count}"] = step_result
                else:
                    results[current_agent_id] = step_result
                
                # 合并上下文，传递给下一个 Agent
                context.update(step_result)
                if isinstance(step_result, dict) and "handoff_params" in step_result:
                    if "params" in context and isinstance(context["params"], dict):
                        context["params"].update(step_result["handoff_params"])
                
                # 获取下一个交接对象
                current_agent_id = step_result.get("next_agent")
                handoff_count += 1
                
            if handoff_count >= max_handoffs:
                print("⚠️ 达到最大 Handoff 次数，可能存在死循环，强制终止。")
            
            # 格式化最终结果
            result = {
                "status": "success",
                "workflow": "swarm_handoff",
                "results": results
            }
        
        return result
    
    def chat(self, message: str) -> str:
        """
        处理自然语言输入
        
        Args:
            message: 用户消息
            
        Returns:
            处理结果
        """
        print(f"\n[用户] {message}")
        
        # 简单意图识别
        if "分析" in message:
            return self._handle_analyze(message)
        elif "推荐" in message:
            return self._handle_recommend(message)
        elif "串关" in message:
            return self._handle_parlay(message)
        elif "状态" in message or "status" in message.lower():
            return self._handle_status()
        else:
            return "您好！我是足球彩票分析助手。请问有什么可以帮您？\n\n可用命令：\n- 分析 [联赛] [主队] vs [客队]\n- 推荐 价值投注\n- 串关 2串1\n- 状态"
    
    def _handle_analyze(self, message: str) -> str:
        """处理分析请求"""
        # 简单解析
        parts = message.replace("分析", "").strip().split("vs")
        if len(parts) >= 2:
            teams = parts[0].strip().split()
            home_team = teams[-1] if teams else "主队"
            away_team = parts[1].strip().split()[0] if parts[1].strip() else "客队"
        else:
            home_team, away_team = "曼联", "利物浦"
        
        result = self.analyze(
            league="英超",
            home_team=home_team,
            away_team=away_team,
            mode="full"
        )
        
        return self._format_result(result)
    
    def _handle_recommend(self, message: str) -> str:
        """处理推荐请求"""
        result = self.analyze(mode="fast")
        
        if "data" in result and "recommendedBets" in result["data"]:
            bets = result["data"]["recommendedBets"]
            if bets:
                return f"推荐投注:\n" + "\n".join([
                    f"- {b['selection']}: 赔率 {b['odds']}, 投注 {b['stake']}元"
                    for b in bets
                ])
        
        return "暂无推荐投注"
    
    def _handle_parlay(self, message: str) -> str:
        """处理串关请求"""
        result = self.analyze(mode="standard")
        return f"串关方案已生成，请查看详细分析结果"
    
    def _handle_status(self) -> str:
        """处理状态查询"""
        status = self.agents["orchestrator"].get_system_status()
        return json.dumps(status, ensure_ascii=False, indent=2)
    
    def _format_result(self, result: dict) -> str:
        """格式化输出结果"""
        output = []
        output.append("\n" + "="*60)
        output.append("分析结果 (Swarm Handoff 架构)")
        output.append("="*60)
        
        results = result.get("results", {})
        
        # 情报收集
        if "scout" in results:
            scout_data = results["scout"]
            output.append(f"\n[1] 情报搜集 Agent:")
            if "ai_report" in scout_data:
                output.append(f"  📝 AI 简报:\n    {scout_data['ai_report']}\n")
            output.append(f"  - 数据源: {scout_data.get('data_source', '未知')}")
            output.append(f"  - 置信度: {scout_data.get('confidence', 'N/A')}")
        
        # 赔率分析
        if "analyst" in results:
            analyst_data = results["analyst"]
            probs = analyst_data.get("probabilities", {})
            output.append(f"\n[2] 赔率分析 Agent ({analyst_data.get('professional_module', '通用分析')}):")
            if "ai_report" in analyst_data:
                output.append(f"  📝 AI 简报:\n    {analyst_data['ai_report']}\n")
            output.append(f"  - 隐含概率: 主 {probs.get('home', 0)*100:.1f}% | 平 {probs.get('draw', 0)*100:.1f}% | 客 {probs.get('away', 0)*100:.1f}%")
            if "calibration_source" in probs:
                output.append(f"  - 校准源: {probs['calibration_source']}")
            
            # 显示专业模块特有数据
            if "professional_data" in analyst_data:
                prof_data = analyst_data["professional_data"]
                if "water_changes" in prof_data:
                    wc = prof_data["water_changes"]
                    output.append(f"  - 实时水位变动: 初盘 {wc.get('initial', {}).get('home', 0)} -> 即时盘 {wc.get('live', {}).get('home', 0)}")
                    output.append(f"    * 庄家倾向: 主队赔率 {wc.get('home_water_trend', 'stable')} (幅度: {wc.get('home_drop_amplitude', 0)})")
                if "spf" in prof_data:
                    output.append(f"  - 北单基础胜率: {prof_data['spf'].get('home_win_rate', 'N/A')}%")
                if "sxd" in prof_data:
                    output.append(f"  - 北单上下单双预测: {prof_data['sxd'].get('most_likely', 'N/A')}")
                if "trad_14" in prof_data:
                    output.append(f"  - 传统足彩稳定性评级: {prof_data['trad_14'].get('stability_rating', 'N/A')}")
                if "poisson" in prof_data:
                    output.append(f"  - 竞彩预期进球: 主 {prof_data['poisson'].get('expected_goals', {}).get('home', 'N/A')} | 客 {prof_data['poisson'].get('expected_goals', {}).get('away', 'N/A')}")
            
        # 策略制定与风控管理
        
        # 提取 Strategist 的数据 (处理可能有多次 Handoff/辩论 的情况)
        strategist_keys = [k for k in results.keys() if k.startswith("strategist")]
        if strategist_keys:
            # 找到最后一次 strategist 的输出
            last_strategist_key = strategist_keys[-1]
            strat_data = results[last_strategist_key]
            
            output.append(f"\n[3] 策略制定 Agent (经过 {len(strategist_keys)} 次博弈):")
            
            if "ai_report" in strat_data:
                output.append(f"  📝 AI 简报:\n    {strat_data['ai_report']}\n")
            if "decision" in strat_data:
                output.append(f"  - 决策: {strat_data.get('decision')}")
            if strat_data.get("expected_value") is not None:
                output.append(f"  - 期望值: {strat_data.get('expected_value'):.4f}")
            if strat_data.get("decision_reason"):
                output.append(f"  - 原因: {strat_data.get('decision_reason')}")
            
            # 打印被辩论打回的痕迹
            if "debate_context" in strat_data:
                output.append(f"  - ⚠️ 触发风控重审:")
                output.append(f"    * 辩论轮次: {strat_data['debate_context'].get('debate_count')}")
                output.append(f"    * 驳回理由: {strat_data['debate_context'].get('rejection_reason')}")
                
            thresholds = strat_data.get("thresholds", {})
            if isinstance(thresholds, dict) and thresholds:
                def _render_threshold(group: str, sel: str, t: dict):
                    be = t.get("breakeven_odds")
                    mv = t.get("move_to_positive_ev", {})
                    target = mv.get("target_odds") if isinstance(mv, dict) else None
                    delta = mv.get("delta_odds") if isinstance(mv, dict) else None
                    line = t.get("line")
                    if be is None and target is None:
                        return None
                    prefix = f"{group}:{sel}"
                    if line is not None:
                        prefix += f"[{line}]"
                    res = f"    * {prefix} -> 保本赔率: {be:.2f}" if be else f"    * {prefix} -> "
                    if target:
                        res += f", 需涨至: {target:.2f} (差 {delta:.2f})"
                    return res
                output.append("  - 监控阈值:")
                for group, sels in thresholds.items():
                    if isinstance(sels, dict):
                        for sel, t in sels.items():
                            line = _render_threshold(group, sel, t)
                            if line:
                                output.append(line)
            
            recommended = strat_data.get("recommended", {})
            if recommended:
                # 兼容专业模块返回的 dict
                if isinstance(recommended, dict):
                    output.append(f"  - 推荐方案: {recommended.get('description', 'N/A')} (风险: {recommended.get('risk', 'N/A')})")
                    if recommended.get("type") == "jingcai_mxn":
                        details = recommended.get("details", {})
                        if "recommended" in details:
                            output.append(f"    * 方案类型: {details['recommended'].get('type')}")
                            output.append(f"    * 投注注数: {details['recommended'].get('bets')}")
                            output.append(f"    * 建议倍数: {details['recommended'].get('multiple', 1)}倍")
                            output.append(f"    * 预计成本: {details['recommended'].get('estimated_cost')}元")
                            output.append(f"    * 奖金区间: {details['recommended'].get('min_prize', 0)} ~ {details['recommended'].get('max_prize', 0)}元")
                    elif recommended.get("type") == "beijing_parlay":
                        details = recommended.get("details", {})
                        if "recommended_combinations" in details:
                            best = details["recommended_combinations"][0]
                            output.append(f"    * 方案类型: {best.get('type')}")
                            output.append(f"    * 投注注数: {best.get('bets')}")
                            output.append(f"    * 建议倍数: {best.get('multiple', 1)}倍")
                            output.append(f"    * 预计成本: {best.get('estimated_cost')}元")
                            output.append(f"    * SP值估算奖金: {best.get('min_prize', 0)} ~ {best.get('max_prize', 0)}元 (已折算65%返奖率)")
                    elif recommended.get("type") == "traditional_rx9":
                        details = recommended.get("details", {})
                        if "cost_analysis" in details:
                            output.append(f"    * 投注注数: {details['cost_analysis'].get('total_bets')}")
                            output.append(f"    * 预计成本: {details['cost_analysis'].get('total_cost')}元")
                            output.append(f"    * 是否在预算内: {'是' if details['cost_analysis'].get('within_budget') else '否'}")
                        if "prize_estimation" in details and details["prize_estimation"]:
                            output.append(f"    * 预计总奖池(模拟): {details['prize_estimation'].get('1st_prize_pool', 0):.0f}元 (100%归属一等奖)")

        # 提取最后一次的风控数据
        risk_keys = [k for k in results.keys() if k.startswith("risk_manager")]
        if risk_keys:
            risk_data = results[risk_keys[-1]]
            output.append(f"\n[4] 风控管理 Agent:")
            output.append(f"  - 建议: {risk_data.get('recommendation', 'N/A')}")
            output.append(f"  - 风控意见: {risk_data.get('reason', 'N/A')}")
            if "checks" in risk_data and "kelly_bet" in risk_data["checks"]:
                kb = risk_data["checks"]["kelly_bet"]
                output.append(f"  - 凯利仓位计算: {kb.get('message', '')}")
                if kb.get("has_edge"):
                    output.append(f"    * 建议动用本金比例: {kb.get('optimal_bet_ratio', 0)*100:.2f}%")
                    output.append(f"    * 建议投注额: {kb.get('recommended_stake', 0):.2f}元")
                
        output.append("\n" + "="*60)
        return "\n".join(output)
    
    def reflect(self, league: str, home_team: str, away_team: str, match_result: dict, lottery_type: str = "jingcai"):
        """
        赛后复盘与记忆更新
        """
        print(f"\n{'='*60}")
        print(f"开始执行赛后复盘 (Memory & Learning)")
        print(f"{'='*60}")
        
        sys.path.insert(0, os.path.join(BASE_DIR, "../../../analyzer/football-lottery-analyzer"))
        try:
            from memory.memory_system import MemorySystem
            from memory.learning_engine import LearningEngine
            from memory.reflector import Reflector
            
            # 初始化记忆组件
            memory_dir = os.path.join(BASE_DIR, "data", "memory")
            os.makedirs(memory_dir, exist_ok=True)
            
            memory = MemorySystem(base_dir=memory_dir)
            engine = LearningEngine(storage_dir=memory_dir)
            reflector = Reflector(memory_system=memory, storage_dir=memory_dir)
            
            print(f"[记忆] 成功加载认知组件: MemorySystem, LearningEngine, Reflector")
            
            # 记录这场比赛的结果 (情景记忆)
            home_goals = match_result.get("home_goals", 0)
            away_goals = match_result.get("away_goals", 0)
            
            # 模拟我们当时投了一个单场胜负
            actual_result = "win" if home_goals > away_goals else "draw" if home_goals == away_goals else "loss"
            
            bet_record = memory.create_betting_record(
                league=league,
                home_team=home_team,
                away_team=away_team,
                bet_type="1x2",
                bet_selection="home",  # 假设我们当时推荐了主胜
                odds=2.0,
                stake=100,
                confidence=0.8,
                analysis_context={"lottery_type": lottery_type}
            )
            
            # 更新比赛结果
            memory.update_betting_result(
                record_id=bet_record.record_id,
                result=actual_result,
                actual_score=f"{home_goals}:{away_goals}"
            )
            
            print(f"[记录] 赛事结果已归档: {home_team} {home_goals}-{away_goals} {away_team}")
            
            # 触发学习引擎 (更新球队和联赛特征)
            # engine.adaptive_optimize(...)
            
            # 如果当时我们输了，触发深度反思
            if actual_result != "win":
                print(f"[反思] 检测到预测失败，开始深度复盘...")
                reflection = reflector.reflect_on_loss(bet_record.record_id)
                print(f"  💡 提取教训: {', '.join(reflection.lessons)}")
                print(f"  📉 置信度惩罚: {reflection.confidence_impact}")
            else:
                print(f"[学习] 预测成功，强化正向特征权重...")
                
            print("\n[系统] 认知库已更新。")
                
        except Exception as e:
            print(f"复盘模块加载失败: {e}")
            import traceback
            traceback.print_exc()

    def get_system_status(self) -> dict:
        """获取系统状态"""
        return self.agents["orchestrator"].get_system_status()


def interactive_mode():
    """交互模式"""
    print("\n" + "="*60)
    print("  足球彩票多Agent分析系统")
    print("  符合 OpenClaw 多Agent规范")
    print("="*60)
    print("\n输入 'quit' 或 'exit' 退出")
    print("输入 'status' 查看系统状态")
    print("-"*60)
    
    system = FootballLotteryMultiAgentSystem()
    
    while True:
        try:
            user_input = input("\n[您] ").strip()
            
            if user_input.lower() in ["quit", "exit", "q"]:
                print("感谢使用，再见！")
                break
            
            response = system.chat(user_input)
            print(f"\n[助手]\n{response}")
            
        except KeyboardInterrupt:
            print("\n\n已退出")
            break
        except Exception as e:
            print(f"\n错误: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="足球彩票多Agent分析系统")
    parser.add_argument("--mode", choices=["interactive", "analyze", "status"], 
                        default="interactive", help="运行模式")
    parser.add_argument("--league", type=str, help="联赛名称")
    parser.add_argument("--home", type=str, help="主队名称")
    parser.add_argument("--away", type=str, help="客队名称")
    parser.add_argument("--odds", type=str, help="赔率JSON")
    parser.add_argument("--markets", type=str, help="市场JSON，例如: {\"totals\":{\"line\":2.5,\"over_odds\":1.9,\"under_odds\":1.9},\"handicap\":{\"line\":-0.5,\"home_odds\":1.95,\"away_odds\":1.85}}")
    parser.add_argument("--lottery-type", choices=["jingcai", "beijing", "traditional"],
                        default="jingcai", help="彩票玩法类型 (默认: jingcai)")
    parser.add_argument("--budget", type=float, default=100, help="投注预算")
    parser.add_argument("--fast", action="store_true", help="快速分析模式")
    parser.add_argument("--reflect", action="store_true", help="执行赛后复盘与记忆更新 (需要 --result 参数)")
    parser.add_argument("--result", type=str, help="赛后结果JSON, e.g. '{\"home_goals\":2, \"away_goals\":1}'")
    
    args = parser.parse_args()
    
    if args.reflect:
        system = FootballLotteryMultiAgentSystem()
        if not args.result:
            print("错误: 复盘模式必须提供 --result 参数。")
            sys.exit(1)
        try:
            match_result = json.loads(args.result)
        except Exception as e:
            print(f"错误: 无法解析 result JSON。{e}")
            sys.exit(1)
            
        # 执行复盘
        system.reflect(
            league=args.league,
            home_team=args.home,
            away_team=args.away,
            match_result=match_result,
            lottery_type=args.lottery_type
        )
        sys.exit(0)

    if args.mode == "interactive":
        interactive_mode()
    elif args.mode == "analyze":
        system = FootballLotteryMultiAgentSystem()
        
        odds = None
        if args.odds:
            try:
                odds = json.loads(args.odds)
            except:
                pass

        markets = None
        if args.markets:
            try:
                markets = json.loads(args.markets)
            except:
                markets = None
        
        result = system.analyze(
            league=args.league,
            home_team=args.home,
            away_team=args.away,
            odds=odds,
            markets=markets,
            budget=args.budget,
            lottery_type=args.lottery_type,
            mode="fast" if args.fast else "full"
        )
        
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.mode == "status":
        system = FootballLotteryMultiAgentSystem()
        print(json.dumps(system.get_system_status(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
