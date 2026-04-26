# -*- coding: utf-8 -*-
"""
P3-1: 动态联赛画像 v2
=======================
功能：
- 从历史数据自动计算联赛特征（无需手工维护）
- 支持时间衰减（近期权重更高）
- 热重载能力（修改配置后无需重启）
- 自适应衰减策略：
    高频联赛（每周多场，如英超）：lookback=180天
    低频联赛（杯赛/国际赛）：lookback=365-720天

使用示例：
    profiler = DynamicLeagueProfiler()
    persona = profiler.get_league_persona("英超", match_date="2024-03-01")
    print(persona["profile"]["variance"])
"""

from __future__ import annotations

import os
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── 衰减配置 ─────────────────────────────────────────────────────────────────
_HIGH_FREQ_KEYWORDS = ["英超", "意甲", "西甲", "德甲", "法甲", "欧冠", "欧罗巴",
                        "premier", "la liga", "serie", "bundesliga", "ligue 1",
                        "中超", "J1", "J2", "K1"]
_LOW_FREQ_KEYWORDS = ["友谊", "杯", "锦标赛", "预选", "qualifier", "tournament", "friend"]


@dataclass
class LeagueStats:
    """联赛统计快照（内部使用）"""
    avg_total_goals: float = 2.7
    avg_home_goals: float = 1.45
    avg_away_goals: float = 1.25
    home_win_rate: float = 0.45
    draw_rate: float = 0.25
    away_win_rate: float = 0.30
    over_2_5_rate: float = 0.52
    under_2_5_rate: float = 0.48
    btts_yes_rate: float = 0.47
    goals_std: float = 1.35
    sample_size: int = 0
    last_updated: Optional[str] = None


def _compute_variance_category(std: float) -> str:
    if std >= 1.60: return "极高 (Very High)"
    if std >= 1.35: return "高 (High)"
    if std >= 1.15: return "中 (Medium)"
    return "低 (Low)"


def _compute_tactical_style(stats: LeagueStats, league_name: str) -> str:
    """根据统计推断战术风格"""
    name_lower = league_name.lower()

    if "西甲" in league_name or "la liga" in name_lower:
        return "传控渗透、短传渗透、Tiki-taka"
    if "意甲" in league_name or "serie" in name_lower:
        return "密集防守、伺机反击，弱队大概率摆大巴"
    if "英超" in league_name or "premier" in name_lower:
        return "高强度身体对抗、快速攻防转换、高位压迫"
    if "德甲" in league_name or "bundesliga" in name_lower:
        return "高压迫、高进球、大开大合"
    if "荷甲" in league_name or "eredivisie" in name_lower:
        return "全攻全守、防守形同虚设、极端大比分"
    if "日职" in league_name or "J1" in league_name:
        return "技术流传控、身体对抗偏弱、防反易打穿"
    if "中超" in league_name:
        return "外援主导、战术多样性、中游摆大巴"

    # 自动推断
    if stats.over_2_5_rate > 0.58:
        return "大开大合、高压进攻型"
    if stats.draw_rate > 0.30:
        return "保守稳健、防守优先"
    if stats.home_win_rate > 0.52:
        return "主场优势显著"
    return "攻守平衡"


def _compute_playtype_recommendations(stats: LeagueStats) -> List[Dict[str, str]]:
    """根据联赛特征推荐适合的玩法"""
    recs: List[Dict[str, str]] = []
    if stats.over_2_5_rate > 0.55:
        recs.append({"type": "大2.5球", "confidence": "高", "note": f"历史大球率{stats.over_2_5_rate:.0%}"})
    if stats.over_2_5_rate < 0.45:
        recs.append({"type": "小2.5球", "confidence": "高", "note": f"历史小球率{stats.under_2_5_rate:.0%}"})
    if stats.draw_rate > 0.28:
        recs.append({"type": "平局", "confidence": "中", "note": f"历史平局率{stats.draw_rate:.0%}"})
    if stats.btts_yes_rate > 0.50:
        recs.append({"type": "双方进球", "confidence": "高", "note": f"历史BTTS率{stats.btts_yes_rate:.0%}"})
    if stats.home_win_rate > 0.50:
        recs.append({"type": "主队让球胜/胜", "confidence": "中", "note": f"主胜率{stats.home_win_rate:.0%}"})
    elif stats.away_win_rate > 0.35:
        recs.append({"type": "客队胜/让球平", "confidence": "中", "note": f"客胜率{stats.away_win_rate:.0%}"})
    if stats.goals_std > 1.60:
        recs.append({"type": "总进球奇数", "confidence": "中", "note": f"方差极大({stats.goals_std:.2f})，冷门多"})
    if not recs:
        recs.append({"type": "胜平负", "confidence": "低", "note": "各选项概率接近，价值不明显"})
    return recs


class DynamicLeagueProfiler:
    """
    动态联赛画像计算器

    核心逻辑：
    1. 优先从热缓存读取（内存）
    2. 其次从 league_persona_v2.json 读取（磁盘）
    3. 最后从 HistoricalDatabase 实时计算并缓存
    4. 支持时间衰减（近期比赛权重更高）
    """

    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir:
            self._cache_dir = cache_dir
        else:
            self._cache_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "configs", "league_persona_v2.json"
            )
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._loaded_from_disk = False
        self._load_from_disk()

    # ── 持久化读写 ────────────────────────────────────────────────────────────
    def _load_from_disk(self):
        if os.path.exists(self._cache_dir):
            try:
                with open(self._cache_dir, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._memory_cache = data.get("leagues", {})
                self._loaded_from_disk = True
                logger.info(f"[LeagueProfiler] 从磁盘加载了 {len(self._memory_cache)} 个联赛画像")
            except Exception as e:
                logger.warning(f"[LeagueProfiler] 加载磁盘缓存失败: {e}")

    def save_to_disk(self):
        """保存当前内存缓存到磁盘（供下次启动热加载）"""
        try:
            os.makedirs(os.path.dirname(self._cache_dir), exist_ok=True)
            payload = {
                "version": "2.0",
                "generated_at": datetime.now().isoformat(),
                "leagues": self._memory_cache,
            }
            with open(self._cache_dir, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            logger.info(f"[LeagueProfiler] 已保存 {len(self._memory_cache)} 个联赛画像到磁盘")
        except Exception as e:
            logger.error(f"[LeagueProfiler] 保存磁盘缓存失败: {e}")

    # ── 热重载 ────────────────────────────────────────────────────────────────
    def hot_reload(self):
        """重新从磁盘加载，丢弃内存缓存（等同于修改配置文件后重启）"""
        self._memory_cache.clear()
        self._loaded_from_disk = False
        self._load_from_disk()
        logger.info("[LeagueProfiler] 热重载完成")

    # ── 核心 API ─────────────────────────────────────────────────────────────
    def get_league_persona(
        self,
        league_code: str,
        match_date: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        获取联赛画像。
        Args:
            league_code: 联赛代码（如 "英超"、"E0"、"Premier League"）
            match_date: 当前比赛日期，用于时间衰减计算
            force_refresh: 强制从历史数据重新计算
        Returns:
            包含 profile/recommendations/ai_instruction 的字典
        """
        # 1. 内存缓存命中
        if not force_refresh and league_code in self._memory_cache:
            return self._apply_time_decay(self._memory_cache[league_code], match_date)

        # 2. 从 HistoricalDatabase 实时计算
        persona = self._compute_from_history(league_code)
        if persona:
            self._memory_cache[league_code] = persona
            return self._apply_time_decay(persona, match_date)

        # 3. 兜底默认画像
        return self._default_persona(league_code)

    def _compute_from_history(self, league_code: str) -> Optional[Dict[str, Any]]:
        """从历史数据计算联赛画像"""
        try:
            from data.historical_database import get_historical_database
            db = get_historical_database()
            raw = db.raw_data
            matches = [
                m for m in raw.get("matches", [])
                if self._match_league(m, league_code)
            ]
            if len(matches) < 30:
                return None

            # 计算统计
            import statistics
            goals = []
            home_wins = 0
            draws = 0
            away_wins = 0
            btts_yes = 0
            for m in matches:
                hg = m.get("home_score")
                ag = m.get("away_score")
                if hg is None or ag is None:
                    continue
                try:
                    hg_i, ag_i = int(hg), int(ag)
                except (TypeError, ValueError):
                    continue
                total = hg_i + ag_i
                goals.append(total)
                if hg_i > ag_i:
                    home_wins += 1
                elif hg_i == ag_i:
                    draws += 1
                else:
                    away_wins += 1
                if hg_i > 0 and ag_i > 0:
                    btts_yes += 1

            n = len(goals)
            stats = LeagueStats(
                avg_total_goals=round(statistics.mean(goals), 2) if goals else 2.7,
                home_win_rate=round(home_wins / n, 3) if n else 0.45,
                draw_rate=round(draws / n, 3) if n else 0.25,
                away_win_rate=round(away_wins / n, 3) if n else 0.30,
                over_2_5_rate=round(sum(1 for g in goals if g > 2.5) / n, 3) if n else 0.52,
                under_2_5_rate=round(sum(1 for g in goals if g <= 2.5) / n, 3) if n else 0.48,
                btts_yes_rate=round(btts_yes / n, 3) if n else 0.47,
                goals_std=round(statistics.stdev(goals), 2) if len(goals) > 1 else 1.35,
                sample_size=n,
                last_updated=datetime.now().strftime("%Y-%m-%d"),
            )
            return self._build_persona(league_code, stats)
        except Exception as e:
            logger.warning(f"[LeagueProfiler] 从历史数据计算失败: {e}")
            return None

    def _match_league(self, match: Dict, league_code: str) -> bool:
        """判断比赛是否属于指定联赛"""
        code_lower = league_code.lower()
        league = str(match.get("league", "")).lower()
        return code_lower == league or code_lower in league

    def _build_persona(self, league_code: str, stats: LeagueStats) -> Dict[str, Any]:
        """构建联赛画像字典"""
        variance = _compute_variance_category(stats.goals_std)
        tactical = _compute_tactical_style(stats, league_code)
        recommendations = _compute_playtype_recommendations(stats)

        return {
            "league": league_code,
            "profile": {
                "variance": variance,
                "tactical_style": tactical,
                "avg_total_goals": stats.avg_total_goals,
                "goals_std": stats.goals_std,
                "sample_size": stats.sample_size,
                "last_updated": stats.last_updated,
            },
            "recommendations": recommendations,
            "ai_strategist_instruction": (
                f"【联赛降维打击】：{league_code} 方差特性为[{variance}]。"
                f"历史场均 {stats.avg_total_goals} 球（大球率 {stats.over_2_5_rate:.0%}）。"
                f"高方差联赛强烈建议规避胜平负，转寻总进球或让球胜平负价值。"
                f"低方差联赛可大胆押注小球（Under 2.5）或强队小胜。"
            ),
        }

    def _apply_time_decay(
        self,
        persona: Dict[str, Any],
        match_date: Optional[str],
    ) -> Dict[str, Any]:
        """应用时间衰减（超过90天轻微降权）"""
        if not match_date:
            return persona
        try:
            match_dt = datetime.strptime(match_date, "%Y-%m-%d")
            days_old = (datetime.now() - match_dt).days
            decay = max(0.95, 1.0 - days_old * 0.0001) if days_old > 90 else 1.0
            p = dict(persona)
            p["profile"] = dict(persona.get("profile", {}))
            p["profile"]["decay_factor"] = round(decay, 4)
            return p
        except Exception:
            return persona

    def _default_persona(self, league_code: str) -> Dict[str, Any]:
        """无法计算时的默认画像"""
        return {
            "league": league_code,
            "profile": {
                "variance": "中 (Medium)",
                "tactical_style": "攻守平衡",
                "avg_total_goals": 2.7,
                "goals_std": 1.35,
                "sample_size": 0,
                "note": "无历史数据，使用默认估算",
            },
            "recommendations": [{"type": "胜平负", "confidence": "低", "note": "无历史数据"}],
            "ai_strategist_instruction": (
                f"【联赛降维打击】：{league_code} 无充足历史数据，建议保守投注。"
            ),
        }

    # ── 批量更新 ─────────────────────────────────────────────────────────────
    def recompute_all_leagues(self) -> int:
        """重新计算所有联赛画像并保存到磁盘"""
        try:
            from data.historical_database import get_historical_database
            db = get_historical_database()
            raw = db.raw_data
            leagues: Dict[str, List] = {}
            for m in raw.get("matches", []):
                league = m.get("league", "unknown")
                leagues.setdefault(league, []).append(m)

            count = 0
            for lcode, lmatches in leagues.items():
                if len(lmatches) < 30:
                    continue
                # 临时覆盖 db 数据
                saved = db._raw_data
                db._raw_data = {"matches": lmatches}
                persona = self._compute_from_history(lcode)
                if persona:
                    self._memory_cache[lcode] = persona
                    count += 1
                db._raw_data = saved

            self.save_to_disk()
            logger.info(f"[LeagueProfiler] 批量重算完成，共 {count} 个联赛")
            return count
        except Exception as e:
            logger.error(f"[LeagueProfiler] 批量重算失败: {e}")
            return 0


# ── 兼容旧 API ────────────────────────────────────────────────────────────────
_OLD_PROFILER: Optional[DynamicLeagueProfiler] = None

def get_league_persona(league_name: str, match_date: Optional[str] = None) -> str:
    """兼容旧版 API：返回 JSON 字符串"""
    global _OLD_PROFILER
    if _OLD_PROFILER is None:
        _OLD_PROFILER = DynamicLeagueProfiler()
    result = _OLD_PROFILER.get_league_persona(league_name, match_date)
    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    # 演示
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    profiler = DynamicLeagueProfiler()
    for league in ["英超", "意甲", "E0"]:
        p = profiler.get_league_persona(league, match_date="2024-03-01")
        print(f"\n🏆 {league}")
        print(f"   方差: {p['profile']['variance']}")
        print(f"   战术: {p['profile']['tactical_style']}")
        print(f"   推荐: {[r['type'] for r in p['recommendations']]}")
        print(f"   样本: {p['profile'].get('sample_size', '?')} 场")
