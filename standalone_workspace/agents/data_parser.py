# -*- coding: utf-8 -*-
"""
Data Parser Agent — 非结构化文本 → 结构化 JSON
=================================================

通过 LLM 将爬取回来的中文新闻/评论等非结构化文本，
提取为干净的 JSON 数据（伤停名单、赔率等）。

集成 EventBus：parser.complete 事件。
"""

import json
import logging
import os
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class DataParserAgent:
    """将非结构化文本解析为结构化 JSON"""

    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("DEEPSEEK_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        if not api_key or api_key in {"dummy-key-for-test", "dummy_key", ""}:
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def parse_injuries(self, team_name: str, raw_text: str) -> dict:
        """从新闻文本提取伤停名单"""
        if not self.client:
            return {"error": "Parser not initialized", "injuries": [], "raw": raw_text}

        prompt = (
            f"你是足球情报提取专家。从以下文本中提取【{team_name}】的伤病/停赛信息。\n"
            '返回 JSON：{"team": "...", "injuries": [{"player": "名", "status": "伤缺/出战成疑", "reason": "..."}]}\n'
            f"无信息则返回空列表。\n\n文本：{raw_text}"
        )
        return await self._json_parse(prompt, "injuries")

    async def parse_odds(self, home_team: str, away_team: str, raw_text: str) -> dict:
        """从非结构化文本提取赔率"""
        if not self.client:
            return {"error": "Parser not initialized", "raw": raw_text}

        prompt = (
            f"你是博彩数据提取专家。从文本中提取 {home_team} vs {away_team} 的赔率。\n"
            '返回 JSON：{"match": "...", "odds": {"home_win": null, "draw": null, "away_win": null}, '
            '"asian_handicap": null, "summary": "一句话分析"}\n'
            f"找不到具体数字就返回 null。\n\n文本：{raw_text}"
        )
        return await self._json_parse(prompt, "odds")

    # ── 内部工具 ────────────────────────────────────────────────────
    async def _json_parse(self, prompt: str, task_type: str) -> dict:
        """统一 JSON 解析调用 + EventBus 发布"""
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            result = json.loads(resp.choices[0].message.content)
        except json.JSONDecodeError:
            result = {"error": "JSON parse failed", "raw": prompt[-200:]}
        except Exception as e:
            logger.warning("Parser [%s] error: %s", task_type, e)
            result = {"error": str(e)}

        # EventBus
        await self._publish_event(task_type, result)
        return result

    async def _publish_event(self, task_type: str, result: dict):
        try:
            from core.event_bus import EventBus
            bus = EventBus()
            await bus.publish("parser.complete", {
                "task_type": task_type,
                "success": "error" not in result,
            })
        except Exception:
            pass
