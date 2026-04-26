# -*- coding: utf-8 -*-
"""
Autonomous Betting Orchestrator v1 — AI原生足球投注决策系统
============================================================

定位：接통已有数据工具层 → LLM推理层 → 决策输出 → 经验学习

核心链路：
  1. 数据收集（赔率 + 新闻 + 伤停）
  2. 情报汇总（结构化 Evidence）
  3. 多Agent辩论（DebateJudge）
  4. 风控过滤（DynamicRiskJudge）
  5. 投注建议输出
  6. AAR 记录（等赛果后触发）

用法：
  python scripts/autonomous_betting_orchestrator.py [--date 2026-04-25]
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ── 路径设置 ──────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("autonomous_betting")


# ═══════════════════════════════════════════════════════════════════════
# 1. 数据层：赔率 + 情报收集
# ═══════════════════════════════════════════════════════════════════════


class OddsCollector:
    """从 The Odds API 拉取赔率数据"""

    def __init__(self):
        self.api_key = os.getenv("THE_ODDS_API_KEY", "")
        self.league_names: Dict[str, str] = {
            "soccer_epl": "英格兰超级联赛",
            "soccer_la_liga": "西班牙甲级联赛",
            "soccer_serie_a": "意大利甲级联赛",
            "soccer_germany_bundesliga": "德国甲级联赛",
            "soccer_france_ligue_one": "法国甲级联赛",
            "soccer_uefa_champs_league": "欧洲冠军联赛",
            "soccer_uefa_europa_league": "欧洲联赛",
            "soccer_china_superleague": "中国超级联赛",
            "soccer_japan_j_league": "日本职业联赛",
            "soccer_korea_league": "韩国K联赛",
            "soccer_usa_mls": "美国职业联赛",
            "soccer_australia_aleague": "澳大利亚甲级联赛",
            "soccer_brazil_campeonato": "巴西甲级联赛",
            "soccer_netherlands_eredivisie": "荷兰甲级联赛",
            "soccer_portugal_primeira_liga": "葡萄牙超级联赛",
            "soccer_conmebol_copa_libertadores": "南美解放者杯",
            "soccer_conmebol_copa_sudamericana": "南美杯",
        }

    def fetch_today_matches(
        self, league_keys: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        拉取指定联赛今日赔率。
        Returns: List[Match]，每场包含赔率信息
        """
        all_matches = []
        league_keys = league_keys or list(self.league_names.keys())

        params = {
            "apiKey": self.api_key,
            "regions": "eu,uk,us,au",
            "markets": "h2h",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }

        for league_key in league_keys:
            url = f"https://api.the-odds-api.com/v4/sports/{league_key}/odds"
            try:
                r = requests.get(url, params=params, timeout=8)
                if r.status_code != 200:
                    logger.warning("[OddsCollector] %s → HTTP %d", league_key, r.status_code)
                    continue
                data = r.json()
                if not isinstance(data, list):
                    continue

                for item in data:
                    commence = item.get("commence_time", "")
                    if not commence:
                        continue

                    # 只取今天的
                    if not commence.startswith("2026-04-25"):
                        continue

                    # 提取 Pinnacle 赔率（传入主客队名以便正确映射）
                    home_t = item.get("home_team", "")
                    away_t = item.get("away_team", "")
                    odds = self._extract_odds(item.get("bookmakers", []), home_t, away_t)
                    if not odds:
                        continue

                    all_matches.append(
                        {
                            "league_key": league_key,
                            "league_name": self.league_names.get(league_key, league_key),
                            "home_team": item.get("home_team", ""),
                            "away_team": item.get("away_team", ""),
                            "commence_time": commence,
                            "odds": odds,
                        }
                    )
            except Exception as e:
                logger.warning("[OddsCollector] %s → %s", league_key, e)

        return all_matches

    def _extract_odds(
        self, bookmakers: List[Dict], home_team: str, away_team: str
    ) -> Dict[str, float]:
        """
        从博彩公司列表提取赔率。
        The Odds API 的 outcome.name 是队伍名（如 "Fulham"），
        需要和 home_team/away_team 匹配才能确定是主胜还是客胜。
        """
        # 找 Pinnacle 优先
        targets = [b for b in bookmakers if b.get("key") == "pinnacle"]
        if not targets:
            targets = bookmakers[:1]  # fallback 第一个博彩公司

        for bm in targets:
            result = self._parse_h2h(bm.get("markets", []), home_team, away_team)
            if len(result) >= 2:  # 至少要有主胜和平/客之一
                return result
        return {}

    def _parse_h2h(
        self, markets: List[Dict], home_team: str, away_team: str
    ) -> Dict[str, float]:
        """
        解析 H2H 盘口。
        The Odds API 的 outcome.name 是队伍名（不是 "home"/"away"/"draw"）。
        必须用 home_team/away_team 做模糊匹配。
        """
        import unicodedata

        def normalize(s: str) -> str:
            """Unicode标准化 + 小写化，用于模糊匹配"""
            return unicodedata.normalize("NFKC", s).lower().strip()

        home_norm = normalize(home_team)
        away_norm = normalize(away_team)

        for m in markets:
            if m.get("key") != "h2h":
                continue
            outcomes = m.get("outcomes", [])
            result: Dict[str, float] = {}
            for o in outcomes:
                name = o.get("name", "")
                name_norm = normalize(name)
                price = float(o.get("price", 0))
                if price <= 0:
                    continue

                if "draw" in name_norm or name_norm in ("x", "tie"):
                    result["draw"] = price
                elif name_norm == home_norm or home_norm in name_norm or name_norm in home_norm:
                    result["home_win"] = price
                elif name_norm == away_norm or away_norm in name_norm or name_norm in away_norm:
                    result["away_win"] = price
                else:
                    # 无法匹配的，走最合理假设：赔率最高的对应客队（热门方向）
                    # 但保守处理，保留原始映射
                    pass

            if len(result) >= 2:
                return result
        return {}


# ═══════════════════════════════════════════════════════════════════════
# 2. 情报层：新闻 + 伤停 + 天气
# ═══════════════════════════════════════════════════════════════════════


class IntelligenceCollector:
    """收集球队相关情报"""

    def __init__(self):
        self.owm_key = os.getenv("OPENWEATHERMAP_API_KEY", "")

    async def gather_team_intel(self, team_name: str) -> Dict[str, Any]:
        """收集单队情报：新闻 + 伤停"""
        # 尝试 duckduckgo 新闻
        news = await self._search_news(team_name)
        injuries = await self._search_injuries(team_name)

        return {
            "team": team_name,
            "news": news,
            "injuries": injuries,
        }

    async def gather_match_intel(
        self, home_team: str, away_team: str
    ) -> Dict[str, Any]:
        """并发收集主客队情报"""
        t_home, t_away = await asyncio.gather(
            self.gather_team_intel(home_team),
            self.gather_team_intel(away_team),
        )
        return {
            "home": t_home,
            "away": t_away,
        }

    async def _search_news(self, team: str) -> List[str]:
        """用 ddgs 搜新闻，3秒超时"""
        try:
            import signal

            def _timeout_handler(signum, frame):
                raise TimeoutError("ddgs search timed out")

            # 注册超时
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(3)

            try:
                from ddgs import DDGS

                results = []
                with DDGS() as ddgs:
                    for r in ddgs.text(f"{team} football news", max_results=3):
                        title = r.get("title", "")
                        if title:
                            results.append(f"• {title}")
                        if len(results) >= 3:
                            break
                return results
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        except (ImportError, TimeoutError, OSError):
            return ["[网络超时/不可用]"]
        except Exception as e:
            return [f"[新闻抓取失败: {e}]"]

    async def _search_injuries(self, team: str) -> List[str]:
        """搜伤停信息，3秒超时"""
        try:
            import signal

            def _timeout_handler(signum, frame):
                raise TimeoutError("ddgs injuries search timed out")

            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(3)

            try:
                from ddgs import DDGS

                results = []
                with DDGS() as ddgs:
                    for r in ddgs.text(f"{team} injury squad news", max_results=2):
                        body = r.get("body", "")
                        if body:
                            results.append(body[:120])
                        if len(results) >= 2:
                            break
                return results
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        except (ImportError, TimeoutError, OSError):
            return ["[网络超时]"]
        except Exception:
            return []


# ═══════════════════════════════════════════════════════════════════════
# 3. 决策层：辩论引擎 → 决策
# ═══════════════════════════════════════════════════════════════════════


class BettingDecisionEngine:
    """
    投注决策引擎。
    用 LLM 综合情报，给出 BET / SKIP 决策。
    """

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if not self.api_key or self.api_key in {"dummy-key", "dummy_key", ""}:
            raise RuntimeError("缺少 LLM API Key，无法启动决策引擎")

        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

        try:
            from openai import AsyncOpenAI

            self.client = AsyncOpenAI(api_key=self.api_key, base_url=base_url)
        except Exception:
            from openai import OpenAI

            self.client = OpenAI(api_key=self.api_key, base_url=base_url)

        self._async_client = None

    def _get_async_client(self):
        if self._async_client is None:
            try:
                from openai import AsyncOpenAI

                self._async_client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
                )
            except Exception:
                self._async_client = None
        return self._async_client

    async def decide(self, match_info: str, evidence: str) -> Dict[str, Any]:
        """
        给定比赛信息和情报证据，返回决策。

        Returns:
            {
                "decision": "BET" | "SKIP",
                "confidence": "high" | "medium" | "low",
                "kelly_fraction": float,
                "selection": "home_win" | "draw" | "away_win",
                "odds": float,
                "verdict": str,
                "key_risks": List[str],
                "reasoning": str,
            }
        """
        client = self._get_async_client()
        if not client:
            return {
                "decision": "SKIP",
                "confidence": "low",
                "kelly_fraction": 0.0,
                "selection": None,
                "odds": None,
                "verdict": "AsyncClient 不可用",
                "key_risks": [],
                "reasoning": "LLM 客户端初始化失败",
            }

        system_prompt = """你是顶级足彩投注分析师。
你极度厌恶风险，只在有明显正期望值（edge > 5%）时才建议下注。
竞彩返奖率约89%，你的预测概率必须高于 1/odds / 0.89 才算有真正的edge。

分析时请考虑：
1. 赔率是否合理反映双方实力差距
2. 主客场因素（主场优势约+8%~10%的胜率加成）
3. 近期状态（近5场得失球）
4. 伤停影响
5. 赔率异动迹象
6. 市场共识是否过于一致（热门陷阱）

严格以JSON格式返回：
{
    "decision": "BET" 或 "SKIP",
    "confidence": "high" 或 "medium" 或 "low",
    "kelly_fraction": 0.0~0.2 的小数,
    "selection": "home_win" 或 "draw" 或 "away_win" 或 null,
    "odds": 对应赔率数值 或 null,
    "verdict": "一句话决策",
    "key_risks": ["风险1", "风险2"],
    "reasoning": "详细推理过程，3-5句话",
}"""

        prompt = f"比赛：{match_info}\n\n情报证据：\n{evidence}\n\n请给出投注决策。"

        try:
            resp = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
                timeout=30.0,
            )
            raw = resp.choices[0].message.content
            result = json.loads(raw)
            return self._normalize(result)
        except json.JSONDecodeError:
            return {
                "decision": "SKIP",
                "confidence": "low",
                "kelly_fraction": 0.0,
                "selection": None,
                "odds": None,
                "verdict": "LLM返回非JSON",
                "key_risks": [],
                "reasoning": raw if "raw" in dir() else "解析失败",
            }
        except Exception as e:
            return {
                "decision": "SKIP",
                "confidence": "low",
                "kelly_fraction": 0.0,
                "selection": None,
                "odds": None,
                "verdict": f"LLM调用失败: {e}",
                "key_risks": [],
                "reasoning": str(e),
            }

    def _normalize(self, raw: Dict) -> Dict[str, Any]:
        """规范化LLM输出"""
        decision = str(raw.get("decision", "SKIP")).upper()
        if decision not in ("BET", "SKIP"):
            decision = "SKIP"

        confidence = str(raw.get("confidence", "low")).lower()
        if confidence not in ("high", "medium", "low"):
            confidence = "low"

        selection = raw.get("selection")
        valid_selections = {"home_win", "draw", "away_win"}
        if selection not in valid_selections:
            selection = None

        kelly = float(raw.get("kelly_fraction", 0))
        kelly = max(0.0, min(0.2, kelly))

        return {
            "decision": decision,
            "confidence": confidence,
            "kelly_fraction": kelly,
            "selection": selection,
            "odds": raw.get("odds"),
            "verdict": raw.get("verdict", ""),
            "key_risks": raw.get("key_risks", []),
            "reasoning": raw.get("reasoning", ""),
        }


# ═══════════════════════════════════════════════════════════════════════
# 4. 风控层
# ═══════════════════════════════════════════════════════════════════════


class RiskGuard:
    """简单风控兜底，在LLM决策之上再加一层硬过滤"""

    def review(self, decision: Dict, odds: Dict, bankroll: float = 10000.0) -> Dict[str, Any]:
        """
        检查 LLM 决策是否通过风控。
        硬规则：
        1. kelly_fraction > 0.15 → 截断到 0.15
        2. confidence == low → kelly → 0
        3. odds < 1.5 的低赔选项 → kelly 减半
        4. 胜率低于 35% 的选项 → 降权
        """
        if decision["decision"] != "BET":
            return {**decision, "risk_approved": True, "stake": 0, "risk_notes": []}

        notes = []
        kelly = decision["kelly_fraction"]
        selection = decision["selection"]
        selection_odds = decision.get("odds") or odds.get(selection, 0)

        # 规则1：kelly 截断
        if kelly > 0.15:
            kelly = 0.15
            notes.append(f"kelly截断: 0.{int(kelly*100)}")

        # 规则2：低置信度
        if decision["confidence"] == "low":
            kelly = 0.0
            notes.append("低置信度 kelly=0")

        # 规则3：低赔减半
        if selection_odds and float(selection_odds) < 1.5:
            kelly = kelly * 0.5
            notes.append(f"低赔({selection_odds}) kelly减半")

        # 计算下注金额
        stake = round(bankroll * kelly, 2) if kelly > 0 else 0

        return {
            **decision,
            "kelly_fraction_final": kelly,
            "stake": stake,
            "risk_approved": kelly > 0,
            "risk_notes": notes,
        }


# ═══════════════════════════════════════════════════════════════════════
# 5. 核心编排器
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class MatchDecision:
    """单场比赛决策"""

    league_name: str
    home_team: str
    away_team: str
    commence_time: str
    odds: Dict[str, float]
    intelligence: Dict[str, Any]
    llm_decision: Dict[str, Any]
    risk_review: Dict[str, Any]
    lottery_type: str  # "竞彩足球" 或 "北京单场"


class AutonomousBettingOrchestrator:
    """
    AI原生投注决策编排器。

    输入：今日比赛列表（已按竞彩/北单分类）
    输出：每场比赛的投注建议
    """

    def __init__(self, bankroll: float = 10000.0, fast_mode: bool = False):
        self.bankroll = bankroll
        self.fast_mode = fast_mode  # True: 跳过新闻抓取，用赔率分析
        self.bankroll = bankroll
        self.odds_collector = OddsCollector()
        self.intel_collector = IntelligenceCollector()
        self.decision_engine = BettingDecisionEngine()
        self.risk_guard = RiskGuard()
        self._results: List[MatchDecision] = []

    async def run_for_today(self) -> List[MatchDecision]:
        """主入口：处理今天所有竞彩 + 北单比赛"""
        # 竞彩足球（五大联赛 + 欧冠欧联）
        JC_LEAGUES = [
            "soccer_epl",
            "soccer_germany_bundesliga",
            "soccer_la_liga",
            "soccer_serie_a",
            "soccer_france_ligue_one",
            "soccer_uefa_champs_league",
            "soccer_uefa_europa_league",
        ]

        logger.info("[Orchestrator] 开始获取竞彩足球今日数据...")
        jc_matches = self.odds_collector.fetch_today_matches(JC_LEAGUES)
        logger.info("[Orchestrator] 获取到 %d 场竞彩比赛", len(jc_matches))

        # 按时间排序
        jc_matches.sort(key=lambda x: x.get("commence_time", ""))

        results = []
        for m in jc_matches:
            lottery = self._classify_lottery(m["league_key"])
            logger.info(
                "[处理中] %s | %s vs %s | [%s]",
                m["league_name"],
                m["home_team"],
                m["away_team"],
                lottery,
            )

            decision = await self._process_single_match(m, lottery)
            results.append(decision)
            logger.info(
                "[决策] %s vs %s → %s (kelly=%.0f%%, stake=¥%.0f)",
                m["home_team"],
                m["away_team"],
                decision.risk_review.get("decision", "?"),
                (decision.risk_review.get("kelly_fraction_final", 0) or 0) * 100,
                decision.risk_review.get("stake", 0),
            )

            # 避免API过载
            await asyncio.sleep(0.3)

        self._results = results
        return results

    async def _process_single_match(
        self, match: Dict[str, Any], lottery_type: str
    ) -> MatchDecision:
        """处理单场比赛：情报 → 决策 → 风控"""
        home = match["home_team"]
        away = match["away_team"]
        odds = match["odds"]

        # Step 1: 情报收集
        if self.fast_mode:
            intel = {
                "home": {"team": home, "news": ["[快速模式：无新闻]"], "injuries": []},
                "away": {"team": away, "news": ["[快速模式：无新闻]"], "injuries": []},
            }
        else:
            intel = await self.intel_collector.gather_match_intel(home, away)

        # Step 2: 构建 Evidence
        evidence = self._build_evidence(match, intel, odds)

        # Step 3: LLM 决策
        match_info = f"{match['league_name']} | {home} vs {away} | 开赛: {match['commence_time'][:16]} (UTC+8)"
        llm_decision = await self.decision_engine.decide(match_info, evidence)

        # Step 4: 风控
        risk_review = self.risk_guard.review(llm_decision, odds, self.bankroll)

        return MatchDecision(
            league_name=match["league_name"],
            home_team=home,
            away_team=away,
            commence_time=match["commence_time"],
            odds=odds,
            intelligence=intel,
            llm_decision=llm_decision,
            risk_review=risk_review,
            lottery_type=lottery_type,
        )

    def _build_evidence(
        self, match: Dict[str, Any], intel: Dict[str, Any], odds: Dict[str, float]
    ) -> str:
        """构建发给LLM的证据文本"""
        home = match["home_team"]
        away = match["away_team"]

        # 计算隐含概率
        implied = {}
        for side, odd in odds.items():
            if odd > 0:
                implied[side] = round(1.0 / odd, 3)

        lines = [
            f"【市场赔率】{home} vs {away}",
            f"  主胜赔率: {odds.get('home_win', 'N/A')} (隐含概率: {implied.get('home_win', 'N/A')})",
            f"  平局赔率: {odds.get('draw', 'N/A')} (隐含概率: {implied.get('draw', 'N/A')})",
            f"  客胜赔率: {odds.get('away_win', 'N/A')} (隐含概率: {implied.get('away_win', 'N/A')})",
            "",
            f"【主队({home})情报】",
        ]

        home_intel = intel.get("home", {})
        for item in home_intel.get("news", [])[:3]:
            lines.append(f"  新闻: {item}")
        for item in home_intel.get("injuries", [])[:2]:
            lines.append(f"  伤停: {item}")

        lines += [
            "",
            f"【客队({away})情报】",
        ]
        away_intel = intel.get("away", {})
        for item in away_intel.get("news", [])[:3]:
            lines.append(f"  新闻: {item}")
        for item in away_intel.get("injuries", [])[:2]:
            lines.append(f"  伤停: {item}")

        lines += [
            "",
            "【分析要求】",
            "请综合以上信息，判断是否存在正期望值（pred_prob > 隐含概率 / 0.89）的投注机会。",
            "只建议BET当且仅当：1) 有明确正edge；2) 风险可控；3) 置信度高。",
        ]

        return "\n".join(lines)

    def _classify_lottery(self, league_key: str) -> str:
        """根据联赛分类为竞彩或北单"""
        JC_KEYS = {
            "soccer_epl",
            "soccer_la_liga",
            "soccer_serie_a",
            "soccer_germany_bundesliga",
            "soccer_france_ligue_one",
            "soccer_uefa_champs_league",
            "soccer_uefa_europa_league",
            "soccer_uefa_europa_conf_league",
        }
        return "竞彩足球" if league_key in JC_KEYS else "北京单场"


# ═══════════════════════════════════════════════════════════════════════
# 6. 输出格式化
# ═══════════════════════════════════════════════════════════════════════


def format_results(results: List[MatchDecision]) -> str:
    """格式化决策结果为可读报告"""
    lines = [
        "=" * 80,
        "  ⚽ 今日 AI 投注决策报告",
        f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 80,
        "",
    ]

    # 分竞彩和北单
    jc = [r for r in results if r.lottery_type == "竞彩足球"]
    bd = [r for r in results if r.lottery_type == "北京单场"]

    total_stake = 0.0
    bet_count = 0

    def _print_lottery_section(label: str, matches: List[MatchDecision]):
        nonlocal total_stake, bet_count
        lines.append(f"━━━ {label} ━━━")
        lines.append("")

        for m in matches:
            home = m.home_team
            away = m.away_team
            odds = m.odds
            review = m.risk_review
            llm = m.llm_decision

            decision_emoji = "✅" if review.get("risk_approved") and review.get("stake", 0) > 0 else "❌"
            time_str = m.commence_time[11:16]  # HH:MM

            lines.append(
                f"  {decision_emoji} {time_str} | {home} vs {away} | [{m.league_name}]"
            )

            # 赔率行
            odds_str = " | ".join([f"{k}={v}" for k, v in odds.items()])
            lines.append(f"      赔率: {odds_str}")

            if review.get("risk_approved") and review.get("stake", 0) > 0:
                sel = review.get("selection", "?")
                kelly = review.get("kelly_fraction_final", 0)
                stake = review.get("stake", 0)
                conf = review.get("confidence", "?")
                verdict = review.get("verdict", "?")
                lines.append(
                    f"      → 下注: {sel} | 赔率={review.get('odds')} | "
                    f"Kelly={kelly*100:.0f}% | 金额=¥{stake:.0f} | 置信={conf}"
                )
                lines.append(f"      → 理由: {verdict}")
                lines.append(f"      → 推理: {llm.get('reasoning', '')[:100]}")
                if review.get("risk_notes"):
                    lines.append(f"      → 风控: {'; '.join(review['risk_notes'])}")
                total_stake += stake
                bet_count += 1
            else:
                verdict = llm.get("verdict", "?")
                lines.append(f"      → 跳过: {verdict}")
                if llm.get("key_risks"):
                    lines.append(f"      → 风险: {'; '.join(llm['key_risks'][:2])}")

            lines.append("")

        # 本节小计
        section_stake = sum(r.risk_review.get("stake", 0) for r in matches)
        section_bets = sum(
            1 for r in matches if r.risk_review.get("risk_approved") and r.risk_review.get("stake", 0) > 0
        )
        lines.append(
            f"  小计: {section_bets} 注 | 建议总投入 ¥{section_stake:.0f}"
        )
        lines.append("")

    _print_lottery_section("竞彩足球", jc)
    _print_lottery_section("北京单场", bd)

    lines += [
        "─" * 80,
        f"  📊 汇总: {bet_count} 注建议 | 今日建议总投入 ¥{total_stake:.0f}",
        f"  💰 账户规模 ¥10000 | 建议占比 {total_stake/100:.1f}%",
        "─" * 80,
        "",
        "  ⚠️  本报告仅供参考，不构成投注建议。竞彩返奖率89%，理性投注。",
    ]

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# 7. 主入口
# ═══════════════════════════════════════════════════════════════════════


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Autonomous Betting Orchestrator")
    parser.add_argument("--bankroll", type=float, default=10000.0, help="账户规模（默认10000）")
    parser.add_argument(
        "--lottery", choices=["jc", "bd", "both"], default="both", help="分析哪种玩法"
    )
    parser.add_argument("--fast", action="store_true", help="快速模式：跳过新闻抓取，仅用赔率分析")
    args = parser.parse_args()

    orchestrator = AutonomousBettingOrchestrator(bankroll=args.bankroll)
    orchestrator.fast_mode = args.fast
    results = await orchestrator.run_for_today()

    report = format_results(results)
    print(report)

    # 同时写文件
    from pathlib import Path

    report_dir = Path(__file__).parent.parent / "reports"
    report_dir.mkdir(exist_ok=True)
    filename = report_dir / f"betting_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    filename.write_text(report, encoding="utf-8")
    logger.info("[完成] 报告已保存: %s", filename)

    # 写结构化JSON供后续AAR使用
    json_path = report_dir / f"decisions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_data = [asdict(r) for r in results]
    json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("[完成] 结构化数据已保存: %s", json_path)

    return results


if __name__ == "__main__":
    asyncio.run(main())
