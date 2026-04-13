import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventDrivenBacktester:
    """
    闭环回测验证框架 (Event-Driven Backtester / Vectorized Backtester)。
    量化策略 Agent 在制定出多空方向或风控 Agent 给出风险平价权重后，
    系统会调用此引擎对历史数据进行高保真回测，以验证夏普比率和最大回撤。
    如果回撤超过红线，策略会被打回重做。
    """
    def __init__(self, historical_prices: pd.DataFrame):
        """
        :param historical_prices: 各资产对齐后的历史收盘价或调整后收盘价 (Adjusted Close)
        """
        self.prices = historical_prices
        # 计算每日对数收益率以保证时间序列相加的准确性
        self.daily_returns = historical_prices.pct_change().dropna()

    def run_backtest(self, target_weights: dict, initial_capital: float = 100000.0) -> dict:
        """
        根据给定的目标权重执行向量化回测，返回核心绩效指标
        :param target_weights: {"SPY": 0.4, "GLD": 0.2, "BTC": 0.1, "CASH": 0.3}
        :param initial_capital: 期初资金
        """
        logger.info("⏳ 正在执行历史数据回测模拟...")
        
        if not self.daily_returns.empty and len(target_weights) > 0:
            # 过滤掉不在历史数据中的资产
            valid_weights = {k: v for k, v in target_weights.items() if k in self.daily_returns.columns}
            
            # 将字典转为 Pandas Series 以便与收益率 DataFrame 对齐计算
            weights_series = pd.Series(valid_weights)
            
            # 计算组合每日加权收益率 (矩阵乘法)
            portfolio_daily_returns = self.daily_returns.dot(weights_series)
            
            # 计算资金净值曲线 (Equity Curve)
            # 假设每日再平衡 (Daily Rebalancing) 以维持目标权重
            equity_curve = initial_capital * (1 + portfolio_daily_returns).cumprod()
            
            # 1. 计算总收益率与年化收益率
            total_return = (equity_curve.iloc[-1] / initial_capital) - 1
            # 假设一年 252 个交易日
            annualized_return = (1 + total_return) ** (252 / len(self.daily_returns)) - 1
            
            # 2. 计算年化波动率与夏普比率 (假设无风险利率为 0)
            annualized_volatility = portfolio_daily_returns.std() * np.sqrt(252)
            sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0.0
            
            # 3. 计算最大回撤 (Max Drawdown)
            # 计算历史最高点
            rolling_max = equity_curve.cummax()
            # 计算每日的回撤幅度
            drawdown = (equity_curve - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
        else:
            raise ValueError("回测失败：历史数据为空或传入的权重字典无效。")

        logger.info(f"✅ 回测完成。夏普比率: {sharpe_ratio:.2f} | 最大回撤: {max_drawdown*100:.2f}%")

        # 整理输出报告
        report = {
            "initial_capital": round(initial_capital, 2),
            "final_capital": round(equity_curve.iloc[-1], 2),
            "total_return": round(float(total_return), 4),
            "annualized_return": round(float(annualized_return), 4),
            "annualized_volatility": round(float(annualized_volatility), 4),
            "sharpe_ratio": round(float(sharpe_ratio), 4),
            "max_drawdown": round(float(max_drawdown), 4),
            # 资金曲线数据量大，仅返回时间戳字符串和净值
            "equity_curve_summary": {str(k.date()): round(v, 2) for k, v in equity_curve.items()}
        }
        
        return report

if __name__ == "__main__":
    # 构造模拟历史价格数据 (几何布朗运动)
    np.random.seed(42)
    dates = pd.date_range(start="2022-01-01", periods=504, freq="B") # 两年数据
    mock_returns = pd.DataFrame({
        "SPY": np.random.normal(0.0003, 0.01, 504),    # 年化收益约 7.5%
        "GLD": np.random.normal(0.0001, 0.008, 504),   # 年化收益约 2.5%
        "BTC": np.random.normal(0.0020, 0.03, 504)     # 年化收益极高，但波动巨大
    }, index=dates)
    
    # 将收益率转化为价格
    mock_prices = 100 * (1 + mock_returns).cumprod()
    
    # 模拟量化策略师给出的目标配置权重
    target_portfolio = {"SPY": 0.50, "GLD": 0.40, "BTC": 0.10}
    
    backtester = EventDrivenBacktester(mock_prices)
    performance = backtester.run_backtest(target_portfolio, 100000.0)
    
    print(f"年化收益: {performance['annualized_return']*100:.2f}%")
    print(f"最大回撤: {performance['max_drawdown']*100:.2f}%")
    print(f"夏普比率: {performance['sharpe_ratio']:.2f}")