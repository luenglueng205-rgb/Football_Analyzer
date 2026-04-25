import io
import time
import json
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── 沙箱执行：优先使用 RestrictedPython，降级到隔离子进程 ──────────────────
try:
    from RestrictedPython import compile_restricted, safe_globals, safe_builtins
    from RestrictedPython.Guards import safe_exec, guarded_getattr, guarded_getitem
    _RESTRICTED_PYTHON_AVAILABLE = True
except ImportError:
    _RESTRICTED_PYTHON_AVAILABLE = False
    logger.warning(
        "RestrictedPython 未安装，代码沙箱不可用。"
        "请运行 `pip install RestrictedPython` 以启用安全执行。"
    )

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORE_SYSTEM_ROOT = _REPO_ROOT / "core_system"
_DEFAULT_SANDBOX_DIR = _CORE_SYSTEM_ROOT / "workspace" / "strategist" / "sandbox"
_DEFAULT_ACTIVE_STRATEGY_PATH = _CORE_SYSTEM_ROOT / "core" / "active_strategy.py"

# ── 允许 AI 生成代码使用的安全内置模块白名单 ──────────────────────────────
_SAFE_MODULES = frozenset({"random", "json", "math", "statistics", "collections"})


def _run_in_restricted_sandbox(code: str) -> dict:
    """
    在 RestrictedPython 沙箱中执行 AI 生成代码。
    只允许访问白名单内置函数，禁止 os / subprocess / shutil / open 等危险操作。
    返回 {"stdout": ..., "ok": True} 或 {"error": ..., "ok": False}
    """
    if not _RESTRICTED_PYTHON_AVAILABLE:
        return {"ok": False, "error": "RestrictedPython 未安装，拒绝执行 AI 生成代码。"}

    try:
        byte_code = compile_restricted(code, filename="<ai_generated>", mode="exec")
    except SyntaxError as e:
        return {"ok": False, "error": f"AI 代码语法错误: {e}"}

    # 构造最小权限全局命名空间
    _allowed_builtins = {
        k: v for k, v in safe_builtins.items()
        if k not in {"__import__", "open", "exec", "eval", "compile"}
    }

    def _safe_import(name, *args, **kwargs):
        if name not in _SAFE_MODULES:
            raise ImportError(f"沙箱拒绝导入模块: '{name}'（不在白名单中）")
        import importlib
        return importlib.import_module(name)

    _allowed_builtins["__import__"] = _safe_import

    captured_output = io.StringIO()
    glb = {
        **safe_globals,
        "__builtins__": _allowed_builtins,
        "_print_": lambda *a, **kw: captured_output.write(" ".join(str(x) for x in a) + "\n"),
        "_getattr_": guarded_getattr,
        "_getitem_": guarded_getitem,
    }

    try:
        exec(byte_code, glb)  # noqa: S102  — byte_code 已由 RestrictedPython 净化
    except Exception as e:
        return {"ok": False, "error": f"沙箱执行异常: {e}"}

    return {"ok": True, "stdout": captured_output.getvalue()}


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
        """模拟大模型（如 GPT-4o 或 Claude 3.5）根据数据直接生成可执行的 Python 代码"""
        print(f"   -> 🧠 [LLM Inference] 正在构思第 {iteration} 代定价模型，编写 Python 代码中...")
        time.sleep(1.0)
        
        # AI 自己写的代码（带有不同的随机因子和逻辑，模拟模型变异）
        code = f"""
import random
import json

def backtest_strategy():
    # AI generated logic iteration {iteration}
    # Fetching historical JSON data (mocked)
    win_rate = random.uniform(0.4, 0.6)
    sharpe_ratio = random.uniform(0.5, 3.5)
    max_drawdown = random.uniform(0.01, 0.15)
    
    result = {{
        "strategy_id": "v{iteration}_ai_generated",
        "sharpe_ratio": round(sharpe_ratio, 2),
        "max_drawdown": round(max_drawdown, 2),
        "code_hash": "{hash(str(iteration))}"
    }}
    
    print(json.dumps(result))

if __name__ == "__main__":
    backtest_strategy()
"""
        return code

    def auto_research_loop(self, max_iterations=3):
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
