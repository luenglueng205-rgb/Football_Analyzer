# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - Reflection Engine
反思引擎模块

功能:
- 从投注结果中学习
- 策略效果评估
- 自我纠错机制
- 生成反思日志
"""

import os
import json
import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from collections import defaultdict


@dataclass
class ReflectionEntry:
    """反思条目"""
    reflection_id: str
    timestamp: str
    trigger_type: str  # loss, win_streak, anomaly, manual
    subject: str  # 关联的策略/联赛/球队
    analysis: str  # 分析内容
    lessons: List[str] = field(default_factory=list)  # 教训列表
    adjustments: List[str] = field(default_factory=list)  # 调整建议
    confidence_impact: float = 0.0  # 置信度影响
    priority: str = "normal"  # high, normal, low


@dataclass
class StrategyEvaluation:
    """策略评估"""
    strategy_id: str
    strategy_name: str
    period_start: str
    period_end: str
    total_uses: int
    successes: int
    failures: int
    pending: int
    win_rate: float
    avg_roi: float
    max_drawdown: float
    sharpe_ratio: float
    recommendations: List[str] = field(default_factory=list)


class Reflector:
    """反思引擎"""
    
    def __init__(self, memory_system, storage_dir: Optional[str] = None):
        self.memory = memory_system
        
        if storage_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            storage_dir = os.path.join(os.path.dirname(base_dir), "data", "memory")
        
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        
        self.reflections_file = os.path.join(storage_dir, "reflections.json")
        self.evaluations_file = os.path.join(storage_dir, "strategy_evaluations.json")
        self.lessons_file = os.path.join(storage_dir, "learned_lessons.json")
        
        self.reflections = self._load_json(self.reflections_file, {"reflections": []})
        self.evaluations = self._load_json(self.evaluations_file, {"evaluations": []})
        self.lessons = self._load_json(self.lessons_file, {"lessons": []})
    
    def _load_json(self, filepath: str, default: Any = None) -> Any:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default if default is not None else {}
    
    def _save_json(self, filepath: str, data: Any) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_reflection(self, reflection: ReflectionEntry) -> str:
        """添加反思条目"""
        self.reflections["reflections"].append(asdict(reflection))
        self._save_json(self.reflections_file, self.reflections)
        return reflection.reflection_id
    
    def reflect_on_loss(self, record_id: str) -> ReflectionEntry:
        """反思失败案例"""
        # 查找记录
        record = None
        for r in self.memory.episodic.records["records"]:
            if r["record_id"] == record_id:
                record = r
                break
        
        if not record:
            raise ValueError(f"找不到记录: {record_id}")
        
        # 生成反思
        reflection_id = f"ref_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 分析可能原因
        analysis_parts = []
        lessons = []
        adjustments = []
        
        # 检查赔率
        odds = record.get("odds", 0)
        if odds < 1.8:
            analysis_parts.append("赔率偏低，风险收益比不佳")
            lessons.append("避免投注低赔率选项（<1.8）")
            adjustments.append("提高赔率阈值到1.8以上")
        
        # 检查置信度
        confidence = record.get("confidence", 0.5)
        if confidence < 0.6:
            analysis_parts.append("置信度过低")
            lessons.append("低于60%置信度的投注应避免")
            adjustments.append("建立更严格的置信度门槛")
        
        # 检查分析上下文
        context = record.get("analysis_context", {})
        if context.get("factors_checked", 0) < 3:
            analysis_parts.append("分析因素不足")
            lessons.append("应从多维度进行分析")
            adjustments.append("增加基本面、赔率、盘口等至少3个维度的分析")
        
        # 综合分析
        analysis = f"失败案例分析 ({record.get('league', '')} {record.get('home_team', '')} vs {record.get('away_team', '')}):\n"
        analysis += "\n".join([f"- {a}" for a in analysis_parts]) if analysis_parts else "- 未能识别关键风险因素"
        
        reflection = ReflectionEntry(
            reflection_id=reflection_id,
            timestamp=datetime.datetime.now().isoformat(),
            trigger_type="loss",
            subject=f"{record.get('bet_type', '')}:{record.get('bet_selection', '')}",
            analysis=analysis,
            lessons=lessons,
            adjustments=adjustments,
            confidence_impact=-0.1,
            priority="high" if len(lessons) > 0 else "normal"
        )
        
        self.add_reflection(reflection)
        
        # 提取并保存教训
        for lesson in lessons:
            self._add_lesson(lesson, "loss")
        
        return reflection
    
    def reflect_on_win_streak(self, strategy_id: str, streak_length: int = 5) -> ReflectionEntry:
        """反思连胜"""
        reflection_id = f"ref_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        strategy = self.memory.procedural.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"找不到策略: {strategy_id}")
        
        analysis = f"策略 {strategy.strategy_name} 连续成功 {streak_length} 次\n"
        analysis += "- 策略在当前市场环境下表现优异\n"
        analysis += "- 可能是市场效率暂时下降\n"
        analysis += "- 需要警惕过度自信"
        
        lessons = [
            "连胜不等于策略永久有效",
            "连胜后应适当减少仓位",
            "定期评估策略有效性"
        ]
        
        adjustments = [
            "设置连胜上限，达到后自动降低投注金额",
            "增加策略回测频率"
        ]
        
        reflection = ReflectionEntry(
            reflection_id=reflection_id,
            timestamp=datetime.datetime.now().isoformat(),
            trigger_type="win_streak",
            subject=strategy_id,
            analysis=analysis,
            lessons=lessons,
            adjustments=adjustments,
            confidence_impact=0.05,  # 小幅提升
            priority="normal"
        )
        
        self.add_reflection(reflection)
        return reflection
    
    def reflect_on_anomaly(self, anomaly_type: str, details: Dict[str, Any]) -> ReflectionEntry:
        """反思异常"""
        reflection_id = f"ref_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        analysis = f"检测到异常: {anomaly_type}\n"
        analysis += f"详情: {json.dumps(details, ensure_ascii=False)}"
        
        lessons = []
        adjustments = []
        
        if anomaly_type == "odds_movement":
            lessons.append("赔率大幅波动可能预示重要信息")
            adjustments.append("关注赔率异动的比赛")
        elif anomaly_type == "low_volume":
            lessons.append("低成交量市场容易被操纵")
            adjustments.append("避免投注低成交量比赛")
        elif anomaly_type == "line_move":
            lessons.append("盘口大幅移动可能存在信息不对称")
            adjustments.append("追踪盘口变化方向")
        
        reflection = ReflectionEntry(
            reflection_id=reflection_id,
            timestamp=datetime.datetime.now().isoformat(),
            trigger_type="anomaly",
            subject=anomaly_type,
            analysis=analysis,
            lessons=lessons,
            adjustments=adjustments,
            priority="high"
        )
        
        self.add_reflection(reflection)
        
        for lesson in lessons:
            self._add_lesson(lesson, "anomaly")
        
        return reflection
    
    def _add_lesson(self, lesson: str, source: str) -> None:
        """添加教训"""
        # 检查是否已存在
        for l in self.lessons["lessons"]:
            if l["content"] == lesson:
                l["occurrence_count"] += 1
                if source not in l.get("sources", []):
                    l.setdefault("sources", []).append(source)
                break
        else:
            self.lessons["lessons"].append({
                "content": lesson,
                "source": source,
                "sources": [source],
                "occurrence_count": 1,
                "first_seen": datetime.datetime.now().isoformat(),
                "last_seen": datetime.datetime.now().isoformat()
            })
        
        self._save_json(self.lessons_file, self.lessons)
    
    def evaluate_strategy(self, strategy_id: str, 
                         period_days: int = 30) -> StrategyEvaluation:
        """评估策略效果"""
        strategy = self.memory.procedural.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"找不到策略: {strategy_id}")
        
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=period_days)).isoformat()
        
        # 获取相关记录
        records = []
        for r in self.memory.episodic.records["records"]:
            if r.get("analysis_context", {}).get("strategy_id") == strategy_id:
                if r.get("timestamp", "") > cutoff:
                    records.append(r)
        
        if not records:
            return StrategyEvaluation(
                strategy_id=strategy_id,
                strategy_name=strategy.strategy_name,
                period_start=cutoff,
                period_end=datetime.datetime.now().isoformat(),
                total_uses=0,
                successes=0,
                failures=0,
                pending=0,
                win_rate=0.0,
                avg_roi=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                recommendations=["暂无足够数据评估"]
            )
        
        total = len(records)
        successes = len([r for r in records if r.get("result") == "win"])
        failures = len([r for r in records if r.get("result") == "loss"])
        pending = total - successes - failures
        
        win_rate = successes / total if total > 0 else 0.0
        
        # 计算ROI
        total_roi = 0.0
        for r in records:
            ev = r.get("expected_value", 0)
            if r.get("result") == "win":
                total_roi += (r.get("odds", 0) - 1) * r.get("stake", 100)
            elif r.get("result") == "loss":
                total_roi -= r.get("stake", 100)
        
        total_stake = sum(r.get("stake", 100) for r in records)
        avg_roi = total_roi / total_stake if total_stake > 0 else 0.0
        
        # 简化计算最大回撤和夏普比
        max_drawdown = abs(min(avg_roi, 0)) if avg_roi < 0 else 0.0
        sharpe_ratio = avg_roi / (max_drawdown + 0.01) if max_drawdown > 0 else avg_roi * 10
        
        # 生成建议
        recommendations = []
        if win_rate < 0.4:
            recommendations.append("胜率过低，考虑调整策略参数或暂停使用")
        if avg_roi < 0:
            recommendations.append("ROI为负，应立即停止使用该策略")
        if pending / total > 0.3:
            recommendations.append("待定比例过高，结果尚不明确")
        if win_rate > 0.6 and avg_roi > 0.1:
            recommendations.append("策略表现优异，可考虑适当增加使用频率")
        
        evaluation = StrategyEvaluation(
            strategy_id=strategy_id,
            strategy_name=strategy.strategy_name,
            period_start=cutoff,
            period_end=datetime.datetime.now().isoformat(),
            total_uses=total,
            successes=successes,
            failures=failures,
            pending=pending,
            win_rate=win_rate,
            avg_roi=avg_roi,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            recommendations=recommendations
        )
        
        self.evaluations["evaluations"].append(asdict(evaluation))
        self._save_json(self.evaluations_file, self.evaluations)
        
        return evaluation
    
    def generate_reflection_report(self, days: int = 7) -> Dict[str, Any]:
        """生成反思报告"""
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        
        # 获取近期反思
        recent_reflections = [
            r for r in self.reflections["reflections"]
            if r.get("timestamp", "") > cutoff
        ]
        
        # 统计
        by_type = defaultdict(int)
        high_priority = []
        all_lessons = []
        
        for r in recent_reflections:
            by_type[r.get("trigger_type", "unknown")] += 1
            if r.get("priority") == "high":
                high_priority.append(r)
            all_lessons.extend(r.get("lessons", []))
        
        # 获取近期统计数据
        recent_stats = self.memory.episodic.get_recent_patterns(days=days)
        overall_stats = self.memory.episodic.calculate_stats()
        
        report = {
            "period": f"最近{days}天",
            "generated_at": datetime.datetime.now().isoformat(),
            "summary": {
                "total_reflections": len(recent_reflections),
                "by_type": dict(by_type),
                "high_priority_count": len(high_priority)
            },
            "high_priority_reflections": high_priority[:5],
            "key_lessons": list(set(all_lessons))[:10],
            "betting_stats": {
                "recent": recent_stats,
                "overall": overall_stats
            },
            "recommendations": self._generate_recommendations(recent_reflections)
        }
        
        return report
    
    def _generate_recommendations(self, reflections: List[Dict]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        loss_count = sum(1 for r in reflections if r.get("trigger_type") == "loss")
        if loss_count > 3:
            recommendations.append("近期失败次数较多，建议降低投注金额")
        
        anomaly_count = sum(1 for r in reflections if r.get("trigger_type") == "anomaly")
        if anomaly_count > 0:
            recommendations.append("检测到异常情况，需密切关注市场动态")
        
        win_streak_count = sum(1 for r in reflections if r.get("trigger_type") == "win_streak")
        if win_streak_count > 2:
            recommendations.append("连胜较多，警惕策略过度拟合")
        
        return recommendations
    
    def get_lessons(self, filter_type: Optional[str] = None,
                   min_occurrences: int = 1) -> List[Dict[str, Any]]:
        """获取教训"""
        lessons = self.lessons["lessons"]
        
        if filter_type:
            lessons = [l for l in lessons if l.get("source") == filter_type]
        
        lessons = [l for l in lessons if l.get("occurrence_count", 0) >= min_occurrences]
        
        return sorted(lessons, key=lambda x: x.get("occurrence_count", 0), reverse=True)
    
    def auto_reflect(self) -> List[ReflectionEntry]:
        """自动反思 - 检查异常并生成反思"""
        results = []
        
        # 检查连续失败
        recent = self.memory.episodic.get_records(limit=10)
        losses = [r for r in recent if r.result == "loss"]
        
        if len(losses) >= 3:
            reflection_id = f"ref_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            reflection = ReflectionEntry(
                reflection_id=reflection_id,
                timestamp=datetime.datetime.now().isoformat(),
                trigger_type="loss",
                subject="continuous_losses",
                analysis=f"检测到连续{len(losses)}次失败",
                lessons=["检测到连续失败模式", "需要暂停并重新评估策略"],
                adjustments=["建议暂停投注1-2天", "检查最近失败案例的共同点"],
                priority="high"
            )
            self.add_reflection(reflection)
            results.append(reflection)
        
        # 检查连胜策略
        for strategy in self.memory.procedural.get_all_strategies():
            if strategy.usage_count >= 5:
                success_rate = strategy.success_count / strategy.usage_count
                if success_rate >= 0.8:
                    reflection = self.reflect_on_win_streak(strategy.strategy_id, 
                                                           int(strategy.usage_count * success_rate))
                    results.append(reflection)
        
        return results
    
    def export_reflections(self, filepath: str) -> bool:
        """导出反思数据"""
        try:
            data = {
                "reflections": self.reflections,
                "evaluations": self.evaluations,
                "lessons": self.lessons,
                "export_time": datetime.datetime.now().isoformat()
            }
            self._save_json(filepath, data)
            return True
        except Exception as e:
            print(f"导出失败: {e}")
            return False


# 导入需要的模块
from memory.memory_system import get_memory_system, MemorySystem


def create_reflector(memory_system: Optional[MemorySystem] = None) -> Reflector:
    """创建反思引擎"""
    if memory_system is None:
        memory_system = get_memory_system()
    return Reflector(memory_system)


if __name__ == "__main__":
    # 测试代码
    memory = get_memory_system()
    reflector = create_reflector(memory)
    
    # 创建测试记录
    record = memory.create_betting_record(
        league="英超",
        home_team="曼联",
        away_team="切尔西",
        bet_type="胜平负",
        bet_selection="胜",
        odds=2.0,
        stake=100.0,
        confidence=0.6
    )
    
    # 更新为失败
    memory.update_betting_result(record.record_id, "loss", "0-2")
    
    # 反思失败
    reflection = reflector.reflect_on_loss(record.record_id)
    print(f"反思条目: {reflection.reflection_id}")
    print(f"分析: {reflection.analysis}")
    print(f"教训: {reflection.lessons}")
    
    # 生成报告
    report = reflector.generate_reflection_report()
    print(f"\n反思报告: {json.dumps(report, ensure_ascii=False, indent=2)}")
