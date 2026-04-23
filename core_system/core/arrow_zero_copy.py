import pyarrow as pa
import time
import numpy as np

# Zero-Bloat Evolution: Apache Arrow 零拷贝内存共享 (Python 写入端)
# 模拟 Data Agent (数据抓取器) 将 100,000 条盘口赔率流瞬间写入共享内存池，
# 避免传统 JSON 序列化带来的巨大延迟。

def write_odds_tensor_to_arrow():
    print("==================================================")
    print("🚀 [Python Data Agent] 启动 Apache Arrow 零拷贝内存池写入...")
    print("==================================================")
    
    num_records = 100_000
    print(f"   -> 📡 正在生成 {num_records} 条实时盘口 Tick 数据 (Pinnacle & Betfair)...")
    
    start_time = time.perf_counter()
    
    # 构建高密度的内存数据列
    match_ids = pa.array([f"EPL_MATCH_{i}" for i in range(num_records)])
    pinnacle_odds = pa.array(np.random.uniform(1.80, 2.10, num_records))
    betfair_vol = pa.array(np.random.uniform(10000, 500000, num_records))
    timestamp = pa.array(np.full(num_records, time.time()))
    
    # 组装为 Arrow 表 (Table)
    table = pa.Table.from_arrays(
        [match_ids, pinnacle_odds, betfair_vol, timestamp],
        names=['match_id', 'pinnacle_odds', 'betfair_vol', 'timestamp']
    )
    
    # 写入 IPC (进程间通信) 内存映射文件，这使得 Rust 可以瞬间零拷贝读取
    ipc_file_path = "global_knowledge_base/live_odds_tensor.arrow"
    with pa.OSFile(ipc_file_path, 'wb') as sink:
        with pa.RecordBatchFileWriter(sink, table.schema) as writer:
            writer.write_table(table)
            
    elapsed = (time.perf_counter() - start_time) * 1000
    
    print(f"   -> ⚡ [Performance] 序列化并写入 {num_records} 条记录耗时: {elapsed:.2f} 毫秒！")
    print(f"   -> 💾 [Memory] Arrow IPC 文件已生成至: {ipc_file_path}")
    print("   -> ✅ [Zero-Copy] Python 端已释放 GIL。Rust 边缘节点现在可以瞬间读取这块物理内存。")

if __name__ == "__main__":
    write_odds_tensor_to_arrow()
