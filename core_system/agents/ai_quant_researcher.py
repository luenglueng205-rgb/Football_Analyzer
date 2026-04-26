import io
import time
import json
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORE_SYSTEM_ROOT = _REPO_ROOT / "core_system"
_DEFAULT_SANDBOX_DIR = _CORE_SYSTEM_ROOT / "workspace" / "strategist" / "sandbox"
_DEFAULT_ACTIVE_STRATEGY_PATH = _CORE_SYSTEM_ROOT / "core" / "active_strategy.py"

# ── 沙箱执行：优先使用隔离的 Code Interpreter MCP 服务 ──────────────────
def _run_in_restricted_sandbox(code: str) -> dict:
    """
    通过系统的 Code Interpreter MCP 隔离执行 AI 生成的代码。
    返回 {"stdout": ..., "ok": True} 或 {"error": ..., "ok": False}
    """
    try:
        import sys
        if str(_CORE_SYSTEM_ROOT.parent) not in sys.path:
            sys.path.insert(0, str(_CORE_SYSTEM_ROOT.parent))
            
        from core_system.skills.code_interpreter.server import execute_quant_script
        result = execute_quant_script(code)
        if result.get("status") == "success":
            return {"ok": True, "stdout": result.get("stdout", "")}
        else:
            return {"ok": False, "error": result.get("stderr", "Unknown error")}
    except Exception as e:
        # 捕获 RestrictedPython 中的运行错误，视同该策略崩溃
        return {"ok": False, "error": f"沙箱执行异常: {e}"}


class QuantResearcherAgent:
    """
    100% AI-Native: 零硬编码，自主编写回测与定价模型代码的 Agent。
    不再运行人类写好的模型，而是自己写 Python 脚本并在沙盒中运行。

    安全说明
    --------
    * AI 生成代码通过 RestrictedPython 沙箱执行，禁止访问 os/subprocess/shutil/open。
    * 部署生产策略前需通过 ``require_human_approval=True``（默认开启）的人工确认门。
    """
    def __init__(self, sandbox_dir=None, active_strategy_path=None, require_human_approval: bool = True):
        self.sandbox_dir = Path(sandbox_dir).expanduser() if sandbox_dir else _DEFAULT_SANDBOX_DIR
        self.active_strategy_path = (
            Path(active_strategy_path).expanduser()
            if active_strategy_path
            else _DEFAULT_ACTIVE_STRATEGY_PATH
        )
        # 人工确认门：默认开启，防止 AI 代码自动覆盖生产文件
        self.require_human_approval = require_human_approval
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.active_strategy_path.parent.mkdir(parents=True, exist_ok=True)
        
    def _simulate_llm_code_generation(self, iteration: int) -> str:
        """调用真实 LLM 生成可执行的 Python 策略代码，取代随机抛硬币"""
        print(f"   -> 🧠 [LLM Inference] 正在调用大模型构思第 {iteration} 代定价模型，编写真实 Python 代码中...")
        
        import re
        import os
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
        
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or "dummy"
        base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
        model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")
        
        client_kwargs = {"api_key": api_key, "model": model_name, "temperature": 0.7}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        prompt = f"""
你是专业的量化分析师，你正在编写一个 Python 脚本来回测一个足彩赔率策略 (迭代版本 {iteration})。
要求：
1. 必须使用纯 Python (标准库，允许 json, math, collections)。
2. 你需要自己生成一些模拟的赔率历史数据（至少 10 场比赛，包含 home_odds, draw_odds, away_odds 和真实赛果 result ('H', 'D', 'A')）。
3. 实现一个简单的凯利准则或泊松分布变体来决定是否下注，并计算回测的胜率、夏普比率 (Sharpe Ratio)、最大回撤 (Max Drawdown)。
4. 必须在最后用 print(json.dumps(...)) 输出结果，包含字典键："strategy_id", "sharpe_ratio", "max_drawdown", "code_hash"。
5. 必须返回纯 Python 代码，不要用 markdown code block 包装，只返回代码本身！
"""
        try:
            llm = ChatOpenAI(**client_kwargs)
            response = llm.invoke([HumanMessage(content=prompt)])
            code = response.content.strip()
            # 如果大模型仍然返回了 markdown 语法，进行清理
            code = re.sub(r"^```python\s*", "", code)
            code = re.sub(r"^```\s*", "", code)
            code = re.sub(r"```\s*$", "", code)
            return code
        except Exception as e:
            print(f"   -> ⚠️ [LLM Fallback] API 调用失败，回退到基础模板: {e}")
            # 失败回退逻辑，不再是纯随机，而是写一个简单的算法
            return f'''
import json
import math

def backtest_strategy():
    # Fallback algorithmic strategy
    results = [1, -1, 1, 1, -1, 1, 0, 1, -1, 1]
    win_rate = sum(1 for x in results if x > 0) / len(results)
    
    # 简单的伪夏普比率计算
    mean_return = 0.05
    std_dev = 0.15
    sharpe_ratio = mean_return / std_dev + (win_rate - 0.5)
    max_drawdown = 0.12
    
    result = {{
        "strategy_id": "v{iteration}_fallback",
        "sharpe_ratio": round(sharpe_ratio, 2),
        "max_drawdown": round(max_drawdown, 2),
        "code_hash": "{hash(str(iteration))}"
    }}
    
    print(json.dumps(result))

if __name__ == "__main__":
    backtest_strategy()
'''

    async def auto_research_loop(self, max_iterations: int = 3):
        print("==================================================")
        print("🧪 [Agentic R&D] 启动全自动量化投研流水线 (AI Code Generation)...")
        print("==================================================")
        
        best_sharpe = 0.0
        best_script_path = None
        best_metrics: dict = {}
        
        for i in range(1, max_iterations + 1):
            print(f"\n   --- [R&D Iteration {i}] ---")
            
            # 1. AI 编写代码
            generated_code = self._simulate_llm_code_generation(i)
            script_path = self.sandbox_dir / f"strategy_v{i}.py"
            
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(generated_code)
            print(f"   -> 💾 [Sandbox] 代码写入完毕: {script_path}")
            
            # 2. ✅ 沙箱执行回测（替换原来的裸 subprocess.run）
            print(f"   -> ⚙️ [Execution] 正在沙箱（RestrictedPython）中执行该策略的回测...")
            result = _run_in_restricted_sandbox(generated_code)

            if not result.get("ok"):
                print(f"   -> 🚨 [Crash] AI 生成的代码执行失败: {result.get('error', '未知错误')}")
                continue
            
            stdout = result.get("stdout", "").strip()
            if not stdout:
                print("   -> 🚨 [Crash] 脚本执行没有返回任何输出。")
                continue
            try:
                # 取 stdout 最后一行 JSON（print(json.dumps(...)) 约定）
                last_line = [l for l in stdout.splitlines() if l.strip()][-1]
                metrics = json.loads(last_line)
                sharpe = metrics["sharpe_ratio"]
                print(f"   -> 📊 [Metrics] 回测结果: Sharpe Ratio = {sharpe}, Max Drawdown = {metrics['max_drawdown']}")
                
                # 3. 优胜劣汰
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_script_path = script_path
                    best_metrics = metrics
                    print("   -> 🌟 [Promotion] 发现目前最优策略，暂存为冠军模型。")
                else:
                    print("   -> 🗑️ [Discard] 夏普比率未打破记录，废弃该代码。")
            except Exception as e:
                print(f"   -> 🚨 [Crash] AI 生成的代码存在 Bug 导致崩溃: {e}。触发重试。")
                
        print("\n==================================================")
        if best_sharpe > 2.0 and best_script_path:
            print(f"🏆 [Candidate] 最优策略候选 ({best_script_path.name}, Sharpe: {best_sharpe})")
            print(f"   指标详情: {json.dumps(best_metrics, ensure_ascii=False)}")

            if self.require_human_approval:
                # ✅ 人工确认门：阻止 AI 代码自动覆盖生产文件
                print("\n⚠️  [HUMAN APPROVAL REQUIRED]")
                print(f"   候选策略路径 : {best_script_path}")
                print(f"   目标生产路径 : {self.active_strategy_path}")
                print("   请人工审查上述策略代码，确认安全后手动运行以下命令完成部署：")
                print(f"   cp '{best_script_path}' '{self.active_strategy_path}'")
                print("   本次自动化流程已在此暂停，等待人工决策。")
            else:
                # 仅在明确关闭确认门时（如 CI 受控环境）才自动部署
                logger.warning("require_human_approval=False，将自动部署策略。请确保此模式仅在受控 CI 环境中使用。")
                shutil.copy2(best_script_path, self.active_strategy_path)
                print(f"   -> 🚀 [Deployment] 已更新主策略脚本: {self.active_strategy_path}")
        else:
            print("⚠️ [Failed] 本轮投研未能发现夏普比率 > 2.0 的有效策略，系统将继续沿用旧模型。")
        print("==================================================")

if __name__ == "__main__":
    researcher = QuantResearcherAgent()
    researcher.auto_research_loop(max_iterations=3)
