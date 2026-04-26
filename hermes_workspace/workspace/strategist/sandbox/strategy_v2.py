import json
import math
import random
from collections import deque

def generate_mock_data(num_games=10):
    data = []
    outcomes = ['H', 'D', 'A']
    for _ in range(num_games):
        home_odds = round(random.uniform(1.5, 5.0), 2)
        draw_odds = round(random.uniform(2.5, 6.0), 2)
        away_odds = round(random.uniform(1.5, 5.0), 2)
        result = random.choice(outcomes)
        data.append({
            'home_odds': home_odds,
            'draw_odds': draw_odds,
            'away_odds': away_odds,
            'result': result
        })
    return data

def kelly_fraction(odds, prob_estimate, bankroll_fraction=0.25):
    if odds <= 1 or prob_estimate <= 0 or prob_estimate >= 1:
        return 0.0
    b = odds - 1
    p = prob_estimate
    q = 1 - p
    f = (b * p - q) / b
    # 限制最大仓位比例
    f = max(0.0, min(f, bankroll_fraction))
    return f

def estimate_prob_from_odds(odds):
    # 简单隐含概率，不考虑边际
    return 1.0 / odds

def backtest_strategy(data, initial_bankroll=1000.0):
    bankroll = initial_bankroll
    equity_curve = [bankroll]
    trades = 0
    wins = 0
    losses = 0
    # 使用泊松分布变体：假设主队进球期望值为1.5，客队0.8，简单模拟
    # 这里我们直接基于赔率计算隐含概率，并用凯利准则
    for game in data:
        home_odds = game['home_odds']
        draw_odds = game['draw_odds']
        away_odds = game['away_odds']
        result = game['result']
        
        # 选择预测：找隐含概率最高的结果，且概率大于50%？简单策略：选主胜或客胜中概率较高的
        prob_home = estimate_prob_from_odds(home_odds)
        prob_draw = estimate_prob_from_odds(draw_odds)
        prob_away = estimate_prob_from_odds(away_odds)
        
        # 泊松变体：假设主队平均进球1.5，客队0.8，但这里直接用赔率隐含概率
        # 我们选择最高概率的结果作为预测，但只当概率超过0.4且赔率大于1.5时下注
        max_prob = max(prob_home, prob_draw, prob_away)
        if max_prob == prob_home and home_odds > 1.5 and max_prob > 0.4:
            predicted = 'H'
            odds = home_odds
        elif max_prob == prob_away and away_odds > 1.5 and max_prob > 0.4:
            predicted = 'A'
            odds = away_odds
        elif max_prob == prob_draw and draw_odds > 2.0 and max_prob > 0.4:
            predicted = 'D'
            odds = draw_odds
        else:
            continue  # 不下注
        
        # 凯利准则
        kelly_f = kelly_fraction(odds, max_prob)
        if kelly_f <= 0:
            continue
        
        bet_amount = bankroll * kelly_f
        if bet_amount <= 0:
            continue
        
        # 模拟下注
        if predicted == result:
            profit = bet_amount * (odds - 1)
            bankroll += profit
            wins += 1
        else:
            bankroll -= bet_amount
            losses += 1
        trades += 1
        equity_curve.append(bankroll)
    
    # 计算指标
    if trades == 0:
        return {
            'strategy_id': 'kelly_v2',
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'code_hash': 'abc123'
        }
    
    win_rate = wins / trades if trades > 0 else 0.0
    
    # 计算收益率序列
    returns = []
    for i in range(1, len(equity_curve)):
        if equity_curve[i-1] > 0:
            r = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(r)
        else:
            returns.append(0.0)
    
    if len(returns) == 0:
        sharpe = 0.0
    else:
        mean_ret = sum(returns) / len(returns)
        std_ret = math.sqrt(sum((r - mean_ret)**2 for r in returns) / len(returns)) if len(returns) > 1 else 0.0
        # 夏普比率：假设无风险利率为0，年化因子忽略（按每笔交易）
        sharpe = mean_ret / std_ret if std_ret > 0 else 0.0
    
    # 最大回撤
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    
    # 生成一个简单的哈希
    code_hash = hex(hash('kelly_v2_backtest'))[:8]
    
    return {
        'strategy_id': 'kelly_v2',
        'sharpe_ratio': round(sharpe, 4),
        'max_drawdown': round(max_dd, 4),
        'code_hash': code_hash
    }

if __name__ == '__main__':
    random.seed(42)  # 可重复性
    data = generate_mock_data(10)
    result = backtest_strategy(data, initial_bankroll=1000.0)
    print(json.dumps(result))
