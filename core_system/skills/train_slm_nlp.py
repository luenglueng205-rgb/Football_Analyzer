import torch
import torch.nn as nn
import os

# Serverless Edge AI (SLM) 预训练任务：
# 训练一个超轻量级的 NLP 模型 (Text -> 胜率偏移量)，导出为 ONNX。
# 它可以被部署在离推特 API 最近的节点，1 毫秒内解析突发伤病情报。

VOCAB = ["injury", "out", "red", "bench", "miss", "start", "return", "goal", "score", "win", "hamstring", "knee", "sick"]

class TinySportsSLM(nn.Module):
    def __init__(self, vocab_size):
        super(TinySportsSLM, self).__init__()
        # 极简的前馈网络，输入为词袋特征 (Bag of Words)
        self.net = nn.Sequential(
            nn.Linear(vocab_size, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 1),
            nn.Sigmoid() # 输出 0.0 (极度负面) 到 1.0 (极度正面)
        )

    def forward(self, x):
        return self.net(x)

def train_and_export_slm():
    print("==================================================")
    print("🧠 [Cloud Brain] 训练专门识别足球突发情报的微型模型 (SLM)...")
    print("==================================================")
    
    vocab_size = len(VOCAB)
    model = TinySportsSLM(vocab_size)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.05)
    
    # 模拟构建一些人工标注的情报数据
    # x = [injury, out, red, bench, miss, start, return, goal, score, win, hamstring, knee, sick]
    X_train = torch.tensor([
        [1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0], # "hamstring injury out miss" -> 极度负面 (0.0)
        [0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0], # "start return" -> 极度正面 (1.0)
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1], # "sick" -> 负面 (0.2)
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], # "bench" -> 中性偏负面 (0.4)
    ], dtype=torch.float32)
    
    y_train = torch.tensor([[0.0], [1.0], [0.2], [0.4]], dtype=torch.float32)
    
    # 极速训练 100 epochs
    for epoch in range(100):
        optimizer.zero_grad()
        loss = criterion(model(X_train), y_train)
        loss.backward()
        optimizer.step()
        
    print(f"   -> 📊 训练完成。Final Loss: {loss.item():.4f}")
    
    # 导出为 ONNX
    os.makedirs("global_knowledge_base/models", exist_ok=True)
    onnx_path = "global_knowledge_base/models/sports_nlp_slm.onnx"
    
    dummy_input = torch.zeros(1, vocab_size)
    torch.onnx.export(
        model, 
        dummy_input, 
        onnx_path, 
        input_names=['text_vec'], 
        output_names=['impact_score'],
        opset_version=11
    )
    print(f"   -> 📦 模型已压缩并导出为 ONNX: {onnx_path} (体积 < 10KB)")

if __name__ == "__main__":
    train_and_export_slm()
