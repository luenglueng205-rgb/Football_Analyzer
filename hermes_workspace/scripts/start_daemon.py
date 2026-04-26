#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from hermes_workspace.core.digital_life.heartbeat_daemon import DigitalLifeDaemon

if __name__ == "__main__":
    # 使用守护进程模式启动 (如 nohup / systemd)
    # 本地直接运行 `python3 core_system/scripts/start_daemon.py`
    print("🚀 [Bootstrap] 准备将系统推入永生循环...")
    daemon = DigitalLifeDaemon(interval_seconds=900) # 每 15 分钟醒一次
    
    try:
        daemon.start()
    except KeyboardInterrupt:
        print("\n👋 [Bootstrap] 收到 Ctrl+C，正在执行平滑退出...")
        sys.exit(0)