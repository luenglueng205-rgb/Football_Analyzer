import os

# 获取当前项目的绝对路径根目录，方便各模块导入
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 外部 API Keys 配置 (实战中应从系统环境变量或平台挂载)
API_KEYS = {
    "ALPHA_VANTAGE": os.getenv("ALPHA_VANTAGE_API_KEY", "DEMO_KEY"),
    "FRED": os.getenv("FRED_API_KEY", "DEMO_KEY"),
    "BINANCE": os.getenv("BINANCE_API_KEY", "DEMO_KEY")
}

# 系统风控配置红线 (风险平价优化器的约束条件)
RISK_LIMITS = {
    "MAX_SINGLE_ASSET_EXPOSURE": 0.40,   # 单一资产最高仓位占比 40%
    "MIN_CASH_BUFFER": 0.05,             # 强制保留 5% 现金作为安全垫
    "TARGET_ANNUAL_VOLATILITY": 0.12     # 投资组合目标年化波动率 12%
}

# 技能市场发现配置
SKILL_DISCOVERY = {
    "MARKETPLACE_URL": "https://api.clawhub.com/v1/skills/search", # 假设的 OpenClaw/WorkBuddy 市场地址
    "PREFERRED_PLATFORM": "workbuddy"
}