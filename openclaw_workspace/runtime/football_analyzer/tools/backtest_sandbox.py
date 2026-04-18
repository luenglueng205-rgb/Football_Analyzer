import json
import logging
import os
import random
from datetime import datetime

logger = logging.getLogger(__name__)

class BacktestSandbox:
    """
    时光机回测沙盒 (Time-Machine Sandbox).
    模拟历史比赛，屏蔽未来信息，让 AI 军师基于历史赔率做决策，并与真实赛果对碰。
    """
    def __init__(self):
        self.hyperparams_path = os.path.join(os.path.dirname(__file__), '..', 'configs', 'hyperparams.json')
        self._load_hyperparams()

    def _load_hyperparams(self):
        try:
            with open(self.hyperparams_path, 'r', encoding='utf-8') as f:
                self.params = json.load(f)
        except Exception as e:
            logger.error(f"加载超参数失败: {e}")
            self.params = {}

    def simulate_match(self, match_data: dict) -> dict:
        """
        核心方法：丢入一场历史比赛的赛前赔率，让系统做决策，最后用真实赛果算分。
        """
        home = match_data['home']
        away = match_data['away']
        odds = match_data['pre_match_odds'] # [Home, Draw, Away]
        true_result = match_data['actual_result'] # "3", "1", or "0"
        
        # 1. 模拟系统三路诸将的权重计算 (提取自 hyperparams)
        w_fun = self.params.get("weights", {}).get("fundamental_quant", 0.33)
        w_con = self.params.get("weights", {}).get("contrarian_quant", 0.33)
        w_smt = self.params.get("weights", {}).get("smart_money_quant", 0.33)
        
        # 为了演示进化效果，这里引入一个简单的“偏见公式”：
        # 如果模型太依赖基本面权重(>0.5)，遇到强队冷门就会翻车。
        # 如果模型太依赖反直觉(>0.5)，命中率极低。
        
        # 模拟 AI 决策 (简化版，替代完整的 SyndicateOS 调用以加快回测)
        # 假设 1.20 赔率的强队，基本面派 100% 看好主胜，反买派看好平/负
        if odds[0] < 1.5:
            ai_score_home = w_fun * 0.9 + w_con * 0.1 + w_smt * 0.5
            ai_score_draw = w_fun * 0.05 + w_con * 0.6 + w_smt * 0.3
        else:
            ai_score_home = w_fun * 0.4 + w_con * 0.4 + w_smt * 0.4
            ai_score_draw = w_fun * 0.3 + w_con * 0.3 + w_smt * 0.3
            
        ai_decision = "3" if ai_score_home > ai_score_draw else "1"
        
        # 2. 判断对错，计算 PnL (模拟投注 100 元)
        stake = 100.0
        if ai_decision == true_result:
            # 命中
            hit_odds = odds[0] if true_result == "3" else (odds[1] if true_result == "1" else odds[2])
            profit = (stake * hit_odds) - stake
            status = "WIN"
        else:
            # 未命中
            profit = -stake
            status = "LOSS"
            
        return {
            "match": f"{home} vs {away}",
            "decision": ai_decision,
            "actual": true_result,
            "odds": odds,
            "status": status,
            "profit": profit,
            "ai_confidence_home": ai_score_home
        }

    def run_batch_simulation(self, historical_matches: list) -> dict:
        """
        跑批 100 场历史数据，生成 PnL 财报，供 AutoTunerAgent 反思。
        """
        logger.info(f"⏳ 启动时光机，开始回测 {len(historical_matches)} 场历史赛事...")
        results = []
        total_profit = 0
        wins = 0
        
        for match in historical_matches:
            res = self.simulate_match(match)
            results.append(res)
            total_profit += res["profit"]
            if res["status"] == "WIN":
                wins += 1
                
        total_matches = len(historical_matches)
        win_rate = wins / total_matches if total_matches > 0 else 0
        roi = total_profit / (total_matches * 100) if total_matches > 0 else 0
        
        report = {
            "total_simulated": total_matches,
            "wins": wins,
            "win_rate": round(win_rate, 3),
            "total_profit": round(total_profit, 2),
            "roi": round(roi, 3),
            "details": results
        }
        
        logger.info(f"📊 时光机报告: 胜率 {win_rate*100:.1f}%, ROI {roi*100:.1f}%, 净利 {total_profit}")
        return report
