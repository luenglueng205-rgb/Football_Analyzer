import os
import json
import logging

class MLFeatureExtractor:
    """
    基于三大彩种隔离体系的机器学习特征工程管道
    负责按彩种分别解析历史比赛数据，提取出供大模型使用的“联赛/球队特性矩阵”。
    """
    
    def __init__(self, chinese_data_dir: str):
        self.data_dir = chinese_data_dir
        self.logger = logging.getLogger(__name__)
        
    def _mine_preferences_from_matches(self, matches: list, lottery_type: str) -> list:
        league_stats = {}
        for m in matches:
            league = m.get("联赛中文名", "未知联赛")
            h_goals = m.get("主队进球")
            a_goals = m.get("客队进球")
            
            if h_goals is None or a_goals is None:
                continue
                
            h_goals = int(h_goals)
            a_goals = int(a_goals)
            total_goals = h_goals + a_goals
            
            if league not in league_stats:
                league_stats[league] = {"count": 0, "home_win": 0, "draw": 0, "away_win": 0, "over_2_5": 0, "under_2_5": 0, "btts": 0}
                
            league_stats[league]["count"] += 1
            if h_goals > a_goals: league_stats[league]["home_win"] += 1
            elif h_goals == a_goals: league_stats[league]["draw"] += 1
            else: league_stats[league]["away_win"] += 1
            
            if total_goals > 2.5: league_stats[league]["over_2_5"] += 1
            else: league_stats[league]["under_2_5"] += 1
            
            if h_goals > 0 and a_goals > 0: league_stats[league]["btts"] += 1
            
        insights = []
        for lg, stats in league_stats.items():
            if stats["count"] < 100: continue
            
            draw_rate = stats["draw"] / stats["count"]
            over_rate = stats["over_2_5"] / stats["count"]
            home_win_rate = stats["home_win"] / stats["count"]
            
            # 针对不同彩种生成不同的玩法特征标签
            if lottery_type == "竞彩":
                if draw_rate > 0.28:
                    insights.append(f"[{lg}] 是竞彩的高平局联赛 (平局率 {draw_rate:.1%})，极度适合【竞彩混合过关：容错防平/让球平】。")
                if home_win_rate > 0.50:
                    insights.append(f"[{lg}] 拥有极强的主场龙效应 (主胜率 {home_win_rate:.1%})，适合【竞彩单选主胜】做稳胆。")
                    
            elif lottery_type == "北单":
                # 北单特有玩法：上下单双、胜负过关
                if over_rate > 0.55:
                    insights.append(f"[{lg}] 是北单典型大球联赛 (大球率 {over_rate:.1%})，北单玩法强烈推荐【上下单双：上单/上双】。")
                elif over_rate < 0.40:
                    insights.append(f"[{lg}] 是北单极度保守联赛，推荐【上下单双：下单/下双】或【总进球 0/1/2】。")
                if draw_rate < 0.20:
                    insights.append(f"[{lg}] 极少平局，北单强烈推荐【胜负过关 (SFGG)】玩法。")
                    
            elif lottery_type == "传统":
                # 传统足彩：核心是寻找做“胆”和“防冷”
                if home_win_rate < 0.40 and draw_rate > 0.25:
                    insights.append(f"[{lg}] 属于传统足彩的“超级冷门温床” (主胜率仅 {home_win_rate:.1%})，在任选九中绝对不能做胆，必须全包或走下盘。")
                elif home_win_rate > 0.55:
                    insights.append(f"[{lg}] 主场极其稳定，是传统足彩 14场/任九 极佳的【主胜稳胆】来源联赛。")
                    
        return insights

    def mine_all_lottery_features(self) -> str:
        """挖掘所有彩种的专属特征"""
        result = []
        
        # 1. 挖掘竞彩特征
        jc_path = os.path.join(self.data_dir, "竞彩足球_chinese_data.json")
        if os.path.exists(jc_path):
            with open(jc_path, 'r', encoding='utf-8') as f:
                jc_data = json.load(f)
                result.append("=== 🔴 竞彩足球专属策略特征 ===")
                result.extend(self._mine_preferences_from_matches(jc_data.get("matches", []), "竞彩"))
                
        # 2. 挖掘北单特征
        bd_path = os.path.join(self.data_dir, "北京单场_chinese_data.json")
        if os.path.exists(bd_path):
            with open(bd_path, 'r', encoding='utf-8') as f:
                bd_data = json.load(f)
                result.append("\n=== 🔵 北京单场专属策略特征 ===")
                result.extend(self._mine_preferences_from_matches(bd_data.get("matches", []), "北单"))
                
        # 3. 挖掘传统足彩特征
        ct_path = os.path.join(self.data_dir, "传统足彩_chinese_data.json")
        if os.path.exists(ct_path):
            with open(ct_path, 'r', encoding='utf-8') as f:
                ct_data = json.load(f)
                result.append("\n=== 🟢 传统足彩专属策略特征 ===")
                result.extend(self._mine_preferences_from_matches(ct_data.get("matches", []), "传统"))
                
        return "\n".join(result)

if __name__ == "__main__":
    extractor = MLFeatureExtractor("/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/Football/analyzer/football-lottery-analyzer/data/chinese_mapped/")
    res = extractor.mine_all_lottery_features()
    print(res)
