# -*- coding: utf-8 -*-
"""
After-Action Review Agent — 赛后复盘
======================================

对比实际赛果与系统预测，生成反思报告，写入动态经验库。

集成 EventBus：aar.complete 事件。
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class AfterActionReviewAgent:
    """赛后复盘智能体"""

    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("DEEPSEEK_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        if not api_key or api_key in {"dummy-key-for-test", "dummy_key", ""}:
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        self._exp_doc = Path(__file__).resolve().parents[1] / "docs" / "DYNAMIC_EXPERIENCE.md"

    async def generate_reflection(self, match_data: dict, prediction: dict) -> dict:
        """
        生成赛后反思。
        返回 {"success": bool, "reflection": str, "lesson": str}
        """
        if not self.client:
            return {
                "success": False,
                "reflection": "No LLM client available.",
                "lesson": "Configure API key for AAR.",
            }

        prompt = (
            "你是顶级足彩复盘分析师。\n"
            f"实际赛果: {json.dumps(match_data, ensure_ascii=False)}\n"
            f"AI赛前预测: {json.dumps(prediction, ensure_ascii=False)}\n\n"
            "请分析预测成功/失败的原因，提取一条50字以内的'血泪教训'或'成功经验'。\n"
            '返回 JSON：{"success": true/false, "reflection": "详细复盘...", "lesson": "精炼教训..."}'
        )

        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            result = json.loads(resp.choices[0].message.content)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("AAR generate_reflection failed: %s", e)
            result = {"success": False, "reflection": str(e), "lesson": "解析失败"}

        # 发布事件
        await self._publish_event(result)
        return result

    async def save_lesson(self, lesson: str) -> bool:
        """追加经验教训到动态经验库"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        line = f"\n- **[{date_str} Auto-RLHF]**: {lesson}\n"
        try:
            self._exp_doc.parent.mkdir(parents=True, exist_ok=True)
            with open(self._exp_doc, "a", encoding="utf-8") as f:
                f.write(line)
            logger.info("[AAR] 经验已保存: %s", lesson[:50])
            return True
        except Exception as e:
            logger.error("AAR save lesson failed: %s", e)
            return False

    async def _publish_event(self, result: dict):
        try:
            from core.event_bus import EventBus
            bus = EventBus()
            await bus.publish("aar.complete", {
                "success": result.get("success", False),
                "lesson": result.get("lesson", ""),
            })
        except Exception:
            pass
