# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - Pattern Recognizer
模式识别模块

功能:
- 发现新的价值规律
- 赔率异常模式库
- 联赛特征提取
"""

import os
import json
import datetime
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict, field
from collections import defaultdict, Counter
import statistics


@dataclass
class Pattern:
    """模式数据结构"""
    pattern_id: str
    name: str
    pattern_type: str  # value, anomaly, trend, correlation
    description: str
    expected_outcome: str
    confidence: float
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    occurrence_count: int = 0
    success_count: int = 0
    avg_effect_size: float = 0.0
    first_discovered: str = ""
    last_validated: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class OddsAnomaly:
    """赔率异常"""
    anomaly_id: str
    timestamp: str
    league: str
    home_team: str
    away_team: str
    anomaly_type: str  # sudden_move, reverse, liquid
    before_odds: Dict[str, float]
    after_odds: Dict[str, float]
    movement_pct: float
    market_consensus: str
    interpretation: str = ""
    validated: bool = False


class PatternRecognizer:
    """模式识别器"""
    
    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            storage_dir = os.path.join(os.path.dirname(base_dir), "data", "memory")
        
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        
        self.patterns_file = os.path.join(storage_dir, "patterns.json")
        self.anomalies_file = os.path.join(storage_dir, "odds_anomalies.json")
        self.correlations_file = os.path.join(storage_dir, "correlations.json")
        
        self.patterns = self._load_json(self.patterns_file, {"patterns": []})
        self.anomalies = self._load_json(self.anomalies_file, {"anomalies": []})
        self.correlations = self._load_json(self.correlations_file, {"correlations": []})
    
    def _load_json(self, filepath: str, default: Any = None) -> Any:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default if default is not None else {}
    
    def _save_json(self, filepath: str, data: Any) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_pattern(self, pattern: Pattern) -> str:
        """添加模式"""
        self.patterns["patterns"].append(asdict(pattern))
        self._save_json(self.patterns_file, self.patterns)
        return pattern.pattern_id
    
    def get_pattern(self, pattern_id: str) -> Optional[Pattern]:
        """获取模式"""
        for p in self.patterns["patterns"]:
            if p["pattern_id"] == pattern_id:
                return Pattern(**p)
        return None
    
    def get_patterns_by_type(self, pattern_type: str) -> List[Pattern]:
        """按类型获取模式"""
        return [Pattern(**p) for p in self.patterns["patterns"] 
                if p.get("pattern_type") == pattern_type]
    
    def discover_value_pattern(self, 
                              records: List[Dict[str, Any]],
                              min_occurrence: int = 5) -> List[Pattern]:
        """发现价值模式"""
        discovered = []
        
        # 按联赛分组分析
        by_league = defaultdict(list)
        for r in records:
            by_league[r.get("league", "unknown")].append(r)
        
        for league, league_records in by_league.items():
            if len(league_records) < min_occurrence:
                continue
            
            # 分析胜平负分布
            results = [r.get("result") for r in league_records]
            win_count = results.count("win")
            total = len(results)
            
            # 按赔率区间分析
            odds_ranges = [(1.5, 2.0), (2.0, 2.5), (2.5, 3.0), (3.0, 4.0)]
            
            for low, high in odds_ranges:
                range_records = [r for r in league_records 
                                if low <= r.get("odds", 0) < high]
                
                if len(range_records) < 3:
                    continue
                
                range_wins = [r for r in range_records if r.get("result") == "win"]
                win_rate = len(range_wins) / len(range_records) if range_records else 0
                
                # 计算期望值
                avg_odds = statistics.mean([r.get("odds", 0) for r in range_records])
                expected_value = win_rate * avg_odds - (1 - win_rate)
                
                # 如果期望值为正，发现价值
                if expected_value > 0.1:
                    pattern_id = f"value_{league}_{low}_{high}"
                    avg_win_odds = statistics.mean([r.get("odds", 0) for r in range_wins]) if range_wins else avg_odds
                    
                    pattern = Pattern(
                        pattern_id=pattern_id,
                        name=f"{league} 联赛 {low}-{high} 赔率区间价值",
                        pattern_type="value",
                        description=f"在 {league} 联赛，赔率在 {low}-{high} 区间时，胜率为 {win_rate:.1%}，期望值为 {expected_value:.2f}",
                        conditions=[
                            {"field": "league", "operator": "equals", "value": league},
                            {"field": "odds", "operator": "between", "value": [low, high]}
                        ],
                        expected_outcome=f"胜率 {win_rate:.1%}，期望值 {expected_value:.2f}",
                        confidence=min(0.9, len(range_records) / 50),
                        occurrence_count=len(range_records),
                        success_count=len(range_wins),
                        avg_effect_size=expected_value,
                        first_discovered=datetime.datetime.now().isoformat(),
                        last_validated=datetime.datetime.now().isoformat(),
                        tags=["赔率区间", league, "价值发现"]
                    )
                    
                    self.add_pattern(pattern)
                    discovered.append(pattern)
        
        return discovered
    
    def detect_odds_anomaly(self,
                            match_data: Dict[str, Any],
                            historical_odds: Dict[str, float],
                            current_odds: Dict[str, float]) -> Optional[OddsAnomaly]:
        """检测赔率异常"""
        movements = {}
        
        for key in set(list(historical_odds.keys()) + list(current_odds.keys())):
            hist = historical_odds.get(key, 0)
            curr = current_odds.get(key, 0)
            
            if hist > 0:
                movement = (curr - hist) / hist * 100
                movements[key] = movement
        
        # 检查是否有大幅移动（>10%）
        significant_moves = {k: v for k, v in movements.items() if abs(v) > 10}
        
        if significant_moves:
            max_move_key = max(significant_moves.items(), key=lambda x: abs(x[1]))[0]
            max_move = significant_moves[max_move_key]
            
            anomaly_type = "sudden_move"
            if max_move < -15:
                anomaly_type = "reverse"  # 大幅下降可能是反向
            
            interpretation = self._interpret_odds_movement(max_move, max_move_key)
            
            anomaly = OddsAnomaly(
                anomaly_id=f"ano_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                timestamp=datetime.datetime.now().isoformat(),
                league=match_data.get("league", ""),
                home_team=match_data.get("home_team", ""),
                away_team=match_data.get("away_team", ""),
                anomaly_type=anomaly_type,
                before_odds=historical_odds,
                after_odds=current_odds,
                movement_pct=max_move,
                market_consensus=max_move_key,
                interpretation=interpretation
            )
            
            self.anomalies["anomalies"].append(asdict(anomaly))
            self._save_json(self.anomalies_file, self.anomalies)
            
            return anomaly
        
        return None
    
    def _interpret_odds_movement(self, movement_pct: float, selection: str) -> str:
        """解释赔率移动"""
        if movement_pct > 20:
            return f"{selection} 赔率大幅上升(+{movement_pct:.1f}%)，可能存在市场分歧或大户投注"
        elif movement_pct > 10:
            return f"{selection} 赔率上升(+{movement_pct:.1f}%)，市场倾向该选项"
        elif movement_pct < -20:
            return f"{selection} 赔率大幅下降({movement_pct:.1f}%)，可能存在反向价值或内幕信息"
        elif movement_pct < -10:
            return f"{selection} 赔率下降({movement_pct:.1f}%)，市场减少对该选项的投注"
        else:
            return f"{selection} 赔率小幅变化({movement_pct:.1f}%)，正常波动"
    
    def analyze_league_characteristics(self,
                                       league: str,
                                       records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析联赛特征"""
        league_records = [r for r in records if r.get("league") == league]
        
        if not league_records:
            return {}
        
        # 基本统计
        total = len(league_records)
        wins = len([r for r in league_records if r.get("result") == "win"])
        losses = len([r for r in league_records if r.get("result") == "loss"])
        
        win_rate = wins / total if total > 0 else 0
        avg_odds = statistics.mean([r.get("odds", 0) for r in league_records])
        
        # 赔率分布
        odds_list = [r.get("odds", 0) for r in league_records]
        odds_stats = {
            "mean": statistics.mean(odds_list) if odds_list else 0,
            "median": statistics.median(odds_list) if odds_list else 0,
            "stdev": statistics.stdev(odds_list) if len(odds_list) > 1 else 0,
            "min": min(odds_list) if odds_list else 0,
            "max": max(odds_list) if odds_list else 0
        }
        
        # 投注类型分布
        bet_types = Counter([r.get("bet_type") for r in league_records])
        
        # 成功率最高的投注类型
        bet_type_success = defaultdict(lambda: {"total": 0, "wins": 0})
        for r in league_records:
            bt = r.get("bet_type", "unknown")
            bet_type_success[bt]["total"] += 1
            if r.get("result") == "win":
                bet_type_success[bt]["wins"] += 1
        
        bet_type_rates = {
            bt: data["wins"] / data["total"] if data["total"] > 0 else 0
            for bt, data in bet_type_success.items()
        }
        
        best_bet_type = max(bet_type_rates.items(), key=lambda x: x[1])[0] if bet_type_rates else None
        
        # 特征总结
        characteristics = {
            "league": league,
            "total_records": total,
            "win_rate": win_rate,
            "avg_odds": avg_odds,
            "odds_distribution": odds_stats,
            "bet_types": dict(bet_types),
            "best_bet_type": best_bet_type,
            "best_bet_type_win_rate": bet_type_rates.get(best_bet_type, 0),
            "suitable_strategies": self._recommend_strategies(win_rate, odds_stats),
            "risk_level": self._assess_risk(win_rate, odds_stats.get("stdev", 0))
        }
        
        return characteristics
    
    def _recommend_strategies(self, win_rate: float, odds_stats: Dict) -> List[str]:
        """推荐策略"""
        strategies = []
        
        if win_rate > 0.55:
            strategies.append("胜率较高，可采用激进策略")
        
        if odds_stats.get("stdev", 0) > 0.5:
            strategies.append("赔率波动大，适合价值投注")
        else:
            strategies.append("赔率稳定，适合固定赔率投注")
        
        if odds_stats.get("mean", 0) > 3.0:
            strategies.append("高赔率区间，适合博冷")
        elif odds_stats.get("mean", 0) < 2.0:
            strategies.append("低赔率区间，稳健为主")
        
        return strategies
    
    def _assess_risk(self, win_rate: float, odds_volatility: float) -> str:
        """评估风险"""
        if win_rate > 0.6 and odds_volatility < 0.3:
            return "低风险"
        elif win_rate > 0.5 and odds_volatility < 0.5:
            return "中等风险"
        else:
            return "高风险"
    
    def find_correlations(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """发现相关性"""
        correlations = []
        
        # 简化版：检查置信度与结果的关系
        high_conf = [r for r in records if r.get("confidence", 0) >= 0.7]
        low_conf = [r for r in records if r.get("confidence", 0) < 0.5]
        
        if high_conf:
            high_win_rate = len([r for r in high_conf if r.get("result") == "win"]) / len(high_conf)
        else:
            high_win_rate = 0
        
        if low_conf:
            low_win_rate = len([r for r in low_conf if r.get("result") == "win"]) / len(low_conf)
        else:
            low_win_rate = 0
        
        if high_conf and low_conf:
            correlations.append({
                "type": "confidence_outcome",
                "description": "置信度与结果的相关性",
                "high_confidence_win_rate": high_win_rate,
                "low_confidence_win_rate": low_win_rate,
                "difference": high_win_rate - low_win_rate,
                "interpretation": f"高置信度({high_win_rate:.1%}) vs 低置信度({low_win_rate:.1%})"
            })
        
        # 记录相关性
        self.correlations["correlations"] = correlations
        self._save_json(self.correlations_file, self.correlations)
        
        return correlations
    
    def validate_pattern(self, pattern_id: str, 
                        new_records: List[Dict[str, Any]]) -> Tuple[bool, float]:
        """验证模式"""
        pattern = self.get_pattern(pattern_id)
        if not pattern:
            return False, 0.0
        
        # 检查条件匹配
        matched = []
        for record in new_records:
            matches = True
            for cond in pattern.conditions:
                field = cond.get("field")
                operator = cond.get("operator")
                value = cond.get("value")
                
                record_value = record.get(field)
                
                if operator == "equals":
                    if record_value != value:
                        matches = False
                elif operator == "between":
                    if not (value[0] <= record_value < value[1]):
                        matches = False
                elif operator == "greater_than":
                    if record_value <= value:
                        matches = False
                elif operator == "less_than":
                    if record_value >= value:
                        matches = False
                
                if not matches:
                    break
            
            if matches:
                matched.append(record)
        
        if not matched:
            return False, 0.0
        
        # 计算新胜率
        new_wins = len([r for r in matched if r.get("result") == "win"])
        new_win_rate = new_wins / len(matched) if matched else 0
        
        # 更新模式
        pattern.occurrence_count += len(matched)
        pattern.success_count += new_wins
        pattern.last_validated = datetime.datetime.now().isoformat()
        
        # 更新置信度
        if pattern.occurrence_count > 0:
            observed_rate = pattern.success_count / pattern.occurrence_count
            pattern.confidence = min(0.95, pattern.confidence * 0.9 + observed_rate * 0.1)
        
        # 更新patterns
        for i, p in enumerate(self.patterns["patterns"]):
            if p["pattern_id"] == pattern_id:
                self.patterns["patterns"][i] = asdict(pattern)
                break
        
        self._save_json(self.patterns_file, self.patterns)
        
        return True, new_win_rate
    
    def get_pattern_recommendations(self, 
                                    context: Dict[str, Any]) -> List[Tuple[Pattern, float]]:
        """根据上下文获取模式推荐"""
        league = context.get("league", "")
        bet_type = context.get("bet_type", "")
        odds = context.get("odds", 0)
        
        recommendations = []
        
        for p in self.patterns["patterns"]:
            score = 0.0
            
            # 检查标签匹配
            if league in p.get("tags", []):
                score += 0.3
            if bet_type in p.get("tags", []):
                score += 0.2
            
            # 检查赔率条件
            for cond in p.get("conditions", []):
                if cond.get("field") == "odds" and cond.get("operator") == "between":
                    low, high = cond.get("value", [0, 999])
                    if low <= odds < high:
                        score += 0.3
            
            # 考虑置信度和成功率
            score += p.get("confidence", 0.5) * 0.2
            
            if score > 0.3:
                recommendations.append((Pattern(**p), score))
        
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:5]
    
    def export_patterns(self, filepath: str) -> bool:
        """导出模式数据"""
        try:
            data = {
                "patterns": self.patterns,
                "anomalies": self.anomalies,
                "correlations": self.correlations,
                "export_time": datetime.datetime.now().isoformat()
            }
            self._save_json(filepath, data)
            return True
        except Exception as e:
            print(f"导出失败: {e}")
            return False


def create_pattern_recognizer() -> PatternRecognizer:
    """创建模式识别器"""
    return PatternRecognizer()


if __name__ == "__main__":
    # 测试代码
    recognizer = create_pattern_recognizer()
    
    # 模拟数据
    test_records = [
        {"league": "英超", "odds": 1.8, "result": "win", "bet_type": "胜平负", "confidence": 0.7},
        {"league": "英超", "odds": 2.2, "result": "win", "bet_type": "胜平负", "confidence": 0.6},
        {"league": "英超", "odds": 2.5, "result": "loss", "bet_type": "胜平负", "confidence": 0.5},
        {"league": "英超", "odds": 1.9, "result": "win", "bet_type": "胜平负", "confidence": 0.7},
        {"league": "英超", "odds": 2.1, "result": "win", "bet_type": "胜平负", "confidence": 0.6},
    ]
    
    # 发现价值模式
    patterns = recognizer.discover_value_pattern(test_records)
    print(f"发现 {len(patterns)} 个价值模式")
    
    for p in patterns:
        print(f"  - {p.name}: {p.expected_outcome}")
    
    # 分析联赛特征
    characteristics = recognizer.analyze_league_characteristics("英超", test_records)
    print(f"\n联赛特征: {json.dumps(characteristics, ensure_ascii=False, indent=2)}")
    
    # 检测赔率异常
    anomaly = recognizer.detect_odds_anomaly(
        {"league": "英超", "home_team": "曼联", "away_team": "切尔西"},
        {"home_win": 2.0, "draw": 3.2, "away_win": 3.5},
        {"home_win": 1.7, "draw": 3.5, "away_win": 4.2}  # 主胜大幅下降
    )
    
    if anomaly:
        print(f"\n检测到异常: {anomaly.interpretation}")
