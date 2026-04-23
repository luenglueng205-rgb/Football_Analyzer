# Phase 1: Long-Term Memory (长期记忆流觉醒) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为系统引入长期记忆库 (Long-Term Memory)，使 AI 能够在每次分析完比赛后，自动提取核心领悟（Insight）并持久化。下次分析相同球队时，系统会自动检索历史记忆，实现经验积累。

**Architecture:** 采用本地轻量级向量数据库 `chromadb` 存储 Embedding。构建一个 `MemoryManager` 工具类，提供 `save_insight` 和 `retrieve_memory` 接口，并将其注册为 MCP Tools 供 AI 调用。修改 `AINativeCoreAgent` 的 System Prompt，教导 AI 如何在决策前后读写记忆。

**Tech Stack:** `chromadb`, `openai` (for embeddings), `pydantic`

---

### Task 1: 安装依赖并搭建 MemoryManager 核心类

**Files:**
- Create: `tools/memory_manager.py`
- Modify: `requirements.txt` (如果存在，否则跳过)
- Test: `tests/test_memory_manager.py` (或者直接用临时脚本测试)

- [x] **Step 1: 安装 chromadb 依赖**

```bash
python3 -m pip install chromadb --user --break-system-packages
```

- [x] **Step 2: 编写 MemoryManager 类**

```python
import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any

class MemoryManager:
    """
    系统的长期记忆中枢。
    使用 ChromaDB 在本地持久化球队的历史表现、教练战术、伤病影响等核心领悟(Insights)。
    """
    def __init__(self, db_path: str = "data/chroma_db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        # 初始化 Chroma 客户端 (持久化到本地)
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # 默认使用 OpenAI 的 text-embedding-3-small 模型 (需确保环境变量有 OPENAI_API_KEY)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key,
                model_name="text-embedding-3-small"
            )
        else:
            # Fallback 到默认的本地模型
            self.ef = embedding_functions.DefaultEmbeddingFunction()
            
        # 创建或获取 Collection
        self.collection = self.client.get_or_create_collection(
            name="football_insights",
            embedding_function=self.ef
        )

    def save_insight(self, team_name: str, insight_text: str, match_id: str, confidence: float = 0.8) -> dict:
        """
        保存一条领悟到长期记忆库
        """
        try:
            # 使用时间戳或随机数确保 ID 唯一，这里简单用 team + match_id
            import time
            doc_id = f"{team_name}_{match_id}_{int(time.time())}"
            
            self.collection.add(
                documents=[insight_text],
                metadatas=[{"team": team_name, "match_id": match_id, "confidence": confidence}],
                ids=[doc_id]
            )
            return {"ok": True, "message": f"Insight for {team_name} saved successfully.", "doc_id": doc_id}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def retrieve_memory(self, team_name: str, query_context: str = "", limit: int = 3) -> dict:
        """
        检索关于某支球队的历史记忆
        如果提供了 query_context，会基于语义进行相似度检索；否则只按 metadata 过滤。
        """
        try:
            query_text = query_context if query_context else f"{team_name} 的战术特点和近期表现"
            
            results = self.collection.query(
                query_texts=[query_text],
                n_results=limit,
                where={"team": team_name} # 严格过滤该球队
            )
            
            if not results["documents"] or not results["documents"][0]:
                return {"ok": True, "data": [], "message": f"No memory found for {team_name}."}
                
            memories = []
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i]
                memories.append({
                    "insight": doc,
                    "match_id": meta.get("match_id"),
                    "confidence": meta.get("confidence")
                })
                
            return {"ok": True, "data": memories}
        except Exception as e:
            return {"ok": False, "error": str(e)}
```

- [x] **Step 3: 编写并运行临时测试脚本**

```bash
cat << 'EOF' > test_memory.py
from tools.memory_manager import MemoryManager
import os
# Ensure API key is set for testing if needed
# os.environ["OPENAI_API_KEY"] = "your_key" 

mm = MemoryManager()
# 1. 存入记忆
res1 = mm.save_insight("曼联", "2024年4月发现：滕哈格在客场面对弱队时，由于中场控制力差，极易被打反击，大球概率高。", "match_123")
print("Save:", res1)

# 2. 检索记忆
res2 = mm.retrieve_memory("曼联", "曼联客场防守表现如何？")
print("Retrieve:", res2)
EOF
python3 test_memory.py
```
Expected: PASS (输出 Save 成功信息，Retrieve 返回刚才存入的文本)

### Task 2: 将 Memory 接口注册为 MCP Tools

**Files:**
- Modify: `tools/mcp_tools.py`
- Modify: `tools/tool_registry_v2.py`

- [x] **Step 1: 在 `mcp_tools.py` 中暴露接口**

```python
# tools/mcp_tools.py
from tools.memory_manager import MemoryManager

# 实例化全局的 memory_manager
_memory_manager = MemoryManager()

@ensure_protocol(mock=False, source="memory")
def retrieve_team_memory(team_name: str, context: str = "") -> dict:
    """检索关于某支球队的长期历史记忆和核心领悟"""
    return _memory_manager.retrieve_memory(team_name, context)

@ensure_protocol(mock=False, source="memory")
def save_team_insight(team_name: str, insight: str, match_id: str = "unknown") -> dict:
    """在分析结束后，将重要的战术发现或模型领悟持久化到长期记忆库"""
    return _memory_manager.save_insight(team_name, insight, match_id)

# 不要忘记在底部的 TOOL_MAPPING 中注册这两个新函数
# TOOL_MAPPING = {
#     ...
#     "retrieve_team_memory": retrieve_team_memory,
#     "save_team_insight": save_team_insight,
# }
```

- [x] **Step 2: 在 `tool_registry_v2.py` 中添加 Pydantic Schema**

```python
# tools/tool_registry_v2.py
# 在合适的位置添加 Args 定义
class RetrieveMemoryArgs(BaseModel):
    team_name: str
    context: str = Field(default="", description="查询的上下文，例如：客场防守表现")

class SaveInsightArgs(BaseModel):
    team_name: str
    insight: str = Field(..., description="高度浓缩的核心领悟，例如：切尔西主场极度依赖边路传中，中路渗透为0")
    match_id: str = Field(default="unknown")

# 在 _TOOLS 列表中追加定义
# ToolDefinition("retrieve_team_memory", "检索关于某支球队的长期历史记忆和核心领悟", RetrieveMemoryArgs, TOOL_MAPPING["retrieve_team_memory"]),
# ToolDefinition("save_team_insight", "在分析结束后，将重要的战术发现或模型领悟持久化到长期记忆库", SaveInsightArgs, TOOL_MAPPING["save_team_insight"]),
```

### Task 3: 升级 AI 大脑 (AINativeCoreAgent) 的心智模型

**Files:**
- Modify: `agents/ai_native_core.py`

- [x] **Step 1: 修改系统提示词 (System Prompt)，教导 AI 读写记忆**

找到 `self.system_prompt` 组装的地方，在 `process` 方法的 `messages` 列表中补充指令：

```python
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"请为我深度量化分析这场比赛：主队 '{home}' 对阵 客队 '{away}'。当前彩种为：'{lottery_desc}'。\n"
                                         f"【最高指令】：你是一个统治华尔街的数字博彩基金大脑。你需要自主调用所有可用工具：\n"
                                         f"1. 必须调用 check_bankroll 查看当前真实可用资金。\n"
                                         f"2. 【长期记忆】：在开始分析前，必须调用 retrieve_team_memory 提取主客队的历史经验！\n"
                                         f"3. 必须分析亚盘水位异动和欧亚转换偏差（不要只用泊松）。\n"
                                         f"4. 决定投资后，必须调用 execute_bet 真正生成实单并写入账本！\n"
                                         f"5. 【经验沉淀】：在给出最终结论前，必须调用 save_team_insight 将你对本场比赛两队的战术发现或盘口规律分别存入记忆库，供未来使用！\n"
                                         f"6. 【极致闭环】：如果发现多个机会，必须调用 calculate_parlay 计算串关组合。决定下注后，必须调用 generate_qr_code 生成物理二维码，并调用 send_webhook_notification 将决策推送到手机！\n"
                                         f"7. 【MOCK 数据隔离】：如果你调用的工具返回了 `\"meta\": {{\"mock\": true}}`，说明该数据为模拟/离线数据，不可信。你在最终决策时，必须对这类数据降权，或者直接拒绝基于该数据进行大额下注（仅输出观察不下注，或者极小仓位）。"}
        ]
```

- [x] **Step 2: 运行一次实盘推演验证记忆闭环**

```bash
python3 run_live_decision.py
```
Expected: 观察终端日志，确认大模型在开始阶段调用了 `retrieve_team_memory`，并在结尾决策前调用了 `save_team_insight`。

- [x] **Step 3: 再次运行验证记忆提取**

```bash
python3 run_live_decision.py
```
Expected: 在第二次运行时，大模型调用 `retrieve_team_memory` 应该能成功返回第一次运行存入的 Insight，并在最终报告中提及这些历史经验。

- [x] **Step 4: Commit**

```bash
git add tools/memory_manager.py tools/mcp_tools.py tools/tool_registry_v2.py agents/ai_native_core.py
git commit -m "feat(p1): implement long-term memory stream using chromadb"
```
