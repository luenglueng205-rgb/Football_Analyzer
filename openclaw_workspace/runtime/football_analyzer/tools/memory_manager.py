import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
from chromadb.config import Settings
import logging
from datetime import datetime
from tools.paths import data_dir
import hashlib
import math
import re

logger = logging.getLogger(__name__)


class _EmbeddingFunctionAdapter:
    def __init__(self, embedding_function: Any):
        self._embedding_function = embedding_function

    def __call__(self, input):
        if isinstance(input, str):
            texts = [input]
        else:
            texts = list(input)
        return self._embedding_function(texts)

    def embed_query(self, input):
        if hasattr(self._embedding_function, "embed_query"):
            return self._embedding_function.embed_query(input)
        return self.__call__(input)

    def embed_documents(self, input):
        if hasattr(self._embedding_function, "embed_documents"):
            return self._embedding_function.embed_documents(input)
        return self.__call__(input)

    def name(self) -> str:
        if hasattr(self._embedding_function, "name"):
            try:
                return str(self._embedding_function.name())
            except Exception:
                return type(self._embedding_function).__name__
        return type(self._embedding_function).__name__

    def get_config(self) -> Dict[str, Any]:
        if hasattr(self._embedding_function, "get_config"):
            try:
                cfg = self._embedding_function.get_config()
                if isinstance(cfg, dict):
                    return cfg
            except Exception:
                pass
        return {"type": "legacy"}

    @staticmethod
    def build_from_config(config: Dict[str, Any]) -> "_EmbeddingFunctionAdapter":
        return NotImplemented

    def is_legacy(self) -> bool:
        if hasattr(self._embedding_function, "is_legacy"):
            try:
                return bool(self._embedding_function.is_legacy())
            except Exception:
                return True
        return True


def _ensure_embedding_function(embedding_function: Any) -> Any:
    required = ("__call__", "name", "get_config", "is_legacy", "embed_query")
    if all(hasattr(embedding_function, attr) for attr in required):
        return embedding_function
    return _EmbeddingFunctionAdapter(embedding_function)


class LocalHashEmbeddingFunction:
    def __init__(self, dim: int = 64):
        self.dim = int(dim)

    @staticmethod
    def name() -> str:
        return "local_hash"

    def get_config(self) -> dict:
        return {"dim": self.dim}

    @staticmethod
    def build_from_config(config: Dict[str, Any]) -> "LocalHashEmbeddingFunction":
        dim = 64
        if isinstance(config, dict) and config.get("dim") is not None:
            try:
                dim = int(config["dim"])
            except Exception:
                dim = 64
        return LocalHashEmbeddingFunction(dim=dim)

    def default_space(self) -> str:
        return "l2"

    def supported_spaces(self) -> List[str]:
        return ["cosine", "l2", "ip"]

    def validate_config_update(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        return

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> None:
        return

    def embed_query(self, input):
        return self.__call__(input)

    def embed_documents(self, input):
        return self.__call__(input)

    def is_legacy(self) -> bool:
        cfg = self.get_config()
        rebuilt = self.build_from_config(cfg)
        return rebuilt is NotImplemented or rebuilt is None

    def __call__(self, input):
        if isinstance(input, str):
            texts = [input]
        else:
            texts = list(input)
        out = []
        for t in texts:
            vec = [0.0] * self.dim
            for tok in re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", (t or "").lower()):
                h = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
                idx = int.from_bytes(h[:4], "little") % self.dim
                sign = 1.0 if (h[4] % 2 == 0) else -1.0
                vec[idx] += sign
            norm = math.sqrt(sum(v * v for v in vec))
            if norm > 0:
                vec = [v / norm for v in vec]
            out.append(vec)
        return out


class MemoryManager:
    """
    系统的长期记忆中枢。
    使用 ChromaDB 在本地持久化球队的历史表现、教练战术、伤病影响等核心领悟(Insights)。
    """
    def __init__(self, db_path=None, *, collection_name: str = "football_insights", embedding_function=None):
        self.db_path = db_path or os.path.join(data_dir(), "chroma_db")
        os.makedirs(self.db_path, exist_ok=True)
        
        # 初始化 Chroma 客户端 (持久化到本地)
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        if embedding_function is not None:
            self.ef = _ensure_embedding_function(embedding_function)
            effective_collection_name = collection_name
        else:
            backend = (os.getenv("MEMORY_EMBEDDING_BACKEND") or "local").strip().lower()
            if backend == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self.ef = embedding_functions.OpenAIEmbeddingFunction(
                        api_key=api_key,
                        model_name="text-embedding-3-small"
                    )
                    effective_collection_name = collection_name
                else:
                    self.ef = LocalHashEmbeddingFunction()
                    effective_collection_name = f"{collection_name}_local"
            elif backend == "default":
                self.ef = embedding_functions.DefaultEmbeddingFunction()
                effective_collection_name = f"{collection_name}_default"
            else:
                self.ef = LocalHashEmbeddingFunction()
                effective_collection_name = f"{collection_name}_local"
            
        # 创建或获取 Collection
        self.collection = self.client.get_or_create_collection(
            name=effective_collection_name,
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
            
            results = self.collection.get(
                where=where_clause,
                limit=limit,
                include=["documents", "metadatas"]
            )
            docs = results.get("documents") or []
            metas = results.get("metadatas") or []

            if not docs:
                return {"ok": True, "data": [], "message": "未找到相似赔率的历史比赛"}

            out = []
            for i, doc in enumerate(docs):
                meta = metas[i] if i < len(metas) else {}
                out.append({"insight": doc, "metadata": meta})
            return {"ok": True, "data": out}
        except Exception as e:
            return {"ok": False, "error": str(e)}
