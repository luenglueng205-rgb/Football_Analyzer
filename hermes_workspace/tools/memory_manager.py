import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any

from tools.paths import data_dir

import hashlib
import math
import re

# ── Type 常量：统一写入/查询时的 metadata type 字段命名 ──────────────────────
# ⚠️  写入方和查询方必须使用同一常量，否则 ChromaDB 的 where 过滤永远匹配不上
MEMORY_TYPE_EPISODIC = "episodic"          # 通用情景记忆（战术洞察等）
MEMORY_TYPE_HISTORICAL_MATCH = "historical_match"  # 带赔率的历史比赛记录


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
        [修改版] 存入记忆时强制打上时间戳
        """
        from datetime import datetime
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            # 使用时间戳或随机数确保 ID 唯一，这里简单用 team + match_id
            import time
            doc_id = f"{team_name}_{match_id}_{int(time.time())}"
            
            self.collection.add(
                documents=[insight_text],
                metadatas=[{"team": team_name, "match_id": match_id, "confidence": confidence, "date": today_str}],
                ids=[doc_id]
            )
            return {"ok": True, "message": f"Insight for {team_name} saved successfully.", "doc_id": doc_id}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def add_episodic_memory(self, content: str, tags: List[str], importance: float = 0.5,
                             memory_type: str = MEMORY_TYPE_EPISODIC):
        """
        向系统的情景记忆库中添加一条历史赛事经验 (Massive Episodic Memory)

        Args:
            memory_type: 记忆类型，默认Episodic。
                         若需让 query_historical_odds() 能检索到（含赔率的情景记忆），
                         请传入 MEMORY_TYPE_HISTORICAL_MATCH。
        """
        try:
            import time
            doc_id = f"episodic_{int(time.time()*1000)}_{hash(content)}"
            
            # ✅ P0-3：统一使用常量，防止 type 字符串硬编码不一致
            self.collection.add(
                documents=[content],
                metadatas=[{
                    "type": memory_type,
                    "importance": importance,
                    "tags": ",".join(tags)
                }],
                ids=[doc_id]
            )
            return {"ok": True, "doc_id": doc_id}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    def retrieve_memory(self, team_name: str, query_context: str = "", limit: int = 5, decay_days: int = 365) -> dict:
        """
        检索关于某支球队的历史记忆
        如果提供了 query_context，会基于语义进行相似度检索；否则只按 metadata 过滤。
        【新增机制】：记忆衰减与遗忘机制 (Memory Decay)。过滤掉超过 decay_days 的陈旧记忆，防止过时战术污染上下文。
        """
        try:
            query_text = query_context if query_context else f"{team_name} 的战术特点和近期表现"
            
            # 计算衰减阈值的时间戳
            from datetime import datetime, timedelta
            cutoff_date = (datetime.now() - timedelta(days=decay_days)).strftime("%Y-%m-%d")
            
            results = self.collection.query(
                query_texts=[query_text],
                n_results=limit,
                where={
                    "$and": [
                        {"team": {"$eq": team_name}},
                        {"date": {"$gte": cutoff_date}} # 遗忘机制：只召回 cutoff_date 之后的记忆
                    ]
                }
            )
            
            if not results.get("documents") or not results["documents"][0]:
                # 尝试不带时间过滤，看是否有历史数据（如果有，说明被遗忘了）
                fallback = self.collection.query(query_texts=[query_text], n_results=1, where={"team": team_name})
                if fallback.get("documents") and fallback["documents"][0]:
                    return {"ok": True, "data": [], "message": f"找到了 {team_name} 的记忆，但因超过 {decay_days} 天已被系统自动遗忘。"}
                return {"ok": True, "data": [], "message": f"No memory found for {team_name}."}
                
            memories = []
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") and results["metadatas"][0] else {}
                memories.append({
                    "insight": doc,
                    "match_id": meta.get("match_id"),
                    "confidence": meta.get("confidence"),
                    "date": meta.get("date", "unknown")
                })
                
            return {"ok": True, "data": memories}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def query_historical_odds(self, league: str, home_odds: float, draw_odds: float, away_odds: float, tolerance: float = 0.10, limit: int = 20) -> dict:
        """
        [修复版] 精确数值过滤查询：彻底摒弃大模型对数字极度不敏感的语义向量查询。
        改用 ChromaDB 的结构化 Metadata 逻辑运算符 ($and, $gte, $lte) 进行硬逻辑区间匹配。

        ✅ P0-3：type 过滤改用 $or，同时命中两类来源：
          * add_historical_matches_batch() 写入的 "historical_match" 记录
          * add_episodic_memory() 中传入 memory_type=HISTORICAL_MATCH 的情景记忆
        """
        try:
            # 构建容差区间
            h_min, h_max = home_odds * (1 - tolerance), home_odds * (1 + tolerance)
            d_min, d_max = draw_odds * (1 - tolerance), draw_odds * (1 + tolerance)
            a_min, a_max = away_odds * (1 - tolerance), away_odds * (1 + tolerance)
            
            # ✅ P0-3：$or 匹配两种 type，消除写/查 type 不一致的查询死区
            where_clause = {
                "$and": [
                    {
                        "$or": [
                            {"type": {"$eq": MEMORY_TYPE_HISTORICAL_MATCH}},
                            {"type": {"$eq": MEMORY_TYPE_EPISODIC}}   # 含赔率的Episodic记忆
                        ]
                    },
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

    def add_historical_matches_batch(self, matches: list) -> dict:
        """
        批量导入结构化的历史比赛数据，不经过昂贵的语义嵌入。
        供数据灌入脚本使用，建立 22 万场的庞大记忆库。
        """
        try:
            documents = []
            metadatas = []
            ids = []
            
            for m in matches:
                home_goals = int(m.get("home_goals", 0))
                away_goals = int(m.get("away_goals", 0))
                total_goals = home_goals + away_goals
                
                # 提取赛果特征标签
                if home_goals > away_goals:
                    result_tag = "主胜"
                    if home_goals - away_goals == 1:
                        result_tag += ", 净胜1球(让平)"
                elif home_goals < away_goals:
                    result_tag = "客胜"
                else:
                    result_tag = "平局"
                    
                over_tag = "大球(>2.5)" if total_goals > 2.5 else "小球(<2.5)"
                
                doc_text = f"{m['league']} | {m['date']} | {m['home_team']} {m['home_goals']}-{m['away_goals']} {m['away_team']} | 标签: {result_tag}, {over_tag}"
                
                documents.append(doc_text)
                
                metadatas.append({
                    "type": MEMORY_TYPE_HISTORICAL_MATCH,
                    "league": m.get("league", "UNK"),
                    "home_odds": float(m.get("home_odds", 1.0)),
                    "draw_odds": float(m.get("draw_odds", 1.0)),
                    "away_odds": float(m.get("away_odds", 1.0)),
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "date": m.get("date", "1970-01-01")
                })
                
                # 唯一 ID
                ids.append(f"hist_{m.get('league')}_{m.get('date')}_{m.get('home_team')}_{m.get('away_team')}")

            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            return {"ok": True, "count": len(matches)}
        except Exception as e:
            return {"ok": False, "error": str(e)}
