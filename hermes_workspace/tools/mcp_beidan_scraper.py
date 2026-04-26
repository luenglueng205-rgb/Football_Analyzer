import asyncio
import json
import logging
from tools.visual_browser import VisualBrowser

logger = logging.getLogger(__name__)

class MCPBeidanScraper:
    """
    2026 版北单 MCP 提取器 (MCP Beidan Scraper)
    该工具通过连接到本地的 VisualBrowser，自动打开 500.com，
    提取动态 SP 值（让球胜平负）。
    """
    
    def __init__(self, mcp_server_url: str = "http://localhost:3000/mcp"):
        self.mcp_server_url = mcp_server_url
        
    async def extract_live_sp(self, home_team: str, away_team: str) -> dict:
        """
        命令 VisualBrowser 提取特定比赛的北单 SP
        """
        print(f"    [MCP Browser] 启动视觉浏览器引擎，访问北单数据中心...")
        
        try:
            browser = VisualBrowser()
            instruction = f"前往 500.com 的北京单场比分直播或赔率页面，搜索 '{home_team}' 和 '{away_team}' 的比赛，提取让球数以及胜、平、负的即时 SP 值。如果找不到，请回复'未找到'"
            result_text = await browser.extract_info(instruction)
            
            print(f"    [MCP Browser] 成功提取到北单数据: {result_text[:100]}...")
            
            return {
                "match": f"{home_team} vs {away_team}",
                "raw_extracted_text": result_text,
                "lottery_type": "beijing",
                "source": "visual_browser",
                "status": "success"
            }
        except Exception as e:
            logger.error(f"提取北单数据失败: {e}")
            # 返回保守默认值以防阻塞
            return {
                "match": f"{home_team} vs {away_team}",
                "handicap": 0,
                "sp_home": 2.50,
                "sp_draw": 3.10,
                "sp_away": 2.50,
                "lottery_type": "beijing",
                "source": "fallback",
                "status": "error",
                "message": str(e)
            }

if __name__ == "__main__":
    scraper = MCPBeidanScraper()
    result = asyncio.run(scraper.extract_live_sp("曼联", "阿森纳"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
