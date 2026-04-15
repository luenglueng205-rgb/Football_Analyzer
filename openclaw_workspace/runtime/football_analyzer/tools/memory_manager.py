import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
from chromadb.config import Settings
import logging
from datetime import datetime
from tools.paths import data_dir

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    系统的长期记忆中枢。
    使用 ChromaDB 在本地持久化球队的历史表现、教练战术、伤病影响等核心领悟(Insights)。
    """
    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.join(data_dir(), "chroma_db")
        os.makedirs(self.db_path, exist_ok=True)
        
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

    def add_episodic_memory(self, content: str, tags: List[str], importance: float = 0.5):
        """
        向系统的情景记忆库中添加一条历史赛事经验 (Massive Episodic Memory)
        """
        try:
            import time
            doc_id = f"episodic_{int(time.time()*1000)}_{hash(content)}"
            
            # 使用 ChromaDB 存储
            self.collection.add(
                documents=[content],
                metadatas=[{
                    "type": "episodic",
                    "importance": importance,
                    "tags": ",".join(tags)
                }],
                ids=[doc_id]
            )
            return {"ok": True, "doc_id": doc_id}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    def retrieve_memory(self, team_name: str, query_context: str = "", limit: int = 5) -> dict:
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

    def query_historical_odds(self, league: str, home_odds: float, draw_odds: float, away_odds: float, tolerance: float = 0.10, limit: int = 20) -> dict:
        """
        [修复版] 精确数值过滤查询：彻底摒弃大模型对数字极度不敏感的语义向量查询。
        改用 ChromaDB 的结构化 Metadata 逻辑运算符 ($and, $gte, $lte) 进行硬逻辑区间匹配。
        """
        try:
            # 构建容差区间
            h_min, h_max = home_odds * (1 - tolerance), home_odds * (1 + tolerance)
            d_min, d_max = draw_odds * (1 - tolerance), draw_odds * (1 + tolerance)
            a_min, a_max = away_odds * (1 - tolerance), away_odds * (1 + tolerance)
            
            # 使用 ChromaDB 强大的 Metadata 过滤语法
            where_clause = {
                "$and": [
                    {"type": {"$eq": "historical_match"}},
                    {"league": {"$eq": league}},
                    {"home_odds": {"$gte": h_min}},
                    {"home_odds": {"$lte": h_max}},
                    {"draw_odds": {"$gte": d_min}},
                    {"draw_odds": {"$lte": d_max}},
                    {"away_odds": {"$gte": a_min}},
                    {"away_odds": {"$lte": a_max}}
                ]
            }
            
            # 注意：这里我们传入一个虚拟的查询文本或直接留空，完全依靠 where 过滤。
            # ChromaDB 要求必须有 query_texts 或 query_embeddings，我们随便传一个即可，因为完全靠 where 拦截。
            results = self.collection.query(
                query_texts=["odds matching"],
                n_results=limit,
                where=where_clause
            )
            
            if not results["documents"] or not results["documents"][0]:
                return {"ok": True, "data": [], "message": "未找到相似赔率的历史比赛"}
                
            return {"ok": True, "data": results["documents"][0]}
        except Exception as e:
            return {"ok": False, "error": str(e)}
