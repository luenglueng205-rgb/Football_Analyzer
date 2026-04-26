# -*- coding: utf-8 -*-
"""
ELO Storage — ELO 评分持久化层
================================

职责：
- 将 ELORatingSystem 的 ratings/history/match_count 持久化到 JSON
- 支持增量写入（只追加新比赛，避免重复更新）
- 跨会话保持 ELO 记忆

文件结构：
  data/elo/
    ratings.json        # 当前 ELO 分（主数据）
    history.json        # 每场比赛的 ELO 变化记录（可选，用于回测）

用法：
    storage = ELOStorage(base_dir="data/elo")
    elo = ELORatingSystem()
    storage.load(elo)
    # ... 赛后：
    storage.save(elo)
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from core_system.tools.paths import data_dir

logger = logging.getLogger(__name__)

# 默认 data 子目录
_DEFAULT_ELO_DIR = os.path.join(data_dir(), "elo")


class ELOStorage:
    """
    ELO 评分持久化控制器。

    线程安全：所有写操作加锁。
    """

    def __init__(self, base_dir: str = _DEFAULT_ELO_DIR):
        self._base = Path(base_dir)
        self._lock = threading.Lock()

        # 确保目录存在
        self._base.mkdir(parents=True, exist_ok=True)

        self._ratings_path = self._base / "ratings.json"
        self._history_path = self._base / "history.json"

    # ─────────────────────────────────────────────────────────────
    #  公开 API
    # ─────────────────────────────────────────────────────────────

    def load(self, elo_system) -> int:
        """
        从 ratings.json 加载 ELO 到 ELORatingSystem 实例。

        Args:
            elo_system: ELORatingSystem 实例（会被 in-place 修改）

        Returns:
            加载的球队数量
        """
        if not self._ratings_path.exists():
            logger.info("[ELO Storage] ratings.json 不存在，初始化空 ELO")
            return 0

        try:
            with open(self._ratings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"[ELO Storage] ratings.json 读取失败: {e}，初始化空 ELO")
            return 0

        ratings_data = data.get("ratings", {})
        match_counts = data.get("match_counts", {})

        loaded = 0
        for team, elo_val in ratings_data.items():
            try:
                elo_system.ratings[team] = float(elo_val)
                elo_system.match_count[team] = int(match_counts.get(team, 0))
                loaded += 1
            except (TypeError, ValueError):
                continue

        logger.info(f"[ELO Storage] 加载 {loaded} 支球队 ELO 评分")
        return loaded

    def save(self, elo_system, updated_matches: Optional[List[Dict]] = None) -> bool:
        """
        将 ELORatingSystem 状态写入 ratings.json。

        可选：同时追加比赛记录到 history.json。

        Args:
            elo_system: ELORatingSystem 实例
            updated_matches: 触发本次保存的比赛列表（用于追加历史）
                [{"home": str, "away": str, "result": "H"/"D"/"A",
                  "home_elo_before": float, "away_elo_before": float,
                  "home_elo_after": float, "away_elo_after": float,
                  "date": str}, ...]

        Returns:
            是否保存成功
        """
        with self._lock:
            try:
                # ── ratings.json ─────────────────────────────────
                ratings_out = {team: round(float(elo), 1) for team, elo in elo_system.ratings.items()}
                counts_out = {team: int(cnt) for team, cnt in elo_system.match_count.items()}

                # 原子写入：先写临时文件再 rename
                tmp_path = self._ratings_path.with_suffix(".tmp")
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "ratings": ratings_out,
                            "match_counts": counts_out,
                            "updated_at": date.today().isoformat(),
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )
                tmp_path.replace(self._ratings_path)

                # ── history.json（追加） ───────────────────────────
                if updated_matches:
                    self._append_history(updated_matches)

                logger.debug(
                    f"[ELO Storage] 保存成功: {len(ratings_out)} 球队 "
                    f"(本次更新 {len(updated_matches or [])} 场)"
                )
                return True

            except Exception as e:
                logger.error(f"[ELO Storage] 保存失败: {e}")
                return False

    def load_history(self) -> List[Dict]:
        """
        读取完整 ELO 变化历史（用于回测/分析）。
        """
        if not self._history_path.exists():
            return []
        try:
            with open(self._history_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"[ELO Storage] history.json 读取失败: {e}")
            return []

    # ─────────────────────────────────────────────────────────────
    #  私有方法
    # ─────────────────────────────────────────────────────────────

    def _append_history(self, matches: List[Dict]) -> None:
        """追加比赛记录到 history.json（追加模式，非覆盖）。"""
        try:
            existing: List[Dict] = []
            if self._history_path.exists():
                with open(self._history_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)

            existing.extend(matches)

            # 限制历史记录大小（最多保留最近 50000 场）
            MAX_HISTORY = 50_000
            if len(existing) > MAX_HISTORY:
                existing = existing[-MAX_HISTORY:]

            with open(self._history_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.warning(f"[ELO Storage] history.json 追加失败: {e}")

    # ─────────────────────────────────────────────────────────────
    #  便捷工厂
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def load_elo_system(
        base_dir: str = _DEFAULT_ELO_DIR,
        elo_class=None,
        **elo_kwargs,
    ) -> Tuple:
        """
        一行初始化：加载已存储的 ELO 并返回 (elo_system, storage)。

        Args:
            base_dir: ELO 数据目录
            elo_class: ELORatingSystem 类（默认导入）
            **elo_kwargs: 传给 ELORatingSystem.__init__ 的参数

        Returns:
            (elo_system, storage) 元组
        """
        if elo_class is None:
            from tools.elo_rating import ELORatingSystem
            elo_class = ELORatingSystem

        elo = elo_class(**elo_kwargs)
        storage = ELOStorage(base_dir=base_dir)
        storage.load(elo)
        return elo, storage
