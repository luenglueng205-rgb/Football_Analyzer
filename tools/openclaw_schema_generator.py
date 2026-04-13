import os
import json

def generate_openclaw_tools_json():
    """将 atomic_skills 生成符合 OpenClaw 规范的 JSON 描述"""
    
    schema = {
        "name": "football-quant-toolkit",
        "description": "足球彩票量化分析工具箱，提供赔率查询、泊松计算、EV评估和串关计算等原子能力。",
        "tools": [
            {
                "name": "get_team_baseline_stats",
                "description": "获取球队真实的底层统计基准数据(消除幻觉)。必须在设定预期进球数前调用，以获取真实的场均进球数基准。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "team_name": {"type": "string", "description": "球队中文名称"}
                    },
                    "required": ["team_name"]
                }
            },
            {
                "name": "get_today_matches_list",
                "description": "获取当天指定彩种的官方在售赛事列表。在开始分析前，必须首先调用此工具获取今天可以买哪些比赛，以确定分析的联赛池。包含单关支持状态和停售业务日期。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lottery_type": {"type": "string", "enum": ["jingcai", "beidan", "traditional"], "description": "彩种类型"},
                        "date": {"type": "string", "description": "比赛日期，格式YYYY-MM-DD，如 2026-04-14"},
                        "limit": {"type": "integer", "description": "限制返回的比赛场数，默认15，防止数据过多"}
                    },
                    "required": ["lottery_type"]
                }
            },
            {
                "name": "get_team_news_and_injuries",
                "description": "获取球队最新的情报、伤病和赛前新闻。当你需要了解某支球队的基本面、核心球员是否受伤、或者球队近期状态时调用。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "team_name": {"type": "string", "description": "球队名称 (如: 阿森纳)"}
                    },
                    "required": ["team_name"]
                }
            },
            {
                "name": "get_live_odds_and_water_changes",
                "description": "获取一场比赛实时的竞彩赔率、亚指让球盘口以及庄家资金水位变动趋势。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "home_team": {"type": "string", "description": "主队名称 (如: 阿森纳)"},
                        "away_team": {"type": "string", "description": "客队名称 (如: 利物浦)"}
                    },
                    "required": ["home_team", "away_team"]
                }
            },
            {
                "name": "calculate_poisson_probability",
                "description": "使用泊松分布数学模型，根据两队的预期进球数，计算出胜、平、负的真实数学概率，以及亚指让球盘的胜率。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "home_expected_goals": {"type": "number", "description": "主队预期进球数 (例如: 1.54)"},
                        "away_expected_goals": {"type": "number", "description": "客队预期进球数 (例如: 1.19)"},
                        "handicap_line": {"type": "number", "description": "让球盘口，主队让球为负数，受让为正数。注意：【竞彩让球】必须输入整数(如 -1, 1)，绝对不能输入亚指小数(-0.25)！"}
                    },
                    "required": ["home_expected_goals", "away_expected_goals"]
                }
            },
            {
                "name": "evaluate_betting_value",
                "description": "计算某项投注的期望值(EV)和凯利公式建议仓位。EV < 0 代表长期必亏。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "probability": {"type": "number", "description": "预测的真实胜率 (0.0 - 1.0)"},
                        "odds": {"type": "number", "description": "博彩公司开出的赔率 (例如 2.15)"},
                        "push_probability": {"type": "number", "description": "走水(退款)的概率，针对亚指整球盘口有效，竞彩胜平负填 0.0"},
                        "lottery_type": {"type": "string", "enum": ["jingcai", "beidan"], "description": "彩种类型。竞彩(jingcai)为固定赔率，北单(beidan)必须计算65%返奖率折损。"}
                    },
                    "required": ["probability", "odds", "lottery_type"]
                }
            },
            {
                "name": "calculate_traditional_rx9_cost",
                "description": "传统足彩 - 任选九场 (RX9) 胆拖投注成本计算器。计算给定胆码和拖码数量下的组合数与总金额。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dan_matches": {"type": "integer", "description": "设为“胆码”的比赛数量 (0-8场)"},
                        "tuo_matches": {"type": "integer", "description": "设为“拖码”的比赛数量 (要求 dan + tuo >= 9)"}
                    },
                    "required": ["dan_matches", "tuo_matches"]
                }
            },
            {
                "name": "calculate_jingcai_parlay_prize",
                "description": "中国体彩竞彩足球 M串N 真实奖金计算器。计算注数、成本、最低奖金、最高奖金。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "matches_odds": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "number"}
                            },
                            "description": "一个二维数组，代表每场比赛你选择的赔率。例如选了3场单选：[[2.15], [3.10], [1.85]]"
                        },
                        "m": {"type": "integer", "description": "串关场数 (例如 3串4 中的 3)"},
                        "n": {"type": "integer", "description": "串关类型 (例如 3串4 中的 4)"}
                    },
                    "required": ["matches_odds", "m", "n"]
                }
            },
            {
                "name": "generate_visual_chart",
                "description": "生成专业的可视化图表(多模态输出)，用于在研报中向用户展示直观的数据分析结果(如赔率趋势折线图、比分概率分布柱状图、或两队多维能力雷达图)。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chart_type": {"type": "string", "enum": ["line_chart", "bar_chart", "column_chart", "radar_chart"], "description": "图表类型。line_chart(折线图), column_chart(柱状图), radar_chart(雷达图)"},
                        "chart_data": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "图表数据数组。折线图/柱状图: [{'time'|'category': string, 'value': number, 'group': string}]。雷达图: [{'name': string, 'value': number, 'group': string}]"
                        },
                        "title": {"type": "string", "description": "图表主标题"},
                        "axis_x_title": {"type": "string", "description": "X轴标题 (折线图/柱状图使用)"},
                        "axis_y_title": {"type": "string", "description": "Y轴标题 (折线图/柱状图使用)"}
                    },
                    "required": ["chart_type", "chart_data", "title"]
                }
            },
            {
                "name": "run_monte_carlo_ht_ft",
                "description": "执行蒙特卡洛时间轴比赛模拟，针对“半全场”(HT/FT) 玩法。利用两队的预期进球数 (xG)，在毫秒级模拟10000次90分钟比赛进程，精确计算出9种半全场赛果(如胜平、胜胜)的概率。适用于竞彩和北京单场的半全场预测。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "home_xg": {
                            "type": "number",
                            "description": "主队全场预期进球数 (xG)，如 1.85"
                        },
                        "away_xg": {
                            "type": "number",
                            "description": "客队全场预期进球数 (xG)，如 0.95"
                        }
                    },
                    "required": ["home_xg", "away_xg"]
                }
            },
            {
                "name": "get_match_environment_impact",
                "description": "分析非结构化环境因素（天气和裁判）。将天气状况（如大雨、狂风）和裁判历史执法尺度（点球率、出牌率）转化为定量的 xG 修正系数。必须在调用泊松分布工具之前使用，以修正基础预期进球数。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "match_id": {
                            "type": "string",
                            "description": "比赛的唯一标识符"
                        },
                        "weather_desc": {
                            "type": "string",
                            "description": "天气描述的英文文本，如 'Heavy rain and very windy'"
                        },
                        "referee_name": {
                            "type": "string",
                            "description": "主裁判的英文姓名，如 'Anthony Taylor'"
                        }
                    },
                    "required": ["match_id", "weather_desc", "referee_name"]
                }
            },
            {
                "name": "check_smart_money_alerts",
                "description": "监控足球博彩赔率的异动，计算真实的隐含概率变化，识别是否有机构资金或聪明资金(Sharp Money)大量介入。输入初盘和即时盘的胜平负赔率。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "match_id": {
                            "type": "string",
                            "description": "比赛的唯一标识符"
                        },
                        "opening_odds": {
                            "type": "object",
                            "description": "初盘赔率字典，如 {'home': 2.1, 'draw': 3.4, 'away': 3.5}"
                        },
                        "current_odds": {
                            "type": "object",
                            "description": "即时赔率字典，如 {'home': 1.85, 'draw': 3.6, 'away': 4.2}"
                        }
                    },
                    "required": ["match_id", "opening_odds", "current_odds"]
                }
            },
            {
                "name": "adjust_team_xg_by_players",
                "description": "根据缺阵球员的 xG90(每90分钟预期进球) 和 xA90(每90分钟预期助攻) 数据，动态调整球队整体的基础 xG。专门用于精确量化伤病停赛对球队进攻火力的衰减影响。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "team_base_xg": {
                            "type": "number",
                            "description": "球队基于历史数据的初始预期进球(xG)，如 2.4"
                        },
                        "missing_players": {
                            "type": "array",
                            "description": "缺阵的核心球员列表，如 [{'name': 'De Bruyne', 'xg90': 0.25, 'xa90': 0.40, 'minutes_share': 1.0}]"
                        }
                    },
                    "required": ["team_base_xg", "missing_players"]
                }
            },
            {
                "name": "get_bayesian_xg_prior",
                "description": "贝叶斯动态更新引擎。当处于赛季初、球队刚刚换帅、或者历史比赛数据少于5场时使用。它结合球队身价等级和新帅加成，计算出一个贝叶斯先验的 xG (预期进球)，以取代失效的历史均值。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "team_value_tier": {
                            "type": "integer",
                            "description": "球队身价档次 (1-4)，1为最顶级的豪门，4为保级队或升班马。"
                        },
                        "recent_xg_avg": {
                            "type": "number",
                            "description": "球队近期极其有限的场均实际 xG。"
                        },
                        "matches_played": {
                            "type": "integer",
                            "description": "近期样本比赛场数 (越少代表置信度越低)。"
                        },
                        "is_new_manager": {
                            "type": "boolean",
                            "description": "球队是否刚刚更换主教练。"
                        },
                        "manager_elo_boost": {
                            "type": "number",
                            "description": "新帅带来的战术红利加成 (如名帅接手 +0.2，平庸教练 0.0)。"
                        }
                    },
                    "required": ["team_value_tier", "recent_xg_avg", "matches_played", "is_new_manager", "manager_elo_boost"]
                }
            },
            {
                "name": "optimize_multi_match_portfolio",
                "description": "同步凯利与马科维茨风险平价组合优化。当你筛选出多场具有 +EV (正期望) 的独立比赛并准备组合下注时，必须调用此工具。它会根据最大全局回撤上限 (15%)，同步计算并返回每场比赛的最佳资金分配比例，避免单日破产。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "bets": {
                            "type": "array",
                            "description": "潜在价值投注列表，格式为 [{'match_id': 'A', 'prob': 0.6, 'odds': 2.0}, ...]"
                        }
                    },
                    "required": ["bets"]
                }
            },
            {
                "name": "predict_closing_line_movement",
                "description": "击败收盘价 (CLV) 预测器。结合当前盘口赔率、模型的真实概率以及外部新闻情感热度，预测临场赔率是否会发生暴跌 (Steam Move)。用于决定是立刻抢下高赔率，还是观望。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "match_id": {
                            "type": "string",
                            "description": "比赛的唯一标识符"
                        },
                        "current_odds": {
                            "type": "number",
                            "description": "当前博彩公司开出的即时赔率 (如 2.10)"
                        },
                        "true_prob": {
                            "type": "number",
                            "description": "量化模型算出的真实胜率 (如 0.55)"
                        },
                        "news_sentiment": {
                            "type": "number",
                            "description": "外部新闻的情感热度得分 (-1.0 到 1.0，如重大利好为 0.8)"
                        }
                    },
                    "required": ["match_id", "current_odds", "true_prob", "news_sentiment"]
                }
            }
        ]
    }
    
    with open("football_quant_tools.json", "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)
    print("生成 OpenClaw Tools JSON 成功: football_quant_tools.json")

if __name__ == "__main__":
    generate_openclaw_tools_json()
