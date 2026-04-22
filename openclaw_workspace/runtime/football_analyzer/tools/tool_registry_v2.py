from pydantic import BaseModel, Field, ValidationError
from typing import Dict, Any, List, Optional
import mcp.types as types
import inspect
from tools.mcp_tools import TOOL_MAPPING
from tools.league_profiler import get_league_persona
from tools.intelligence_gatherer import gather_match_intelligence
from tools.simulated_ticket import generate_simulated_ticket
from tools.market_deep_analyzer import deep_evaluate_all_markets

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

class ListClawHubToolsArgs(BaseModel):
    pass

class CallClawHubToolArgs(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)

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
    ToolDefinition("list_clawhub_tools", "列出 ClawHub 市场工具注册表中的工具", ListClawHubToolsArgs, TOOL_MAPPING["list_clawhub_tools"]),
    ToolDefinition("call_clawhub_tool", "调用 ClawHub 市场工具（代理到本地 call_target）", CallClawHubToolArgs, TOOL_MAPPING["call_clawhub_tool"]),
]

REGISTRY = {t.name: t for t in _TOOLS}

def export_registry() -> Dict[str, Any]:
    tools = []
    for t in sorted(_TOOLS, key=lambda x: x.name):
        schema = t.model.model_json_schema()
        if "title" in schema:
            del schema["title"]
        tools.append({"name": t.name, "description": t.description, "input_schema": schema})
    return {"version": "tool_registry_v2", "tools": tools}

def get_openai_tools() -> list:
    tools = [t.to_openai() for t in _TOOLS]
    
    # 动态注册联赛画像工具
    tools.append({
        "type": "function",
        "function": {
            "name": "get_league_persona",
            "description": "获取指定联赛的战术画像、方差特征和AI策略建议。必须在分析初期调用以确定大方向策略。",
            "parameters": {
                "type": "object",
                "properties": {
                    "league_name": {"type": "string", "description": "联赛名称，例如 '英超', '意甲', '荷甲', '日职联'"}
                },
                "required": ["league_name"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "gather_match_intelligence",
            "description": "全网动态感知工具。获取最新的球队伤停、天气或突发新闻，以便修正数学模型的偏差。",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_a": {"type": "string", "description": "主队名称"},
                    "team_b": {"type": "string", "description": "客队名称"}
                },
                "required": ["team_a", "team_b"]
            }
        }
    })
    
    tools.extend([{
        "type": "function",
        "function": {
            "name": "calculate_complex_parlay",
            "description": "Calculate complex parlay combinations (M串N) and double/multiple selections (复式投注). Use this when you want to recommend a strategy involving multiple matches with combinations like 3串4, or when you want to pick multiple outcomes for a single match (e.g., picking both Win and Draw).",
            "parameters": {
                "type": "object",
                "properties": {
                    "matches_odds": {
                        "type": "array",
                        "description": "A 2D array of odds. Each inner array represents a match. For a single selection, pass [1.85]. For a double selection (复式双选), pass [1.85, 3.20]. Example for 3 matches where the first is double selection: [[1.85, 3.20], [2.10], [1.90]]",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"}
                        }
                    },
                    "m": {
                        "type": "integer",
                        "description": "The number of matches in the parlay (e.g., 3 for 3串4)"
                    },
                    "n": {
                        "type": "integer",
                        "description": "The parlay type (e.g., 4 for 3串4)"
                    },
                    "stake_per_bet": {
                        "type": "number",
                        "description": "Stake per single combination bet (default 2.0)"
                    }
                },
                "required": ["matches_odds", "m", "n"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_chuantong_combinations",
            "description": "计算传统足彩（14场胜负彩、任选九场、6场半全场、4场进球彩）的复式注数与成本。当你在分析传统足彩时，如果采用了双选或全包的防冷策略，必须调用此工具计算总注数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "match_selections": {
                        "type": "array",
                        "description": "选定的场次结果数列表。例如任九选了10场，其中2场双选，8场单选，则传入 [2, 2, 1, 1, 1, 1, 1, 1, 1, 1]",
                        "items": {"type": "integer"}
                    },
                    "play_type": {
                        "type": "string",
                        "description": "玩法类型",
                        "enum": ["14_match", "renjiu", "6_htft", "4_goals"]
                    }
                },
                "required": ["match_selections", "play_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_simulated_ticket",
            "description": "生成500彩票网风格的虚拟模拟选号单。在完成分析后，不需要物理出票时，调用此工具将结果格式化展示。",
            "parameters": {
                "type": "object",
                "properties": {
                    "match": {"type": "string", "description": "赛事名称，如 '曼城 vs 切尔西'"},
                    "play_type": {"type": "string", "description": "玩法类型，如 '让球胜平负', '总进球'"},
                    "selection": {"type": "string", "description": "具体选项，如 '主胜', '3球'"},
                    "odds": {"type": "number", "description": "赔率 SP 值"},
                    "stake": {"type": "number", "description": "投入本金"},
                    "confidence": {"type": "number", "description": "AI 置信度 (0.0 - 1.0)"},
                    "reasoning": {"type": "string", "description": "简短的策略洞察理由"},
                    "lottery_type": {"type": "string", "description": "The type of lottery (e.g. JINGCAI, BEIDAN, ZUCAI)."}
                },
                "required": ["match", "play_type", "selection", "odds", "stake", "confidence", "reasoning"]
            }
        }
    }])
    
    tools.append({
        "type": "function",
        "function": {
            "name": "deep_evaluate_all_markets",
            "description": "全智能玩法识别引擎。利用 22 万条历史数据回测当前比赛的所有玩法，计算真实的打出概率和期望值（EV）。大模型在做最终决策前必须调用此工具获取量化证据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "lottery_type": {"type": "string", "description": "当前彩种，例如 'JINGCAI', 'BEIDAN', 'ZUCAI'"},
                    "home_team": {"type": "string", "description": "主队名称"},
                    "away_team": {"type": "string", "description": "客队名称"},
                    "league": {"type": "string", "description": "联赛名称"},
                    "home_win_odds": {"type": "number", "description": "主胜赔率"},
                    "draw_odds": {"type": "number", "description": "平局赔率"},
                    "away_win_odds": {"type": "number", "description": "客胜赔率"}
                },
                "required": ["lottery_type", "home_team", "away_team", "league", "home_win_odds", "draw_odds", "away_win_odds"]
            }
        }
    })
    
    return tools

def get_mcp_tools() -> list:
    return [t.to_mcp() for t in _TOOLS]

async def execute_tool(name: str, args_dict: dict) -> dict:
    if name == "calculate_complex_parlay":
        from tools.atomic_skills import calculate_jingcai_parlay_prize
        odds = args_dict.get("matches_odds")
        m = args_dict.get("m")
        n = args_dict.get("n")
        return calculate_jingcai_parlay_prize(odds, m, n)

    if name == "calculate_chuantong_combinations":
        from tools.parlay_rules_engine import ParlayRulesEngine
        engine = ParlayRulesEngine()
        selections = args_dict.get("match_selections")
        play_type = args_dict.get("play_type")
        try:
            total_tickets = engine.calculate_chuantong_combinations(selections, play_type)
            return json.dumps({"status": "success", "total_tickets": total_tickets, "total_cost": total_tickets * 2}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

    if name == "get_league_persona":
        return get_league_persona(**args_dict)
    
    if name == "gather_match_intelligence":
        return gather_match_intelligence(**args_dict)
        
    if name == "generate_simulated_ticket":
        return generate_simulated_ticket(**args_dict)
        
    if name == "deep_evaluate_all_markets":
        return deep_evaluate_all_markets(**args_dict)
        
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
