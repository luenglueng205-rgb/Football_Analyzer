import json

class GrandmasterRouter:
    """
    2026 AI-Native: 顶级指挥官 (The Supervisor)
    它不做任何数学计算，只负责基于大局观 (赛程、奖池、冷门预警) 
    将比赛分发给三大绝对物理隔离的体彩专家 (Jingcai, Beidan, Toto14)。
    """
    def __init__(self):
        self.min_ev = 0.05

    def dispatch_matches(self, match_data: dict, true_probs: dict, market_conditions: dict):
        print("\n==================================================")
        print(f"👑 [Grandmaster] 顶级指挥官启动: 正在审阅全局赛程与奖池...")
        print("==================================================")
        
        # 1. 足彩14场 (Toto14) 拦截：如果有巨额滚存，优先唤醒屠龙者
        toto_rollover = market_conditions.get("toto14_rollover_pool", 0)
        if toto_rollover > 10_000_000:
            print(f"   -> 💣 [Alert] 检测到足彩14场存在千万级巨额滚存！")
            print("   -> 📡 [Dispatch] 唤醒【足彩屠龙者 Agent】: 放弃竞彩蝇头小利，立即启动矩阵过滤，寻找盲点冷门博取头奖！")
            return "TOTO_14_EXPERT"
            
        # 2. 北单 (Beidan) 拦截：如果大众情绪极端失控 (必发/舆情数据异常)
        public_consensus = market_conditions.get("public_consensus_home", 0.5)
        true_home_prob = true_probs.get("HAD_H", 0.5)
        
        if public_consensus > 0.85 and true_home_prob < 0.50:
            print(f"   -> 🎭 [Alert] 检测到严重的大众情绪失控！散户在疯狂买入主队 (热度 85%)，但真实胜率仅为 {true_home_prob:.0%}。")
            print("   -> 📡 [Dispatch] 唤醒【北单反指大师 Agent】: 将此场比赛推入延迟执行队列，在停售前 5 分钟计算最终浮动 SP，重仓买入对立面！")
            return "BEIDAN_EXPERT"
            
        # 3. 竞彩 (Jingcai) 常规狙击：寻找固定赔率的错盘
        jingcai_odds = market_conditions.get("jingcai_odds", {})
        highest_ev = -1.0
        best_market = None
        
        for market, prob in true_probs.items():
            if isinstance(prob, dict): continue # 简化演示，跳过嵌套
            odds = jingcai_odds.get(market, 0)
            if odds > 0:
                ev = (prob * odds) - 1.0
                if ev > highest_ev:
                    highest_ev = ev
                    best_market = market
                    
        if highest_ev > self.min_ev:
            print(f"   -> 🎯 [Alert] 发现竞彩固定赔率漏洞！({best_market} 存在 +{highest_ev:.2%} 的正期望)")
            print("   -> 📡 [Dispatch] 唤醒【竞彩狙击手 Agent】: 准备单关或低协方差 2串1 组合出票。")
            return "JINGCAI_EXPERT"
            
        print("   -> 🛑 [Pass] 全局扫描完毕，当前无任何符合体彩三大专家出手标准的投资标的。")
        return "NO_ACTION"

if __name__ == "__main__":
    router = GrandmasterRouter()
    
    print("\n>>> 场景一：足彩奖池大爆发 <<<")
    router.dispatch_matches({}, {}, {"toto14_rollover_pool": 15_000_000})
    
    print("\n>>> 场景二：北单大众情绪失控 <<<")
    router.dispatch_matches({}, {"HAD_H": 0.40}, {"public_consensus_home": 0.90})
    
    print("\n>>> 场景三：竞彩常规错盘 <<<")
    router.dispatch_matches({}, {"HAD_D": 0.35}, {"jingcai_odds": {"HAD_D": 3.20}})
