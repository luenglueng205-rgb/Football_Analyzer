# -*- coding: utf-8 -*-
"""
P3-2: 数据质量验证器
=====================
功能：
- 对历史比赛数据（dict 格式）进行健康度评分（0-100）
- 检查维度：完整性、准确性、一致性、时效性、唯一性
- 输出缺失字段列表、具体问题描述
- 支持批量评分和按联赛过滤

使用示例：
    validator = DataQualityValidator()
    result = validator.validate_match(match_dict)
    print(result.health_score)
"""

from __future__ import annotations

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── 核心字段定义 ───────────────────────────────────────────────────────────────
_REQUIRED_FIELDS = [
    "home_team", "away_team", "date", "league",
    "home_score", "away_score", "result",
]
_OPTIONAL_FIELDS = [
    "home_odds", "draw_odds", "away_odds",
    "round", "season", "referee", "stadium",
    "home_possession", "away_possession",
    "home_shots", "away_shots",
    "home_corners", "away_corners",
]
_ODDS_RANGE = (1.01, 100.0)   # 赔率合法范围
_SCORE_RANGE = (0, 15)        # 进失球合法范围


@dataclass
class MatchQuality:
    """单场比赛数据质量评分结果"""
    health_score: float = 100.0        # 综合健康度（0-100）
    completeness_score: float = 100.0  # 完整性（0-100）
    accuracy_score: float = 100.0      # 准确性（0-100）
    consistency_score: float = 100.0   # 一致性（0-100）
    timeliness_score: float = 100.0     # 时效性（0-100）
    uniqueness_score: float = 100.0    # 唯一性（0-100）

    missing_fields: List[str] = field(default_factory=list)
    accuracy_issues: List[str] = field(default_factory=list)
    consistency_issues: List[str] = field(default_factory=list)
    timeliness_issues: List[str] = field(default_factory=list)
    uniqueness_issues: List[str] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        return {
            "health_score": round(self.health_score, 2),
            "completeness_score": round(self.completeness_score, 2),
            "accuracy_score": round(self.accuracy_score, 2),
            "consistency_score": round(self.consistency_score, 2),
            "timeliness_score": round(self.timeliness_score, 2),
            "uniqueness_score": round(self.uniqueness_score, 2),
            "missing_fields": self.missing_fields,
            "all_issues": (
                self.accuracy_issues + self.consistency_issues
                + self.timeliness_issues + self.uniqueness_issues
            ),
        }

    def grade(self) -> str:
        """文字评级"""
        s = self.health_score
        if s >= 95:  return "A+ 优秀"
        if s >= 85:  return "A  良好"
        if s >= 70:  return "B  及格"
        if s >= 50:  return "C  较差"
        return "D  不合格"


@dataclass
class BatchQualityResult:
    """批量验证汇总结果"""
    total: int = 0
    avg_health: float = 0.0
    grade_counts: Dict[str, int] = field(default_factory=dict)
    by_league: Dict[str, float] = field(default_factory=dict)
    worst_matches: List[Tuple[str, float]] = field(default_factory=list)  # (标识, score)

    def report(self) -> str:
        lines = [
            f"{'='*50}",
            f"  数据质量批量验证报告",
            f"{'='*50}",
            f"  总样本量      : {self.total}",
            f"  平均健康度    : {self.avg_health:.1f}",
            f"  评级分布      : {json.dumps(self.grade_counts, ensure_ascii=False)}",
            f"  联赛健康度    : {json.dumps(self.by_league, ensure_ascii=False)}",
            f"  最差样本 TOP-5:",
        ]
        for i, (ident, score) in enumerate(self.worst_matches[:5], 1):
            lines.append(f"    {i}. {ident} → {score:.1f}")
        lines.append("=" * 50)
        return "\n".join(lines)


class DataQualityValidator:
    """
    历史比赛数据质量验证器
    """

    def __init__(self, strict_mode: bool = False):
        """
        Args:
            strict_mode: True 时，低分比赛会打印详细诊断信息
        """
        self.strict_mode = strict_mode

    # ── 主入口 ────────────────────────────────────────────────────────────────
    def validate_match(self, match: Dict[str, Any]) -> MatchQuality:
        """
        验证单场比赛数据质量。
        评分从 100 起步，各维度独立扣分。
        """
        q = MatchQuality()

        # 1. 完整性检查
        self._check_completeness(match, q)

        # 2. 准确性检查（赔率、比分范围）
        self._check_accuracy(match, q)

        # 3. 一致性检查（比分 ↔ result 字段一致性）
        self._check_consistency(match, q)

        # 4. 时效性检查（日期格式合法性）
        self._check_timeliness(match, q)

        # 5. 唯一性检查（简单哈希，检测重复）
        self._check_uniqueness(match, q)

        # 综合健康度 = 各维度加权平均
        q.health_score = (
            q.completeness_score  * 0.30
            + q.accuracy_score    * 0.25
            + q.consistency_score * 0.20
            + q.timeliness_score  * 0.15
            + q.uniqueness_score  * 0.10
        )
        q.health_score = max(0.0, min(100.0, q.health_score))

        if self.strict_mode and q.health_score < 70:
            ident = self._match_ident(match)
            print(f"[⚠️ 数据质量警告] {ident} 得分 {q.health_score:.1f}")
            if q.all_issues:
                for issue in q.all_issues[:5]:
                    print(f"    - {issue}")

        return q

    def validate_batch(
        self,
        matches: List[Dict[str, Any]],
        league_filter: Optional[str] = None,
    ) -> BatchQualityResult:
        """
        批量验证，返回汇总报告。
        """
        if league_filter:
            matches = [m for m in matches
                       if str(m.get("league", "")).lower() == league_filter.lower()]

        total = len(matches)
        if total == 0:
            return BatchQualityResult()

        results = [self.validate_match(m) for m in matches]
        avg_health = sum(r.health_score for r in results) / total

        # 评级分布
        grade_counts: Dict[str, int] = {}
        for r in results:
            g = r.grade()
            grade_counts[g] = grade_counts.get(g, 0) + 1

        # 按联赛分组
        league_scores: Dict[str, List[float]] = {}
        for match, result in zip(matches, results):
            league = str(match.get("league", "unknown"))
            league_scores.setdefault(league, []).append(result.health_score)
        by_league = {
            k: round(sum(v) / len(v), 1)
            for k, v in league_scores.items()
            if k != "unknown"
        }

        # 最差样本
        scored = [
            (self._match_ident(m), r.health_score)
            for m, r in zip(matches, results)
        ]
        worst = sorted(scored, key=lambda x: x[1])[:5]

        return BatchQualityResult(
            total=total,
            avg_health=round(avg_health, 2),
            grade_counts=grade_counts,
            by_league=by_league,
            worst_matches=worst,
        )

    # ── 各维度检查 ────────────────────────────────────────────────────────────
    def _check_completeness(self, match: Dict[str, Any], q: MatchQuality):
        """检查核心字段是否缺失"""
        missing = []
        for field_name in _REQUIRED_FIELDS:
            if field_name not in match or match[field_name] is None or str(match[field_name]).strip() == "":
                missing.append(field_name)
        q.missing_fields = missing
        if missing:
            # 每缺失一个核心字段 -10 分
            q.completeness_score = max(0.0, 100.0 - len(missing) * 10)
        # 额外检查赔率
        odds_missing = sum(
            1 for f in ["home_odds", "draw_odds", "away_odds"]
            if f not in match or not match[f]
        )
        if odds_missing == 3:
            q.completeness_score = max(0.0, q.completeness_score - 5)

    def _check_accuracy(self, match: Dict[str, Any], q: MatchQuality):
        """检查赔率和比分的数值合法性"""
        issues = []

        # 赔率范围
        for field_name in ["home_odds", "draw_odds", "away_odds"]:
            val = match.get(field_name)
            if val is not None:
                try:
                    v = float(val)
                    if not (_ODDS_RANGE[0] <= v <= _ODDS_RANGE[1]):
                        issues.append(f"{field_name}={v} 超出合法范围 {_ODDS_RANGE}")
                except (TypeError, ValueError):
                    issues.append(f"{field_name} 非数值: {val}")

        # 比分范围（负数为非法）
        for field_name in ["home_score", "away_score"]:
            val = match.get(field_name)
            if val is not None:
                try:
                    v = int(val)
                    if v < _SCORE_RANGE[0] or v > _SCORE_RANGE[1]:
                        issues.append(f"{field_name}={v} 超出合理范围")
                except (TypeError, ValueError):
                    issues.append(f"{field_name} 非整数: {val}")

        q.accuracy_issues = issues
        if issues:
            q.accuracy_score = max(0.0, 100.0 - len(issues) * 8)

    def _check_consistency(self, match: Dict[str, Any], q: MatchQuality):
        """检查 result 字段是否与比分一致"""
        issues = []
        try:
            hs = int(match.get("home_score", 0) or 0)
            as_ = int(match.get("away_score", 0) or 0)
            result = str(match.get("result", "")).upper().strip()
            if result == "H" and not (hs > as_):
                issues.append(f"result=H 但主队{hs}未赢")
            elif result == "A" and not (as_ > hs):
                issues.append(f"result=A 但客队{as_}未赢")
            elif result == "D" and not (hs == as_):
                issues.append(f"result=D 但比分{hs}:{as_}非平局")
        except (TypeError, ValueError):
            pass   # 已在 accuracy 检查中处理

        q.consistency_issues = issues
        if issues:
            q.consistency_score = max(0.0, 100.0 - len(issues) * 15)

    def _check_timeliness(self, match: Dict[str, Any], q: MatchQuality):
        """检查日期格式合法性"""
        issues = []
        date_str = match.get("date", "")
        if not date_str:
            issues.append("date 字段为空")
        else:
            # 支持常见格式
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S"):
                try:
                    from datetime import datetime
                    datetime.strptime(str(date_str).strip(), fmt)
                    break
                except ValueError:
                    continue
            else:
                issues.append(f"date 格式异常: {date_str}")

        q.timeliness_issues = issues
        if issues:
            q.timeliness_score = max(0.0, 100.0 - len(issues) * 20)

    def _check_uniqueness(self, match: Dict[str, Any], q: MatchQuality):
        """唯一性：基于主客队+日期的简单哈希（需外部去重表配合）"""
        # 此处只做占位，具体去重由调用方维护 seen_keys 集合
        q.uniqueness_score = 100.0

    # ── 工具 ─────────────────────────────────────────────────────────────────
    def _match_ident(self, match: Dict[str, Any]) -> str:
        return f"{match.get('date','?')} {match.get('home_team','?')} vs {match.get('away_team','?')}"

    @staticmethod
    def load_matches_from_file(filepath: str) -> List[Dict[str, Any]]:
        """从 JSON 文件加载比赛数据"""
        if not os.path.exists(filepath):
            logger.error(f"文件不存在: {filepath}")
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data.get("matches", [])
        elif isinstance(data, list):
            return data
        return []

    @staticmethod
    def load_matches_from_directory(dirpath: str) -> List[Dict[str, Any]]:
        """从目录加载所有 JSON 文件"""
        import glob
        matches = []
        for path in glob.glob(os.path.join(dirpath, "*.json")):
            matches.extend(DataQualityValidator.load_matches_from_file(path))
        return matches


if __name__ == "__main__":
    # 快速演示
    sample = {
        "home_team": "Manchester United",
        "away_team": "Liverpool",
        "date": "2024-03-01",
        "league": "Premier League",
        "home_score": 2,
        "away_score": 2,
        "result": "D",
        "home_odds": 2.10,
        "draw_odds": 3.40,
        "away_odds": 3.50,
    }
    validator = DataQualityValidator(strict_mode=True)
    r = validator.validate_match(sample)
    print(f"健康度: {r.health_score:.1f} | {r.grade()}")
    print(f"汇总: {json.dumps(r.summary(), ensure_ascii=False, indent=2)}")
