import os
import sys
import asyncio
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.tool_registry_v2 import execute_tool, export_registry

@pytest.mark.asyncio
async def test_run_st_gnn_simulator():
    """测试 ST-GNN 模拟器是否能通过 tool_registry_v2 被成功调用"""
    
    # 检查注册表中是否包含该工具
    registry = export_registry()
    tool_names = [t["name"] for t in registry["tools"]]
    assert "run_st_gnn_simulator" in tool_names
    print("✅ 工具已成功注册到 Tool Registry v2")
    
    # 构造注册表所要求的 STGNNSimulatorArgs 参数
    args = {
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "current_minute": 75
    }
    
    print(f"\n正在调用 run_st_gnn_simulator, 参数: {args}")
    
    # 调用执行入口
    result = await execute_tool("run_st_gnn_simulator", args)
    print("返回结果:", result)
    
    assert isinstance(result, dict)
    
    if "ok" in result and not result["ok"]:
        pytest.fail(f"工具执行层错误: {result.get('error')}")
    else:
        assert result["status"] == "success"
        assert "dynamic_xg_home_next_5m" in result
        assert "tactical_observation" in result
        print("✅ ST-GNN 模拟器调用成功！")

if __name__ == "__main__":
    asyncio.run(test_run_st_gnn_simulator())