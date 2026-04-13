import json
import logging
from typing import Dict, Any, List
import pandas as pd
from quant.risk_parity import RiskParityEngine
from backtest.engine import EventDrivenBacktester

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MacroQuantTools:
    """
    供大语言模型 (LLM) 调用的量化工具集封装。
    将底层的 Python 数学引擎和回测沙箱转化为符合 JSON Schema 的 Agent 工具。
    """
    
    @staticmethod
    def calculate_risk_parity_portfolio(asset_returns_json: str) -> str:
        """
        计算多资产风险平价 (Risk Parity) 最优权重。
        :param asset_returns_json: 包含多资产历史对齐收益率的 JSON 字符串
        """
        logger.info("执行工具: calculate_risk_parity_portfolio")
        try:
            # 将大模型传入的 JSON 转回 DataFrame
            data = json.loads(asset_returns_json)
            df_returns = pd.DataFrame(data)
            
            engine = RiskParityEngine(df_returns)
            optimal_weights = engine.optimize_weights()
            
            return json.dumps({
                "status": "success",
                "optimal_weights": optimal_weights,
                "message": "风险平价计算成功，各资产对组合的风险贡献已完全相等。"
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"风险平价计算失败: {e}")
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

    @staticmethod
    def run_historical_backtest(asset_prices_json: str, target_weights: Dict[str, float], initial_capital: float = 100000.0) -> str:
        """
        执行历史回测，验证策略权重是否符合风控要求。
        :param asset_prices_json: 历史价格数据的 JSON 字符串
        :param target_weights: 量化策略师生成的目标仓位权重
        """
        logger.info("执行工具: run_historical_backtest")
        try:
            data = json.loads(asset_prices_json)
            df_prices = pd.DataFrame(data)
            
            backtester = EventDrivenBacktester(df_prices)
            report = backtester.run_backtest(target_weights, initial_capital)
            
            # 删除过大的资金曲线数据，防止撑爆大模型上下文
            if "equity_curve_summary" in report:
                del report["equity_curve_summary"]
                
            return json.dumps({
                "status": "success",
                "backtest_report": report
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"历史回测失败: {e}")
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

# 全局入口函数映射，供 Agent 框架路由
def call_quant_tool(tool_name: str, **kwargs) -> str:
    tools = {
        "calculate_risk_parity_portfolio": MacroQuantTools.calculate_risk_parity_portfolio,
        "run_historical_backtest": MacroQuantTools.run_historical_backtest
    }
    if tool_name in tools:
        return tools[tool_name](**kwargs)
    return json.dumps({"error": f"Tool {tool_name} not found."})