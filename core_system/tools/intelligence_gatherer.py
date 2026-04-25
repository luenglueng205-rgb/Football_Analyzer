"""
重构后的情报聚合器：三个 Agent 并发执行

升级前：串行 DDGS 搜索 → 单次调用，返回 JSON 字符串
升级后：NewsAgent + InjuriesAgent + SocialAgent 并发 → 返回结构化 Dict

延迟优化：串行 3×T → 并发 max(T_news, T_injuries, T_social)

接口兼容：
- gather_match_intelligence()      同步版本（兼容旧调用）
- gather_match_intelligence_async() 异步版本（推荐给 ai_native_core 使用）
"""
import os
import sys
import asyncio
import json
import logging
from typing import Any, Dict

# 确保项目路径在 sys.path 中（与 atomic_skills.py 保持一致）
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from tools.intelligence import InjuriesAgent, NewsAgent, SocialAgent

logger = logging.getLogger(__name__)


class IntelligenceAggregator:
    """
    情报聚合器 — 协调三个 Agent 并发执行
    
    架构：
    ┌─────────────┐  ┌──────────────────┐  ┌─────────────┐
    │  NewsAgent   │  │ InjuriesAgent    │  │ SocialAgent │
    │  (新闻抓取)  │  │  (伤停信息)       │  │  (舆情情绪) │
    └──────┬──────┘  └───────┬──────────┘  └──────┬──────┘
           │                 │                    │
           └────────┬────────┴────────────────────┘
                    ▼
          IntelligenceAggregator._synthesize_signal()
                    ▼
          {news, injuries, social, overall_signal}
    """

    def __init__(self):
        self.news_agent = NewsAgent()
        self.injuries_agent = InjuriesAgent()
        self.social_agent = SocialAgent()

    async def gather_all(self, team_a: str, team_b: str) -> Dict[str, Any]:
        """
        并发执行三个 Agent，聚合结果
        
        Args:
            team_a: 主队名称
            team_b: 客队名称
            
        Returns:
            dict: {
                "news": {...},
                "injuries": {...},
                "social": {...},
                "overall_signal": {...}
            }
        """
        # 三个 Agent 并发启动
        news_task = asyncio.create_task(self.news_agent.gather(team_a, team_b))
        injuries_task = asyncio.create_task(self.injuries_agent.gather(team_a, team_b))
        social_task = asyncio.create_task(self.social_agent.gather(team_a, team_b))

        # 等待全部完成，return_exceptions 保证单个失败不阻塞整体
        news_result, injuries_result, social_result = await asyncio.gather(
            news_task, injuries_task, social_task,
            return_exceptions=True,
        )

        # 异常兜底 — 失败的 Agent 返回 error 占位，不影响其他 Agent 结果
        if isinstance(news_result, Exception):
            logger.error(f"NewsAgent 异常: {news_result}")
            news_result = {"error": str(news_result), "team_a_news": [], "team_b_news": [], "cross_news": []}
        if isinstance(injuries_result, Exception):
            logger.error(f"InjuriesAgent 异常: {injuries_result}")
            injuries_result = {"error": str(injuries_result), "team_a_injuries": [], "team_b_injuries": [], "key_players_out": []}
        if isinstance(social_result, Exception):
            logger.error(f"SocialAgent 异常: {social_result}")
            social_result = {"error": str(social_result), "team_a_sentiment": {}, "team_b_sentiment": {}, "overall_bias": "NEUTRAL"}

        return {
            "news": news_result,
            "injuries": injuries_result,
            "social": social_result,
            "overall_signal": self._synthesize_signal(news_result, injuries_result, social_result),
        }

    def _synthesize_signal(
        self,
        news: Dict[str, Any],
        injuries: Dict[str, Any],
        social: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        综合三方情报，给出整体信号
        
        该信号直接供 ai_native_core 的决策引擎使用：
        - sentiment: 舆情倾向（逆向投注参考）
        - key_absences: 关键缺阵（xG 调整输入）
        - breaking_news: 突发新闻（模型覆盖度降级）
        - confidence: 数据完整度置信度
        """
        signal: Dict[str, Any] = {
            "sentiment": social.get("overall_bias", "NEUTRAL"),
            "key_absences": injuries.get("key_players_out", []),
            "breaking_news": news.get("cross_news", []),
            "confidence": 0.7,
            "ai_strategist_instruction": self._build_ai_instruction(news, injuries, social),
        }

        # 有 Agent 失败时降低置信度
        has_error = any(
            "error" in d for d in [news, injuries, social] if isinstance(d, dict)
        )
        if has_error:
            signal["confidence"] = 0.4

        return signal

    @staticmethod
    def _build_ai_instruction(
        news: Dict[str, Any],
        injuries: Dict[str, Any],
        social: Dict[str, Any],
    ) -> str:
        """
        构建 AI 策略指令（保留原有功能，增强为三方综合）
        
        原版只输出一条 DDGS 相关指令，
        升级后综合新闻、伤停、舆情给出多维度建议。
        """
        parts = ["【多模态感知建议】："]

        # 伤停相关指令
        key_out = injuries.get("key_players_out", []) if isinstance(injuries, dict) else []
        if key_out:
            parts.append(
                f"检测到关键球员缺阵 {key_out}，"
                "必须在 Poisson 期望模型中大幅下调其球队进攻/防守系数。"
            )

        # 舆情偏差指令
        bias = social.get("overall_bias", "NEUTRAL") if isinstance(social, dict) else "NEUTRAL"
        if bias != "NEUTRAL":
            direction = "主场热门" if bias == "HOME_FAVORED" else "客场热门"
            parts.append(
                f"市场整体倾向{direction}，"
                "请评估是否存在逆向价值投注机会（Kelly 公式应降低热门方仓位）。"
            )

        # 新闻相关指令
        cross = news.get("cross_news", []) if isinstance(news, dict) else []
        if cross:
            parts.append(
                "发现涉及两队的交叉新闻，请对以上抓取到的新闻进行情感分析。"
            )

        # 天气等环境因素（原有逻辑的保留）
        parts.append(
            "如果是雨雪天气，必须大幅上调平局（Draw）或小球（Under 2.5）的发生概率。"
        )

        return " ".join(parts)


# ---------------------------------------------------------------------------
# 全局单例（懒初始化）
# ---------------------------------------------------------------------------
_gatherer: IntelligenceAggregator | None = None


def _get_gatherer() -> IntelligenceAggregator:
    """获取或创建全局单例"""
    global _gatherer
    if _gatherer is None:
        _gatherer = IntelligenceAggregator()
    return _gatherer


# ---------------------------------------------------------------------------
# 同步包装 — 兼容原有接口
# ---------------------------------------------------------------------------
def gather_match_intelligence(team_a: str, team_b: str) -> str:
    """
    同步接口：兼容原有调用方式
    
    原版签名返回 JSON 字符串，保持不变。
    内部实际并发执行三个 Agent。
    
    Args:
        team_a: 主队名称
        team_b: 客队名称
        
    Returns:
        str: JSON 字符串（保持向后兼容）
    """
    try:
        # Python 3.10+ 兼容：直接使用 asyncio.run()，
        # 它会自动创建新事件循环（无 running loop 时）
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                asyncio.run, _get_gatherer().gather_all(team_a, team_b)
            )
            result = future.result(timeout=30)

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"gather_match_intelligence 失败: {e}")
        return json.dumps(
            {"error": f"Failed to gather live intelligence: {e}. Proceed with historical data only."}
        )


# ---------------------------------------------------------------------------
# 同步字典接口 — P1-1 三个 workflow 共用
# ---------------------------------------------------------------------------
def gather_match_intelligence_dict(team_a: str, team_b: str, timeout: float = 30.0) -> Dict[str, Any]:
    """
    同步接口：返回结构化字典（非 JSON 字符串）。

    供 BeidanWorkflow / ZucaiWorkflow 等同步 workflow 调用。
    内部用 ThreadPoolExecutor + asyncio.run() 执行并发三路采集。

    Args:
        team_a: 主队名称
        team_b: 客队名称
        timeout: 超时秒数（默认 30s）

    Returns:
        {
            "news": {...},
            "injuries": {...},
            "social": {...},
            "overall_signal": {...}
        }
        若失败：{"news": {}, "injuries": {}, "social": {}, "overall_signal": {"error": str}}
    """
    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                asyncio.run, _get_gatherer().gather_all(team_a, team_b)
            )
            return future.result(timeout=timeout)
    except Exception as e:
        logger.warning(f"gather_match_intelligence_dict 失败: {e}，返回空情报")
        return {
            "news": {},
            "injuries": {},
            "social": {},
            "overall_signal": {"error": str(e), "confidence": 0.0, "sentiment": "NEUTRAL"},
        }


# ---------------------------------------------------------------------------
# 异步版本 — 推荐
# ---------------------------------------------------------------------------
async def gather_match_intelligence_async(team_a: str, team_b: str) -> Dict[str, Any]:
    """
    异步接口（推荐）
    
    推荐给 ai_native_core.py 等已运行在事件循环中的模块直接调用，
    避免同步版本的线程池开销。
    
    Args:
        team_a: 主队名称
        team_b: 客队名称
        
    Returns:
        Dict[str, Any]: 结构化情报结果
    """
    return await _get_gatherer().gather_all(team_a, team_b)
