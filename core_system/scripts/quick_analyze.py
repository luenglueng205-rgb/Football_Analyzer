#!/usr/bin/env python3
"""快速分析：基于已有赔率数据跑 LLM 决策"""
import os, sys, json, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv

load_dotenv()

# 今日已知赔率（来自 The Odds API 成功抓取的数据）
TODAY_MATCHES = [
    # ── 英超 2026-04-25 ──────────────────────────────────────────
    {
        "league_name": "英格兰超级联赛",
        "lottery_type": "竞彩足球",
        "home_team": "Fulham",
        "away_team": "Aston Villa",
        "commence_time": "2026-04-25T11:30:00Z",
        "odds": {"home_win": 2.61, "draw": 3.56, "away_win": 2.71},
    },
    {
        "league_name": "英格兰超级联赛",
        "lottery_type": "竞彩足球",
        "home_team": "Liverpool",
        "away_team": "Crystal Palace",
        "commence_time": "2026-04-25T14:00:00Z",
        "odds": {"home_win": 1.53, "draw": 4.60, "away_win": 5.95},
    },
    {
        "league_name": "英格兰超级联赛",
        "lottery_type": "竞彩足球",
        "home_team": "West Ham United",
        "away_team": "Everton",
        "commence_time": "2026-04-25T14:00:00Z",
        "odds": {"home_win": 2.35, "draw": 3.42, "away_win": 3.16},
    },
    {
        "league_name": "英格兰超级联赛",
        "lottery_type": "竞彩足球",
        "home_team": "Wolverhampton Wanderers",
        "away_team": "Tottenham Hotspur",
        "commence_time": "2026-04-25T14:00:00Z",
        "odds": {"home_win": 4.69, "draw": 4.21, "away_win": 1.71},
    },
    {
        "league_name": "英格兰超级联赛",
        "lottery_type": "竞彩足球",
        "home_team": "Arsenal",
        "away_team": "Newcastle United",
        "commence_time": "2026-04-25T16:30:00Z",
        "odds": {"home_win": 1.43, "draw": 4.84, "away_win": 7.41},
    },
    # ── 德甲 2026-04-25 ──────────────────────────────────────────
    {
        "league_name": "德国甲级联赛",
        "lottery_type": "竞彩足球",
        "home_team": "1. FC Heidenheim",
        "away_team": "FC St. Pauli",
        "commence_time": "2026-04-25T13:30:00Z",
        "odds": {"home_win": 2.35, "draw": 3.45, "away_win": 3.15},
    },
    {
        "league_name": "德国甲级联赛",
        "lottery_type": "竞彩足球",
        "home_team": "1. FC Köln",
        "away_team": "Bayer Leverkusen",
        "commence_time": "2026-04-25T13:30:00Z",
        "odds": {"home_win": 3.77, "draw": 3.98, "away_win": 1.93},
    },
    {
        "league_name": "德国甲级联赛",
        "lottery_type": "竞彩足球",
        "home_team": "Augsburg",
        "away_team": "Eintracht Frankfurt",
        "commence_time": "2026-04-25T13:30:00Z",
        "odds": {"home_win": 2.72, "draw": 3.72, "away_win": 2.52},
    },
    {
        "league_name": "德国甲级联赛",
        "lottery_type": "竞彩足球",
        "home_team": "FSV Mainz 05",
        "away_team": "Bayern Munich",
        "commence_time": "2026-04-25T13:30:00Z",
        "odds": {"home_win": 4.33, "draw": 4.59, "away_win": 1.70},
    },
    {
        "league_name": "德国甲级联赛",
        "lottery_type": "竞彩足球",
        "home_team": "VfL Wolfsburg",
        "away_team": "Borussia M'gladbach",
        "commence_time": "2026-04-25T13:30:00Z",
        "odds": {"home_win": 3.11, "draw": 3.67, "away_win": 2.30},
    },
]


async def run_analysis():
    from openai import AsyncOpenAI

    api_key = os.getenv("DEEPSEEK_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    SYSTEM_PROMPT = """你是顶级足彩投注分析师（AI原生 v1）。
你极度厌恶风险，只在有明显正期望值时才建议下注。

竞彩返奖率约89%，这意味着你的预测概率必须 > (1/odds) / 0.89 才算有真正的正edge。
例如：赔率2.0，隐含概率50%，调整后需要56.2%才有正edge。

请用中文回答。

考虑因素：
1. 赔率是否反映真实实力差（用 odds→隐含概率 判断市场定价）
2. 主客场因素（主场约+8%~10%胜率加成）
3. 热门陷阱（大众一致看好时谨慎）

严格以JSON格式返回：
{"decision": "BET" 或 "SKIP", "confidence": "high"/"medium"/"low",
 "kelly_fraction": 0.0~0.2, "selection": "home_win"/"draw"/"away_win"/null,
 "odds": 赔率数值/null, "verdict": "一句话结论",
 "key_risks": ["风险1"], "reasoning": "3-5句推理过程"}"""

    results = []

    for match in TODAY_MATCHES:
        home = match["home_team"]
        away = match["away_team"]
        odds = match["odds"]

        implied = {k: round(1.0 / v, 3) for k, v in odds.items()}

        # 转换为北京时间
        ct = match["commence_time"]
        utc_hour = int(ct[11:13])
        bj_hour = utc_hour + 8
        time_str = f"{bj_hour:02d}:{ct[14:16]}"

        evidence = f"""【比赛】{match['league_name']} | {home} vs {away} | 开赛: {time_str} (北京时间)
【市场赔率（Pinnacle）】{home}(主) vs {away}(客)
  {home} 胜: {odds['home_win']} (隐含概率 {implied['home_win']})
  平局: {odds['draw']} (隐含概率 {implied['draw']})
  {away} 胜: {odds['away_win']} (隐含概率 {implied['away_win']})
【竞彩说明】返奖率89%，需预测概率 > 隐含概率/0.89 才算有正edge"""

        prompt = f"比赛信息：\n{evidence}\n\n请给出投注决策。"

        print(f"⏳ 分析中: {home} vs {away} ...", flush=True)

        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
                timeout=30.0,
            )
            raw = json.loads(resp.choices[0].message.content)
        except Exception as e:
            raw = {"decision": "SKIP", "confidence": "low", "kelly_fraction": 0,
                   "selection": None, "odds": None, "verdict": f"LLM错误: {e}",
                   "key_risks": [], "reasoning": str(e)}

        # 风控
        kelly = min(raw.get("kelly_fraction", 0), 0.15)
        if raw.get("confidence") == "low":
            kelly = 0
        sel = raw.get("selection")
        sel_odds = raw.get("odds") or (odds.get(sel) if sel else None)
        if sel_odds and float(sel_odds) < 1.5:
            kelly = kelly * 0.5

        stake = round(10000 * kelly, 2)
        approved = raw.get("decision") == "BET" and kelly > 0

        print(f"  → {raw.get('decision', '?')} | {raw.get('verdict', '')[:40]}")

        results.append({
            "league_name": match["league_name"],
            "lottery_type": match["lottery_type"],
            "home_team": home,
            "away_team": away,
            "time": time_str,
            "odds": odds,
            "decision": raw.get("decision"),
            "confidence": raw.get("confidence"),
            "kelly_fraction": raw.get("kelly_fraction"),
            "kelly_final": kelly,
            "selection": sel,
            "selection_odds": sel_odds,
            "stake": stake,
            "approved": approved,
            "verdict": raw.get("verdict"),
            "key_risks": raw.get("key_risks", []),
            "reasoning": raw.get("reasoning", ""),
        })

        await asyncio.sleep(0.5)

    # 输出报告
    print("\n" + "=" * 80)
    print("  ⚽ 今日竞彩足球 AI 投注决策报告")
    print(f"  生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    for m in results:
        emoji = "✅" if m["approved"] else "❌"
        print(f"{emoji} {m['time']} | {m['home_team']} vs {m['away_team']} | [{m['league_name']}]")
        print(f"   赔率: {m['home_team']}={m['odds']['home_win']} | draw={m['odds']['draw']} | {m['away_team']}={m['odds']['away_win']}")
        if m["approved"]:
            sel_emoji = {"home_win": "主胜", "draw": "平局", "away_win": "客胜"}.get(m["selection"], m["selection"])
            print(f"   → 下注: {sel_emoji} @ {m['selection_odds']} | Kelly={m['kelly_final']*100:.0f}% | 金额=¥{m['stake']:.0f} | 置信={m['confidence']}")
            print(f"   → {m['verdict']}")
        else:
            print(f"   → 跳过: {m['verdict']}")
            if m["key_risks"]:
                print(f"   → 风险: {'; '.join(m['key_risks'][:2])}")
        print()

    approved_list = [m for m in results if m["approved"]]
    total_stake = sum(m["stake"] for m in approved_list)
    print("-" * 80)
    print(f"  📊 汇总: {len(approved_list)} 注建议 | 建议总投入 ¥{total_stake:.0f} / ¥10000 ({total_stake/100:.1f}%)")
    print("-" * 80)
    print("  ⚠️  仅供参考，不构成投注建议。理性投注，量力而行。")

    # 保存
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    ts = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"{reports_dir}/quick_analysis_{ts}.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n已保存: quick_analysis_{ts}.json")


if __name__ == "__main__":
    asyncio.run(run_analysis())
