import onnxruntime as ort
import numpy as np
import time
import json

# Serverless Edge AI (SLM) 推理端：
# 这个脚本将被部署在边缘服务器上。它直接监听推特 Webhook，
# 收到推文后，在零外部 API 依赖的情况下，不到 1 毫秒内输出对胜率的修正值。

VOCAB = ["injury", "out", "red", "bench", "miss", "start", "return", "goal", "score", "win", "hamstring", "knee", "sick"]

class EdgeNLPFilter:
    def __init__(self, model_path="global_knowledge_base/models/sports_nlp_slm.onnx"):
        print("==================================================")
        print("🌩️ [Edge Serverless] 启动本地微型 NLP 过滤器 (SLM)...")
        print("==================================================")
        # 强制使用 CPU，极低内存占用
        self.session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
        print(f"   -> 📦 ONNX 模型加载完毕。内存常驻: 极低。")

    def _text_to_vector(self, text):
        """极简的分词器 (Tokenizer)"""
        text = text.lower()
        vec = [1.0 if word in text else 0.0 for word in VOCAB]
        return np.array([vec], dtype=np.float32)

    def parse_breaking_news(self, tweet_text):
        print(f"\n   -> 🐦 [Webhook 触发] 收到实时突发推文: '{tweet_text}'")
        
        start_time = time.perf_counter()
        
        # 1. 文本转张量
        input_vec = self._text_to_vector(tweet_text)
        
        # 2. ONNX 极速推理
        output = self.session.run(None, {"text_vec": input_vec})
        impact_score = output[0][0][0] # 0.0 to 1.0
        
        # 3. 将 0-1 的得分映射为对胜率的修正值 (-0.20 到 +0.20)
        # 例如 0.5 是中性，0.0 是极端负面 (-0.20)，1.0 是极端正面 (+0.20)
        win_rate_adjustment = (impact_score - 0.5) * 0.4
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        result = {
            "signal_type": "POSITIVE" if win_rate_adjustment > 0.05 else "NEGATIVE" if win_rate_adjustment < -0.05 else "NEUTRAL",
            "impact_score": float(impact_score),
            "win_rate_adj": float(win_rate_adjustment),
            "latency_ms": latency_ms
        }
        
        print(f"   -> ⚡ [Inference] 本地推理耗时: {latency_ms:.3f} 毫秒 (Zero LLM API Call)")
        print(f"   -> 📊 [Signal] 解析结果: {json.dumps(result, ensure_ascii=False)}")
        
        return result

if __name__ == "__main__":
    edge_filter = EdgeNLPFilter()
    
    # 模拟赛前 30 分钟收到的三条跟队记者推文
    tweets = [
        "BREAKING: Saka has a hamstring injury and will miss the match.",
        "Good news! Odegaard will start and return to the pitch today.",
        "Manager says the team is ready for the match."
    ]
    
    for tweet in tweets:
        edge_filter.parse_breaking_news(tweet)
