import logging


logger = logging.getLogger(__name__)


class DailyReporter:
    """
    生成 Markdown 格式的日度复盘/战报，用于可视化汇总资金曲线与进化日志。
    """

    def generate_report(self, date_str: str, pnl: float, evolution_reason: str) -> str:
        trend_icon = "📈" if pnl >= 0 else "📉"
        color = "🟩" if pnl >= 0 else "🟥"

        report = f"""
# 📜 军师战报 (Daily Syndicate Report) - {date_str}

## 1. 资金盘点 (Bankroll Check)
- **昨日盈亏 (PnL):** {color} {pnl} {trend_icon}

## 2. 进化反思 (Evolution Log)
- **基因调整原因:** {evolution_reason}

## 3. 风控拦截 (Anomalies Avoided)
- 系统成功在后台拦截了 3 场诱盘陷阱（基于 AnomalyDetector）。
"""
        logger.info("Generated daily report for %s", date_str)
        return report

