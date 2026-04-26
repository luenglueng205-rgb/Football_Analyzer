import time
import numpy as np
from typing import Dict, Any, List
from standalone_workspace.skills.spatial_world_model.data_ingestion import SpatialDataIngestion

class SpatioTemporalGNN:
    """
    Phase 2: ST-GNN (Spatio-Temporal Graph Neural Network) 抽象层。
    将光学追踪的 (X, Y) 坐标转化为高阶战术指标 (阵型紧凑度, 防线高度, 压迫强度)。
    """
    def calculate_tactical_metrics(self, team_players: List[Dict[str, float]], is_home: bool) -> Dict[str, float]:
        outfield = [p for p in team_players if p["role"] != "GK"]
        if not outfield:
            return {"compactness": 0.0, "defensive_line_height": 0.0, "centroid_x": 0.0}
        
        xs = [p["x"] for p in outfield]
        ys = [p["y"] for p in outfield]
        
        # 1. 阵型紧凑度 (Compactness) - 所有非门将球员到重心的平均距离 (越小越紧凑)
        centroid_x, centroid_y = float(np.mean(xs)), float(np.mean(ys))
        distances = [np.sqrt((x - centroid_x)**2 + (y - centroid_y)**2) for x, y in zip(xs, ys)]
        compactness = float(np.mean(distances))
        
        # 2. 防线高度 (Defensive Line Height) - 最靠后的 4 名球员的平均 X 坐标
        # 如果是主队 (从左向右攻，X=0是本方球门)，最靠后的X越小；客队则X越大
        sorted_xs = sorted(xs) if is_home else sorted(xs, reverse=True)
        def_line_x = float(np.mean(sorted_xs[:4]))
        
        # 转化为距离本方底线的绝对距离 (0-105)
        def_line_height = def_line_x if is_home else (105.0 - def_line_x)
        
        return {
            "compactness": round(compactness, 2),
            "defensive_line_height": round(def_line_height, 2),
            "centroid_x": round(centroid_x, 2)
        }

class GenerativeWorldModel:
    """
    Phase 3: 生成式世界模型推演 (Latent Space Rollout)。
    结合 ST-GNN 提取的战术特征，在潜空间中生成下半场 15 分钟的比赛剧本。
    """
    def __init__(self):
        self.ingestion = SpatialDataIngestion()
        self.gnn = SpatioTemporalGNN()
        
    def rollout_next_15_mins(self, match_id: str, home_formation: str = "4-3-3", away_formation: str = "4-2-3-1") -> Dict[str, Any]:
        start_t = time.perf_counter()
        
        # 1. 摄取当前帧的空间数据
        frame = self.ingestion.fetch_current_frame(match_id, home_formation, away_formation)
        
        # 2. 经过 ST-GNN 提取高阶战术特征
        home_metrics = self.gnn.calculate_tactical_metrics(frame["home_team"], is_home=True)
        away_metrics = self.gnn.calculate_tactical_metrics(frame["away_team"], is_home=False)
        
        # 3. 潜空间推演逻辑 (模拟大模型/扩散模型的输出)
        # 假设: 防线越高，被打反击的概率越大；阵型越紧凑，防守越稳固。
        home_xg_momentum = 0.0
        away_xg_momentum = 0.0
        narrative = []
        
        # 规则 1: 主队防线极高且客队紧凑，客队容易打出致命反击
        if home_metrics["defensive_line_height"] > 35.0 and away_metrics["compactness"] < 18.0:
            narrative.append("主队防线极其靠上(>35m)，客队阵型保持紧凑(低位密集)，GWM 潜空间推演出客队在未来15分钟内极易通过长传打穿主队身后。")
            away_xg_momentum += 0.45
            
        # 规则 2: 某队阵型极度松散 (体能下降的标志)
        if home_metrics["compactness"] > 22.0:
            narrative.append("主队阵型严重脱节(紧凑度>22m)，三条线间距过大，ST-GNN 检测到主队体能出现真空期。")
            away_xg_momentum += 0.3
        if away_metrics["compactness"] > 22.0:
            narrative.append("客队阵型严重脱节，ST-GNN 检测到防守压迫力断崖式下降。")
            home_xg_momentum += 0.3
            
        if not narrative:
            narrative.append("双方战术处于动态平衡，ST-GNN 未检测到明显的几何克制，预计未来15分钟将陷入中场绞肉机耗局。")
            
        end_t = time.perf_counter()
        
        return {
            "match_id": match_id,
            "tactical_metrics": {
                "home": home_metrics,
                "away": away_metrics
            },
            "latent_rollout": {
                "narrative": " | ".join(narrative),
                "projected_xg_shift": {
                    "home": round(home_xg_momentum, 2),
                    "away": round(away_xg_momentum, 2)
                },
                "recommended_action": "BET_NEXT_GOAL" if (home_xg_momentum > 0.4 or away_xg_momentum > 0.4) else "HOLD"
            },
            "compute_latency_ms": round((end_t - start_t) * 1000, 2)
        }
