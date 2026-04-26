import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import os
import json
from datetime import datetime
from unittest.mock import patch
from standalone_workspace.core.digital_life.heartbeat_daemon import DigitalLifeDaemon

def test_circadian_rhythm():
    # 1. 确保开启 LLM 开关（你想测试大模型的真实反思的话）
    os.environ["AUTO_TUNER_USE_LLM"] = "1"
    
    # 2. 初始化守护进程 (设置心跳间隔为1秒)
    daemon = DigitalLifeDaemon(interval_seconds=1)
    
    # 3. 往海马体写入几条假的亏损记录，确保军师有数据复盘
    fake_episodes = [
        {
            "match_id": "TEST_MOCK_001",
            "action": "BUY_HOME",
            "PnL": -100,  # 模拟亏损，触发反思进化
            "context": {"odds": 1.95, "league": "英超"}
        },
        {
            "match_id": "TEST_MOCK_002",
            "action": "BUY_AWAY",
            "PnL": -50,  # 模拟亏损
            "context": {"odds": 3.10, "league": "西甲"}
        },
        {
            "match_id": "TEST_MOCK_003",
            "action": "BUY_HOME",
            "PnL": 20,   # 模拟盈利
            "context": {"odds": 1.20, "league": "英超"}
        }
    ]
    
    # 确保海马体目录存在并写入假数据
    os.makedirs(os.path.dirname(daemon.hippo.episodic_memory_file), exist_ok=True)
    with open(daemon.hippo.episodic_memory_file, "w", encoding="utf-8") as f:
        json.dump(fake_episodes, f)

    print("✅ 成功注入假数据至海马体！")

    # 4. Mock 时间为凌晨 3 点
    fake_now = datetime(2026, 4, 26, 3, 0, 0)
    
    # 因为 datetime 是内建模块，不能直接 patch datetime.datetime，我们 patch daemon 里的 datetime
    with patch('core_system.core.digital_life.heartbeat_daemon.datetime') as mock_datetime:
        # 将 datetime.now() 的返回值替换为我们伪造的凌晨 3 点
        mock_datetime.now.return_value = fake_now
        
        print("🕒 已将系统时间 Mock 为凌晨 3 点，准备触发夜间生物钟...")
        # 传入 test_mode=True，让守护进程跳动一次后自动退出
        daemon.start(test_mode=True)

if __name__ == "__main__":
    test_circadian_rhythm()