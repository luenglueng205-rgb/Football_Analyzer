# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - Learning Engine
学习引擎模块

功能:
- 从错误中学习
- 策略自适应优化
- 置信度调整
"""

import os
import json
import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict, field
from collections import defaultdict
import math


@dataclass
class LearningRecord:
    """学习记录"""
    record_id: str
    timestamp: str
    event_type: str  # bet_result, pattern_update, strategy_adjustment
    subject: str
    before_state: Dict[str, Any]
    after_state: Dict[str, Any]
    learning_outcome: str
    effectiveness_score: float  # 0-1


@dataclass
class StrategyAdjustment:
    """策略调整"""
    adjustment_id: str
    timestamp: str
    strategy_id: str
    adjustment_type: str  # parameter, threshold, weight
    parameter_name: str
    old_value: Any
    new_value: Any
    reason: str
    expected_impact: str


@dataclass
class ConfidenceAdjustment:
    """置信度调整"""
    adjustment_id: str
    timestamp: str
    target_type: str  # league, team, strategy, pattern
    target_id: str
    old_confidence: float
    new_confidence: float
    reason: str
    evidence: List[str] = field(default_factory=list)


class LearningEngine:
    """学习引擎"""
    
    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            storage_dir = os.path.join(os.path.dirname(base_dir), "data", "memory")
        
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        
        self.learning_file = os.path.join(storage_dir, "learning_records.json")
        self.adjustments_file = os.path.join(storage_dir, "strategy_adjustments.json")
        self.confidence_file = os.path.join(storage_dir, "confidence_adjustments.json")
        self.config_file = os.path.join(storage_dir, "learning_config.json")
        
        self.learning_records = self._load_json(self.learning_file, {"records": []})
        self.adjustments = self._load_json(self.adjustments_file, {"adjustments": []})
        self.confidence_changes = self._load_json(self.confidence_file, {"changes": []})
        self.config = self._load_json(self.config_file, self._default_config())
    
    def _default_config(self) -> Dict[str, Any]:
        return {
            "learning_rate": 0.1,
            "min_confidence_delta": 0.05,
            "max_confidence": 0.95,
            "min_confidence": 0.2,
            "consecutive_win_bonus": 0.02,
            "consecutive_loss_penalty": 0.05,
            "pattern_validity_window": 30,  # 天
            "auto_adjust_threshold": 5,  # 最小样本数
            "enabled": True
        }
    
    def _load_json(self, filepath: str, default: Any = None) -> Any:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default if default is not None else {}
    
    def _save_json(self, filepath: str, data: Any) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def learn_from_result(self,
                         record_id: str,
                         result: str,
                         expected_outcome: Optional[str] = None) -> LearningRecord:
        """从结果中学习"""
        record_id = f"lr_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        learning_outcome = ""
        effectiveness = 0.5
        before_state = {}
        after_state = {}
        
        if result == "win":
            learning_outcome = "投注成功，策略有效"
            effectiveness = 1.0
        elif result == "loss":
            learning_outcome = "投注失败，需要分析原因"
            effectiveness = 0.0
        else:
            learning_outcome = "投注待定，暂不调整"
            effectiveness = 0.5
        
        learning = LearningRecord(
            record_id=record_id,
            timestamp=datetime.datetime.now().isoformat(),
            event_type="bet_result",
            subject=record_id,
            before_state=before_state,
            after_state=after_state,
            learning_outcome=learning_outcome,
            effectiveness_score=effectiveness
        )
        
        self.learning_records["records"].append(asdict(learning))
        self._save_json(self.learning_file, self.learning_records)
        
        return learning
    
    def adjust_confidence(self,
                         target_type: str,
                         target_id: str,
                         adjustment: float,
                         reason: str,
                         evidence: Optional[List[str]] = None) -> ConfidenceAdjustment:
        """调整置信度"""
        adjustment_id = f"ca_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 获取当前置信度
        current_confidence = self._get_current_confidence(target_type, target_id)
        old_confidence = current_confidence
        
        # 计算新置信度
        new_confidence = current_confidence + adjustment
        new_confidence = max(self.config["min_confidence"], 
                           min(self.config["max_confidence"], new_confidence))
        
        # 更新实际置信度
        self._update_confidence(target_type, target_id, new_confidence)
        
        change = ConfidenceAdjustment(
            adjustment_id=adjustment_id,
            timestamp=datetime.datetime.now().isoformat(),
            target_type=target_type,
            target_id=target_id,
            old_confidence=old_confidence,
            new_confidence=new_confidence,
            reason=reason,
            evidence=evidence or []
        )
        
        self.confidence_changes["changes"].append(asdict(change))
        self._save_json(self.confidence_file, self.confidence_changes)
        
        return change
    
    def _get_current_confidence(self, target_type: str, target_id: str) -> float:
        """获取当前置信度"""
        # 这里需要从实际存储中读取
        return 0.5  # 默认值
    
    def _update_confidence(self, target_type: str, target_id: str, confidence: float) -> None:
        """更新置信度"""
        # 这里需要更新实际存储
        pass
    
    def analyze_consecutive_results(self,
                                   records: List[Dict[str, Any]],
                                   target_id: str) -> Dict[str, Any]:
        """分析连续结果"""
        # 查找相关记录
        relevant = [r for r in records 
                   if r.get("analysis_context", {}).get("target_id") == target_id
                   or r.get("league") == target_id
                   or r.get("bet_type") == target_id]
        
        if not relevant:
            return {}
        
        # 分析最近结果
        recent = relevant[:10]
        outcomes = [r.get("result") for r in recent]
        
        # 统计连续
        consecutive_wins = 0
        consecutive_losses = 0
        current_streak = 0
        current_type = None
        
        for outcome in outcomes:
            if outcome == current_type:
                current_streak += 1
            else:
                if current_type == "win":
                    consecutive_wins = max(consecutive_wins, current_streak)
                elif current_type == "loss":
                    consecutive_losses = max(consecutive_losses, current_streak)
                current_type = outcome
                current_streak = 1
        
        # 处理最后一个
        if current_type == "win":
            consecutive_wins = max(consecutive_wins, current_streak)
        elif current_type == "loss":
            consecutive_losses = max(consecutive_losses, current_streak)
        
        # 计算胜率
        wins = outcomes.count("win")
        total = len(outcomes)
        win_rate = wins / total if total > 0 else 0
        
        return {
            "target_id": target_id,
            "total_records": total,
            "wins": wins,
            "losses": outcomes.count("loss"),
            "pending": outcomes.count("pending"),
            "win_rate": win_rate,
            "max_consecutive_wins": consecutive_wins,
            "max_consecutive_losses": consecutive_losses,
            "needs_adjustment": consecutive_losses >= 3 or win_rate < 0.4,
            "recommended_action": self._get_action(win_rate, consecutive_losses)
        }
    
    def _get_action(self, win_rate: float, consecutive_losses: int) -> str:
        """获取建议操作"""
        if consecutive_losses >= 5:
            return "立即暂停，建议全面复盘"
        elif consecutive_losses >= 3:
            return "降低投注金额，重新评估策略"
        elif win_rate < 0.4:
            return "胜率过低，需要调整策略参数"
        elif win_rate < 0.5:
            return "胜率偏低，适当减少投注"
        elif win_rate > 0.6:
            return "表现优异，可考虑增加投注"
        else:
            return "维持现状，继续观察"
    
    def adaptive_optimize(self,
                         strategy_id: str,
                         recent_records: List[Dict[str, Any]]) -> List[StrategyAdjustment]:
        """自适应优化策略"""
        if not self.config["enabled"]:
            return []
        
        adjustments = []
        
        # 分析策略表现
        strategy_records = [r for r in recent_records
                          if r.get("analysis_context", {}).get("strategy_id") == strategy_id]
        
        if len(strategy_records) < self.config["auto_adjust_threshold"]:
            return adjustments
        
        # 计算关键指标
        wins = len([r for r in strategy_records if r.get("result") == "win"])
        total = len(strategy_records)
        win_rate = wins / total if total > 0 else 0
        
        # 计算平均赔率
        avg_odds = sum(r.get("odds", 0) for r in strategy_records) / total if total > 0 else 0
        
        # 计算平均置信度
        avg_confidence = sum(r.get("confidence", 0.5) for r in strategy_records) / total if total > 0 else 0
        
        # 期望值
        expected_value = win_rate * avg_odds - (1 - win_rate)
        
        # 根据表现调整
        if win_rate < 0.4 and total >= 10:
            # 胜率过低，降低相关置信度
            adjustment = StrategyAdjustment(
                adjustment_id=f"sa_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                timestamp=datetime.datetime.now().isoformat(),
                strategy_id=strategy_id,
                adjustment_type="threshold",
                parameter_name="min_confidence",
                old_value=0.5,
                new_value=0.6,
                reason=f"胜率过低({win_rate:.1%})，提高最低置信度要求",
                expected_impact="减少低质量投注"
            )
            adjustments.append(adjustment)
        
        if expected_value < 0 and total >= 10:
            # 期望值为负，建议暂停
            adjustment = StrategyAdjustment(
                adjustment_id=f"sa_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                timestamp=datetime.datetime.now().isoformat(),
                strategy_id=strategy_id,
                adjustment_type="parameter",
                parameter_name="active",
                old_value=True,
                new_value=False,
                reason=f"期望值为负({expected_value:.2f})，暂停策略",
                expected_impact="避免进一步损失"
            )
            adjustments.append(adjustment)
        
        # 保存调整记录
        for adj in adjustments:
            self.adjustments["adjustments"].append(asdict(adj))
        
        self._save_json(self.adjustments_file, self.adjustments)
        
        return adjustments
    
    def bayesian_update(self,
                       prior: float,
                       evidence_win: bool,
                       odds: float) -> float:
        """贝叶斯更新置信度"""
        # 简化的贝叶斯更新
        # P(H|E) = P(E|H) * P(H) / P(E)
        
        # 似然
        if evidence_win:
            likelihood = min(1.0, odds - 1) / (odds - 0.5) if odds > 1 else 0.5
        else:
            likelihood = 1 - likelihood if evidence_win else 0.5
        
        # 归一化
        posterior = likelihood * prior / (likelihood * prior + (1 - likelihood) * (1 - prior))
        
        # 应用学习率
        learning_rate = self.config["learning_rate"]
        updated = posterior * learning_rate + prior * (1 - learning_rate)
        
        return updated
    
    def calculate_expected_value(self,
                                 probability: float,
                                 odds: float) -> float:
        """计算期望值"""
        return probability * (odds - 1) - (1 - probability) * 1
    
    def Kelly_criterion(self,
                        win_rate: float,
                        odds: float,
                        fraction: float = 0.25) -> float:
        """凯利公式计算投注比例"""
        # b = 赔率 - 1
        # p = 胜率
        # q = 1 - p
        # f* = (bp - q) / b
        
        b = odds - 1
        p = win_rate
        q = 1 - p
        
        if b <= 0:
            return 0
        
        kelly = (b * p - q) / b
        
        # 限制在安全范围
        kelly = max(0, min(kelly, fraction))
        
        return kelly
    
    def update_knowledge(self,
                        knowledge_type: str,
                        entity_id: str,
                        new_data: Dict[str, Any]) -> bool:
        """更新知识"""
        try:
            if knowledge_type == "league":
                # 更新联赛知识
                pass
            elif knowledge_type == "team":
                # 更新球队知识
                pass
            elif knowledge_type == "pattern":
                # 更新模式
                pass
            
            return True
        except Exception as e:
            print(f"更新知识失败: {e}")
            return False
    
    def get_learning_summary(self, days: int = 30) -> Dict[str, Any]:
        """获取学习摘要"""
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        
        # 近期学习记录
        recent_learning = [
            r for r in self.learning_records["records"]
            if r.get("timestamp", "") > cutoff
        ]
        
        # 近期调整
        recent_adjustments = [
            a for a in self.adjustments["adjustments"]
            if a.get("timestamp", "") > cutoff
        ]
        
        # 置信度变化
        recent_confidence = [
            c for c in self.confidence_changes["changes"]
            if c.get("timestamp", "") > cutoff
        ]
        
        # 统计
        avg_effectiveness = 0.0
        if recent_learning:
            avg_effectiveness = sum(
                r.get("effectiveness_score", 0) for r in recent_learning
            ) / len(recent_learning)
        
        # 按类型分组
        by_type = defaultdict(int)
        for a in recent_adjustments:
            by_type[a.get("adjustment_type", "unknown")] += 1
        
        return {
            "period": f"最近{days}天",
            "generated_at": datetime.datetime.now().isoformat(),
            "learning_records_count": len(recent_learning),
            "adjustments_count": len(recent_adjustments),
            "confidence_changes_count": len(recent_confidence),
            "avg_effectiveness": avg_effectiveness,
            "adjustments_by_type": dict(by_type),
            "system_health": self._assess_system_health(recent_learning, avg_effectiveness),
            "recommendations": self._generate_recommendations(
                recent_learning, recent_adjustments, avg_effectiveness
            )
        }
    
    def _assess_system_health(self, 
                            learning_records: List[Dict],
                            avg_effectiveness: float) -> str:
        """评估系统健康状态"""
        if not learning_records:
            return "未知（数据不足）"
        
        if avg_effectiveness >= 0.7:
            return "优秀"
        elif avg_effectiveness >= 0.5:
            return "良好"
        elif avg_effectiveness >= 0.3:
            return "一般"
        else:
            return "需要改进"
    
    def _generate_recommendations(self,
                                 learning_records: List[Dict],
                                 adjustments: List[Dict],
                                 effectiveness: float) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if effectiveness < 0.4:
            recommendations.append("整体表现不佳，建议暂停并进行全面复盘")
        
        if len(adjustments) > 10:
            recommendations.append("调整过于频繁，可能存在过度优化")
        
        loss_count = sum(
            1 for r in learning_records 
            if r.get("event_type") == "bet_result" and r.get("effectiveness_score", 0) == 0
        )
        
        if loss_count > 5:
            recommendations.append(f"近期失败次数较多({loss_count}次)，建议降低风险敞口")
        
        return recommendations
    
    def export_learning_data(self, filepath: str) -> bool:
        """导出学习数据"""
        try:
            data = {
                "learning_records": self.learning_records,
                "adjustments": self.adjustments,
                "confidence_changes": self.confidence_changes,
                "config": self.config,
                "export_time": datetime.datetime.now().isoformat()
            }
            self._save_json(filepath, data)
            return True
        except Exception as e:
            print(f"导出失败: {e}")
            return False
    
    def import_learning_data(self, filepath: str) -> bool:
        """导入学习数据"""
        try:
            data = self._load_json(filepath)
            
            if "learning_records" in data:
                self.learning_records = data["learning_records"]
                self._save_json(self.learning_file, self.learning_records)
            
            if "adjustments" in data:
                self.adjustments = data["adjustments"]
                self._save_json(self.adjustments_file, self.adjustments)
            
            if "confidence_changes" in data:
                self.confidence_changes = data["confidence_changes"]
                self._save_json(self.confidence_file, self.confidence_changes)
            
            if "config" in data:
                self.config = data["config"]
                self._save_json(self.config_file, self.config)
            
            return True
        except Exception as e:
            print(f"导入失败: {e}")
            return False


def create_learning_engine() -> LearningEngine:
    """创建学习引擎"""
    return LearningEngine()


if __name__ == "__main__":
    # 测试代码
    engine = create_learning_engine()
    
    # 测试凯利公式
    kelly = engine.Kelly_criterion(win_rate=0.55, odds=2.0)
    print(f"凯利公式建议投注比例: {kelly:.2%}")
    
    # 测试期望值计算
    ev = engine.calculate_expected_value(probability=0.55, odds=2.0)
    print(f"期望值: {ev:.2f}")
    
    # 测试贝叶斯更新
    new_conf = engine.bayesian_update(prior=0.6, evidence_win=True, odds=2.0)
    print(f"贝叶斯更新后置信度: {new_conf:.2f}")
    
    # 学习摘要
    summary = engine.get_learning_summary()
    print(f"\n学习摘要: {json.dumps(summary, ensure_ascii=False, indent=2)}")
