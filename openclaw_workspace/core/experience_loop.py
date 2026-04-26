# -*- coding: utf-8 -*-
"""
Experience Loop — 赛果→反思→ELO更新→记忆闭环
============================================

系统自我进化的核心闭环：

1. 获取赛果（DataGateway）
2. 与历史预测对比（MemoryManager / episodic.json）
3. 调用 AfterActionReviewAgent 生成反思
4. 将教训写入动态经验库（DYNAMIC_EXPERIENCE.md）
5. 将教训写入 ChromaDB 长期记忆（MemoryManager）
6. **更新 ELO 评分（ELOUpdateService）** ← P0-3
7. 通过 EventBus 广播进化事件

这个闭环使系统具备真正的"学习能力"——每一场比赛的结果都会变成未来的决策依据。
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ExperienceLoop:
    """
    赛果 → 反思 → ELO更新 → 记忆 闭环控制器。

    真正的学习闭环：
    1. 获取赛果（DataGateway）
    2. 与历史预测对比（MemoryManager / episodic.json）
    3. 调用 AfterActionReviewAgent 生成反思
    4. 将教训写入动态经验库（DYNAMIC_EXPERIENCE.md）
    5. 将教训写入 ChromaDB 长期记忆（MemoryManager）
    6. **更新 ELO 评分（ELOUpdateService）** ← P0-3 新增
    7. 通过 EventBus 广播进化事件
    """

    def __init__(self, data_gateway=None, memory_manager=None, elo_update_service=None):
        self._gw = data_gateway
        self._mm = memory_manager
        self._elo_svc = elo_update_service  # 延迟初始化

    def _get_gateway(self):
        """延迟初始化 DataGateway"""
        if self._gw is None:
            try:
                from core.data_gateway import DataGateway
                self._gw = DataGateway()
            except Exception as e:
                logger.error("DataGateway 初始化失败: %s", e)
                return None
        return self._gw

    def _get_memory_manager(self):
        """延迟初始化 MemoryManager"""
        if self._mm is None:
            try:
                from tools.memory_manager import MemoryManager
                self._mm = MemoryManager()
            except Exception as e:
                logger.warning("MemoryManager 初始化失败: %s", e)
                return None
        return self._mm

    # ═══════════════════════════════════════════════════════════════════
    #  主入口：同步版本
    # ═══════════════════════════════════════════════════════════════════

    def run_daily_loop(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        执行一天的完整经验闭环。
        适合 daemon 或 cron 调用。

        返回：
        {
            "date": "2026-04-24",
            "results_fetched": int,
            "predictions_matched": int,
            "lessons_generated": int,
            "lessons": [str],
            "errors": [str],
        }
        """
        target_date = target_date or date.today().isoformat()
        result = {
            "date": target_date,
            "results_fetched": 0,
            "predictions_matched": 0,
            "lessons_generated": 0,
            "lessons": [],
            "errors": [],
        }

        # 1. 获取赛果
        gw = self._get_gateway()
        if not gw:
            result["errors"].append("DataGateway 不可用")
            return result

        results_resp = gw.get_results_sync(target_date)
        if not results_resp.get("ok"):
            result["errors"].append(f"获取赛果失败: {results_resp.get('error', '')}")
            return result

        results = (results_resp.get("data") or {}).get("results") or []
        result["results_fetched"] = len(results)
        if not results:
            logger.info("[ExpLoop] %s 无赛果", target_date)
            return result

        # 2. 匹配历史预测并生成反思
        mm = self._get_memory_manager()

        for match in results:
            match_id = match.get("match_id", "")
            home = match.get("home_team", "")
            away = match.get("away_team", "")
            home_score = match.get("home_score")
            away_score = match.get("away_score")
            actual_result = self._score_to_result(home_score, away_score)

            # 查找该比赛的预测
            prediction = self._find_prediction(mm, match_id, home, away, target_date)

            if prediction is None:
                continue

            result["predictions_matched"] += 1

            # 判断预测是否正确
            is_correct = (prediction.get("predicted_result") == actual_result)

            match_data = {
                "match_id": match_id,
                "home": home,
                "away": away,
                "score": f"{home_score}:{away_score}",
                "actual_result": actual_result,
            }

            # 3. 写入 episodic memory
            self._save_episodic(mm, match_data, prediction, is_correct)

            # 4. 生成反思（仅在预测错误时深入反思）
            if not is_correct:
                lesson = self._quick_reflection(match_data, prediction)
                if lesson:
                    result["lessons"].append(lesson)
                    result["lessons_generated"] += 1

                    # 5. 写入动态经验库
                    self._save_to_experience_doc(lesson)

                    # 6. 写入 ChromaDB
                    self._save_to_vector_db(mm, home, away, lesson, target_date)

        # 6. 更新 ELO 评分（P0-3 核心功能） ← 新增
        elo_result = self._update_elo_from_results(results, target_date)
        result["elo_update"] = elo_result

        # 7. 发布 EventBus 事件
        self._publish_event(result)

        logger.info(
            "[ExpLoop] %s 闭环完成: %d 赛果, %d 匹配预测, %d 教训生成, %d ELO更新",
            target_date, result["results_fetched"],
            result["predictions_matched"], result["lessons_generated"],
            elo_result.get("processed", 0),
        )
        return result

    # ═══════════════════════════════════════════════════════════════════
    #  辅助方法
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _score_to_result(home_score, away_score) -> str:
        """比分 → 标准赛果 (H/D/A)"""
        if home_score is None or away_score is None:
            return "UNKNOWN"
        h, a = int(home_score), int(away_score)
        if h > a:
            return "H"
        elif h == a:
            return "D"
        return "A"

    def _find_prediction(
        self, mm, match_id: str, home: str, away: str, target_date: str,
    ) -> Optional[Dict]:
        """在 episodic memory 中查找该比赛的预测"""
        if mm is None:
            return None

        try:
            # 使用 MemoryManager 的查询接口
            query = f"{home} vs {away} {target_date} 预测"
            memories = mm.query_episodic(query)
            if memories:
                return memories[0]
        except Exception:
            pass
        return None

    def _save_episodic(self, mm, match_data: dict, prediction: dict, is_correct: bool):
        """保存到 episodic memory"""
        if mm is None:
            return
        try:
            mm.add_episodic_memory(
                type="experience_loop",
                content=json.dumps({
                    "match": match_data,
                    "prediction": prediction,
                    "is_correct": is_correct,
                    "timestamp": datetime.now().isoformat(),
                }, ensure_ascii=False),
                metadata={
                    "match_id": match_data.get("match_id", ""),
                    "date": match_data.get("match_id", ""),
                },
            )
        except Exception as e:
            logger.debug("[ExpLoop] episodic 保存失败: %s", e)

    @staticmethod
    def _quick_reflection(match_data: dict, prediction: dict) -> str:
        """快速本地反思（不调用 LLM），提取一条精炼教训"""
        actual = match_data.get("actual_result", "?")
        predicted = prediction.get("predicted_result", "?")
        market = prediction.get("market", "胜平负")
        home = match_data.get("home", "")
        away = match_data.get("away", "")

        if actual == predicted:
            return ""  # 预测正确，无需生成教训

        lessons_map = {
            ("H", "D"): f"{home}vs{away}：预测主胜但打平。主队进攻效率可能被高估，注意区分主场优势与实际实力差距。",
            ("H", "A"): f"{home}vs{away}：预测主胜但客胜。严重低估客队或遭遇冷门。建议检查伤停、换帅等突发因素。",
            ("D", "H"): f"{home}vs{away}：预测平局但主胜。低估了主队进攻火力或客队防守薄弱。",
            ("D", "A"): f"{home}vs{away}：预测平局但客胜。低估了客队赢球决心或主队轮换。",
            ("A", "H"): f"{home}vs{away}：预测客胜但主胜。过度看好客队，忽略了主场优势。{market}盘口需谨慎。",
            ("A", "D"): f"{home}vs{away}：预测客胜但打平。客队未能兑现实力，可能存在隐藏伤停或战术保守。",
        }
        return lessons_map.get((predicted, actual), "")

    def _save_to_experience_doc(self, lesson: str):
        """追加到 DYNAMIC_EXPERIENCE.md"""
        from pathlib import Path
        doc_path = Path(__file__).resolve().parents[1] / "docs" / "DYNAMIC_EXPERIENCE.md"
        try:
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            date_str = date.today().isoformat()
            with open(doc_path, "a", encoding="utf-8") as f:
                f.write(f"\n- **[{date_str} Auto-RLHF]**: {lesson}\n")
        except Exception as e:
            logger.warning("[ExpLoop] 经验文档写入失败: %s", e)

    def _save_to_vector_db(self, mm, home: str, away: str, lesson: str, target_date: str):
        """写入 ChromaDB 向量记忆"""
        if mm is None:
            return
        try:
            mm.add_episodic_memory(
                type="lesson",
                content=f"[{target_date}] {home} vs {away}: {lesson}",
                metadata={"date": target_date, "teams": f"{home},{away}"},
            )
        except Exception as e:
            logger.debug("[ExpLoop] 向量记忆写入失败: %s", e)

    @staticmethod
    def _publish_event(result: dict):
        """发布 EventBus 事件"""
        try:
            import asyncio
            from core.event_bus import EventBus

            async def _pub():
                bus = EventBus()
                await bus.publish("experience_loop.complete", result)

            # 尝试在已有事件循环中运行
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_pub())
            except RuntimeError:
                asyncio.run(_pub())
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════
    #  ELO 更新（P0-3）
    # ═══════════════════════════════════════════════════════════════════

    def _get_elo_service(self):
        """延迟初始化 ELO 更新服务"""
        if self._elo_svc is None:
            try:
                from tools.elo_update_service import ELOUpdateService
                self._elo_svc = ELOUpdateService()
                logger.info("[ExpLoop] ELOUpdateService 初始化完成")
            except Exception as e:
                logger.warning(f"[ExpLoop] ELOUpdateService 初始化失败: {e}")
                return None
        return self._elo_svc

    def _update_elo_from_results(
        self, results: List[Dict], target_date: str
    ) -> Dict[str, Any]:
        """
        将每日赛果批量更新到 ELO 评分系统。

        这是 P0-3 的核心实现：比赛结束后，ELO 评分随之更新，
        下一次预测时用最新的 ELO 值，真正实现"学习闭环"。
        """
        elo_svc = self._get_elo_service()
        if elo_svc is None:
            return {"processed": 0, "skipped": 0, "error": "service_unavailable"}

        try:
            elo_result = elo_svc.update_results(results, date_str=target_date)
            return elo_result
        except Exception as e:
            logger.warning(f"[ExpLoop] ELO 批量更新失败: {e}")
            return {"processed": 0, "skipped": 0, "error": str(e)}

    def update_single_match_elo(
        self,
        home: str,
        away: str,
        result: str,
        match_id: Optional[str] = None,
        date_str: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        单场比赛的 ELO 更新（供 Workflow 实时调用）。

        与 update_results 的区别：
        - 传入原始 result 字符串（已确定 H/D/A），不需从比分推导
        - 更精确，适用于已知赛果的场景
        """
        elo_svc = self._get_elo_service()
        if elo_svc is None:
            return None
        try:
            return elo_svc.update_single(
                home=home,
                away=away,
                result=result,
                match_id=match_id,
                date_str=date_str,
            )
        except Exception as e:
            logger.warning(f"[ExpLoop] 单场 ELO 更新失败: {e}")
            return None


if __name__ == "__main__":
    loop = ExperienceLoop()
    print("=== Experience Loop 启动 ===")
    print("正在执行每日经验闭环...")
    result = loop.run_daily_loop()
    print(json.dumps(result, ensure_ascii=False, indent=2))
