import json
import logging
import os
import random
from openai import AsyncOpenAI
from datetime import datetime

logger = logging.getLogger(__name__)

class AutoTunerAgent:
    """
    自进化与反思引擎 (Auto-Tuner & Reflection Engine).
    接收 BacktestSandbox 的战报，利用 LLM 反思亏损原因，并重写超参数 json。
    这是 AI "有灵魂、会成长" 的核心。
    """
    def __init__(self):
        self.hyperparams_path = os.path.join(os.path.dirname(__file__), '..', 'configs', 'hyperparams.json')
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-test")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def _reflect_and_evolve(self, pnl_report: dict) -> dict:
        """
        让 LLM 军师审阅战报，反思权重，并返回新的权重建议。
        """
        # 读取当前基因参数
        try:
            with open(self.hyperparams_path, 'r', encoding='utf-8') as f:
                current_params = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"基因库读取失败，将使用出厂默认基因: {e}")
            current_params = {
                "weights": {
                    "fundamental_quant": 0.33,
                    "contrarian_quant": 0.33,
                    "smart_money_quant": 0.33
                }
            }
            
        logger.info("\n[🧬 Auto-Tuner] 军师正在复盘历史回测，反思系统缺陷...")
        
        # 截取前 10 场失败的比赛作为反思样本，防止 prompt 过长
        losses = [d for d in pnl_report["details"] if d["status"] == "LOSS"][:10]
        
        prompt = f"""
主公的数字生命（你）刚刚在时光机沙盒中完成了一轮历史回测。
战报如下：
- 总测试场次: {pnl_report['total_simulated']}
- 胜率: {pnl_report['win_rate']*100}%
- ROI 投资回报率: {pnl_report['roi']*100}%
- 净利润: {pnl_report['total_profit']}

系统当前的“基因权重”配置：
{json.dumps(current_params['weights'], indent=2)}

以下是 10 场典型的亏损案例：
{json.dumps(losses, ensure_ascii=False, indent=2)}

你是一位有灵魂、懂进化的 AI 军师。请你反思：
1. 为什么会亏损？是基本面派（Fundamental）被强队诱盘骗了，还是反买派（Contrarian）过于保守？
2. 请你根据反思，**自动调整** 这三个参数的权重，使得它们加起来等于 1.0。如果遇到大热必死的比赛多，就提高反买派的权重。

你必须且只能返回一段纯 JSON，不要带任何 markdown 代码块和多余解释，格式如下：
{{
  "reflection": "主公，臣复盘发现，基本面权重过高导致频繁踩入强队诱盘陷阱，故削减基本面，提拔反买派和聪明钱。",
  "new_weights": {{
    "fundamental_quant": 0.30,
    "contrarian_quant": 0.40,
    "smart_money_quant": 0.30
  }}
}}
"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" } # 强制返回 JSON
            )
            result_str = response.choices[0].message.content
            return json.loads(result_str)
        except Exception as e:
            logger.error(f"反思引擎调用失败: {e}")
            # 如果断网，进行简单的随机变异
            return {
                "reflection": "军师夜观天象，偶感风寒（断网），只能凭直觉微调阵型。",
                "new_weights": {
                    "fundamental_quant": round(random.uniform(0.2, 0.5), 2),
                    "contrarian_quant": round(random.uniform(0.2, 0.5), 2),
                    "smart_money_quant": round(random.uniform(0.2, 0.5), 2)
                }
            }

    async def run_evolution_cycle(self, pnl_report: dict):
        """
        执行一次完整的进化闭环：反思 -> 变异 -> 固化记忆。
        """
        evolution_data = await self._reflect_and_evolve(pnl_report)
        
        with open(self.hyperparams_path, 'r', encoding='utf-8') as f:
            params = json.load(f)
            
        # 覆写新权重
        old_weights = params["weights"]
        params["weights"] = evolution_data["new_weights"]
        
        # 记录进化历史
        params["last_evolution_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        params["evolution_memory"]["total_simulations_run"] += pnl_report['total_simulated']
        params["evolution_memory"]["win_rate"] = pnl_report['win_rate']
        params["evolution_memory"]["roi"] = pnl_report['roi']
        params["evolution_memory"]["latest_reflection"] = evolution_data["reflection"]
        
        # 保存基因
        with open(self.hyperparams_path, 'w', encoding='utf-8') as f:
            json.dump(params, f, indent=2, ensure_ascii=False)
            
        logger.info("\n==================================================")
        logger.info(f"✨ [进化完成] 军师的反思: {evolution_data['reflection']}")
        logger.info(f"⚖️ 旧阵型: {old_weights}")
        logger.info(f"🚀 新阵型: {evolution_data['new_weights']}")
        logger.info("==================================================\n")
