/**
 * Football Lottery Analyst Skill
 * 足球彩票分析技能 - OpenClaw Skill规范
 */

const path = require('path');

/**
 * 计算隐含概率
 */
function calculateImpliedProbability(odds) {
  const { home, draw, away } = odds;
  return {
    home: 1 / home,
    draw: 1 / draw,
    away: 1 / away
  };
}

/**
 * 计算庄家抽水
 */
function calculateJuice(odds) {
  const probs = calculateImpliedProbability(odds);
  const total = probs.home + probs.draw + probs.away;
  const juice = (total - 1) * 100;
  
  return {
    percentage: juice,
    type: juice < 3 ? 'low' : juice < 5 ? 'normal' : 'high',
    interpretation: juice < 3 ? '庄家抽水低，市场竞争激烈' 
                 : juice < 5 ? '庄家抽水适中'
                 : '庄家抽水较高'
  };
}

/**
 * 识别价值投注
 */
function identifyValueBets(odds, estimatedProb) {
  const results = {};
  
  for (const [outcome, odd] of Object.entries(odds)) {
    const impliedProb = 1 / odd;
    const value = (estimatedProb[outcome] * odd) - 1;
    
    results[outcome] = {
      odds: odd,
      impliedProb: impliedProb,
      estimatedProb: estimatedProb[outcome],
      value: value,
      hasValue: value > 0.05
    };
  }
  
  return results;
}

/**
 * 计算串关赔率
 */
function calculateParlayOdds(matches, m) {
  let totalOdds = 1;
  
  for (const match of matches.slice(0, m)) {
    totalOdds *= match.odds;
  }
  
  return {
    totalOdds: totalOdds,
    combinations: 1,
    expectedReturn: totalOdds - 1
  };
}

/**
 * 主执行函数
 */
async function execute(input, context = {}) {
  const { action, league, home_team, away_team, odds, budget, stakes } = input;
  
  console.log('[Football Analyst] 开始分析...');
  console.log(`联赛: ${league || '未指定'}`);
  console.log(`对阵: ${home_team || '?'} vs ${away_team || '?'}`);
  
  // 默认赔率
  const defaultOdds = odds || { home: 2.0, draw: 3.2, away: 3.5 };
  const defaultBudget = budget || 100;
  
  // 1. 计算隐含概率
  const probs = calculateImpliedProbability(defaultOdds);
  
  // 2. 计算庄家抽水
  const juice = calculateJuice(defaultOdds);
  
  // 3. 评估各选项价值 (假设均匀分布)
  const estimatedProb = { home: 0.45, draw: 0.28, away: 0.27 };
  const values = identifyValueBets(defaultOdds, estimatedProb);
  
  // 4. 找出最佳投注
  let bestBet = null;
  let maxValue = -Infinity;
  
  for (const [outcome, data] of Object.entries(values)) {
    if (data.value > maxValue) {
      maxValue = data.value;
      bestBet = { outcome, ...data };
    }
  }
  
  // 5. 生成推荐
  const recommendations = [];
  
  if (bestBet && bestBet.hasValue) {
    const stake = Math.min(defaultBudget * 0.2, 50);
    const expectedReturn = stake * bestBet.odds;
    
    recommendations.push({
      type: 'single',
      selection: bestBet.outcome,
      odds: bestBet.odds,
      stake: stake,
      expectedReturn: expectedReturn,
      value: bestBet.value,
      confidence: Math.min(bestBet.value * 10, 0.9)
    });
  }
  
  // 6. 风险评估
  const riskAssessment = {
    overallRisk: maxValue > 0.1 ? 'medium' : 'high',
    kellyFraction: maxValue > 0 ? maxValue : 0,
    recommendedStake: bestBet ? Math.round(defaultBudget * Math.min(maxValue, 0.2)) : 0,
    maxAllowedStake: Math.round(defaultBudget * 0.2),
    warnings: maxValue < 0 ? ['期望值为负，不建议投注'] : []
  };
  
  // 返回结果
  return {
    status: 'success',
    data: {
      league: league || '未知联赛',
      match: `${home_team || '主队'} vs ${away_team || '客队'}`,
      odds: defaultOdds,
      probabilities: probs,
      juiceAnalysis: juice,
      valueAnalysis: values,
      recommendedBets: recommendations,
      riskAssessment: riskAssessment
    },
    confidence: bestBet ? 0.75 + bestBet.value * 0.5 : 0.5,
    warnings: riskAssessment.warnings
  };
}

/**
 * OpenClaw Skill导出格式
 */
module.exports = {
  name: 'football-lottery-analyst',
  version: '1.0.0',
  description: '中国体育彩票足球彩票智能分析技能',
  
  // Skill元数据
  metadata: {
    author: 'CodeBuddy Team',
    tags: ['football', 'lottery', 'betting', 'analysis']
  },
  
  // 执行入口
  handler: async (ctx) => {
    const { input, memory, config } = ctx;
    return await execute(input, { memory, config });
  },
  
  // 快捷方法
  analyze: async (params) => execute({ action: 'analyze', ...params }),
  recommend: async (params) => execute({ action: 'recommend', ...params }),
  parlay: async (params) => execute({ action: 'parlay', ...params })
};
