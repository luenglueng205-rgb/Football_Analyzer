import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from mcp.server.fastmcp import FastMCP
from hermes_workspace.skills.news_arbitrage.social_listener import SocialNewsListener

# Initialize the MCP Server
mcp = FastMCP("NewsArbitrageListener")
listener = SocialNewsListener()

@mcp.tool()
def fetch_arbitrage_news(team_name: str) -> dict:
    """
    获取毫秒级最新突发新闻或社交媒体情报。
    用于捕捉赔率变动前的信息差，在庄家封盘前实现套利。
    
    Args:
        team_name: 要监听和获取新闻的球队名称 (如 'Arsenal')
        
    Returns:
        包含最新新闻文本、影响 xG(进球期望) 的浮点数以及毫秒级延迟的字典。
    """
    return listener.fetch_latest_news(team_name)

if __name__ == "__main__":
    # Start the FastMCP server with stdio transport
    print("Starting Social News Arbitrage MCP Server...", file=sys.stderr)
    mcp.run()