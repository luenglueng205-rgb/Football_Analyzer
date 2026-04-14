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
