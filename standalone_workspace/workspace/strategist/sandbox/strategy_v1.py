import json
import math
import random
from collections import deque

# 生成模拟赔率历史数据
def generate_mock_data():
    random.seed(42)
    data = []
    for _ in range(15):  # 至少10场，这里生成15场
        home_odds = round(random.uniform(1.5, 3.5), 2)
        draw_odds = round(random.uniform(3.0, 5.0), 2)
        away_odds = round(random.uniform(1.5, 3.5), 2)
        # 根据赔率隐含概率随机生成赛果（偏向低赔方）
        prob_home = 1.0 / home_odds
        prob_draw = 1.0 / draw_odds
        prob_away = 1.0 / away_odds
        total_prob = prob_home + prob_draw + prob_away
        prob_home /= total_prob
        prob_draw /= total_prob
        prob_away /= total_prob
        r = random.random()
        if r < prob_home:
            result = 'H'
        elif r < prob_home + prob_draw:
            result = 'D'
        else:
            result = 'A'
        data.append({
            'home_odds': home_odds,
            'draw_odds': draw_odds,
            'away_odds': away_odds,
            'result': result
        })
    return data

# 凯利准则下注决策
def kelly_criterion(odds, prob_estimate, bankroll, fraction=0.25):
    # 计算凯利比例
    b = odds - 1  # 净赔率
    p = prob_estimate
    q = 1 - p
    if b <= 0:
        return 0.0
    f_star = (b * p - q) / b  # 完整凯利
    if f_star <= 0:
        return 0.0
    # 使用分数凯利控制风险
    f = fraction * f_star
    return f * bankroll

# 简单泊松变体：根据历史平均进球数估算概率（这里简化为主队胜率基于赔率隐含概率）
def estimate_prob(odds, result_type, market_avg_prob=0.5):
    # 使用赔率隐含概率作为估计，简单调整
    implied = 1.0 / odds
    return implied

# 回测函数
def backtest(data):
    bankroll = 1000.0
    initial_bankroll = bankroll
    daily_returns = []
    portfolio_values = [bankroll]
    max_drawdown = 0.0
    peak = bankroll
    wins = 0
    bets = 0

    for match in data:
        home_odds = match['home_odds']
        draw_odds = match['draw_odds']
        away_odds = match['away_odds']
        result = match['result']

        # 对每个结果计算凯利下注，选择预期价值最高的（这里简单只下注主胜）
        # 估计主胜概率（基于赔率隐含概率）
        prob_home = estimate_prob(home_odds, 'H')
        # 计算凯利下注额
        stake = kelly_criterion(home_odds, prob_home, bankroll)
        if stake > 0 and stake <= bankroll:
            bets += 1
            if result == 'H':
                profit = stake * (home_odds - 1)
                bankroll += profit
                wins += 1
            else:
                bankroll -= stake
            daily_returns.append((bankroll - portfolio_values[-1]) / portfolio_values[-1] if portfolio_values[-1] != 0 else 0)
            portfolio_values.append(bankroll)
            # 更新最大回撤
            if bankroll > peak:
                peak = bankroll
            drawdown = (peak - bankroll) / peak if peak > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        else:
            # 不下注时收益为0
            daily_returns.append(0.0)
            portfolio_values.append(bankroll)

    # 计算夏普比率
    if len(daily_returns) > 0:
        mean_return = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
        std_dev = math.sqrt(variance) if variance > 0 else 0.0001
        sharpe_ratio = mean_return / std_dev * math.sqrt(252)  # 年化，假设252个交易日
    else:
        sharpe_ratio = 0.0

    # 胜率
    win_rate = wins / bets if bets > 0 else 0.0

    # 计算代码哈希（简单模拟）
    code_hash = "a1b2c3d4e5f6g7h8i9j0"  # 固定哈希

    result_dict = {
        "strategy_id": "kelly_v1",
        "sharpe_ratio": round(sharpe_ratio, 4),
        "max_drawdown": round(max_drawdown, 4),
        "code_hash": code_hash
    }
    return result_dict

if __name__ == "__main__":
    data = generate_mock_data()
    result = backtest(data)
    print(json.dumps(result))
