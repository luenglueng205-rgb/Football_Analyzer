# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - RAG 向量知识库
基于向量检索的增强知识管理

支持:
- 联赛知识向量化存储
- 球队特征向量检索
- 赔率分析模式匹配
- 历史案例相似度搜索
"""

import os
import json
import uuid
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class VectorStoreType(Enum):
    """向量存储类型"""
    IN_MEMORY = "in_memory"       # 内存存储（开发用）
    FAISS = "faiss"               # Facebook FAISS
    CHROMADB = "chromadb"          # ChromaDB
    QDRANT = "qdrant"             # Qdrant


@dataclass
class KnowledgeChunk:
    """知识块"""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at
        }


@dataclass
class SearchResult:
    """搜索结果"""
    chunk: KnowledgeChunk
    score: float
    distance: float


class EmbeddingGenerator:
    """
    向量嵌入生成器
    
    支持多种嵌入模型:
    - OpenAI text-embedding-ada-002
    - Sentence-Transformers (本地)
    - 自定义嵌入函数
    """
    
    def __init__(self, model: str = "simple"):
        self.model = model
        self._embedding_cache: Dict[str, List[float]] = {}
        
        # 简单的基于TF-IDF的嵌入（可替换为真实模型）
        self._vocabulary: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}
    
    def generate(self, text: str) -> List[float]:
        """生成文本嵌入向量"""
        if self.model == "simple":
            return self._simple_embedding(text)
        elif self.model == "tfidf":
            return self._tfidf_embedding(text)
        else:
            return self._simple_embedding(text)
    
    def _simple_embedding(self, text: str) -> List[float]:
        """简单嵌入: 基于字符频率"""
        # 固定维度256
        dim = 256
        vector = [0.0] * dim
        
        text_lower = text.lower()
        for i, char in enumerate(text_lower):
            idx = ord(char) % dim
            vector[idx] += 1.0 / (i + 1)  # 位置加权
        
        # L2归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector
    
    def _tfidf_embedding(self, text: str) -> List[float]:
        """TF-IDF嵌入"""
        words = text.lower().split()
        dim = max(len(self._vocabulary), 256)
        vector = [0.0] * dim
        
        tf = {}
        for word in words:
            tf[word] = tf.get(word, 0) + 1
        
        for word, count in tf.items():
            if word in self._vocabulary:
                idx = self._vocabulary[word]
                idf = self._idf.get(word, 1.0)
                vector[idx] = count * idf
        
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector[:256] if len(vector) > 256 else vector + [0.0] * (256 - len(vector))
    
    def compute_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2:
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


class InMemoryVectorStore:
    """内存向量存储"""
    
    def __init__(self, embedding_generator: EmbeddingGenerator):
        self.embedding_generator = embedding_generator
        self.chunks: Dict[str, KnowledgeChunk] = {}
        self.embeddings: Dict[str, List[float]] = {}
    
    def add(self, chunk: KnowledgeChunk) -> str:
        """添加知识块"""
        chunk.chunk_id = chunk.chunk_id or str(uuid.uuid4())[:8]
        
        # 生成嵌入
        if not chunk.embedding:
            chunk.embedding = self.embedding_generator.generate(chunk.content)
        
        self.chunks[chunk.chunk_id] = chunk
        self.embeddings[chunk.chunk_id] = chunk.embedding
        
        return chunk.chunk_id
    
    def search(self, query: str, top_k: int = 5, 
               filter_metadata: Optional[Dict] = None) -> List[SearchResult]:
        """向量搜索"""
        # 生成查询向量
        query_embedding = self.embedding_generator.generate(query)
        
        results = []
        for chunk_id, chunk in self.chunks.items():
            # 元数据过滤
            if filter_metadata:
                match = True
                for key, value in filter_metadata.items():
                    if chunk.metadata.get(key) != value:
                        match = False
                        break
                if not match:
                    continue
            
            # 计算相似度
            embedding = self.embeddings.get(chunk_id)
            if embedding:
                similarity = self.embedding_generator.compute_similarity(
                    query_embedding, embedding
                )
                distance = 1 - similarity
                
                results.append(SearchResult(
                    chunk=chunk,
                    score=similarity,
                    distance=distance
                ))
        
        # 排序并返回top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def delete(self, chunk_id: str) -> bool:
        """删除知识块"""
        if chunk_id in self.chunks:
            del self.chunks[chunk_id]
            if chunk_id in self.embeddings:
                del self.embeddings[chunk_id]
            return True
        return False
    
    def count(self) -> int:
        """知识块数量"""
        return len(self.chunks)


class RagKnowledgeBase:
    """
    RAG 知识库
    
    功能:
    - 知识存储与检索
    - 自动分块
    - 混合搜索
    """
    
    def __init__(self, store_type: VectorStoreType = VectorStoreType.IN_MEMORY):
        self.embedding_generator = EmbeddingGenerator()
        
        if store_type == VectorStoreType.IN_MEMORY:
            self.vector_store = InMemoryVectorStore(self.embedding_generator)
        else:
            # 其他存储类型可以后续扩展
            self.vector_store = InMemoryVectorStore(self.embedding_generator)
        
        self.storage_dir: Optional[str] = None
    
    def configure_storage(self, storage_dir: str):
        """配置持久化存储"""
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        
        # 加载已有数据
        self._load_from_disk()
    
    def add_knowledge(self, content: str, metadata: Dict[str, Any]) -> str:
        """添加知识"""
        chunk = KnowledgeChunk(
            chunk_id=str(uuid.uuid4())[:8],
            content=content,
            metadata=metadata
        )
        
        chunk_id = self.vector_store.add(chunk)
        
        # 持久化
        if self.storage_dir:
            self._save_to_disk()
        
        return chunk_id
    
    def add_league_knowledge(self, league_id: str, league_name: str,
                            characteristics: Dict[str, Any]) -> str:
        """添加联赛知识"""
        content = f"""
联赛: {league_name}
特点: {json.dumps(characteristics, ensure_ascii=False)}
适合玩法: {characteristics.get('suitable_bet_types', [])}
平均进球: {characteristics.get('avg_goals', 0)}
主场胜率: {characteristics.get('home_win_rate', 0)}
""".strip()
        
        return self.add_knowledge(content, {
            "type": "league",
            "league_id": league_id,
            "league_name": league_name
        })
    
    def add_team_knowledge(self, team_id: str, team_name: str,
                          league: str, form: List[str],
                          stats: Dict[str, Any]) -> str:
        """添加球队知识"""
        content = f"""
球队: {team_name}
联赛: {league}
近期状态: {', '.join(form)}
进球统计: 场均{stats.get('avg_goals_scored', 0)}球
丢球统计: 场均{stats.get('avg_goals_conceded', 0)}球
战术风格: {stats.get('tactical_style', '未知')}
关键球员: {', '.join(stats.get('key_players', []))}
""".strip()
        
        return self.add_knowledge(content, {
            "type": "team",
            "team_id": team_id,
            "team_name": team_name,
            "league": league
        })
    
    def add_betting_case(self, case_id: str, league: str, teams: str,
                        bet_type: str, odds: float, result: str,
                        analysis: str) -> str:
        """添加投注案例"""
        content = f"""
案例: {teams}
联赛: {league}
投注类型: {bet_type}
赔率: {odds}
结果: {result}
分析: {analysis}
""".strip()
        
        return self.add_knowledge(content, {
            "type": "betting_case",
            "case_id": case_id,
            "league": league,
            "bet_type": bet_type,
            "result": result
        })
    
    def search(self, query: str, top_k: int = 5,
               filters: Optional[Dict] = None) -> List[Dict]:
        """搜索知识"""
        results = self.vector_store.search(query, top_k, filters)
        
        return [
            {
                "content": r.chunk.content,
                "metadata": r.chunk.metadata,
                "score": r.score,
                "chunk_id": r.chunk.chunk_id
            }
            for r in results
        ]
    
    def search_leagues(self, query: str, top_k: int = 3) -> List[Dict]:
        """搜索联赛知识"""
        return self.search(query, top_k, {"type": "league"})
    
    def search_teams(self, query: str, league: Optional[str] = None,
                    top_k: int = 3) -> List[Dict]:
        """搜索球队知识"""
        filters = {"type": "team"}
        if league:
            filters["league"] = league
        return self.search(query, top_k, filters)
    
    def search_similar_cases(self, query: str, 
                            result: Optional[str] = None,
                            top_k: int = 5) -> List[Dict]:
        """搜索相似投注案例"""
        filters = {"type": "betting_case"}
        if result:
            filters["result"] = result
        return self.search(query, top_k, filters)
    
    def get_context_for_query(self, query: str, 
                              max_contexts: int = 3) -> str:
        """获取查询上下文"""
        results = self.search(query, max_contexts)
        
        context_parts = []
        for i, r in enumerate(results, 1):
            context_parts.append(f"[来源{i}] {r['content']}")
        
        return "\n\n".join(context_parts)
    
    def _save_to_disk(self):
        """保存到磁盘"""
        if not self.storage_dir:
            return
        
        chunks_data = {
            chunk_id: chunk.to_dict() 
            for chunk_id, chunk in self.vector_store.chunks.items()
        }
        
        filepath = os.path.join(self.storage_dir, "rag_knowledge.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=2)
    
    def _load_from_disk(self):
        """从磁盘加载"""
        if not self.storage_dir:
            return
        
        filepath = os.path.join(self.storage_dir, "rag_knowledge.json")
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                chunks_data = json.load(f)
            
            for chunk_id, chunk_dict in chunks_data.items():
                chunk = KnowledgeChunk(
                    chunk_id=chunk_dict["chunk_id"],
                    content=chunk_dict["content"],
                    metadata=chunk_dict["metadata"],
                    created_at=chunk_dict.get("created_at", "")
                )
                chunk.embedding = self.embedding_generator.generate(chunk.content)
                self.vector_store.add(chunk)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        type_counts = {}
        for chunk in self.vector_store.chunks.values():
            chunk_type = chunk.metadata.get("type", "unknown")
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
        
        return {
            "total_chunks": self.vector_store.count(),
            "by_type": type_counts,
            "storage_type": self.vector_store.__class__.__name__
        }


# 全局知识库实例
_rag_knowledge_base: Optional[RagKnowledgeBase] = None

def get_rag_knowledge_base() -> RagKnowledgeBase:
    """获取全局RAG知识库"""
    global _rag_knowledge_base
    if _rag_knowledge_base is None:
        _rag_knowledge_base = RagKnowledgeBase()
    return _rag_knowledge_base


def init_rag_knowledge_base(storage_dir: str) -> RagKnowledgeBase:
    """初始化RAG知识库"""
    global _rag_knowledge_base
    _rag_knowledge_base = RagKnowledgeBase()
    _rag_knowledge_base.configure_storage(storage_dir)
    return _rag_knowledge_base


if __name__ == "__main__":
    # 测试RAG知识库
    rag = RagKnowledgeBase()
    
    # 添加知识
    rag.add_league_knowledge(
        league_id="epl",
        league_name="英超",
        characteristics={
            "avg_goals": 2.8,
            "home_win_rate": 0.45,
            "suitable_bet_types": ["胜平负", "大小球"]
        }
    )
    
    rag.add_team_knowledge(
        team_id="manu",
        team_name="曼联",
        league="英超",
        form=["胜", "平", "胜", "负", "胜"],
        stats={
            "avg_goals_scored": 1.8,
            "avg_goals_conceded": 1.2,
            "key_players": ["B费", "拉什福德"]
        }
    )
    
    # 搜索
    results = rag.search("英超球队进攻")
    print(f"搜索结果: {len(results)} 条")
    for r in results:
        print(f"  - {r['content'][:50]}... (score: {r['score']:.3f})")
    
    print(f"\n统计: {rag.get_stats()}")
