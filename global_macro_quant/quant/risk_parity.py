import numpy as np
import pandas as pd
from scipy.optimize import minimize
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskParityEngine:
    """
    底层纯数学与量化引擎 (供风控 Agent 调用)。
    风险平价 (Risk Parity) 的核心思想是让组合中每个资产对总风险的贡献度相等（Equal Risk Contribution）。
    摒弃传统的均值-方差优化器极端的权重分配，极大降低宏观黑天鹅事件的冲击。
    """
    def __init__(self, returns_df: pd.DataFrame):
        """
        :param returns_df: 包含多资产（股票、外汇、Crypto等）对齐后历史收益率的 DataFrame
        """
        self.returns = returns_df
        # 假设一年 252 个交易日，计算年化协方差矩阵
        self.cov_matrix = returns_df.cov().values * 252 

    def _calculate_portfolio_variance(self, weights: np.ndarray) -> float:
        """计算投资组合的总方差 (风险)"""
        return np.dot(weights.T, np.dot(self.cov_matrix, weights))

    def _risk_contribution(self, weights: np.ndarray) -> np.ndarray:
        """计算每个单一资产对组合总方差的边际风险贡献 (Marginal Risk Contribution)"""
        portfolio_variance = self._calculate_portfolio_variance(weights)
        if portfolio_variance == 0:
            return np.zeros_like(weights)
            
        marginal_risk_contribution = np.dot(self.cov_matrix, weights)
        risk_contribution = np.multiply(weights, marginal_risk_contribution) / portfolio_variance
        return risk_contribution

    def _risk_parity_objective(self, weights: np.ndarray) -> float:
        """优化器的目标函数：最小化各项资产风险贡献的方差 (使其趋于均等)"""
        risk_contribution = self._risk_contribution(weights)
        target_contribution = np.ones(len(weights)) / len(weights) # 理想状态：每个资产贡献 1/N 的风险
        # 计算当前风险贡献与目标贡献的平方差之和
        return np.sum(np.square(risk_contribution - target_contribution))

    def optimize_weights(self) -> dict:
        """执行 SciPy 优化，求解并返回风险平价最优权重"""
        num_assets = len(self.cov_matrix)
        initial_weights = np.ones(num_assets) / num_assets # 初始等权分配
        
        # 约束条件 1：所有权重之和必须等于 1 (100% 满仓，现金可视为一种无风险资产)
        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
        # 约束条件 2：每个资产的权重必须在 0 到 1 之间（禁止做空与杠杆，实战可修改此边界）
        bounds = tuple((0.0, 1.0) for _ in range(num_assets))

        result = minimize(
            self._risk_parity_objective,
            initial_weights,
            method='SLSQP', # 序列最小二乘规划算法
            bounds=bounds,
            constraints=constraints,
            options={'disp': False, 'ftol': 1e-9}
        )

        if not result.success:
            logger.error(f"风险平价权重优化失败: {result.message}")
            raise ValueError("风险平价权重优化失败")

        logger.info(f"✅ 风险平价优化成功，已平滑 {num_assets} 项资产的波动率。")
        # 将 Numpy 数组转换为带资产名称的字典
        optimized_dict = dict(zip(self.returns.columns, result.x))
        # 保留 4 位小数
        return {k: round(float(v), 4) for k, v in optimized_dict.items()}

if __name__ == "__main__":
    # 测试：构建四种不同波动率资产的模拟收益率矩阵
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=252, freq="B")
    mock_returns = pd.DataFrame({
        "SPY": np.random.normal(0.0005, 0.01, 252),    # 美股 (中波动)
        "GLD": np.random.normal(0.0002, 0.008, 252),   # 黄金 (低波动)
        "TLT": np.random.normal(0.0001, 0.005, 252),   # 美债 (极低波动)
        "BTC": np.random.normal(0.001, 0.03, 252)      # 加密货币 (极高波动)
    }, index=dates)
    
    engine = RiskParityEngine(mock_returns)
    weights = engine.optimize_weights()
    print("各资产的最优风险平价权重分布:")
    for asset, weight in weights.items():
        print(f"  - {asset}: {weight * 100:.2f}%")