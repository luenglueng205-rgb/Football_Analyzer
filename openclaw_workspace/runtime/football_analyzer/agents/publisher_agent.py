import os
import json
from openai import AsyncOpenAI
from datetime import datetime

try:
    from tools.paths import data_dir
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.paths import data_dir

class PublisherAgent:
    """
    负责将冷冰冰的终端日志，转化为具有极强专业性和传播性的《AI数字博彩研报》。
    """
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-test")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
    def report_dir(self) -> str:
        return data_dir("reports")

    def report_path(self, home: str, away: str, date_str: str) -> str:
        safe_home = str(home).replace(os.sep, "_")
        safe_away = str(away).replace(os.sep, "_")
        filename = f"{date_str}_{safe_home}_vs_{safe_away}.md"
        return os.path.join(self.report_dir(), filename)

    def _write_report(self, report: str, home: str, away: str, date_str: str) -> str:
        filename = self.report_path(home, away, date_str)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        return filename

    async def publish(self, home: str, away: str, os_result: dict) -> str:
        if os.getenv("OPENCLAW_MOCK_LLM") == "1":
            date_str = datetime.now().strftime("%Y%m%d")
            report = "\n".join([
                f"# {date_str} {home} vs {away} 研报（MOCK）",
                "",
                "## Scout 情报",
                str(os_result.get("scout_report") or ""),
                "",
                "## 三派观点",
                json.dumps(os_result.get("debates") or {}, ensure_ascii=False, indent=2),
                "",
                "## 最终裁决",
                str(os_result.get("final_decision") or ""),
                "",
            ])
            self._write_report(report, home, away, date_str)
            return report

        print(f"\n[📰 Publisher] 正在撰写《AI 华尔街数字博彩研报》...")
        
        prompt = f"""
你是《华尔街数字博彩研报》的首席AI分析师，文风专业、犀利、带有一点华尔街交易员的傲慢。
请根据以下内部多空博弈会议的记录，撰写一篇针对 {home} vs {away} 的公开投资研报。
研报必须包含：
1. 赛事基本面概述。
2. 交易大厅激辩实录（简述三派宽客的分歧点）。
3. 首席风控官(Judge)的最终裁决与资金管理建议。
4. 使用 Markdown 格式，排版精美，适合发到公众号或 Telegram。

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
            filename = self._write_report(report, home, away, date_str)
            print(f"[📰 Publisher] 研报已生成并保存至: {filename}")
            return report
            
        except Exception as e:
            print(f"[📰 Publisher] 研报生成失败: {e}")
            return "研报生成失败"
