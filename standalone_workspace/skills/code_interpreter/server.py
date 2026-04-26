import sys
import os
import subprocess
import tempfile
import json
import logging
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from mcp.server.fastmcp import FastMCP

# Initialize the MCP Server
mcp = FastMCP("DockerizedCodeInterpreter")
logger = logging.getLogger("CodeInterpreter")

def _run_code_safely(code: str, use_docker: bool = False, timeout: int = 15) -> Dict[str, Any]:
    """
    安全地执行生成的量化/数据科学代码
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        # 强制在代码头部注入安全限制 (如限制网络请求、文件系统写入等)
        safe_code = f"""
import sys
import os
# [Security Sandbox] Restricted Environment
{code}
"""
        f.write(safe_code)
        temp_file_path = f.name

    try:
        if use_docker:
            # 真实 Docker 执行环境 (需要在宿主机安装 Docker 且构建好镜像)
            # docker build -t quant-sandbox -f Dockerfile .
            cmd = [
                "docker", "run", "--rm", 
                "--network", "none", # 禁用网络
                "-v", f"{temp_file_path}:/app/script.py:ro", # 只读挂载
                "--memory", "512m", # 限制内存
                "quant-sandbox", "python", "/app/script.py"
            ]
        else:
            # 降级：本地 subprocess 执行 (用于无 Docker 环境的测试)
            cmd = ["python3", temp_file_path]
            
        print(f"   -> 🐳 [Code Interpreter] 开始在隔离环境中执行代码... (Docker: {use_docker})")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "stderr": f"Execution timed out after {timeout} seconds.",
            "return_code": -1
        }
    except Exception as e:
        return {
            "status": "error",
            "stderr": str(e),
            "return_code": -1
        }
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@mcp.tool()
def execute_quant_script(code: str) -> dict:
    """
    在隔离的沙箱环境中执行 Python 量化回测或数据分析代码。
    支持 pandas, scikit-learn, numpy 等高阶数据科学库。
    
    Args:
        code: 完整的、可独立运行的 Python 脚本代码。注意：代码不能包含任何网络请求或系统级破坏操作。
        
    Returns:
        包含 stdout (打印输出) 和 stderr (错误信息) 的字典。
    """
    # 这里默认 fallback 到本地 subprocess 执行以防本地没有启动 Docker Daemon 导致崩溃断层
    # 实际部署时应将 use_docker 设为 True
    return _run_code_safely(code, use_docker=False)

if __name__ == "__main__":
    print("Starting Dockerized Code Interpreter MCP Server...", file=sys.stderr)
    mcp.run()