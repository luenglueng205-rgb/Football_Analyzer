"""
Prompt Engine v1 — 分层 Prompt 注入

设计理念：
- Layer 0 (核心规则)：LOTTERY_RULES.md + 16_MARKETS_RULES.md — 不可逾越的红线
- Layer 1 (联赛画像)：根据当前联赛动态注入方差特征和策略建议
- Layer 2 (动态经验)：DYNAMIC_EXPERIENCE.md — 从实战中积累的血泪教训
- Layer 3 (临场上下文)：当前比赛、玩法、赔率 — 由调用方拼接

每个 Layer 独立加载、独立测试，组合后成为一个完整的 System Prompt。
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 默认 docs 目录
_DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")


class PromptEngine:
    """分层 Prompt 构建引擎"""

    def __init__(self, docs_dir: Optional[str] = None):
        self._docs_dir = docs_dir or _DOCS_DIR
        # 缓存已加载的文件内容，避免重复 IO
        self._cache: dict[str, str] = {}

    def _load_file(self, filename: str) -> str:
        """加载文件内容，带缓存"""
        if filename in self._cache:
            return self._cache[filename]

        path = os.path.join(self._docs_dir, filename)
        if not os.path.exists(path):
            logger.warning(f"Prompt 文件不存在: {path}")
            return ""

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            self._cache[filename] = content
            return content
        except Exception as e:
            logger.error(f"读取 Prompt 文件失败 ({filename}): {e}")
            return ""

    # ── Layer 0: 核心规则 ──────────────────────────────────────────────
    def _layer0_core_rules(self) -> str:
        """加载彩票规则 + 16 种玩法规则"""
        rules = self._load_file("LOTTERY_RULES.md")
        markets = self._load_file("16_MARKETS_RULES.md")

        parts = []
        if rules:
            parts.append("## 彩票规则（红线）\n" + rules)
        if markets:
            parts.append("\n## 16 种玩法规则\n" + markets)

        return "\n\n".join(parts)

    # ── Layer 1: 联赛画像 ──────────────────────────────────────────────
    def _layer1_league_persona(self, league_name: str) -> str:
        """根据联赛名称加载或生成联赛画像"""
        if not league_name:
            return ""

        try:
            from core.league_profiler_v2 import get_league_persona
            result = get_league_persona(league_name)

            if isinstance(result, dict):
                persona_text = result.get("persona", result.get("description", ""))
                if persona_text:
                    return f"\n## 联赛画像：{league_name}\n{persona_text}"
            elif isinstance(result, str):
                if result.strip():
                    return f"\n## 联赛画像：{league_name}\n{result}"
        except Exception as e:
            logger.warning(f"加载联赛画像失败 ({league_name}): {e}")

        return f"\n## 联赛：{league_name}\n（联赛画像加载失败，请根据你的知识库自行判断该联赛的方差特征）"

    # ── Layer 2: 动态经验 ──────────────────────────────────────────────
    def _layer2_dynamic_experience(self) -> str:
        """加载实战经验库"""
        exp = self._load_file("DYNAMIC_EXPERIENCE.md")
        if not exp:
            return ""

        return (
            "\n## 终身经验法则（Living Memory）\n"
            "以下是从真实盈亏中总结的认知准则，必须作为最高优先级的风控指令：\n\n"
            + exp
        )

    # ── 组装 ───────────────────────────────────────────────────────────
    def build(
        self,
        league_name: str = "",
        home_team: str = "",
        away_team: str = "",
    ) -> str:
        """
        构建完整的 System Prompt。

        Args:
            league_name: 联赛名称（用于注入联赛画像）
            home_team: 主队名称（上下文）
            away_team: 客队名称（上下文）

        Returns:
            完整的 System Prompt 字符串
        """
        # 角色定义
        role = (
            "你是一名顶级的 AI 彩票精算师，拥有独立思考和自主决策能力。\n"
            "你擅长足球数据分析、赔率解读、风控策略和投注优化。\n"
            "你有权决定使用哪些工具、以什么顺序使用，以及什么时候应该空仓。\n\n"
            "核心原则：\n"
            "- EV 为负的比赛，坚决空仓，不要硬凑\n"
            "- 低赔蚊子肉（< 1.40）大概率是诱盘，除非有极强反转信号\n"
            "- 宁可错过，不可错投\n"
            "- 每场比赛都要独立分析，串关不等于降低风险\n"
            "- 复式/双选是防冷门的好策略，但要计算清楚成本\n"
        )

        # 分层叠加
        layers = [
            self._layer0_core_rules(),
            self._layer1_league_persona(league_name),
            self._layer2_dynamic_experience(),
        ]

        # 过滤空层
        non_empty = [layer for layer in layers if layer.strip()]

        return role + "\n\n" + "\n\n".join(non_empty)

    def clear_cache(self):
        """清除文件缓存（用于测试或热更新规则文件）"""
        self._cache.clear()
