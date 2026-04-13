from quant.risk_parity import RiskParityEngine
from backtest.engine import EventDrivenBacktester
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    系统总入口：演示多智能体全球宏观量化投资系统的核心工作流。
    步骤：动态挂载技能获取数据 -> 风险平价计算 -> 历史回测验证 -> 生成报告
    """
    logger.info("===============================================")
    logger.info("   全球宏观量化投资系统 (Global Macro Quant)   ")
    logger.info("===============================================\n")
    
    # ---------------------------------------------------------
    # 步骤 1: 模拟多智能体通过 ClawHub 挂载技能并获取多资产数据
    # ---------------------------------------------------------
    logger.info("[Orchestrator] 正在协调各 Agent 获取跨资产类别的历史行情数据...")
    
    # 实际应用中，这里是由 `discovery.py` 动态挂载的第三方工具（如雅虎财经、币安API）实时拉取数据。
    # 为保证系统直接可运行，这里使用 Pandas 构建四类资产（美股、黄金、美债、比特币）的两年对齐历史收益率。
    np.random.seed(1024)
    dates = pd.date_range(start="2022-01-01", periods=504, freq="B")
    
    # 模拟真实世界的资产波动率特征 (均值, 标准差, 交易日)
    mock_returns = pd.DataFrame({
        "SPY": np.random.normal(0.0004, 0.012, 504),   # S&P 500 (中收益, 中波动)
        "GLD": np.random.normal(0.0002, 0.008, 504),   # 黄金 (避险资产, 低收益, 低波动)
        "TLT": np.random.normal(0.0001, 0.005, 504),   # 20年期美债 (极低波动)
        "BTC": np.random.normal(0.0015, 0.035, 504)    # 比特币 (高收益, 极高波动)
    }, index=dates)
    
    logger.info(f"✅ 数据获取与时间轴对齐完成。数据范围: {dates[0].date()} 至 {dates[-1].date()}，共 {len(dates)} 个交易日。")
    
    # ---------------------------------------------------------
    # 步骤 2: 风控 Agent 介入，执行风险平价 (Risk Parity) 模型
    # ---------------------------------------------------------
    logger.info("\n[Risk Manager] 收到数据，正在摒弃均值-方差模型，计算风险平价最优仓位...")
    
    rp_engine = RiskParityEngine(mock_returns)
    try:
        optimal_weights = rp_engine.optimize_weights()
    except Exception as e:
        logger.error(f"风险平价优化失败: {e}")
        return
        
    logger.info("✅ 风险平价计算完成。各资产建议分配权重如下 (确保风险贡献度相等):")
    for asset, weight in optimal_weights.items():
        logger.info(f"  - {asset:4s}: {weight * 100:>5.2f}%")
        
    # 注意：高波动的 BTC 被分配了极低的权重（通常<5%），而极低波动的 TLT 获得了最大的权重。
    # 这正是“风险平价”的核心魅力：让各类资产对组合的总风险贡献一致，避免组合被加密货币的暴涨暴跌绑架。
        
    # ---------------------------------------------------------
    # 步骤 3: 策略 Agent 介入，执行历史回测验证 (Backtest)
    # ---------------------------------------------------------
    logger.info("\n[Quant Strategist] 收到风控权重，正在启动向量化回测沙箱验证策略有效性...")
    
    # 将收益率转化为收盘价格序列，用于回测引擎计算净值曲线
    mock_prices = 100 * (1 + mock_returns).cumprod()
    
    backtester = EventDrivenBacktester(mock_prices)
    performance_report = backtester.run_backtest(optimal_weights, initial_capital=1_000_000.0) # 100万初始资金
    
    # ---------------------------------------------------------
    # 步骤 4: 输出最终投研报告
    # ---------------------------------------------------------
    logger.info("\n===============================================")
    logger.info("   投资组合历史回测报告 (Portfolio Backtest)   ")
    logger.info("===============================================")
    logger.info(f"▶ 期初资金: $ {performance_report['initial_capital']:,.2f}")
    logger.info(f"▶ 期末净值: $ {performance_report['final_capital']:,.2f}")
    logger.info(f"▶ 绝对收益: {performance_report['total_return']*100:.2f}%")
    logger.info(f"▶ 年化收益: {performance_report['annualized_return']*100:.2f}%")
    logger.info(f"▶ 年化波动: {performance_report['annualized_volatility']*100:.2f}%")
    logger.info(f"▶ 夏普比率: {performance_report['sharpe_ratio']:.2f}")
    
    # 风控红线校验
    max_dd = performance_report['max_drawdown'] * 100
    if max_dd < -15.0:
        logger.error(f"🚨 警告: 最大回撤达到 {max_dd:.2f}%，超过了 -15% 的系统风控红线！策略将被打回重做。")
    else:
        logger.info(f"▶ 最大回撤: {max_dd:.2f}% (处于安全范围内)")
        
    logger.info("===============================================")
    logger.info("系统演示完毕。在真实的 OpenClaw 环境中，以上步骤将由 4 个独立的 LLM Agent 协作完成。")

if __name__ == "__main__":
    main()