import json
import logging
from typing import Dict, Any, List

# 模拟 2026 年 MCP Server 暴露的工具能力
from tools.analyzer_api import AnalyzerAPI
from tools.smart_money_tracker import SmartMoneyTracker
from tools.bayesian_xg import BayesianXGModel
from tools.mcp_beidan_scraper import MCPBeidanScraper
from tools.vision_odds_reader import VisionOddsReader
from tools.monte_carlo import MonteCarloSimulator
from tools.dark_intel import DarkIntelExtractor
from tools.markowitz_portfolio import MarkowitzPortfolioOptimizer
from tools.betting_ledger import BettingLedger
from tools.asian_handicap_analyzer import AsianHandicapAnalyzer
from tools.parlay_filter_matrix import ParlayFilterMatrix
from tools.qrcode_ticket_generator import generate_ticket_qr
from tools.notification_dispatcher import dispatch_notification
from tools.memory_manager import MemoryManager
from skills.lottery_math_engine import LotteryMathEngine
import os

_ledger = BettingLedger()
_ah_analyzer = AsianHandicapAnalyzer()
_parlay_matrix = ParlayFilterMatrix()
_memory_manager = MemoryManager()

logger = logging.getLogger(__name__)

import functools
import inspect

def ensure_protocol(mock=False, source="local"):
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                res = await func(*args, **kwargs)
                if isinstance(res, dict) and "ok" in res and "meta" in res:
                    return res
                return {"ok": True, "data": res, "error": None, "meta": {"mock": mock, "source": source}}
            except Exception as e:
                logger.error(f"Tool {func.__name__} failed: {e}")
                return {"ok": False, "data": None, "error": {"code": "EXECUTION_ERROR", "message": str(e)}, "meta": {"mock": mock, "source": source}}
                
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                res = func(*args, **kwargs)
                if isinstance(res, dict) and "ok" in res and "meta" in res:
                    return res
                return {"ok": True, "data": res, "error": None, "meta": {"mock": mock, "source": source}}
            except Exception as e:
                logger.error(f"Tool {func.__name__} failed: {e}")
                return {"ok": False, "data": None, "error": {"code": "EXECUTION_ERROR", "message": str(e)}, "meta": {"mock": mock, "source": source}}
                
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

@ensure_protocol(mock=False, source="parlay_matrix")
def calculate_parlay(matches: list, parlay_type: str, total_stake: float) -> dict:
    """计算多场比赛串关的容错组合与资金分配（例如：2x1, 3x1, 3x4）。"""
    return _parlay_matrix.calculate_parlay(matches, parlay_type, total_stake)

@ensure_protocol(mock=False, source="ticket_generator")
def generate_qr_code(ticket_string: str) -> dict:
    """生成包含实单票根信息的二维码图片，用于线下实体店扫码出票。"""
    return generate_ticket_qr(ticket_string)

@ensure_protocol(mock=False, source="webhook_dispatcher")
async def send_webhook_notification(message: str) -> dict:
    """将最终的分析报告和实单二维码推送到用户的手机（微信/飞书）。"""
    url = os.getenv("WEBHOOK_URL", "dummy")
    return await dispatch_notification(url, message)

@ensure_protocol(mock=False, source="memory")
def retrieve_team_memory(team_name: str, context: str = "") -> dict:
    """检索关于某支球队的长期历史记忆和核心领悟"""
    return _memory_manager.retrieve_memory(team_name, context)

@ensure_protocol(mock=False, source="memory")
def save_team_insight(team_name: str, insight: str, match_id: str = "unknown") -> dict:
    """在分析结束后，将重要的战术发现或模型领悟持久化到长期记忆库"""
    return _memory_manager.save_insight(team_name, insight, match_id)

@ensure_protocol(mock=False, source="ledger")
def execute_bet(match_id: str, lottery_type: str, selection: str, odds: float, stake: float) -> dict:
    """执行真实下注并记录到本地 SQLite 账本，生成体彩实单代码。"""
    return _ledger.execute_bet(match_id, lottery_type, selection, odds, stake)

@ensure_protocol(mock=False, source="ledger")
def check_bankroll() -> dict:
    """查看当前真实可用资金(Bankroll)与历史 ROI，进行资金风控。"""
    return _ledger.check_bankroll()

@ensure_protocol(mock=False, source="ah_analyzer")
def analyze_asian_handicap_divergence(euro_home_odds: float, actual_asian_handicap: float, home_water: float) -> dict:
    """分析欧亚转换偏差。如果实际开出的亚盘比理论盘深或浅，系统将识别出这是诱盘还是真实看好。"""
    return _ah_analyzer.analyze_divergence(euro_home_odds, actual_asian_handicap, home_water)

@ensure_protocol(mock=False, source="ah_analyzer")
def analyze_water_drop(opening_water: float, live_water: float) -> dict:
    """计算从初盘到临场的水位下降幅度，判断庄家是真实降赔防范，还是高水阻筹。"""
    return _ah_analyzer.analyze_water_drop(opening_water, live_water)

@ensure_protocol(mock=False, source="api_stats")
def get_team_stats(team_name: str, league: str = None) -> Dict[str, Any]:
    """获取球队历史统计数据（如进球率、控球率等基本面数据）。"""
    return AnalyzerAPI.get_team_stats(team_name, league)

@ensure_protocol(mock=False, source="live_odds")
def get_live_odds(home_team: str, away_team: str) -> Dict[str, Any]:
    return AnalyzerAPI.get_live_odds_protocol(home_team=home_team, away_team=away_team)

@ensure_protocol(mock=False, source="live_fixtures")
def get_live_fixtures() -> Dict[str, Any]:
    """获取今日竞彩足球赛事列表"""
    return AnalyzerAPI.get_live_fixtures_protocol()

@ensure_protocol(mock=False, source="live_injuries")
def get_live_injuries(team_name: str) -> Dict[str, Any]:
    return AnalyzerAPI.get_live_injuries_protocol(team_name=team_name)

@ensure_protocol(mock=False, source="live_news")
def get_live_news(team_name: str, limit: int = 5) -> Dict[str, Any]:
    return AnalyzerAPI.get_live_news_protocol(team_name=team_name, limit=limit)

@ensure_protocol(mock=False, source="live_fixtures")
def get_today_fixtures(date: str, lottery_type: str) -> Dict[str, Any]:
    return AnalyzerAPI.get_live_fixtures_protocol()

@ensure_protocol(mock=False, source="scores")
def get_match_result(match_id: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "data": None,
        "error": {"code": "NOT_IMPLEMENTED", "message": "scores provider not enabled yet"},
        "meta": {"mock": False, "source": "scores", "confidence": 0.0, "stale": True},
    }

@ensure_protocol(mock=False, source="news_search")
def search_news(query: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "data": None,
        "error": {"code": "NOT_IMPLEMENTED", "message": "news search provider not enabled yet"},
        "meta": {"mock": False, "source": "news_search", "confidence": 0.0, "stale": True},
    }

@ensure_protocol(mock=True, source="beidan_scraper")
async def scrape_beidan_sp(home_team: str, away_team: str) -> Dict:
    """
    (MCP Browser Tool) 使用无头浏览器提取北京单场 (北单) 的实时让球数和 SP 值。
    当你分析的 lottery_type 是 beijing 时，必须调用此工具。
    """
    scraper = MCPBeidanScraper()
    return await scraper.extract_live_sp(home_team, away_team)

@ensure_protocol(mock=False, source="math_poisson")
def calculate_poisson_probabilities(home_xg: float, away_xg: float) -> Dict[str, float]:
    """
    (Math Tool) 传入主客队的预期进球 (xG)，计算泊松分布下的胜平负真实概率。
    请确保传入的 xG 已经过你的贝叶斯/伤停衰减调整。
    """
    from math import exp
    def _factorial(n: int) -> int:
        if n < 2: return 1
        r = 1
        for i in range(2, n + 1): r *= i
        return r
        
    def _poisson_pmf(k: int, mu: float) -> float:
        if k < 0: return 0.0
        if mu <= 0: return 1.0 if k == 0 else 0.0
        return exp(-mu) * (mu ** k) / _factorial(k)
        
    max_goals = 10
    p_home = 0.0
    p_draw = 0.0
    p_away = 0.0
    
    for hg in range(max_goals + 1):
        ph = _poisson_pmf(hg, home_xg)
        for ag in range(max_goals + 1):
            pa = _poisson_pmf(ag, away_xg)
            joint = ph * pa
            if hg > ag:
                p_home += joint
            elif hg == ag:
                p_draw += joint
            else:
                p_away += joint
                
    return {"home_win": p_home, "draw": p_draw, "away_win": p_away}

@ensure_protocol(mock=False, source="math_engine")
def calculate_all_markets(home_xg: float, away_xg: float, handicap: float = -1.0) -> dict:
    """计算竞彩/北单所有衍生玩法(胜平负、让球、总进球、半全场、上下单双)的理论概率。"""
    engine = LotteryMathEngine()
    return engine.calculate_all_markets(home_xg, away_xg, handicap)

@ensure_protocol(mock=False, source="smart_money")
def detect_smart_money(opening_odds: Dict[str, float], live_odds: Dict[str, float]) -> Dict[str, Any]:
    """
    (Risk Tool) 对比初盘(Opening)和即时盘(Live)，剥离庄家抽水，检测聪明资金(Sharp Money)的砸盘方向。
    """
    return SmartMoneyTracker.detect_sharp_money(opening_odds, live_odds)

@ensure_protocol(mock=True, source="vision_odds")
async def capture_and_analyze_trend(home_team: str, away_team: str) -> Dict:
    """
    (Vision Tool) 命令 MCP Browser 截取赔率走势图和必发交易量柱状图，
    使用 Vision 模型分析“盘感”（是缓慢降水还是断崖式跳水）。
    """
    reader = VisionOddsReader()
    return await reader.capture_and_analyze_trend(home_team, away_team)

@ensure_protocol(mock=False, source="monte_carlo")
def run_monte_carlo_simulation(home_xg: float, away_xg: float) -> Dict[str, Any]:
    """(Math Tool) 基于 xG 进行 10 万次微秒级蒙特卡洛模拟，精准预测胜平负、大小球等分布概率。"""
    sim = MonteCarloSimulator(simulations=100000)
    return sim.simulate_match(home_xg, away_xg)

@ensure_protocol(mock=True, source="dark_intel")
async def analyze_dark_intel(team_name: str, raw_social_text: str) -> Dict[str, Any]:
    """(Intel Tool) 分析球队的暗网情报/社交媒体生肉情绪，转化为 xG 修正因子。"""
    extractor = DarkIntelExtractor()
    return await extractor.analyze_social_sentiment(team_name, raw_social_text)

@ensure_protocol(mock=False, source="portfolio_optimizer")
def optimize_portfolio(matches: List[Dict]) -> Dict[str, Any]:
    """(Risk Tool) 现代投资组合理论：将多场比赛视为一个资产包，计算全局最优分数凯利注码分配。"""
    opt = MarkowitzPortfolioOptimizer()
    return opt.optimize_portfolio(matches)

# --- 封装为 OpenAI Tool Schemas ---
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_bet",
            "description": "执行真实下注并记录到本地 SQLite 账本，生成体彩实单代码。当你做出最终投资决策时，必须调用此工具生成实单。",
            "parameters": {
                "type": "object",
                "properties": {
                    "match_id": {"type": "string", "description": "比赛唯一标识, e.g. '20260414_RM_MCI'"},
                    "lottery_type": {"type": "string", "description": "彩种类型, e.g. 'jingcai'"},
                    "selection": {"type": "string", "description": "投注选项, e.g. '主胜', '大2.5'"},
                    "odds": {"type": "number", "description": "赔率"},
                    "stake": {"type": "number", "description": "投注金额"}
                },
                "required": ["match_id", "lottery_type", "selection", "odds", "stake"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_bankroll",
            "description": "查看当前真实可用资金(Bankroll)与历史总下注数，用于后续计算凯利仓位。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_asian_handicap_divergence",
            "description": "分析欧亚转换偏差。如果实际开出的亚盘比理论盘深或浅，系统将识别出这是诱盘还是真实看好。",
            "parameters": {
                "type": "object",
                "properties": {
                    "euro_home_odds": {"type": "number", "description": "主胜的欧洲赔率, e.g. 1.50"},
                    "actual_asian_handicap": {"type": "number", "description": "实际亚盘让球数, e.g. -0.75"},
                    "home_water": {"type": "number", "description": "亚盘主队水位"}
                },
                "required": ["euro_home_odds", "actual_asian_handicap", "home_water"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_water_drop",
            "description": "计算从初盘到临场的水位下降幅度，判断庄家是真实降赔防范，还是高水阻筹。",
            "parameters": {
                "type": "object",
                "properties": {
                    "opening_water": {"type": "number"},
                    "live_water": {"type": "number"}
                },
                "required": ["opening_water", "live_water"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_team_stats",
            "description": "获取球队历史统计数据（如进球率）。",
            "parameters": {
                "type": "object",
                "properties": {"team_name": {"type": "string"}, "league": {"type": "string"}},
                "required": ["team_name"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "scrape_beidan_sp",
            "description": "(MCP Browser Tool) 使用无头浏览器提取北京单场(北单)的实时让球数和 SP 值。当 lottery_type 为 beijing 时必调。",
            "parameters": {
                "type": "object",
                "properties": {"home_team": {"type": "string"}, "away_team": {"type": "string"}},
                "required": ["home_team", "away_team"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_poisson_probabilities",
            "description": "(Math Tool) 传入主客队的预期进球 (xG)，计算泊松分布下的胜平负真实概率。请确保传入的 xG 已经过你的衰减调整。",
            "parameters": {
                "type": "object",
                "properties": {"home_xg": {"type": "number"}, "away_xg": {"type": "number"}},
                "required": ["home_xg", "away_xg"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_all_markets",
            "description": "计算竞彩/北单所有衍生玩法(胜平负、让球、总进球、半全场、上下单双)的理论概率。",
            "parameters": {
                "type": "object",
                "properties": {
                    "home_xg": {"type": "number", "description": "主队预期进球数"},
                    "away_xg": {"type": "number", "description": "客队预期进球数"},
                    "handicap": {"type": "number", "description": "让球数(例如主让一球为 -1.0，客让一球为 1.0)"}
                },
                "required": ["home_xg", "away_xg"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "capture_and_analyze_trend",
            "description": "(Vision Tool) 命令 MCP 截取赔率走势图，分析“盘感”（缓慢降水还是跳水），寻找肉眼可见的诱盘形态。",
            "parameters": {
                "type": "object",
                "properties": {"home_team": {"type": "string"}, "away_team": {"type": "string"}},
                "required": ["home_team", "away_team"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "detect_smart_money",
            "description": "(Risk Tool) 对比初盘和即时盘，剥离抽水，检测聪明资金的砸盘方向。",
            "parameters": {
                "type": "object",
                "properties": {
                    "opening_odds": {
                        "type": "object",
                        "properties": {"home": {"type": "number"}, "draw": {"type": "number"}, "away": {"type": "number"}}
                    },
                    "live_odds": {
                        "type": "object",
                        "properties": {"home": {"type": "number"}, "draw": {"type": "number"}, "away": {"type": "number"}}
                    }
                },
                "required": ["opening_odds", "live_odds"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_monte_carlo_simulation",
            "description": "(Math Tool) 传入主客队的预期进球(xG)，进行 10 万次微秒级蒙特卡洛模拟，精准预测胜平负、大小球等分布概率。",
            "parameters": {
                "type": "object",
                "properties": {"home_xg": {"type": "number"}, "away_xg": {"type": "number"}},
                "required": ["home_xg", "away_xg"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_dark_intel",
            "description": "(Intel Tool) 传入球队的暗网情报/社交媒体生肉情绪，大模型将自动提取情绪得分，并将其转化为 xG 修正因子 (-1.0 ~ 1.0)。",
            "parameters": {
                "type": "object",
                "properties": {"team_name": {"type": "string"}, "raw_social_text": {"type": "string"}},
                "required": ["team_name", "raw_social_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_portfolio",
            "description": "(Risk Tool) 现代投资组合理论：将多场比赛视为一个资产包，根据 EV 和凯利公式，自动计算全局最优分数凯利注码分配。",
            "parameters": {
                "type": "object",
                "properties": {
                    "matches": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "match_name": {"type": "string"},
                                "selection": {"type": "string"},
                                "probability": {"type": "number"},
                                "odds": {"type": "number"},
                                "ev": {"type": "number"},
                                "lottery_type": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["matches"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_parlay",
            "description": "计算多场比赛串关的容错组合与资金分配。支持的 parlay_type: '2x1', '3x1', '3x4'。",
            "parameters": {
                "type": "object",
                "properties": {
                    "matches": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "match_id": {"type": "string"},
                                "selection": {"type": "string"},
                                "odds": {"type": "number"}
                            }
                        }
                    },
                    "parlay_type": {"type": "string", "description": "e.g. '2x1' or '3x4'"},
                    "total_stake": {"type": "number", "description": "总投注金额"}
                },
                "required": ["matches", "parlay_type", "total_stake"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_qr_code",
            "description": "生成包含实单票根信息的二维码图片，用于线下实体店扫码出票。",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_string": {"type": "string", "description": "出票字符串, e.g. '竞彩|001主胜+002客胜|2x1|100元'"}
                },
                "required": ["ticket_string"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_webhook_notification",
            "description": "将最终的分析报告和实单二维码推送到用户的手机（微信/飞书）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Markdown 格式的终极分析报告"}
                },
                "required": ["message"]
            }
        }
    }
]

TOOL_MAPPING = {
    "get_team_stats": get_team_stats,
    "get_live_odds": get_live_odds,
    "get_live_injuries": get_live_injuries,
    "get_live_news": get_live_news,
    "get_today_fixtures": get_today_fixtures,
    "get_match_result": get_match_result,
    "search_news": search_news,
    "scrape_beidan_sp": scrape_beidan_sp,
    "calculate_poisson_probabilities": calculate_poisson_probabilities,
    "calculate_all_markets": calculate_all_markets,
    "detect_smart_money": detect_smart_money,
    "capture_and_analyze_trend": capture_and_analyze_trend,
    "run_monte_carlo_simulation": run_monte_carlo_simulation,
    "analyze_dark_intel": analyze_dark_intel,
    "optimize_portfolio": optimize_portfolio,
    "execute_bet": execute_bet,
    "check_bankroll": check_bankroll,
    "analyze_asian_handicap_divergence": analyze_asian_handicap_divergence,
    "analyze_water_drop": analyze_water_drop,
    "calculate_parlay": calculate_parlay,
    "generate_qr_code": generate_qr_code,
    "send_webhook_notification": send_webhook_notification,
    "retrieve_team_memory": retrieve_team_memory,
    "save_team_insight": save_team_insight
}
