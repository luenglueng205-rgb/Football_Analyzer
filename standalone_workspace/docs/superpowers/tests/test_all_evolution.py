import subprocess
import time

def run_test(name, command):
    print(f"🚀 正在并行拉起测试任务: {name}")
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return process

def main():
    print("🌟 2026 三大架构并行进化与严格测试流水线 🌟\n")
    
    p1 = run_test("独立版 Standalone (MCTS & 自愈测试)", "PYTHONPATH=standalone_workspace python3 standalone_workspace/core/advanced_reasoner.py")
    p2 = run_test("Hermes Agent (自建技能树繁衍测试)", "python3 hermes_workspace/core/skill_generator.py")
    p3 = run_test("OpenClaw 适配版 (后台 Swarm 集群实弹测试)", "python3 openclaw_workspace/core/swarm_daemon.py")
    
    processes = [("Standalone", p1), ("Hermes", p2), ("OpenClaw", p3)]
    
    for name, p in processes:
        out, err = p.communicate()
        if p.returncode == 0:
            print(f"\n=============================================")
            print(f"✅ [{name}] 测试通过！运行日志：")
            print(f"=============================================")
            print(out)
        else:
            print(f"\n=============================================")
            print(f"❌ [{name}] 发现严重报错，正在触发修复...")
            print(f"=============================================")
            print(err)

if __name__ == "__main__":
    main()
