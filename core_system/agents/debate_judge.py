import asyncio
import os
import json
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class MultiAgentDebateEngine:
    """
    2026 版多路并行辩论引擎 (Multi-Agent Debate)
    消除单一大模型的幻觉和证实偏差。
    """
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-test")
        try:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        except Exception:
            self.client = None

    async def run_debate(self, match_info: str, evidence: str) -> str:
        """
        主持一场关于是否投注的辩论。
        Agent A (激进派) vs Agent B (保守派) -> Judge (法官裁决)
        """
        if not self.client:
            print("⚠️ 未配置 API KEY，返回 Mock 辩论结果。")
            return self._mock_debate(evidence)
            
        print("\n[🏛️ Multi-Agent Debate] 启动多路并行辩论法庭...")
        
        # 1. 并发获取激进派和保守派的意见
        task_a = self._get_persona_opinion("激进派 (Value-Seeker)", 
            "你是一个极具攻击性的足彩精算师。你总能从数据的夹缝中找到 EV>0 的博冷机会，你认为庄家经常故意开出诱人的盘口。请阅读以下证据，给出强烈建议下注的理由。", 
            evidence)
            
        task_b = self._get_persona_opinion("保守派 (Risk-Averse)", 
            "你是一个极度保守的华尔街风控官。你极其厌恶风险，对任何微小的聪明资金异动都保持警惕，坚信'保住本金第一'。请阅读以下证据，寻找致命的漏洞，强烈建议放弃投注。", 
            evidence)
            
        try:
            opinion_a, opinion_b = await asyncio.wait_for(asyncio.gather(task_a, task_b), timeout=30.0)
        except asyncio.TimeoutError:
            print("    [⚠️ 辩论超时] 辩手未能按时提交证词。")
            opinion_a = "激进派因网络或推理超时未能提交证词。"
            opinion_b = "保守派因网络或推理超时未能提交证词。"
        
        print(f"    [辩手 A 激进派] 发言完毕。")
        print(f"    [辩手 B 保守派] 发言完毕。")
        
        # 2. 法官 (Judge) 综合裁决
        print("    [👨‍⚖️ 法官 Judge] 正在阅读双方辩词，结合 OpenClaw 记忆进行终极裁决...")
        judge_prompt = f"""
        你是一场足彩投资辩论的首席法官 (Chief Actuary)。
        当前比赛: {match_info}
        客观证据: {evidence}
        
        激进派意见: {opinion_a}
        保守派意见: {opinion_b}
        
        请作为绝对中立、理性的裁决者，指出双方的逻辑漏洞，并结合凯利准则，给出最终的、具有执行力的【终极投资决策】(Bet 或 Skip，以及具体的注码建议)。
        """
        
        try:
            response = await asyncio.wait_for(self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": judge_prompt}],
                temperature=0.3 # 法官需要低温度，保持理性
            ), timeout=30.0)
            return response.choices[0].message.content
        except asyncio.TimeoutError:
            return "法官裁决超时，请根据前面搜集的硬数据执行保守策略。"
        except Exception as e:
            return f"法官裁决失败: {e}"

    async def _get_persona_opinion(self, persona_name: str, system_prompt: str, evidence: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"客观证据如下：{evidence}\n请给出你的观点。"}
                ],
                temperature=0.8
            )
            return response.choices[0].message.content
        except Exception:
            return f"{persona_name} 缺席辩论。"
            
    def _mock_debate(self, evidence: str) -> str:
        return """
[👨‍⚖️ 法官终极裁决]
激进派认为主队 xG 高达 2.1，EV>0，极具投资价值。
保守派指出客胜赔率发生了 4.5% 的异常偏移，庄家可能在掩护客队。
综合裁决：保守派的“聪明资金追踪”在北单体系中具有更高的置信度权重。虽然 xG 占优，但盘口异动打破了安全边际。
最终结论：**SKIP (放弃投注)**，保护本金。
"""
