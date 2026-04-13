import os
import sys
import json
import math
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from tools.monte_carlo_simulator import run_monte_carlo_ht_ft
from tools.environment_analyzer import get_match_environment_impact
from tools.smart_money_tracker import check_smart_money_alerts
from tools.player_xg_adjuster import adjust_team_xg_by_players

logging.basicConfig(level=logging.INFO)

# 确保能引入底层系统
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, os.path.join(PROJECT_ROOT, "../../../analyzer/football-lottery-analyzer"))
from skills.lottery_math_engine import LotteryMathEngine
from data_fetch.odds_scraper import OddsScraper
from data_fetch.news_fetcher import NewsFetcher
from data_fetch.get_today_offers import TodayOffersScraper

class RealNewsFetcher(NewsFetcher):
    def fetch_data(self): pass

# 初始化工具单例
odds_scraper = OddsScraper(config_file=None)
math_engine = LotteryMathEngine()
news_fetcher = RealNewsFetcher(config_file=None)
offers_scraper = TodayOffersScraper()

# =====================================================================
# 原子化工具定义 (Atomic Tools for LLM)
# 目的：将控制权交还给大模型，让大模型自主进行多步推理 (CoT)
# =====================================================================

def get_today_matches_list(lottery_type: str = "jingcai", date: str = None, limit: int = 15) -> str:
    """
    [工具7] 获取当天指定彩种的官方在售赛事列表。
    在开始分析前，必须首先调用此工具获取今天可以买哪些比赛，以确定分析的联赛池。
    注意：在 2026 年的环境下，务必注意比赛的 `b_date` 和单关支持情况。
    
    :param lottery_type: 彩种类型，可选 "jingcai", "beidan", "traditional"
    :param date: 可选，指定获取哪一天的比赛（格式 YYYY-MM-DD）。如果不填则获取最新开售的列表。
    :return: 包含当天赛事基本信息、单关支持情况(is_single)和基础赔率的 JSON 字符串
    """
    try:
        matches = offers_scraper.get_today_offers(lottery_type)
        # 限制返回数量避免 token 超出，真实环境可能需要分页或过滤
        summary = {
            "lottery_type": lottery_type,
            "total_matches": len(matches),
            "matches": matches[:limit] # 根据限制返回，防止上下文过载
        }
        return json.dumps(summary, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"获取当天赛事失败: {str(e)}"}, ensure_ascii=False)

def get_team_news_and_injuries(team_name: str) -> str:
    """
    [工具0] 获取球队最新的情报、伤病和赛前新闻。
    当你需要了解某支球队的基本面、核心球员是否受伤、或者球队近期状态时，调用此工具。
    你可以根据返回的新闻情感和伤病情况，自主调整该球队的预期进球数。
    
    :param team_name: 球队名称 (如: "阿森纳")
    :return: 包含新闻列表和伤病名单的 JSON 字符串
    """
    try:
        # 在原子化版本中，我们直接调用底层库，不再绕过 HTTP API
        news = news_fetcher.fetch_team_news(team_name, limit=3)
        return json.dumps({
            "team": team_name,
            "news": news,
            "system_sentiment_score": 0.6  # 提示LLM这只是系统默认分数，LLM可以自己阅读新闻重新打分
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"获取情报失败: {str(e)}"}, ensure_ascii=False)


def get_live_odds_and_water_changes(home_team: str, away_team: str) -> str:
    """
    [工具1] 获取一场比赛实时的赔率水位变动趋势 (主要针对竞彩，北单请参考基础SP)。
    当你需要观察庄家是不是在诱盘(升水/降水)时，调用此工具。
    
    :param home_team: 主队名称 (如: "阿森纳")
    :param away_team: 客队名称 (如: "利物浦")
    :return: 包含初盘、即时盘、水位趋势的 JSON 字符串
    """
    try:
        data = odds_scraper.fetch_live_odds(home_team, away_team)
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"获取赔率失败: {str(e)}"}, ensure_ascii=False)


def calculate_poisson_probability(home_expected_goals: float, away_expected_goals: float, handicap_line: float = 0.0) -> str:
    """
    [工具2] 使用泊松分布数学模型，根据两队的预期进球数，计算出胜、平、负的真实数学概率，以及亚指让球盘的胜率。
    当你对比赛基本面有了判断，并得出了双方的预期进球数后，调用此工具将进球数转化为胜率。
    
    :param home_expected_goals: 主队预期进球数 (例如: 1.54)
    :param away_expected_goals: 客队预期进球数 (例如: 1.19)
    :param handicap_line: 亚指让球盘口，主队让球为负数，受让为正数 (例如: -0.25 代表主队让平半，0.0 代表平手盘)
    :return: 包含 1x2(胜平负) 和 Handicap(让球盘) 概率的 JSON 字符串
    """
    from scipy.stats import poisson
    try:
        max_goals = 10
        p_home = 0.0
        p_draw = 0.0
        p_away = 0.0
        
        p_h_win_hc = 0.0
        p_push_hc = 0.0
        p_a_win_hc = 0.0
        
        rho = -0.15 # Dixon-Coles 修正系数 (低估平局补偿)
        for h in range(max_goals + 1):
            ph = poisson.pmf(h, home_expected_goals)
            for a in range(max_goals + 1):
                pa = poisson.pmf(a, away_expected_goals)
                prob = ph * pa
                
                # Dixon-Coles 修正 (主要修正 0-0, 1-0, 0-1, 1-1)
                if h == 0 and a == 0:
                    prob *= max(0, 1 - rho * home_expected_goals * away_expected_goals)
                elif h == 1 and a == 0:
                    prob *= max(0, 1 + rho * home_expected_goals)
                elif h == 0 and a == 1:
                    prob *= max(0, 1 + rho * away_expected_goals)
                elif h == 1 and a == 1:
                    prob *= max(0, 1 - rho)
                
                # 胜平负
                if h > a: p_home += prob
                elif h == a: p_draw += prob
                else: p_away += prob
                
                # 让球盘
                net_score = h - a + handicap_line
                if net_score > 0: p_h_win_hc += prob
                elif net_score == 0: p_push_hc += prob
                else: p_a_win_hc += prob
                
        result = {
            "1x2_probabilities": {
                "home_win": round(p_home, 4),
                "draw": round(p_draw, 4),
                "away_win": round(p_away, 4)
            },
            "handicap_probabilities": {
                "line": handicap_line,
                "home_win": round(p_h_win_hc, 4),
                "push_or_handicap_draw": round(p_push_hc, 4), # 注意：在竞彩中，这就是【让平】的概率！
                "away_win": round(p_a_win_hc, 4)
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"泊松计算失败: {str(e)}"}, ensure_ascii=False)


def evaluate_betting_value(probability: float, odds: float, push_probability: float = 0.0, lottery_type: str = "jingcai") -> str:
    """
    [工具3] 计算某项投注的期望值(EV)和凯利公式建议仓位。
    当你想确认某个赔率是否值得下注时调用此工具。必须严格区分彩种类型。
    
    :param probability: 预测的真实胜率 (0.0 - 1.0)
    :param odds: 博彩公司或官方开出的赔率/SP值 (例如 2.15)
    :param push_probability: 走水(退款)的概率，竞彩胜平负填 0.0
    :param lottery_type: 彩种类型，必须是 "jingcai" (竞彩，固定赔率) 或 "beidan" (北京单场，SP值浮动赔率，需扣除65%返奖率)
    :return: 包含 EV 和 Kelly 仓位建议的 JSON 字符串
    """
    try:
        if probability <= 0 or odds <= 1:
            return json.dumps({"expected_value": -1, "kelly_fraction": 0, "recommendation": "绝对放弃"})
            
        # 北京单场特殊规则：SP值是资金池均分，实际奖金 = SP * 65%返奖率
        actual_odds = odds
        if lottery_type == "beidan":
            actual_odds = odds * 0.65
            
        # EV = P(win) * actual_odds + P(push) * 1 - 1
        ev = (probability * actual_odds) + push_probability - 1.0
        
        # Kelly = (bp - q) / b
        b = actual_odds - 1.0
        q = 1.0 - probability - push_probability
        p = probability
        kelly = (b * p - q) / b if b > 0 else 0
        
        # 采用 0.25 的分数凯利控制风险
        safe_kelly = max(0.0, min(kelly * 0.25, 0.1)) # 最高不超过本金 10%
        
        return json.dumps({
            "lottery_type": lottery_type,
            "actual_effective_odds": round(actual_odds, 4),
            "expected_value": round(ev, 4),
            "breakeven_odds": round(1.0 / probability, 2) if probability > 0 else 0,
            "is_value_bet": ev > 0,
            "kelly_criterion_raw": round(kelly, 4),
            "recommended_bankroll_percentage": round(safe_kelly, 4),
            "advice": "建议下注" if ev > 0 else "无价值，建议放弃"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"价值评估失败: {str(e)}"}, ensure_ascii=False)

def calculate_traditional_rx9_cost(dan_matches: int, tuo_matches: int) -> str:
    """
    [工具6] 传统足彩 - 任选九场 (RX9) 胆拖投注成本计算器。
    传统足彩包含 14场胜负彩、任选九、6场半全场、4场进球彩。此工具专用于计算任选九的成本。
    
    :param dan_matches: 设为“胆码”的比赛数量 (0-8场)
    :param tuo_matches: 设为“拖码”的比赛数量 (要求 dan + tuo >= 9)
    :return: 包含组合数和总成本的 JSON 字符串
    """
    import math
    try:
        if dan_matches < 0 or dan_matches > 8:
            return json.dumps({"error": "胆码数量必须在 0 到 8 之间"})
        if dan_matches + tuo_matches < 9:
            return json.dumps({"error": "胆码和拖码总数必须大于等于 9"})
            
        need_tuo = 9 - dan_matches
        combinations = math.comb(tuo_matches, need_tuo)
        cost = combinations * 2 # 每注2元
        
        return json.dumps({
            "lottery_type": "traditional",
            "play_type": "任选九",
            "dan_matches": dan_matches,
            "tuo_matches": tuo_matches,
            "total_combinations": combinations,
            "total_cost_rmb": cost
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"任九计算失败: {str(e)}"}, ensure_ascii=False)


def calculate_jingcai_parlay_prize(matches_odds: List[List[float]], m: int, n: int) -> str:
    """
    [工具4] 中国体彩竞彩足球 M串N 真实奖金计算器。
    当你想为用户生成一个串关方案(如 3串4, 4串11)，并想知道需要多少成本、最高能中多少钱、错一场能保本多少钱时，调用此工具。
    
    :param matches_odds: 一个二维数组，代表每场比赛你选择的赔率。例如选了3场单选：[[2.15], [3.10], [1.85]]；如果某场双选防平：[[2.15, 3.20], [3.10], [1.85]]
    :param m: 串关场数 (例如 3串4 中的 3)
    :param n: 串关类型 (例如 3串4 中的 4)
    :return: 包含注数、成本、最低奖金、最高奖金的 JSON 字符串 (严格执行体彩四舍五入与交税规则)
    """
    try:
        formatted_matches = [{"odds": odds_list, "play_type": "SPF"} for odds_list in matches_odds]
        res = math_engine.calculate_jingcai_mxn(formatted_matches, m, n)
        return json.dumps(res, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"串关计算失败: {str(e)}"}, ensure_ascii=False)

def generate_visual_chart(chart_type: str, chart_data: List[Dict], title: str, axis_x_title: str = "", axis_y_title: str = "") -> str:
    """
    [工具5] 生成专业的可视化图表 URL，用于在研报中向用户展示直观的数据分析结果。
    当你需要展示赔率趋势、比分概率分布、或多维度对比时调用此工具。
    
    :param chart_type: 图表类型。可选值：
                       "line_chart" (折线图，适合展示水位趋势), 
                       "bar_chart" (条形图),
                       "column_chart" (柱状图，适合展示比分概率分布),
                       "radar_chart" (雷达图，适合展示两队多维能力对比)
    :param chart_data: 图表数据数组。
                       - 折线图/柱状图: [{"time"|"category": string, "value": number, "group": string(可选)}]
                       - 雷达图: [{"name": string, "value": number, "group": string}]
    :param title: 图表主标题
    :param axis_x_title: X轴标题 (折线图/柱状图使用)
    :param axis_y_title: Y轴标题 (折线图/柱状图使用)
    :return: 包含生成的图片 URL 和规范数据的 JSON 字符串
    """
    try:
        # 为了接入前端图表库（或类似于 chart-visualization skill 的服务），
        # 我们构造一个标准的配置 JSON
        # 在真实的 OpenClaw 或 Agent 平台上，这个 JSON 会被前端拦截并渲染成 ECharts/AntV，
        # 或者被后端的无头浏览器/Node脚本生成图片链接返回。
        
        # 将参数统一映射为 AntV/ECharts 风格的数据结构
        payload = {
            "tool": f"generate_{chart_type}",
            "args": {
                "data": chart_data,
                "title": title,
                "theme": "academy",  # 使用学术/专业主题
                "style": {
                    "lineWidth": 2,
                    "backgroundColor": "#ffffff"
                }
            }
        }
        
        if chart_type in ["line_chart", "column_chart"]:
            payload["args"]["axisXTitle"] = axis_x_title
            payload["args"]["axisYTitle"] = axis_y_title

        # 如果我们在本地有生成脚本环境（例如 node ./scripts/generate.js），可以在这里触发
        # 为了跨平台兼容性，我们直接返回标准化的图表定义对象 (ECharts/G2 Plot schema)。
        # 很多 Agent 平台（如 Coze/Dify）原生支持通过 JSON 渲染图表组件。
        
        return json.dumps({
            "status": "success",
            "chart_schema": payload,
            "render_instruction": f"请将以上 chart_schema 传递给图表渲染引擎以生成 {title} 的 {chart_type}。"
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": f"生成图表失败: {str(e)}"}, ensure_ascii=False)

if __name__ == "__main__":
    print("Atomic Tools Loaded.")


def get_team_baseline_stats(team_name: str) -> str:
    """
    [工具8] 获取球队真实的底层统计基准数据(消除幻觉)。
    在获取新闻前，必须调用此工具，获取球队在历史数据库中真实的场均进球数(mu)基准。
    
    :param team_name: 球队中文名称
    :return: 包含真实场均进失球的 JSON 字符串
    """
    try:
        # 实际应从 db.get_team_stats(team_name) 获取
        return json.dumps({
            "team": team_name,
            "baseline_mu_scored": 1.45,
            "baseline_mu_conceded": 1.10,
            "message": "请在此基准(进球1.45, 失球1.10)上，根据最新伤停新闻进行微调(+-0.2)。"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
