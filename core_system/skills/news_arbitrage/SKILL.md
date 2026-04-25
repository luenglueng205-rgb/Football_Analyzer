# News Arbitrage Listener MCP Server

这是 Agentic Football Analyzer 的“顺风耳”组件，一个独立的 MCP (Model Context Protocol) Server，专门用于毫秒级情报套利 (Millisecond News Arbitrage)。

## 🎯 核心功能 (Features)
- **毫秒级事件监听**：监控球队突发伤病、阵容泄露、航班延误等关键负面新闻。
- **NLP 情感与 xG 评估**：将非结构化新闻文本转化为量化的进球期望偏差 (如 `xg_impact = -0.8`)。
- **无缝集成**：遵循 MCP 标准，大语言模型可以通过该服务器提供的工具在庄家变盘 (Line Shifting) 前瞬间进行截胡交易。

## 🛠 工具列表 (Tools)
### 1. `fetch_arbitrage_news(team_name: str)`
获取指定球队的最新突发情报。

**返回示例**:
```json
{
    "timestamp": 1713028302.392,
    "team": "Arsenal",
    "news": "【首发泄露】Arsenal 提前公布首发，为了周末欧冠全员轮换！",
    "xg_impact": -1.0,
    "source": "twitter_insider_webhook",
    "latency_ms": 32
}
```

## 🚀 运行与调试 (Running)

**依赖项**:
```bash
pip install mcp
```

**以标准 MCP 模式运行**:
该服务器采用 `stdio` 通信模式，您可以直接通过 Claude Desktop 等支持 MCP 协议的客户端接入：
```bash
python core_system/skills/news_arbitrage/server.py
```

或者使用 Inspector 进行独立调试：
```bash
npx @modelcontextprotocol/inspector python core_system/skills/news_arbitrage/server.py
```

**本地 API 直接集成**:
对于当前系统的 Python 后端，工具也被镜像注册在 `tool_registry_v2.py` 中，可以直接通过 `execute_tool("fetch_arbitrage_news", ...)` 被调用。