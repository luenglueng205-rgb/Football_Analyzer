import os
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI
import httpx

# 加载 .env
load_dotenv()

logger = logging.getLogger(__name__)

class LLMService:
    """
    统一的 LLM 调用服务
    """
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            api_key = os.getenv("OPENAI_API_KEY", "dummy_key")
            base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
            
            # 兼容处理：防止旧版本 openai 报错
            try:
                cls._client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    http_client=httpx.Client()
                )
            except Exception as e:
                # 兼容极简模式
                cls._client = OpenAI(
                    api_key=api_key,
                    base_url=base_url
                )
        return cls._client

    @classmethod
    def generate_report(cls, system_prompt: str, data_context: str) -> str:
        """
        根据 Agent 提供的上下文数据，生成自然语言分析报告
        """
        try:
            client = cls.get_client()
            # 如果没有配置真实的API KEY，返回模拟数据（避免程序报错中断）
            if client.api_key == "dummy_key" or client.api_key == "your_api_key_here":
                logger.warning("未配置有效的 OPENAI_API_KEY，返回模拟大模型推理结果。")
                return cls._get_mock_report(system_prompt, data_context)

            response = client.chat.completions.create(
                model="gpt-4o-mini", # 或 deepseek-chat, gpt-3.5-turbo
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请根据以下硬核数据，生成专业的足彩分析研报：\n{data_context}"}
                ],
                temperature=0.3,
                max_tokens=800
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return f"❌ AI 分析报告生成失败，请检查网络或 API Key。错误信息：{e}"

    @classmethod
    def _get_mock_report(cls, system_prompt: str, data_context: str) -> str:
        """模拟的自然语言输出，供测试时使用"""
        if "Scout" in system_prompt:
            return "【AI情报总结】主队近期状态火热（3胜1平），而客队在防守端存在隐患。根据历史数据，该联赛主场优势明显，且主队主力前锋伤愈复出，预计将对客队球门造成巨大威胁。"
        elif "Analyst" in system_prompt:
            try:
                obj = json.loads(data_context)
                odds = obj.get("odds", {})
                probs = obj.get("probabilities", {})
                o = odds.get("home")
                p = probs.get("home")
                if o and p:
                    ev = (float(o) * float(p)) - 1
                    if ev > 0:
                        return f"【AI盘口洞察】主胜赔率 {o:.2f} 与模型胜率 {p:.1%} 形成正向期望值（EV={ev:.4f}）。该盘口存在价值空间，但仍需结合阵容与临场信息确认。"
                    return f"【AI盘口洞察】主胜赔率 {o:.2f} 与模型胜率 {p:.1%} 计算得到期望值为负（EV={ev:.4f}）。当前盘口更偏向定价合理或略偏热，建议谨慎或寻找替代选项。"
            except Exception:
                pass
            return "【AI盘口洞察】当前赔率与模型胜率计算未显示明显正向期望值，建议谨慎或寻找替代选项。"
        elif "Strategist" in system_prompt:
            try:
                obj = json.loads(data_context)
                decision = obj.get("decision")
                reason = obj.get("decision_reason")
                ev = obj.get("expected_value")
                bet = obj.get("bet")
                thresholds = obj.get("thresholds", {})
                if decision == "skip":
                    target_hint = None
                    if isinstance(thresholds, dict):
                        for group, selections in thresholds.items():
                            if not isinstance(selections, dict):
                                continue
                            for sel, t in selections.items():
                                mv = t.get("move_to_positive_ev", {}) if isinstance(t, dict) else {}
                                target = mv.get("target_odds") if isinstance(mv, dict) else None
                                line = t.get("line") if isinstance(t, dict) else None
                                if target:
                                    suffix = f"@{line}" if line is not None else ""
                                    target_hint = f"{group}:{sel}{suffix} 转正赔率≥{float(target):.2f}"
                                    break
                            if target_hint:
                                break
                    if ev is not None:
                        suffix = f"；监控：{target_hint} 再考虑介入" if target_hint else ""
                        return f"【AI策略生成】本场策略建议不下注：{reason}（EV={float(ev):.4f}）{suffix}。"
                    suffix = f"；监控：{target_hint} 再考虑介入" if target_hint else ""
                    return f"【AI策略生成】本场策略建议不下注：{reason}{suffix}。"
                if bet:
                    market = bet.get("market") or bet.get("type")
                    line = bet.get("line")
                    suffix = f"@{line}" if line is not None else ""
                    return f"【AI策略生成】建议下注 {market}:{bet.get('selection')}{suffix}，参考赔率 {bet.get('odds')}，建议投注 {bet.get('stake')}。策略已自动对齐风控上限。"
            except Exception:
                pass
            return "【AI策略生成】已生成合规投注策略，并自动对齐风控规则。"
        else:
            return "【AI综合评估】这是一场值得关注的比赛，各项数据指标均指向主队不败。"
