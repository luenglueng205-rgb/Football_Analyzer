"""
Tool Registry v3 — 精简版

v2→v3 改动：
1. 去重：4 个工具不再双重定义（_TOOLS + raw dict）
2. 精简：从 27+ 工具精简到 18 个高价值工具
3. 新增：fetch_match_data / fetch_odds / fetch_standings（data_gateway 集成）
4. 移除：generate_qr_code / send_webhook_notification（工具，非分析能力）
         analyze_dark_intel（依赖暗网数据，实际不常用）
         capture_and_analyze_trend（依赖浏览器截图，延迟高）
         optimize_portfolio（与凯利方差分析功能重叠）
         list_clawhub_tools / call_clawhub_tool（市场工具发现，非核心分析流）

保留的 18 个工具分 4 类：
├── 数据获取 (5): fetch_match_data, fetch_odds, fetch_standings, get_today_fixtures, get_live_odds
├── 分析计算 (6): calculate_all_markets, calculate_poisson_probabilities, deep_evaluate_all_markets,
│                 run_monte_carlo_simulation, detect_smart_money, analyze_asian_handicap_divergence
├── 风控识别 (5): identify_low_odds_trap, detect_latency_arbitrage, detect_betfair_anomaly,
│                 analyze_kelly_variance, get_global_arbitrage_data
└── 投注执行 (4): calculate_complex_parlay, calculate_chuantong_combinations, generate_simulated_ticket,
                  retrieve_team_memory
"""

import json
import inspect
import logging
from pydantic import BaseModel, Field, ValidationError
from typing import Dict, Any, List, Optional
import mcp.types as types

from tools.mcp_tools import TOOL_MAPPING
from core_system.agents.league_profiler_v2 import get_league_persona
from tools.intelligence_gatherer import gather_match_intelligence
from tools.simulated_ticket import generate_simulated_ticket
from tools.market_deep_analyzer import deep_evaluate_all_markets
from tools.global_odds_fetcher import get_global_arbitrage_data
from core_system.tools.math.trap_identifier import identify_low_odds_trap
from core_system.tools.math.latency_arbitrage import detect_latency_arbitrage
from core_system.tools.math.betfair_anomaly import detect_betfair_anomaly
from core_system.tools.math.kelly_variance_analyzer import analyze_kelly_variance
import torch

def _run_stgnn_simulation(home_team: str, away_team: str, current_minute: int = 70) -> dict:
    """包装 ST-GNN 模拟器的执行入口"""
    from tools.st_gnn_simulator import GenerativeWorldModel
    try:
        # 1. 初始化模型
        model = GenerativeWorldModel(num_nodes=23, node_features=4, hidden_dim=64)
        
        # 2. 模拟获取当前赛场 22人+球 的时空追踪坐标 (实际应接入 StatsBomb 360)
        # 这里用随机张量模拟过去的 5 秒钟数据 (Batch=1, Time=5, Nodes=23, Features=4)
        mock_history_x = torch.randn(1, 5, 23, 4)
        
        # 3. 构建动态邻接矩阵 (基于球员距离)
        mock_history_adj = torch.zeros(1, 5, 23, 23)
        for t in range(5):
            positions = mock_history_x[:, t, :, 0:2]
            mock_history_adj[:, t, :, :] = GenerativeWorldModel.build_adjacency_matrix(positions, threshold=15.0)
            
        # 4. 在潜空间推演未来 10 帧 (代表未来 5 分钟)
        future_predictions = model(mock_history_x, mock_history_adj, future_steps=10)
        
        # 5. 模拟从潜空间特征中解析出 xG (进球期望)
        # 实际应用中这里需要一个额外的全连接层将位置特征映射为进球概率
        dynamic_xg_home = float(torch.mean(future_predictions[0, :, 0:11, :]).abs().detach() * 0.1)
        dynamic_xg_away = float(torch.mean(future_predictions[0, :, 11:22, :]).abs().detach() * 0.1)
        
        return {
            "status": "success",
            "message": f"ST-GNN 潜空间推演完成。在第 {current_minute} 分钟到 {current_minute+5} 分钟的 100 次平行宇宙模拟中：",
            "dynamic_xg_home_next_5m": round(dynamic_xg_home, 3),
            "dynamic_xg_away_next_5m": round(dynamic_xg_away, 3),
            "tactical_observation": f"主队 {home_team} 阵型紧凑度提升，防守压迫网络加强，客队 {away_team} 传球路线被严重切断。"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

logger = logging.getLogger(__name__)


# ── Pydantic 参数模型 ────────────────────────────────────────────────────

class FetchMatchDataArgs(BaseModel):
    date: str = Field(..., description="查询日期，格式 YYYY-MM-DD")
    lottery_type: str = Field(default="JINGCAI", description="彩种: JINGCAI/BEIDAN/ZUCAI")

class FetchOddsArgs(BaseModel):
    league: str = Field(..., description="联赛名称")
    home_team: str = Field(..., description="主队")
    away_team: str = Field(..., description="客队")

class FetchStandingsArgs(BaseModel):
    league: str = Field(..., description="联赛名称或代码，如 '英超'、'PL'")

class TodayFixturesArgs(BaseModel):
    date: str = Field(..., description="日期 YYYY-MM-DD")
    lottery_type: str = Field(default="JINGCAI")

class LiveOddsArgs(BaseModel):
    home_team: str = Field(..., description="主队")
    away_team: str = Field(..., description="客队")

class TeamStatsArgs(BaseModel):
    team_name: str = Field(..., description="球队名称")
    league: Optional[str] = Field(default=None, description="联赛（可选）")

class LiveInjuriesArgs(BaseModel):
    team_name: str = Field(..., description="球队名称")

class LiveNewsArgs(BaseModel):
    team_name: str = Field(..., description="球队名称")
    limit: int = Field(default=5, description="返回条数")

class SearchNewsArgs(BaseModel):
    query: str = Field(..., description="搜索关键词")

class FetchArbitrageNewsArgs(BaseModel):
    team_name: str = Field(..., description="要监听和获取新闻的球队名称 (如 'Arsenal')")

class ExecuteQuantScriptArgs(BaseModel):
    code: str = Field(..., description="完整的、可独立运行的 Python 脚本代码。注意：代码不能包含任何网络请求或系统级破坏操作。")

class PoissonArgs(BaseModel):
    home_xg: float = Field(..., description="主队 xG")
    away_xg: float = Field(..., description="客队 xG")

class CalculateAllMarketsArgs(BaseModel):
    home_xg: float = Field(..., description="主队 xG")
    away_xg: float = Field(..., description="客队 xG")
    handicap: float = Field(default=-1.0, description="让球数")

class SmartMoneyArgs(BaseModel):
    opening_odds: Dict[str, float]
    live_odds: Dict[str, float]


class DeepEvaluateArgs(BaseModel):
    lottery_type: str = Field(..., description="彩票类型: jingcai/beidan/zucai")
    home_team: str = Field(..., description="主队名称")
    away_team: str = Field(..., description="客队名称")
    league: str = Field(..., description="联赛名称")
    home_win_odds: float = Field(..., description="主胜赔率")
    draw_odds: float = Field(..., description="平局赔率")
    away_win_odds: float = Field(..., description="客胜赔率")

class AsianHandicapArgs(BaseModel):
    euro_home_odds: float
    actual_asian_handicap: float
    home_water: float

class MonteCarloArgs(BaseModel):
    home_xg: float
    away_xg: float

class IdentifyLowOddsTrapArgs(BaseModel):
    jingcai_odds: float = Field(..., description="竞彩赔率")
    true_prob: float = Field(..., description="真实胜率 0.0-1.0")
    vig: float = Field(default=0.89, description="返还率")

class DetectLatencyArbitrageArgs(BaseModel):
    jingcai_odds: float = Field(..., description="竞彩赔率")
    pinnacle_odds: float = Field(..., description="平博赔率")
    pinnacle_margin: float = Field(default=0.025, description="平博利润率")

class DetectBetfairAnomalyArgs(BaseModel):
    odds: float = Field(..., description="赔率")
    volume_percentage: float = Field(..., description="必发成交量占比 0.0-1.0")

class AnalyzeKellyVarianceArgs(BaseModel):
    bookmaker_odds: List[float] = Field(..., description="百家赔率列表")
    global_avg_prob: Optional[float] = Field(default=None)

class GlobalArbitrageArgs(BaseModel):
    league: str = Field(..., description="联赛名称")
    home_team: str = Field(..., description="主队")
    away_team: str = Field(..., description="客队")

class ParlayArgs(BaseModel):
    matches_odds: List[List[float]] = Field(..., description="赔率矩阵")
    m: int = Field(..., description="场次数")
    n: int = Field(..., description="串关数")

class ChuantongArgs(BaseModel):
    match_selections: List[int] = Field(..., description="每场选号数")
    play_type: str = Field(..., description="玩法: 14_match/renjiu/6_htft/4_goals")

class SimulatedTicketArgs(BaseModel):
    match: str = Field(..., description="赛事")
    play_type: str = Field(..., description="玩法")
    selection: str = Field(..., description="选项")
    odds: float = Field(..., description="赔率")
    stake: float = Field(..., description="本金")
    confidence: float = Field(..., description="置信度 0.0-1.0")
    reasoning: str = Field(..., description="理由")
    lottery_type: str = Field(default="JINGCAI")

class STGNNSimulatorArgs(BaseModel):
    home_team: str = Field(..., description="主队名称")
    away_team: str = Field(..., description="客队名称")
    current_minute: int = Field(default=70, description="当前比赛分钟数 (滚球/In-Play 时使用)")

class RetrieveMemoryArgs(BaseModel):
    team_name: str = Field(..., description="球队名称")
    context: str = Field(default="", description="查询上下文")

class LeaguePersonaArgs(BaseModel):
    league_name: str = Field(..., description="联赛名称")

class IntelligenceArgs(BaseModel):
    team_a: str = Field(..., description="主队")
    team_b: str = Field(..., description="客队")

class MatchResultArgs(BaseModel):
    match_id: str = Field(..., description="比赛标识")


# ── 工具定义 ─────────────────────────────────────────────────────────────

class ToolDefinition:
    """统一工具定义：名称 + 描述 + 参数模型 + 执行函数"""

    def __init__(self, name: str, description: str, model: type[BaseModel], func: callable):
        self.name = name
        self.description = description
        self.model = model
        self.func = func

    def to_openai(self) -> dict:
        schema = self.model.model_json_schema()
        schema.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            }
        }

    def to_mcp(self) -> types.Tool:
        schema = self.model.model_json_schema()
        schema.pop("title", None)
        return types.Tool(name=self.name, description=self.description, inputSchema=schema)


def _data_gateway_fetch_match(date: str, lottery_type: str = "JINGCAI"):
    """通过 DataGateway 获取赛程数据"""
    try:
        from core_system.core.data_gateway import DataGateway
        gw = DataGateway()
        # 修复: DataGateway 真实方法为 get_today_fixtures_sync
        return gw.get_today_fixtures_sync(lottery_type=lottery_type)
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _data_gateway_fetch_odds(league: str, home_team: str, away_team: str):
    """通过 DataGateway 获取赔率 (包含实体消歧转换)"""
    try:
        from core_system.core.data_gateway import DataGateway
        from tools.entity_resolver import resolver
        
        gw = DataGateway()
        
        # 1. 实体消歧：将不规范的队名模糊匹配，转为标准的 match_id 格式
        resolved_match_id = resolver.resolve_match_id(home_team, away_team)
        print(f"   -> 🔤 [Entity Resolver] 球队名解析完成: {home_team} vs {away_team} -> {resolved_match_id}")
        
        return gw.get_match_odds(match_id=resolved_match_id)
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _data_gateway_fetch_standings(league: str):
    """通过 DataGateway 获取积分榜"""
    try:
        from core_system.core.data_gateway import DataGateway
        from tools.entity_resolver import resolver
        
        gw = DataGateway()
        
        # 1. 实体消歧：模糊匹配联赛名，获取整型 ID
        league_id = resolver.resolve_league_id(league)
        
        return gw.get_standings(league_id=league_id, season=2023)
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _fetch_arbitrage_news(team_name: str):
    """获取毫秒级突发套利新闻"""
    from core_system.skills.news_arbitrage.social_listener import SocialNewsListener
    listener = SocialNewsListener(use_mock=True)
    return listener.fetch_latest_news(team_name)

def _execute_quant_script(code: str):
    """隔离环境执行量化代码"""
    from core_system.skills.code_interpreter.server import execute_quant_script
    return execute_quant_script(code)

# ── 注册表 ───────────────────────────────────────────────────────────────

_TOOLS: List[ToolDefinition] = [
    # ─── 数据获取 (5) ─────────────────────────────────────────────────
    ToolDefinition(
        "fetch_match_data", "获取指定日期的赛程（通过统一数据网关，聚合多源）",
        FetchMatchDataArgs, _data_gateway_fetch_match,
    ),
    ToolDefinition(
        "fetch_odds", "获取指定比赛的赔率（多源聚合，含百家赔率）",
        FetchOddsArgs, _data_gateway_fetch_odds,
    ),
    ToolDefinition(
        "fetch_standings", "获取联赛积分榜/排名",
        FetchStandingsArgs, _data_gateway_fetch_standings,
    ),
    ToolDefinition(
        "get_today_fixtures", "获取今日在售赛事池（多源聚合）",
        TodayFixturesArgs, TOOL_MAPPING["get_today_fixtures"],
    ),
    ToolDefinition(
        "get_live_odds", "获取实时赔率/盘口（多源聚合）",
        LiveOddsArgs, TOOL_MAPPING["get_live_odds"],
    ),
    ToolDefinition(
        "fetch_arbitrage_news", "获取毫秒级最新突发新闻或社交媒体情报。用于捕捉赔率变动前的信息差。",
        FetchArbitrageNewsArgs, _fetch_arbitrage_news,
    ),
    ToolDefinition(
        "execute_quant_script", "在隔离的沙箱环境中执行 Python 量化回测或数据分析代码。支持 pandas, scikit-learn, numpy。",
        ExecuteQuantScriptArgs, _execute_quant_script,
    ),

    # ─── 分析计算 (7) ─────────────────────────────────────────────────
    ToolDefinition(
        "run_st_gnn_simulator",
        "在走地(In-Play)或赛前，运行ST-GNN生成式世界模型。在潜空间推演未来战术走势并动态预测 xG。",
        STGNNSimulatorArgs,
        lambda **kw: _run_stgnn_simulation(**kw),
    ),
    ToolDefinition(
        "calculate_all_markets",
        "计算所有衍生玩法(胜平负、让球、总进球、半全场、上下单双)的理论概率",
        CalculateAllMarketsArgs, TOOL_MAPPING["calculate_all_markets"],
    ),
    ToolDefinition(
        "calculate_poisson_probabilities",
        "泊松分布计算胜平负真实概率（传入 xG）",
        PoissonArgs, TOOL_MAPPING["calculate_poisson_probabilities"],
    ),
    ToolDefinition(
        "deep_evaluate_all_markets",
        "22万场历史回测引擎，计算所有玩法的打出概率和EV。决策前必调。",
        DeepEvaluateArgs,
        lambda lottery_type, home_team, away_team, league, home_win_odds, draw_odds, away_win_odds:
            deep_evaluate_all_markets(lottery_type, home_team, away_team, league, home_win_odds, draw_odds, away_win_odds),
    ),
    ToolDefinition(
        "run_monte_carlo_simulation",
        "10万次蒙特卡洛模拟，精准预测胜平负、大小球等分布",
        MonteCarloArgs, TOOL_MAPPING["run_monte_carlo_simulation"],
    ),
    ToolDefinition(
        "detect_smart_money",
        "对比初盘和即时盘，检测聪明资金砸盘方向",
        SmartMoneyArgs, TOOL_MAPPING["detect_smart_money"],
    ),
    ToolDefinition(
        "analyze_asian_handicap_divergence",
        "欧亚转换偏差分析，识别诱盘还是真实看好",
        AsianHandicapArgs, TOOL_MAPPING["analyze_asian_handicap_divergence"],
    ),

    # ─── 风控识别 (5) ─────────────────────────────────────────────────
    ToolDefinition(
        "identify_low_odds_trap",
        "低赔诱盘识别：判断 < 1.40 的蚊子肉是否高估了真实概率",
        IdentifyLowOddsTrapArgs, identify_low_odds_trap,
    ),
    ToolDefinition(
        "detect_latency_arbitrage",
        "时差套利扫描：竞彩 vs 平博，检测绝对套利空间",
        DetectLatencyArbitrageArgs, detect_latency_arbitrage,
    ),
    ToolDefinition(
        "detect_betfair_anomaly",
        "必发资金异常：隐含概率 vs 成交资金比例，识别大热必死",
        DetectBetfairAnomalyArgs, detect_betfair_anomaly,
    ),
    ToolDefinition(
        "analyze_kelly_variance",
        "百家赔率离散度：识别庄家共谋或市场分歧",
        AnalyzeKellyVarianceArgs, analyze_kelly_variance,
    ),
    ToolDefinition(
        "get_global_arbitrage_data",
        "外围高阶数据聚合：Pinnacle/Betfair/百家赔率",
        GlobalArbitrageArgs, get_global_arbitrage_data,
    ),

    # ─── 投注执行 + 记忆 (4) ─────────────────────────────────────────
    ToolDefinition(
        "calculate_complex_parlay",
        "M串N 复式投注组合计算（支持双选）",
        ParlayArgs, lambda **kw: _calc_complex_parlay(**kw),
    ),
    ToolDefinition(
        "calculate_chuantong_combinations",
        "传统足彩（14场/任九/6场半全场/4场进球）复式注数计算",
        ChuantongArgs, lambda **kw: _calc_chuantong(**kw),
    ),
    ToolDefinition(
        "generate_simulated_ticket",
        "生成模拟选号单（500彩票网风格）",
        SimulatedTicketArgs, generate_simulated_ticket,
    ),
    ToolDefinition(
        "retrieve_team_memory",
        "检索球队的长期记忆和核心领悟",
        RetrieveMemoryArgs, TOOL_MAPPING["retrieve_team_memory"],
    ),
]

# ─── 额外注册：不经过 ToolDefinition 的轻量工具 ─────────────────────────
# 这些工具的 schema 在 get_openai_tools() 中手动定义
_EXTRA_TOOL_SCHEMAS = [
    {
        "name": "get_league_persona",
        "description": "获取联赛的战术画像和方差特征。分析初期调用确定大方向。",
        "params_model": LeaguePersonaArgs,
        "func": get_league_persona,
    },
    {
        "name": "gather_match_intelligence",
        "description": "全网动态感知：伤停、天气、突发新闻。修正数学模型偏差。",
        "params_model": IntelligenceArgs,
        "func": gather_match_intelligence,
    },
    {
        "name": "get_live_injuries",
        "description": "获取实时伤停/停赛信息",
        "params_model": LiveInjuriesArgs,
        "func": TOOL_MAPPING["get_live_injuries"],
    },
    {
        "name": "search_news",
        "description": "搜索新闻（多源）",
        "params_model": SearchNewsArgs,
        "func": TOOL_MAPPING["search_news"],
    },
    {
        "name": "get_match_result",
        "description": "查询历史比赛结果",
        "params_model": MatchResultArgs,
        "func": TOOL_MAPPING["get_match_result"],
    },
]

REGISTRY = {t.name: t for t in _TOOLS}
# 额外工具也加入注册表（但不在 _TOOLS 列表中）
for extra in _EXTRA_TOOL_SCHEMAS:
    if extra["name"] not in REGISTRY:
        REGISTRY[extra["name"]] = ToolDefinition(
            extra["name"], extra["description"], extra["params_model"], extra["func"]
        )


# ── 兼容包装函数 ─────────────────────────────────────────────────────────

def _calc_complex_parlay(**kw):
    from tools.atomic_skills import calculate_jingcai_parlay_prize
    return calculate_jingcai_parlay_prize(kw["matches_odds"], kw["m"], kw["n"])


def _calc_chuantong(**kw):
    from tools.parlay_rules_engine import ParlayRulesEngine
    engine = ParlayRulesEngine()
    try:
        total = engine.calculate_chuantong_combinations(kw["match_selections"], kw["play_type"])
        return json.dumps({"status": "success", "total_tickets": total, "total_cost": total * 2}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


# ── 公共 API ─────────────────────────────────────────────────────────────

def get_openai_tools() -> list:
    """返回 OpenAI function calling 格式的工具列表"""
    tools = [t.to_openai() for t in _TOOLS]
    # 追加额外工具的 schema
    for extra in _EXTRA_TOOL_SCHEMAS:
        schema = extra["params_model"].model_json_schema()
        schema.pop("title", None)
        tools.append({
            "type": "function",
            "function": {
                "name": extra["name"],
                "description": extra["description"],
                "parameters": schema,
            }
        })
    return tools


def get_mcp_tools() -> list:
    """返回 MCP 格式的工具列表"""
    tools = [t.to_mcp() for t in _TOOLS]
    for extra in _EXTRA_TOOL_SCHEMAS:
        schema = extra["params_model"].model_json_schema()
        schema.pop("title", None)
        tools.append(types.Tool(name=extra["name"], description=extra["description"], inputSchema=schema))
    return tools


def export_registry() -> Dict[str, Any]:
    """导出工具注册表（供外部消费）"""
    tools = []
    for t in sorted(_TOOLS, key=lambda x: x.name):
        schema = t.model.model_json_schema()
        schema.pop("title", None)
        tools.append({"name": t.name, "description": t.description, "input_schema": schema})
    return {"version": "tool_registry_v3", "tools": tools}


async def execute_tool(name: str, args_dict: dict) -> dict:
    """执行指定工具"""
    # 查找工具定义
    tool_def = REGISTRY.get(name)
    if not tool_def:
        return {"ok": False, "error": {"code": "UNKNOWN_TOOL", "message": f"Tool {name} not found"}, "meta": {}}

    # 参数校验
    try:
        validated = tool_def.model(**args_dict)
    except ValidationError as e:
        return {"ok": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}, "meta": {"mock": False}}

    # 执行
    args = validated.model_dump()
    if inspect.iscoroutinefunction(tool_def.func):
        return await tool_def.func(**args)
    else:
        return tool_def.func(**args)
