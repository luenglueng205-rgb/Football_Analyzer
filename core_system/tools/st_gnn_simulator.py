import torch
import torch.nn as nn
import torch.nn.functional as F

class GraphConvolution(nn.Module):
    """
    轻量级图卷积层 (Graph Convolutional Layer)
    用于捕捉同一时刻，球场上 22 名球员与足球之间的空间几何互动。
    """
    def __init__(self, in_features, out_features):
        super(GraphConvolution, self).__init__()
        self.linear = nn.Linear(in_features, out_features)

    def forward(self, x, adj):
        # x: [Batch, Nodes, Features] - 球员的特征 (如坐标、速度)
        # adj: [Batch, Nodes, Nodes] - 球员之间的邻接矩阵 (如传球网络、防守压迫距离)
        
        # 1. 特征变换
        support = self.linear(x)
        # 2. 空间聚合：将邻居球员的特征通过邻接矩阵加权聚合到当前球员身上
        output = torch.bmm(adj, support)
        return F.relu(output)


class STGNN_Cell(nn.Module):
    """
    时空图神经网络单元 (Spatio-Temporal GNN Cell)
    结合 GCN (空间特征) 和 GRU (时间记忆)，学习球员的运动惯性与战术意图。
    """
    def __init__(self, node_features, hidden_dim):
        super(STGNN_Cell, self).__init__()
        self.hidden_dim = hidden_dim
        
        # 空间特征提取
        self.gcn = GraphConvolution(node_features, hidden_dim)
        # 时间特征提取 (处理 GCN 输出和上一步的隐藏状态)
        self.gru = nn.GRUCell(hidden_dim, hidden_dim)

    def forward(self, x, adj, h_prev):
        """
        x: 当前帧的球员特征 [Batch, Nodes, Features]
        adj: 当前帧的邻接矩阵 [Batch, Nodes, Nodes]
        h_prev: 上一帧的隐藏状态记忆 [Batch, Nodes, Hidden_Dim]
        """
        # 1. 提取当前帧的空间战术特征
        spatial_features = self.gcn(x, adj)
        
        # 2. 展平以输入 GRU
        batch_size, num_nodes, _ = spatial_features.shape
        spatial_flat = spatial_features.view(batch_size * num_nodes, self.hidden_dim)
        h_prev_flat = h_prev.view(batch_size * num_nodes, self.hidden_dim)
        
        # 3. 更新时间记忆 (结合历史惯性与当前空间特征)
        h_next_flat = self.gru(spatial_flat, h_prev_flat)
        h_next = h_next_flat.view(batch_size, num_nodes, self.hidden_dim)
        
        return h_next


class GenerativeWorldModel(nn.Module):
    """
    2026 AI-Native: 生成式足球世界模型 (Generative World Model)
    在潜空间 (Latent Space) 中推演未来比赛走向的轻量级模拟器。
    """
    def __init__(self, num_nodes=23, node_features=4, hidden_dim=64):
        super(GenerativeWorldModel, self).__init__()
        self.num_nodes = num_nodes # 22名球员 + 1个足球
        self.node_features = node_features # 默认特征: [x, y, vx, vy] (坐标与速度)
        self.hidden_dim = hidden_dim
        
        # 核心时空引擎
        self.st_cell = STGNN_Cell(node_features, hidden_dim)
        
        # 解码器：将高维隐藏状态还原为下一帧真实的物理状态
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, node_features)
        )

    def forward(self, x_seq, adj_seq, future_steps=10):
        """
        核心推演方法 (Rollout)
        x_seq: 历史轨迹序列 [Batch, Time, Nodes, Features]
        adj_seq: 历史邻接矩阵序列 [Batch, Time, Nodes, Nodes]
        future_steps: 想要在潜空间中推演的未来帧数
        """
        batch_size, seq_len, num_nodes, _ = x_seq.shape
        device = x_seq.device
        
        # 初始化空白的大脑记忆
        h_t = torch.zeros(batch_size, num_nodes, self.hidden_dim).to(device)
        
        # ==========================================
        # 阶段 1: 观察历史 (Burn-in 阶段)，建立比赛上下文记忆
        # ==========================================
        for t in range(seq_len):
            h_t = self.st_cell(x_seq[:, t, :, :], adj_seq[:, t, :, :], h_t)
            
        # ==========================================
        # 阶段 2: 想象未来 (Latent Rollout 阶段)，自回归生成
        # ==========================================
        current_x = x_seq[:, -1, :, :]
        # 简化处理：在极短的推演时间内(如5秒)，假设基础阵型拓扑结构不变
        current_adj = adj_seq[:, -1, :, :] 
        
        predictions = []
        for _ in range(future_steps):
            # 1. 生成下一步的隐藏战术状态
            h_t = self.st_cell(current_x, current_adj, h_t)
            
            # 2. 解码出下一步的物理状态 (球员和球跑到了哪里)
            next_x = self.decoder(h_t)
            predictions.append(next_x.unsqueeze(1))
            
            # 3. 自回归：将大脑想象出的画面，作为下一步推演的输入
            current_x = next_x
            
        # 返回未来 N 帧的完整推演录像: [Batch, Future_Steps, Nodes, Features]
        return torch.cat(predictions, dim=1)

    @staticmethod
    def build_adjacency_matrix(positions: torch.Tensor, threshold=15.0) -> torch.Tensor:
        """
        辅助工具：根据球员在球场上的真实坐标距离，动态构建图的边 (邻接矩阵)。
        positions: [Batch, Nodes, 2] (仅包含 X, Y 坐标)
        threshold: 判定产生战术压迫或传球联系的距离阈值 (如 15 米)
        """
        batch_size, num_nodes, _ = positions.shape
        
        # 计算两两之间的欧式距离矩阵 [Batch, Nodes, Nodes]
        # 使用广播机制: (a-b)^2 = a^2 + b^2 - 2ab
        pos_sq = torch.sum(positions ** 2, dim=-1, keepdim=True)
        dist_sq = pos_sq + pos_sq.transpose(1, 2) - 2 * torch.bmm(positions, positions.transpose(1, 2))
        dist = torch.sqrt(torch.clamp(dist_sq, min=1e-6))
        
        # 二值化：距离小于 threshold 的球员之间连一条边 (值为1)，否则为0
        adj = (dist < threshold).float()
        
        # 归一化处理 (防止度数过大的节点特征爆炸)
        row_sum = adj.sum(dim=-1, keepdim=True)
        adj_normalized = adj / torch.clamp(row_sum, min=1e-6)
        
        return adj_normalized


# ==========================================
# 独立测试与演示代码
# ==========================================
if __name__ == "__main__":
    print("🚀 [World Model] 正在初始化 ST-GNN 生成式足球世界模型...")
    
    # 模拟一场比赛的一个瞬间 (Batch=1)
    BATCH_SIZE = 1
    SEQ_LEN = 5 # 观察过去 5 帧
    NUM_NODES = 23 # 22名球员 + 1个足球
    FEATURES = 4 # [x坐标, y坐标, x速度, y速度]
    
    model = GenerativeWorldModel(num_nodes=NUM_NODES, node_features=FEATURES, hidden_dim=64)
    
    # 伪造一些历史追踪数据 (随机生成)
    mock_history_x = torch.randn(BATCH_SIZE, SEQ_LEN, NUM_NODES, FEATURES)
    
    # 根据坐标伪造历史邻接矩阵
    mock_history_adj = torch.zeros(BATCH_SIZE, SEQ_LEN, NUM_NODES, NUM_NODES)
    for t in range(SEQ_LEN):
        positions = mock_history_x[:, t, :, 0:2] # 提取 xy 坐标
        mock_history_adj[:, t, :, :] = GenerativeWorldModel.build_adjacency_matrix(positions, threshold=15.0)
        
    print(f"📊 [Data Ingestion] 成功注入历史时空图谱。Shape: {mock_history_x.shape}")
    print("🧠 [Latent Rollout] 大脑开始在潜空间中推演未来 10 帧的比赛走向...")
    
    # 运行推演
    future_predictions = model(mock_history_x, mock_history_adj, future_steps=10)
    
    print(f"✅ [Simulation Complete] 推演完成！")
    print(f"🎥 生成的未来录像数据 Shape: {future_predictions.shape} (Batch, Future_Frames, Nodes, Features)")
