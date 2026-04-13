#!/usr/bin/env python3
"""
综合分析报告生成器
功能：
1. 生成竞彩足球分析报告
2. 生成北京单场分析报告
3. 生成传统足彩分析报告
4. 生成综合投注建议
"""

import json
import os
import sys
from typing import Dict, List, Optional
from datetime import datetime

# 路径设置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PROJECT_ROOT)
DATA_DIR = os.path.join(BASE_DIR, 'data', 'chinese_mapped')

# 导入其他模块
sys.path.insert(0, SCRIPT_DIR)
try:
    from odds_analyzer import (
        analyze_value_bets_by_odds_range,
        analyze_value_bets_by_league,
        find_best_value_combinations,
        load_data as load_odds_data,
        calculate_bookmaker_margin
    )
    from strategy_backtest import (
        backtest_all_strategies,
        backtest_strategy,
        strategy_favorite_only,
        strategy_low_odds_home,
        load_data as load_backtest_data
    )
    MODULES_AVAILABLE = True
except ImportError as e:
    MODULES_AVAILABLE = False


def load_rules() -> Dict:
    """加载官方规则"""
    filepath = os.path.join(PROJECT_ROOT, 'official_rules.json')
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_jingcai_report() -> str:
    """生成竞彩足球分析报告"""
    data = load_odds_data("竞彩足球")
    matches = data["matches"]
    rules = load_rules()
    
    report = []
    report.append("=" * 80)
    report.append("竞彩足球综合分析报告")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    
    # 1. 数据概览
    report.append("\n【一、数据概览】")
    report.append(f"  总比赛数: {len(matches):,}")
    valid = [m for m in matches if m.get('主队赔率')]
    report.append(f"  有效比赛数(有赔率): {len(valid):,}")
    report.append(f"  涉及联赛数: {len(data.get('leagues', []))}")
    
    # 2. 赔率区间分析
    report.append("\n【二、赔率区间分析】")
    odds_analysis = analyze_value_bets_by_odds_range(matches)
    
    report.append(f"{'区间':<10} {'比赛数':>8} {'主胜率':>8} {'理论':>8} {'主胜价值':>10} {'建议':>10}")
    report.append("-" * 65)
    
    for vb in odds_analysis:
        best = vb["best_bet"]
        value = vb["home_value"] if best[0] == "主胜" else (vb["draw_value"] if best[0] == "平局" else vb["away_value"])
        report.append(
            f"{vb['name']:<10} {vb['match_count']:>8} "
            f"{best[1]:>7.1f}% {best[2]:>7.1f}% {value:>+9.1f}% "
            f"{'值得投注' if value > 3 else ('谨慎' if value > 0 else '避免'):>10}"
        )
    
    # 3. 联赛价值排名
    report.append("\n【三、联赛价值排名TOP10】")
    league_analysis = analyze_value_bets_by_league(matches)
    
    report.append(f"{'联赛':<20} {'比赛数':>8} {'主胜率':>8} {'主胜价值':>10} {'整体价值':>10} {'建议':>10}")
    report.append("-" * 70)
    
    for league in league_analysis[:10]:
        rec = league["recommendation"]["type"]
        rec_text = {"avoid": "避免", "neutral": "中性", "slight_value": "轻投", "value_bet": "重点投"}.get(rec, rec)
        report.append(
            f"{league['league_name']:<20} {league['match_count']:>8} "
            f"{league['home_win_rate']:>7.1f}% {league['home_value']:>+9.1f}% {league['overall_value']:>+9.1f}% "
            f"{rec_text:>10}"
        )
    
    # 4. 策略回测结果
    report.append("\n【四、策略回测结果】")
    # 使用部分数据加速
    sample_matches = matches[:50000]
    strategies = [
        ("只押热门(<1.5)", strategy_favorite_only),
        ("只押低赔(<1.8)", strategy_low_odds_home),
    ]
    
    report.append(f"{'策略':<25} {'投注数':>8} {'胜率':>8} {'ROI':>10} {'最大连赢':>8} {'评价':>10}")
    report.append("-" * 75)
    
    for name, func in strategies:
        result = backtest_strategy(sample_matches, func)
        roi = result["roi"]
        evaluation = "优秀" if roi > 5 else ("良好" if roi > 0 else ("一般" if roi > -5 else "较差"))
        report.append(
            f"{name:<25} {result['total_bets']:>8} "
            f"{result['win_rate']:>7.1f}% {roi:>+9.1f}% "
            f"{result['max_win_streak']:>8} {evaluation:>10}"
        )
    
    # 5. 投注建议
    report.append("\n【五、综合投注建议】")
    report.append("  根据历史数据分析，建议如下：")
    report.append("")
    report.append("  1. 低赔稳健策略:")
    report.append("     - 选择赔率1.3-1.5的主队胜，历史胜率约70-80%")
    report.append("     - 适合资金充裕、追求稳定的玩家")
    report.append("     - 建议2-3串1组合，提高收益")
    report.append("")
    report.append("  2. 价值投注策略:")
    report.append("     - 关注赔率3.0-4.0的选项，可能存在价值")
    report.append("     - 适合有一定分析能力的玩家")
    report.append("")
    report.append("  3. 串关策略:")
    report.append("     - 2串1/3串1是最佳选择")
    report.append("     - 避免超过4串，风险急剧增加")
    
    report.append("\n" + "=" * 80)
    
    return "\n".join(report)


def generate_beijing_report() -> str:
    """生成北京单场分析报告"""
    data = load_odds_data("北京单场")
    matches = data["matches"]
    
    report = []
    report.append("=" * 80)
    report.append("北京单场综合分析报告")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    
    # 数据概览
    report.append("\n【一、数据概览】")
    report.append(f"  总比赛数: {len(matches):,}")
    valid = [m for m in matches if m.get('主队赔率')]
    report.append(f"  有效比赛数: {len(valid):,}")
    
    # 赔率区间分析
    report.append("\n【二、赔率区间分析】")
    odds_analysis = analyze_value_bets_by_odds_range(matches)
    
    for vb in odds_analysis[:5]:
        report.append(f"  {vb['name']}: 主胜{vb['home_win_rate']:.1f}%, 理论{vb['theoretical_home']:.1f}%, 价值{vb['home_value']:+.1f}%")
    
    # 联赛分析
    report.append("\n【三、联赛价值排名TOP5】")
    league_analysis = analyze_value_bets_by_league(matches)
    
    for i, league in enumerate(league_analysis[:5], 1):
        report.append(f"  {i}. {league['league_name']}: 整体价值{league['overall_value']:+.1f}%")
    
    # 投注建议
    report.append("\n【四、投注建议】")
    report.append("  1. 上下盘策略: 总进球>2.5为上盘，约50%概率")
    report.append("  2. 单双策略: 单双各约50%，可作为串关搭配")
    report.append("  3. SP值分析: 注意SP值的实时变化")
    report.append("  4. 串关策略: 最高支持15串，选择2-4场最佳")
    
    report.append("\n" + "=" * 80)
    
    return "\n".join(report)


def generate_traditional_report() -> str:
    """生成传统足彩分析报告"""
    data = load_odds_data("传统足彩")
    matches = data["matches"]
    
    report = []
    report.append("=" * 80)
    report.append("传统足彩综合分析报告")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    
    # 数据概览
    report.append("\n【一、数据概览】")
    report.append(f"  总比赛数: {len(matches):,}")
    
    # 联赛分析
    report.append("\n【二、联赛特征分析】")
    league_analysis = analyze_value_bets_by_league(matches)
    
    for i, league in enumerate(league_analysis[:5], 1):
        report.append(f"  {i}. {league['league_name']}: 主胜{league['home_win_rate']:.1f}%, 价值{league['overall_value']:+.1f}%")
    
    # 投注建议
    report.append("\n【三、投注策略建议】")
    report.append("  1. 14场胜负:")
    report.append("     - 复式投注可提高中奖概率")
    report.append("     - 胆拖策略: 确定场次做胆，不确定场次复式")
    report.append("  2. 任选9场:")
    report.append("     - 选择9场最有把握的比赛")
    report.append("     - 可多选几场进行复式投注")
    report.append("  3. 半全场/进球:")
    report.append("     - 难度较高，建议小额尝试")
    
    report.append("\n" + "=" * 80)
    
    return "\n".join(report)


def generate_comprehensive_report() -> str:
    """生成综合分析报告"""
    report = []
    report.append("=" * 80)
    report.append("体育彩票综合分析报告")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    
    # 竞彩足球
    report.append("\n\n")
    report.append(generate_jingcai_report())
    
    # 北京单场
    report.append("\n\n")
    report.append(generate_beijing_report())
    
    # 传统足彩
    report.append("\n\n")
    report.append(generate_traditional_report())
    
    return "\n".join(report)


def save_report(report: str, filename: str):
    """保存报告到文件"""
    reports_dir = os.path.join(PROJECT_ROOT, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    filepath = os.path.join(reports_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"报告已保存: {filepath}")


# ============================================================
# 测试
# ============================================================

def main():
    """测试函数"""
    print("=" * 70)
    print("综合分析报告生成器 - 测试")
    print("=" * 70)
    
    print("\n【生成竞彩足球报告】")
    jingcai_report = generate_jingcai_report()
    print(jingcai_report[:2000])
    print("...")
    
    print("\n【生成北京单场报告】")
    beijing_report = generate_beijing_report()
    print(beijing_report[:1000])
    print("...")
    
    print("\n【生成传统足彩报告】")
    traditional_report = generate_traditional_report()
    print(traditional_report[:1000])
    print("...")
    
    # 保存报告
    save_report(jingcai_report, f"jingcai_report_{datetime.now().strftime('%Y%m%d')}.txt")
    
    print("\n✓ 测试完成!")


if __name__ == "__main__":
    main()
