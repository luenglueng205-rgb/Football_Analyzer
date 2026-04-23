import json
import time
import os

class HippocampusMemory:
    """
    2026 Agentic OS - 海马体 (Continuous Long-Term Memory)
    负责多级记忆管理 (类 MemGPT/Zep 架构)，将短期快照压缩提炼为长期真理。
    """
    def __init__(self, memory_dir="global_knowledge_base/memory_core"):
        self.memory_dir = memory_dir
        os.makedirs(self.memory_dir, exist_ok=True)
        self.working_memory = [] # 当前处理上下文 (RAM)
        self.episodic_memory_file = os.path.join(self.memory_dir, "episodic.json") # 情节记忆 (日记)
        self.semantic_memory_file = os.path.join(self.memory_dir, "semantic_truth.json") # 语义记忆 (提炼的规律)
        
        self._init_memory_files()

    def _init_memory_files(self):
        if not os.path.exists(self.episodic_memory_file):
            with open(self.episodic_memory_file, "w") as f: json.dump([], f)
        if not os.path.exists(self.semantic_memory_file):
            with open(self.semantic_memory_file, "w") as f: json.dump({"truths": [], "risk_tolerance": 0.05}, f)

    def record_episode(self, match_id, action, pnl, context_snapshot):
        """记录每一次交易的心路历程 (盈亏、环境特征)"""
        episode = {
            "timestamp": time.time(),
            "match": match_id,
            "action": action,
            "PnL": pnl, # 真实盈亏反馈 (Profit and Loss)
            "context": context_snapshot
        }
        
        with open(self.episodic_memory_file, "r+") as f:
            episodes = json.load(f)
            episodes.append(episode)
            f.seek(0)
            json.dump(episodes[-1000:], f, indent=2) # 滚动保留最近 1000 条记忆
            f.truncate()
            
        print(f"   [Memory] 🧠 痛觉/快感已记录入海马体情节库 (Match: {match_id}, PnL: {pnl})")

    def sleep_and_consolidate(self):
        """
        夜间休眠模式：主动归纳提炼 (Semantic Consolidation)
        将过去一天的亏损日志，提炼成不可违背的“语义真理”。
        """
        print("   [Memory] 🌙 进入深度睡眠记忆重组模式 (Memory Consolidation)...")
        with open(self.episodic_memory_file, "r") as f:
            episodes = json.load(f)
            
        losses = [e for e in episodes if e["PnL"] < 0]
        if len(losses) >= 3:
            # 模拟大模型提取共性特征 (例如发现英超浅盘全亏)
            new_truth = "RULE_UPDATE: 英超让平半盘口，若必发交易量>80%且未降水，胜率期望下降 25%。禁止买入。"
            
            with open(self.semantic_memory_file, "r+") as f:
                semantic = json.load(f)
                if new_truth not in semantic["truths"]:
                    semantic["truths"].append(new_truth)
                    semantic["risk_tolerance"] = max(0.01, semantic["risk_tolerance"] - 0.01) # 亏损后自动调低风险容忍度
                    f.seek(0)
                    json.dump(semantic, f, indent=2, ensure_ascii=False)
                    f.truncate()
            print(f"   [Memory] 💡 顿悟！从亏损中提取出新的语义真理并固化: {new_truth}")
            print(f"   [Memory] 🛡️ 系统的风险容忍度已自主下调。")
        else:
            print("   [Memory] 💤 记忆回放完毕，今日无严重创伤需要重塑认知。")

if __name__ == "__main__":
    hippo = HippocampusMemory()
    # 模拟三次连续的同类型亏损
    for i in range(3):
        hippo.record_episode(f"EPL_Match_{i}", "BUY_HOME", -100, {"asian_handicap": -0.25, "betfair_vol": 0.85})
    hippo.sleep_and_consolidate()
