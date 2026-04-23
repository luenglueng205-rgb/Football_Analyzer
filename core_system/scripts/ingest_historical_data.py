import os
import sys
import json
import time

# Add standalone_workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.memory_manager import MemoryManager

def run_data_ingestion():
    print("="*60)
    print("🧬 启动“胖大脑”知识灌注程序 (Brain Neural Link Ingestion)")
    print("="*60)
    
    # 强制将环境变量设为 local hash 模式，以最高速度插入这 22 万条不依赖语义的硬逻辑数据
    os.environ["MEMORY_EMBEDDING_BACKEND"] = "local"
    
    # 获取 JSON 路径
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "datasets", "raw", "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json")
    
    if not os.path.exists(json_path):
        print(f"❌ 找不到数据文件: {json_path}")
        return
        
    print(f"📡 正在读取历史数据源: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    matches = data.get("matches", [])
    total_matches = len(matches)
    print(f"✅ 成功加载 {total_matches} 条比赛记录 (涵盖五大联赛及外围赛事)")
    
    if total_matches == 0:
        print("❌ 数据集为空。")
        return
        
    print("🧠 正在唤醒 ChromaDB 记忆中枢...")
    memory = MemoryManager()
    
    # ChromaDB 的单次最大 batch size 是 5461，所以我们设置 5000
    batch_size = 5000
    total_inserted = 0
    start_time = time.time()
    
    # 我们灌入全量 22 万条数据以构建完整的历史知识库
    target_insert = total_matches
    print(f"🚀 开始将全量 {target_insert} 场真实比赛灌入 ChromaDB...")
    
    for i in range(0, target_insert, batch_size):
        batch = matches[i:i+batch_size]
        res = memory.add_historical_matches_batch(batch)
        
        if res.get("ok"):
            total_inserted += res.get("count", 0)
            print(f"   [进度] 已成功灌入 {total_inserted}/{target_insert} 条...")
        else:
            print(f"   [错误] 灌入失败: {res.get('error')}")
            break
            
    elapsed = time.time() - start_time
    print(f"\n🎉 灌注完成！耗时: {elapsed:.2f} 秒。")
    print(f"💡 AI 原生系统（独立版）现在的底层大脑中，已经真实装载了 {total_inserted} 场结构化比赛数据。")
    print("下一次，当 AI 调用 deep_evaluate_all_markets 时，它将通过 ChromaDB 的元数据 (Metadata) 过滤器，在毫秒级时间内匹配到这些真实比赛，并基于此算出绝对精准的 EV！")

if __name__ == "__main__":
    run_data_ingestion()
