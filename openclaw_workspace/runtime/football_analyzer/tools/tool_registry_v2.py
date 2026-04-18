from pydantic import BaseModel, Field, ValidationError
from typing import Dict, Any, List, Optional
import mcp.types as types
import inspect
from tools.mcp_tools import TOOL_MAPPING

class ToolDefinition:
    def __init__(self, name: str, description: str, model: type[BaseModel], func: callable):
        self.name = name
        self.description = description
        self.model = model
        self.func = func

    def to_openai(self) -> dict:
        schema = self.model.model_json_schema()
        if "title" in schema:
            del schema["title"]
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema
            }
        }

    def to_mcp(self) -> types.Tool:
        schema = self.model.model_json_schema()
        if "title" in schema:
            del schema["title"]
        return types.Tool(
            name=self.name,
            description=self.description,
            inputSchema=schema
        )

# Define Pydantic Models for validation
class WaterDropArgs(BaseModel):
    opening_water: float
    live_water: float

class TeamStatsArgs(BaseModel):
    team_name: str
    league: Optional[str] = None

class BankrollArgs(BaseModel):
    pass

class MatchArgs(BaseModel):
    match_id: str
    selection: str
    odds: float

class ParlayArgs(BaseModel):
    matches: List[MatchArgs]
    parlay_type: str
    total_stake: float

class QRArgs(BaseModel):
    ticket_string: str

class WebhookArgs(BaseModel):
    message: str

class ExecuteBetArgs(BaseModel):
    match_id: str
    lottery_type: str
    selection: str
    odds: float
    stake: float

class AsianHandicapArgs(BaseModel):
    euro_home_odds: float
    actual_asian_handicap: float
    home_water: float

class ScrapeBeidanArgs(BaseModel):
    home_team: str
    away_team: str

class LiveOddsArgs(BaseModel):
    home_team: str
    away_team: str

class LiveInjuriesArgs(BaseModel):
    team_name: str

class LiveNewsArgs(BaseModel):
    team_name: str
    limit: int = 5

class TodayFixturesArgs(BaseModel):
    date: str
    lottery_type: str

class MatchResultArgs(BaseModel):
    match_id: str

class SearchNewsArgs(BaseModel):
    query: str

class PoissonArgs(BaseModel):
    home_xg: float
    away_xg: float

class CalculateAllMarketsArgs(BaseModel):
    home_xg: float = Field(..., description="主队预期进球数")
    away_xg: float = Field(..., description="客队预期进球数")
    handicap: float = Field(default=-1.0, description="让球数(例如主让一球为 -1.0，客让一球为 1.0)")

class SmartMoneyArgs(BaseModel):
    opening_odds: Dict[str, float]
    live_odds: Dict[str, float]

class CaptureTrendArgs(BaseModel):
    home_team: str
    away_team: str

class MonteCarloArgs(BaseModel):
    home_xg: float
    away_xg: float

class DarkIntelArgs(BaseModel):
    team_name: str
    raw_social_text: str

class PortfolioMatchArgs(BaseModel):
    home_team: str
    away_team: str
    odds: Dict[str, float]
    probabilities: Dict[str, float]
    type: str

class OptimizePortfolioArgs(BaseModel):
    matches: List[PortfolioMatchArgs]

class RetrieveMemoryArgs(BaseModel):
    team_name: str
    context: str = Field(default="", description="查询的上下文，例如：客场防守表现")

class SaveInsightArgs(BaseModel):
    team_name: str
    insight: str = Field(..., description="高度浓缩的核心领悟，例如：切尔西主场极度依赖边路传中，中路渗透为0")
    match_id: str = Field(default="unknown")

class ComplexParlayArgs(BaseModel):
    matches_odds: List[List[float]] = Field(description="A 2D array of odds. Each inner array represents a match.")
    m: int = Field(description="The number of matches in the parlay")
    n: int = Field(description="The parlay type")
    stake_per_bet: float = Field(2.0, description="Stake per single combination bet")

class ChuantongCombinationsArgs(BaseModel):
    match_selections: List[int] = Field(description="选定的场次结果数列表。")
    play_type: str = Field(description="玩法类型: 14_match, renjiu, 6_htft, 4_goals")

_TOOLS = [
    ToolDefinition("analyze_water_drop", "计算从初盘到临场的水位下降幅度", WaterDropArgs, TOOL_MAPPING["analyze_water_drop"]),
    ToolDefinition("get_team_stats", "获取球队历史统计数据", TeamStatsArgs, TOOL_MAPPING["get_team_stats"]),
    ToolDefinition("get_live_odds", "获取实时赔率/盘口（多源聚合）", LiveOddsArgs, TOOL_MAPPING["get_live_odds"]),
    ToolDefinition("get_live_injuries", "获取实时伤停/停赛（多源聚合）", LiveInjuriesArgs, TOOL_MAPPING["get_live_injuries"]),
    ToolDefinition("get_live_news", "获取实时新闻/舆情（多源聚合）", LiveNewsArgs, TOOL_MAPPING["get_live_news"]),
    ToolDefinition("get_today_fixtures", "获取今日在售赛事池（多源聚合）", TodayFixturesArgs, TOOL_MAPPING["get_today_fixtures"]),
    ToolDefinition("get_match_result", "获取赛果/比分（多源聚合）", MatchResultArgs, TOOL_MAPPING["get_match_result"]),
    ToolDefinition("search_news", "搜索新闻（多源聚合）", SearchNewsArgs, TOOL_MAPPING["search_news"]),
    ToolDefinition("check_bankroll", "查看当前真实可用资金", BankrollArgs, TOOL_MAPPING["check_bankroll"]),
    ToolDefinition("calculate_parlay", "计算多场比赛串关的容错组合", ParlayArgs, TOOL_MAPPING["calculate_parlay"]),
    ToolDefinition("generate_qr_code", "生成二维码", QRArgs, TOOL_MAPPING["generate_qr_code"]),
    ToolDefinition("send_webhook_notification", "推送通知", WebhookArgs, TOOL_MAPPING["send_webhook_notification"]),
    ToolDefinition("execute_bet", "执行下注并记录账本", ExecuteBetArgs, TOOL_MAPPING["execute_bet"]),
    ToolDefinition("analyze_asian_handicap_divergence", "分析欧亚转换偏差", AsianHandicapArgs, TOOL_MAPPING["analyze_asian_handicap_divergence"]),
    ToolDefinition("scrape_beidan_sp", "抓取北单SP", ScrapeBeidanArgs, TOOL_MAPPING["scrape_beidan_sp"]),
    ToolDefinition("calculate_poisson_probabilities", "计算泊松分布", PoissonArgs, TOOL_MAPPING["calculate_poisson_probabilities"]),
    ToolDefinition("calculate_all_markets", "计算竞彩/北单所有衍生玩法(胜平负、让球、总进球、半全场、上下单双)的理论概率", CalculateAllMarketsArgs, TOOL_MAPPING["calculate_all_markets"]),
    ToolDefinition("detect_smart_money", "检测聪明资金", SmartMoneyArgs, TOOL_MAPPING["detect_smart_money"]),
    ToolDefinition("capture_and_analyze_trend", "截图分析走势", CaptureTrendArgs, TOOL_MAPPING["capture_and_analyze_trend"]),
    ToolDefinition("run_monte_carlo_simulation", "运行蒙特卡洛模拟", MonteCarloArgs, TOOL_MAPPING["run_monte_carlo_simulation"]),
    ToolDefinition("analyze_dark_intel", "分析暗网情报", DarkIntelArgs, TOOL_MAPPING["analyze_dark_intel"]),
    ToolDefinition("optimize_portfolio", "优化投资组合", OptimizePortfolioArgs, TOOL_MAPPING["optimize_portfolio"]),
    ToolDefinition("retrieve_team_memory", "检索关于某支球队的长期历史记忆和核心领悟", RetrieveMemoryArgs, TOOL_MAPPING["retrieve_team_memory"]),
    ToolDefinition("save_team_insight", "在分析结束后，将重要的战术发现或模型领悟持久化到长期记忆库", SaveInsightArgs, TOOL_MAPPING["save_team_insight"]),
    ToolDefinition("calculate_complex_parlay", "计算包含双选的 M串N 复式组合成本与最大回报", ComplexParlayArgs, TOOL_MAPPING.get("calculate_complex_parlay")),
    ToolDefinition("calculate_chuantong_combinations", "计算足彩任九或14场等复式注数与成本", ChuantongCombinationsArgs, TOOL_MAPPING.get("calculate_chuantong_combinations"))
]

REGISTRY = {t.name: t for t in _TOOLS}

def get_openai_tools() -> list:
    return [t.to_openai() for t in _TOOLS]

def get_mcp_tools() -> list:
    return [t.to_mcp() for t in _TOOLS]

async def execute_tool(name: str, args_dict: dict) -> dict:
    if name not in REGISTRY:
        return {"ok": False, "error": {"code": "UNKNOWN_TOOL", "message": f"Tool {name} not found"}, "meta": {}}
        
    tool_def = REGISTRY[name]
    try:
        validated_args = tool_def.model(**args_dict)
    except ValidationError as e:
        return {
            "ok": False,
            "error": {"code": "VALIDATION_ERROR", "message": str(e)},
            "meta": {"mock": False}
        }
        
    if inspect.iscoroutinefunction(tool_def.func):
        return await tool_def.func(**validated_args.model_dump())
    else:
        return tool_def.func(**validated_args.model_dump())
