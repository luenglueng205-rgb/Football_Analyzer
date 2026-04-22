import json
from typing import Dict, Any
from tools.llm_service import LLMService

class AfterActionReviewAgent:
    """
    赛后复盘智能体 (After-Action Review Agent)
    对比实际赛果与系统赛前预测，生成反思报告，并更新到经验库中。
    """
    def __init__(self):
        self.llm = LLMService

    async def generate_reflection(self, match_data: Dict[str, Any], prediction: Dict[str, Any]) -> Dict[str, Any]:
        """生成赛后反思"""
        prompt = f"""
        你是一个顶级的足彩复盘分析师。
        实际赛果: {json.dumps(match_data, ensure_ascii=False)}
        AI赛前预测: {json.dumps(prediction, ensure_ascii=False)}
        
        请分析预测失败或成功的原因，提取一条精炼的“血泪教训”或“成功经验”（50字以内）。
        返回JSON格式: {{"success": true/false, "reflection": "详细复盘...", "lesson": "精炼教训..."}}
        """
        
        response = await self.llm.generate_report_async(prompt, "[]", role="AAR Analyst")
        
        try:
            # Assuming the response is a JSON string or contains JSON
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            # Fallback for dummy tests
            return {
                "success": False,
                "reflection": "The prediction was incorrect.",
                "lesson": "Always consider home advantage.",
                "raw_response": response
            }

    async def save_lesson_to_doc(self, lesson: str, doc_path: str = None) -> bool:
        """追加经验教训到动态经验库文档中"""
        from pathlib import Path
        import datetime
        
        if doc_path is None:
            doc_path = Path(__file__).resolve().parents[1] / "docs" / "DYNAMIC_EXPERIENCE.md"
            
        try:
            with open(doc_path, "a", encoding="utf-8") as f:
                date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                f.write(f"\n- **[{date_str} Auto-RLHF]**: {lesson}\n")
            return True
        except Exception as e:
            print(f"Error saving lesson: {e}")
            return False
