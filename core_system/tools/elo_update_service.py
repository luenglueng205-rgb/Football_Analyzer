# -*- coding: utf-8 -*-
"""
ELO Update Service — 赛后 ELO 自动更新服务
============================================

集中管理赛后 ELO 更新逻辑，供 ExperienceLoop 和 Workflow 调用。

调用链：
  ExperienceLoop.run_daily_loop()
      └→ ELOUpdateService.update_results()   ← 每日批量更新

  MentorWorkflow.run() (post_match)
      └→ ELOUpdateService.update_single()     ← 单场实时更新

更新后自动持久化到 data/elo/ratings.json + history.json
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from core_system.tools.elo_storage import ELOStorage
from core_system.tools.paths import data_dir

logger = logging.getLogger(__name__)

# 默认 ELO 存储目录，指向 workspace/data/elo
_DEFAULT_ELO_DIR = os.path.join(data_dir(), "elo")


class ELOUpdateService:
    """
    ELO 赛后更新服务。

    支持两种模式：
    1. 批量更新（ExperienceLoop 每日调用）
    2. 单场更新（MentorWorkflow赛后实时调用）

    自动跳过：
    - 结果为 UNKNOWN 或空
    - 主客队相同
    - 已处理过的比赛（通过 match_id 去重）
    """

    def __init__(
        self,
        elo_dir: str = _DEFAULT_ELO_DIR,
        k_factor: float = 20.0,
        home_advantage: float = 65.0,
    ):
        self._elo_dir = elo_dir

        # 延迟导入避免循环依赖
        self._elo_class = None
        self._storage_class = None

        # 缓存的 ELO 系统和存储（延迟初始化）
        self._elo: Optional[Any] = None
        self._storage: Optional[Any] = None

        # 已更新比赛 ID（内存去重，防止单次运行中重复更新）
        self._updated_ids: set = set()

        # ELO 参数
        self._k_factor = k_factor
        self._home_advantage = home_advantage

    # ─────────────────────────────────────────────────────────────
    #  懒加载 ELO 系统
    # ─────────────────────────────────────────────────────────────

    def _ensure_elo(self) -> Tuple[Any, Any]:
        """
        确保 ELO 系统和存储已初始化。

        Returns:
            (elo_system, storage)
        """
        if self._elo is None or self._storage is None:
            from tools.elo_rating import ELORatingSystem
            from tools.elo_storage import ELOStorage

            self._elo = ELORatingSystem(
                k_factor=self._k_factor,
                home_advantage=self._home_advantage,
            )
            self._storage = ELOStorage(base_dir=self._elo_dir)
            loaded = self._storage.load(self._elo)
            logger.info(f"[ELO Update] 初始化完成，{loaded} 支球队 ELO 已加载")

        return self._elo, self._storage

    # ─────────────────────────────────────────────────────────────
    #  核心更新方法
    # ─────────────────────────────────────────────────────────────

    def update_single(
        self,
        home: str,
        away: str,
        result: str,
        match_id: Optional[str] = None,
        date_str: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        更新单场比赛后的 ELO 评分。

        Args:
            home: 主队名称
            away: 客队名称
            result: "H"（主胜）/"D"（平局）/"A"（客胜）
            match_id: 比赛 ID（用于去重）
            date_str: 比赛日期（如 "2026-04-25"）

        Returns:
            {"home_elo_before": float, "away_elo_before": float,
             "home_elo_after": float, "away_elo_after": float,
             "home_change": float, "away_change": float}
            或 None（跳过/无效）
        """
        elo, storage = self._ensure_elo()

        # ── 去重检查 ────────────────────────────────────────────
        if match_id and match_id in self._updated_ids:
            logger.debug(f"[ELO Update] 跳过重复比赛: {match_id}")
            return None

        # ── 有效性检查 ──────────────────────────────────────────
        if result not in ("H", "D", "A"):
            logger.debug(f"[ELO Update] 无效结果 '{result}'，跳过: {home} vs {away}")
            return None

        if not home or not away or home == away:
            logger.debug(f"[ELO Update] 无效球队，跳过: {home} vs {away}")
            return None

        # ── 记录更新前 ELO ─────────────────────────────────────
        elo_before_h = elo.ratings.get(home, elo.default_elo)
        elo_before_a = elo.ratings.get(away, elo.default_elo)

        # ── 执行 ELO 更新 ──────────────────────────────────────
        try:
            change = elo.update_match(home, away, result)
        except Exception as e:
            logger.warning(f"[ELO Update] 更新失败: {home} vs {away} → {e}")
            return None

        # ── 持久化 ──────────────────────────────────────────────
        history_record = {
            "home": home,
            "away": away,
            "result": result,
            "home_elo_before": round(elo_before_h, 1),
            "away_elo_before": round(elo_before_a, 1),
            "home_elo_after": change["home_new"],
            "away_elo_after": change["away_new"],
            "home_change": change["home_change"],
            "away_change": change["away_change"],
            "date": date_str or "",
            "match_id": match_id or "",
        }

        storage.save(elo, updated_matches=[history_record])

        if match_id:
            self._updated_ids.add(match_id)

        logger.info(
            f"[ELO Update] {home}({elo_before_h:.0f}) vs {away}({elo_before_a:.0f}) "
            f"→ {result} | "
            f"{home}: {change['home_change']:+.1f}({change['home_new']:.0f}), "
            f"{away}: {change['away_change']:+.1f}({change['away_new']:.0f})"
        )

        return change

    def update_results(
        self,
        results: List[Dict],
        date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        批量更新每日赛果后的 ELO。

        Args:
            results: 比赛结果列表
                [{"home_team": str, "away_team": str,
                  "score_ft": str, "match_id": str, ...}, ...]
            date_str: 比赛日期

        Returns:
            {
                "processed": int,    # 成功处理场次
                "skipped": int,      # 跳过场次
                "updates": [dict],   # 每场更新详情
                "elo_snapshot": {"top": [...], "total_teams": int}
            }
        """
        elo, storage = self._ensure_elo()

        out = {
            "processed": 0,
            "skipped": 0,
            "updates": [],
            "elo_snapshot": None,
        }

        for match in results:
            home = str(match.get("home_team") or match.get("home") or "").strip()
            away = str(match.get("away_team") or match.get("away") or "").strip()
            match_id = str(match.get("match_id") or match.get("fid") or "")
            score = match.get("score_ft") or match.get("score") or ""

            # 从比分推导结果
            result = self._score_to_result(score)

            if result is None:
                out["skipped"] += 1
                continue

            change = self.update_single(
                home=home,
                away=away,
                result=result,
                match_id=match_id,
                date_str=date_str,
            )

            if change:
                out["processed"] += 1
                out["updates"].append({
                    "home": home,
                    "away": away,
                    "result": result,
                    "score": score,
                    **change,
                })
            else:
                out["skipped"] += 1

        # 生成 ELO 快照
        rankings = elo.get_rankings(top_n=20)
        out["elo_snapshot"] = {
            "top": rankings,
            "total_teams": len(elo.ratings),
            "date": date_str or "",
        }

        logger.info(
            f"[ELO Update] 批量更新完成: {out['processed']} 场处理, "
            f"{out['skipped']} 场跳过, 共 {len(elo.ratings)} 支球队 ELO"
        )
        return out

    # ─────────────────────────────────────────────────────────────
    #  查询 API
    # ─────────────────────────────────────────────────────────────

    def get_rating(self, team: str) -> Dict[str, Any]:
        """查询球队当前 ELO。"""
        elo, _ = self._ensure_elo()
        return elo.get_rating(team)

    def get_probabilities(self, home: str, away: str) -> Dict[str, float]:
        """查询两队对碰的胜平负概率（基于当前 ELO）。"""
        elo, _ = self._ensure_elo()
        return elo.to_probabilities(home, away)

    def get_rankings(self, top_n: int = 20) -> List[Dict]:
        """查询 ELO 排名。"""
        elo, _ = self._ensure_elo()
        return elo.get_rankings(top_n=top_n)

    def get_form_divergence(self, team: str) -> Dict[str, Any]:
        """检测球队状态与实力的背离（价值信号）。"""
        elo, _ = self._ensure_elo()
        return elo.detect_form_vs_rating_divergence(team)

    # ─────────────────────────────────────────────────────────────
    #  内部工具
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _score_to_result(score_str: str) -> Optional[str]:
        """
        比分字符串 → 标准结果。

        支持格式： "2-1", "1:1", "0-0", "2", "1-2"
        """
        if not score_str:
            return None

        try:
            # 尝试 "X-Y" 格式
            for sep in ("-", ":"):
                if sep in str(score_str):
                    parts = str(score_str).split(sep)
                    if len(parts) == 2:
                        h = int(parts[0].strip())
                        a = int(parts[1].strip())
                        if h > a:
                            return "H"
                        elif h < a:
                            return "A"
                        else:
                            return "D"
        except (ValueError, IndexError):
            pass

        return None

    # ─────────────────────────────────────────────────────────────
    #  统计/调试
    # ─────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """获取 ELO 系统统计信息（调试用）。"""
        elo, _ = self._ensure_elo()
        return {
            "total_teams": len(elo.ratings),
            "total_matches_processed": sum(elo.match_count.values()) // 2,
            "elo_mean": round(sum(elo.ratings.values()) / max(len(elo.ratings), 1), 1),
            "elo_range": (
                round(min(elo.ratings.values()), 1),
                round(max(elo.ratings.values()), 1),
            )
            if elo.ratings
            else (1500.0, 1500.0),
            "storage_dir": self._elo_dir,
        }
