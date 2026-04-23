import json
from tools.atomic_skills import (
    get_today_matches_list,
    get_team_news_and_injuries,
    calculate_poisson_probability,
    evaluate_betting_value,
    calculate_jingcai_parlay_prize,
    generate_visual_chart
)

print("==================================================")
print("🤖 模拟大模型 (LLM) 严格执行 SOP 的思维链与工具调用")
print("==================================================\n")

print("【用户输入】: 帮我分析一下今天的竞彩比赛，我想要一个稳健的混合过关串关方案。")
print("\n[LLM 思考] 识别到彩种为【竞彩】，第一步：调用 get_today_matches_list 获取在售赛事池。")
print("-> Calling Tool: get_today_matches_list(lottery_type='jingcai')")

# 因为在沙盒环境无法直接连外网体彩API，我们用 Mock 数据模拟工具返回的结果
mock_today_matches = {
    "lottery_type": "jingcai",
    "total_matches": 2,
    "matches": [
        {
            "match_num_str": "周三001",
            "league": "英超",
            "home_team": "阿森纳",
            "away_team": "利物浦",
            "handicap": -1,
            "odds": {
                "SPF": {"h": 2.15, "d": 3.40, "a": 2.80},
                "RQSPF": {"h": 4.50, "d": 3.80, "a": 1.55}
            }
        },
        {
            "match_num_str": "周三002",
            "league": "欧冠",
            "home_team": "皇马",
            "away_team": "曼城",
            "handicap": 1,
            "odds": {
                "SPF": {"h": 2.65, "d": 3.50, "a": 2.20},
                "RQSPF": {"h": 1.50, "d": 4.00, "a": 4.60}
            }
        }
    ]
}
print(f"<- Tool Return: {json.dumps(mock_today_matches, ensure_ascii=False)}")

print("\n[LLM 思考] 获取到两场焦点战。接下来我需要逐场分析。先看阿森纳打利物浦，查一下伤停。")
print("-> Calling Tool: get_team_news_and_injuries(team_name='阿森纳')")
mock_news = {"team": "阿森纳", "news": [{"title": "萨卡轻伤出战成疑", "sentiment": "neutral"}], "system_sentiment_score": 0.5}
print(f"<- Tool Return: {json.dumps(mock_news, ensure_ascii=False)}")

print("\n[LLM 思考] 萨卡出战成疑，阿森纳攻击力可能受损。我将阿森纳的预期进球设为 1.4，利物浦设为 1.2。现在调用泊松模型算概率。")
print("-> Calling Tool: calculate_poisson_probability(home_expected_goals=1.4, away_expected_goals=1.2, handicap_line=-1.0)")
res_poisson_1 = json.loads(calculate_poisson_probability(1.4, 1.2, -1.0))
print(f"<- Tool Return: {json.dumps(res_poisson_1, ensure_ascii=False)}")

print("\n[LLM 思考] 拿到真实概率了。主胜率 42.6%，让球主胜率才 15.6%。我来分别测算一下它们的 EV (期望值)。")
print("-> Calling Tool: evaluate_betting_value(probability=0.426, odds=2.15, lottery_type='jingcai') [测试胜平负]")
ev_spf_1 = json.loads(evaluate_betting_value(0.426, 2.15, 0.0, "jingcai"))
print(f"<- Tool Return: {json.dumps(ev_spf_1, ensure_ascii=False)}")

print("-> Calling Tool: evaluate_betting_value(probability=0.156, odds=4.50, lottery_type='jingcai') [测试让球胜平负]")
ev_rqspf_1 = json.loads(evaluate_betting_value(0.156, 4.50, 0.0, "jingcai"))
print(f"<- Tool Return: {json.dumps(ev_rqspf_1, ensure_ascii=False)}")

print("\n[LLM 思考] 两者 EV 都是负的！阿森纳单场没有投注价值。等等，我看一眼让负(利物浦受让赢盘)的概率。让负概率是 61.4%，赔率是 1.55。")
print("-> Calling Tool: evaluate_betting_value(probability=0.614, odds=1.55, lottery_type='jingcai') [测试让球负]")
ev_rq_away_1 = json.loads(evaluate_betting_value(0.614, 1.55, 0.0, "jingcai"))
print(f"<- Tool Return: {json.dumps(ev_rq_away_1, ensure_ascii=False)}")

print("\n[LLM 思考] 让负的 EV 也是负的 (-0.048)，竞彩抽水太狠了。但我必须出方案，我把【让负(1.55)】作为这场的最优防守选项放入备选池。")
print("\n[LLM 思考] 接下来看皇马打曼城。假设我算出皇马主场受让1球（让胜）的 EV 很高，赔率是 1.50。现在我把这两场组合起来，做一个 2串1。")
print("-> Calling Tool: calculate_jingcai_parlay_prize(matches_odds=[[1.55], [1.50]], m=2, n=1)")
res_parlay = json.loads(calculate_jingcai_parlay_prize([[1.55], [1.50]], 2, 1))
print(f"<- Tool Return: {json.dumps(res_parlay, ensure_ascii=False)}")

print("\n[LLM 思考] 最后，我需要生成一张图表来展示两队的预期进球和实力对比。")
print("-> Calling Tool: generate_visual_chart(chart_type='radar_chart', ...)")
res_chart = json.loads(generate_visual_chart("radar_chart", [{"name": "预期进球", "value": 1.4, "group": "阿森纳"}, {"name": "预期进球", "value": 1.2, "group": "利物浦"}], "赛前实力模型对比"))
print(f"<- Tool Return: {json.dumps(res_chart, ensure_ascii=False)}")

print("\n==================================================")
print("✅ LLM 思考完毕，开始输出最终 Markdown 研报...")
