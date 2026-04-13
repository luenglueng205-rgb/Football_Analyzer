import json
import logging
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.skill_manager import DynamicSkillManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuantOrchestrator:
    """
    量化投研委员会主席 (Orchestrator)。
    负责拆解宏观任务，当遇到本地无法处理的数据时（如查财报、查推特情感），
    主动调用 DynamicSkillManager 向技能市场求助。
    """
    
    def __init__(self):
        self.skill_manager = DynamicSkillManager()
        
    def analyze_macro_event(self, event_description: str) -> Dict[str, Any]:
        """
        核心调度流程：
        1. 大模型拆解宏观事件 (如: 美联储加息预期)
        2. 判断本地是否有分析工具
        3. 发现缺失工具，触发自我进化
        4. 获取第三方数据，传递给本地风控引擎 (凯利准则)
        """
        logger.info(f"[Orchestrator] 收到宏观分析任务: {event_description}")
        
        # 步骤 1: 需求感知 (Perception)
        # 假设大模型分析后认为需要 "美联储最新非农数据"
        missing_capability = "获取最新的美国非农就业人数 (Nonfarm Payrolls)"
        required_format = '{"payrolls": int, "unemployment_rate": float}'
        
        # 步骤 2: 动态发现与技能固化 (Discovery & Integration)
        logger.info(f"本地缺少工具，准备向技能市场搜索能力: {missing_capability}")
        success = self.skill_manager.discover_and_learn_skill(
            missing_capability=missing_capability,
            required_output_format=required_format
        )
        
        if success:
            logger.info("系统成功进化，获得了新的分析能力。")
            
            # 步骤 3: 使用新技能 (Runtime Execution)
            # 大模型会自动根据 Schema 生成参数发起调用
            # 模拟调用第三方接口获取的数据
            mock_data = {"payrolls": 175000, "unemployment_rate": 3.9}
            logger.info(f"成功调用第三方技能获取到宏观数据: {mock_data}")
            
            # 步骤 4: 交给本地的量化风控引擎 (Quant & Risk Engine)
            # 例如: 非农不及预期，降息概率增加，大模型建议增加黄金多头仓位
            # RiskManager 审核后通过，凯利准则计算出 5% 的仓位暴露
            final_portfolio = {
                "recommendation": "Overweight Gold (GLD)",
                "confidence": 0.85,
                "kelly_fraction": 0.05,
                "reasoning": "非农数据走弱，支持美联储降息预期，黄金宏观利好。"
            }
            
            return final_portfolio
        else:
            logger.error("未能从技能市场找到合适的安全工具，分析任务受限。")
            return {"error": "Missing required macro data skills."}

if __name__ == "__main__":
    orchestrator = QuantOrchestrator()
    result = orchestrator.analyze_macro_event("分析下周三公布的美国非农就业数据对黄金的影响。")
    print("\n[最终投资建议]\n", json.dumps(result, ensure_ascii=False, indent=2))