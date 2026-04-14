import json
import os
import math
from typing import List, Dict, Any

# 在 2026 年，我们不建议单纯的字符串匹配，而是用 Embedding 计算余弦相似度。
# 考虑到本地测试无 Key 降级，这里提供一个基于特征向量的轻量级相似度引擎 (Temporal Graph RAG 雏形)

try:
    from tools.paths import data_dir
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.paths import data_dir

class TemporalGraphRAG:
    """
    2026 版时序知识图谱与 RAG 引擎
    不再只靠 "loss" 这个词来反思，而是记录当时盘口的具体特征（向量化），
    当遇到类似的盘口特征时，自动唤醒当时的教训。
    """
    def __init__(self, db_path: str = None):
        if db_path is None:
            self.db_path = os.path.join(data_dir(), "memory", "graph_rag.json")
        else:
            self.db_path = db_path
            
        self.nodes = self._load_db()

    def _load_db(self) -> List[Dict]:
        if os.path.exists(self.db_path):
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_db(self):
        dir_name = os.path.dirname(self.db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self.nodes, f, ensure_ascii=False, indent=2)

    def _calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """简单的余弦相似度计算"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def add_lesson(self, match_info: Dict, odds_features: List[float], lesson: str, rl_weight: float = 1.0):
        """
        录入翻车教训（节点）
        odds_features: [主胜赔率, 让球盘口, 水位变动幅度, 必发热度] 等归一化向量
        """
        node = {
            "match": match_info,
            "vector": odds_features,
            "lesson": lesson,
            "weight": rl_weight,  # RLMF (市场反馈强化学习) 权重
            "timestamp": "2026-04-14T10:00:00"
        }
        self.nodes.append(node)
        self._save_db()
        print(f"[GraphRAG] 已将教训录入知识图谱: {lesson} (权重: {rl_weight})")

    def search_similar_patterns(self, current_features: List[float], top_k: int = 2) -> List[Dict]:
        """
        RAG 检索：遇到新比赛时，查找历史上最相似的操盘套路
        """
        results = []
        for node in self.nodes:
            sim = self._calculate_similarity(current_features, node["vector"])
            if sim > 0.8: # 相似度阈值
                results.append({
                    "lesson": node["lesson"],
                    "similarity": sim,
                    "weight": node["weight"],
                    "historical_match": f"{node['match'].get('home')} vs {node['match'].get('away')}"
                })
        
        results.sort(key=lambda x: x["similarity"] * x["weight"], reverse=True)
        return results[:top_k]

    def rlmf_feedback(self, lesson_text: str, is_correct: bool):
        """
        市场反馈强化学习 (RLMF)：
        如果系统提取的教训在本次预测中被证明是正确的，则增加该图谱路径的权重；否则降低。
        """
        for node in self.nodes:
            if node["lesson"] == lesson_text:
                if is_correct:
                    node["weight"] *= 1.1 # 增强 10%
                    print(f"[RLMF] 市场反馈正确，强化教训权重: {lesson_text} -> {node['weight']:.2f}")
                else:
                    node["weight"] *= 0.8 # 衰减 20%
                    print(f"[RLMF] 市场反馈错误，削弱教训权重: {lesson_text} -> {node['weight']:.2f}")
        self._save_db()

# 测试用例
if __name__ == "__main__":
    rag = TemporalGraphRAG("test_rag.json")
    # 录入一条 2025 年的翻车记录：初盘半一，临场狂降水，最后大热必死
    rag.add_lesson(
        match_info={"home": "曼联", "away": "伯恩茅斯", "league": "英超"},
        odds_features=[1.75, -0.75, -0.20, 0.85], # [主胜, 盘口, 水位跌幅, 热度]
        lesson="半一盘深开且临场疯狂造热降水，典型诱盘，大热必死！",
        rl_weight=1.0
    )
    
    print("\n[GraphRAG] 正在分析今天的比赛：阿森纳 vs 维拉...")
    # 今天阿森纳的盘口特征非常相似
    current_features = [1.70, -0.75, -0.22, 0.88] 
    
    similar_lessons = rag.search_similar_patterns(current_features)
    if similar_lessons:
        print("⚠️ [GraphRAG 警报] 发现历史相似操盘套路！")
        for s in similar_lessons:
            print(f"  - 历史比赛: {s['historical_match']}")
            print(f"  - 相似度: {s['similarity']*100:.1f}%")
            print(f"  - 提取教训: {s['lesson']}")
            
    # 清理测试文件
    if os.path.exists("test_rag.json"):
        os.remove("test_rag.json")
