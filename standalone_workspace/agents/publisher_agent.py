import os
import json
from openai import AsyncOpenAI
from datetime import datetime

class PublisherAgent:
    """
    负责将冷冰冰的终端日志，转化为具有极强专业性和传播性的《AI数字博彩研报》。
    """
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-test")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
    async def publish(self, home: str, away: str, os_result: dict) -> str:
        print(f"\n[📰 Publisher] 主公，您的专属 AI 军师正在为您起草《破阵锦囊》...")
        
        prompt = f"""
你是主公（用户）身边最忠诚、最睿智的首席 AI 数字军师（Persona：有温度、有灵魂的卧龙）。
你的文风不应该是冷冰冰的机器日志，也不该是傲慢的华尔街交易员，而应该是一位深谙兵法、体贴主公资金安全、且精通现代数字博彩数学（泊松分布、凯利公式、竞彩/北单规则）的超级智囊。
请根据以下内部多空博弈会议的记录，为主公撰写一篇针对 {home} vs {away} 的专属投资锦囊《破阵锦囊》。

锦囊必须包含：
1. 战局纵览：用军师的口吻，为主公点破这场比赛的本质（是稳胆，还是诱盘陷阱？）。
2. 诸将廷推：简述系统内三派宽客（基本面、数据流、资金流）的分歧点。
3. 军师裁决：基于首席风控官(Judge)的最终判定，给出明确的资金管理和彩票玩法建议（需严格遵守竞彩或北单的 M串1、M串N 物理规则）。
4. 护主箴言：附上一句有温度的风控提醒，体现出你对主公本金的极致保护。
5. 使用 Markdown 格式，排版精美，适合在手机上阅读。

会议记录：
{json.dumps(os_result, ensure_ascii=False)}
"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            report = response.choices[0].message.content
            
            # 保存到本地文件
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"reports/{date_str}_{home}_vs_{away}.md"
            os.makedirs("reports", exist_ok=True)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"[📰 Publisher] 研报已生成并保存至: {filename}")
            return report
            
        except Exception as e:
            print(f"[📰 Publisher] 研报生成失败: {e}")
            return "研报生成失败"
