import asyncio
import os
import json
import logging
from openai import AsyncOpenAI
from tools.visual_browser import VisualBrowser

logger = logging.getLogger(__name__)

class VisionOddsReader:
    """
    2026 版多模态盘口感知工具 (Vision Odds Trend Reader)
    调用 VisualBrowser 执行浏览器端的数据获取和视觉分析。
    """
    
    def __init__(self):
        self.model = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-test")
        try:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        except Exception:
            self.client = None

    async def capture_and_analyze_trend(self, home_team: str, away_team: str) -> dict:
        """
        命令 MCP Browser 截取澳客/懂帝的赔率走势图，并解析盘口走势。
        """
        print(f"\n    [📸 Vision Reader] 启动多模态感知。正在让无头浏览器检索 '{home_team}' 的赔率趋势...")
        
        try:
            browser = VisualBrowser()
            instruction = f"前往足球赔率网站(如澳客或懂球帝)，搜索 '{home_team}' vs '{away_team}' 的比赛。查看欧赔和亚盘的赔率走势图，以及必发交易量数据。分析：1. 赔率走势是平稳过渡还是断崖式下跌？ 2. 有无明显的诱盘特征（如强行升盘但水位居高不下）？请给出一小段盘感解读。"
            result_text = await browser.extract_info(instruction)
            
            print(f"    [📸 Vision Reader] 分析成功: {result_text[:100]}...")
            
            return {
                "status": "success",
                "vision_analysis": result_text,
                "source": "visual_browser"
            }
        except Exception as e:
            logger.error(f"视觉盘口分析失败: {e}")
            return {"status": "error", "message": str(e), "vision_analysis": "无法获取有效走势图", "source": "fallback"}

if __name__ == "__main__":
    reader = VisionOddsReader()
    result = asyncio.run(reader.capture_and_analyze_trend("曼城", "阿森纳"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
