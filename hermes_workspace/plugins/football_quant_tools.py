# Hermes Agent Plugin: Football Quant Arbitrage
# 注入到 ~/.hermes/plugins/ 即可被 Hermes 原生识别
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../standalone_workspace')))

from tools.global_odds_fetcher import get_global_arbitrage_data
from skills.latency_arbitrage import detect_latency_arbitrage
from skills.trap_identifier import identify_low_odds_trap
from skills.betfair_anomaly import detect_betfair_anomaly
from skills.kelly_variance_analyzer import analyze_kelly_variance

def fetch_live_global_odds(league: str, home: str, away: str) -> str:
    """获取外围(平博/必发)的高阶活水赔率。"""
    return get_global_arbitrage_data(league, home, away)

def check_latency_arbitrage(jingcai_odds: float, pinnacle_odds: float) -> str:
    """检测中国体彩与国际主流机构的时差套利空间。"""
    res = detect_latency_arbitrage(jingcai_odds, pinnacle_odds)
    return f"Arbitrage: {res['is_arbitrage']}, EV: {res['expected_value']}, Alert: {res['alert']}"

def run_bookmaker_mindset_check(match_data: dict) -> dict:
    """综合调用所有庄家思维工具，进行极限排雷。"""
    pass # Hermes 甚至会自己组合这些函数，无需我们硬编码大长串
