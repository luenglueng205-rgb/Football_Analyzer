import numpy as np
import time
from typing import Dict, List, Any

class SpatialDataIngestion:
    """
    空间数据摄取引擎 (Phase 1)
    模拟类似 StatsBomb 360 或 SkillCorner 的光学追踪数据。
    生成 22 名球员与足球在球场上的 (X, Y) 坐标序列。
    球场尺寸标准: 105m x 68m
    """
    def __init__(self):
        self.pitch_length = 105.0
        self.pitch_width = 68.0
        
    def _generate_formation_base(self, formation: str, is_home: bool) -> List[Dict[str, float]]:
        """基于阵型生成基础站位坐标"""
        # 简化版：随机分布在己方半场或进攻半场
        positions = []
        # 守门员
        if is_home:
            positions.append({"role": "GK", "x": 5.0, "y": self.pitch_width / 2})
        else:
            positions.append({"role": "GK", "x": self.pitch_length - 5.0, "y": self.pitch_width / 2})
            
        # 其他 10 名球员随机散布
        for i in range(1, 11):
            if is_home:
                x = np.random.uniform(10.0, self.pitch_length / 2 + 10.0)
            else:
                x = np.random.uniform(self.pitch_length / 2 - 10.0, self.pitch_length - 10.0)
            y = np.random.uniform(5.0, self.pitch_width - 5.0)
            positions.append({"role": f"Outfield_{i}", "x": round(x, 2), "y": round(y, 2)})
            
        return positions

    def fetch_current_frame(self, match_id: str, home_formation: str = "4-3-3", away_formation: str = "4-2-3-1") -> Dict[str, Any]:
        """获取当前帧的光学追踪数据 (Mock)"""
        start_t = time.perf_counter()
        
        home_players = self._generate_formation_base(home_formation, is_home=True)
        away_players = self._generate_formation_base(away_formation, is_home=False)
        
        # 足球位置 (随机在人群中)
        ball_x = np.random.uniform(30.0, 75.0)
        ball_y = np.random.uniform(10.0, 58.0)
        
        end_t = time.perf_counter()
        
        return {
            "match_id": match_id,
            "timestamp": time.time(),
            "pitch_dimensions": {"length": self.pitch_length, "width": self.pitch_width},
            "ball": {"x": round(ball_x, 2), "y": round(ball_y, 2), "z": 0.0},
            "home_team": home_players,
            "away_team": away_players,
            "latency_ms": round((end_t - start_t) * 1000, 2)
        }
        
    def fetch_tracking_sequence(self, match_id: str, frames: int = 50) -> List[Dict[str, Any]]:
        """获取连续多帧的追踪数据序列（用于图神经网络的动态边构建）"""
        sequence = []
        base_frame = self.fetch_current_frame(match_id)
        
        # 基于第一帧做随机游走 (Random Walk) 模拟连续帧
        for i in range(frames):
            frame = {
                "frame_id": i,
                "ball": {
                    "x": max(0, min(self.pitch_length, base_frame["ball"]["x"] + np.random.normal(0, 2))),
                    "y": max(0, min(self.pitch_width, base_frame["ball"]["y"] + np.random.normal(0, 2)))
                },
                "home_team": [],
                "away_team": []
            }
            
            for p in base_frame["home_team"]:
                frame["home_team"].append({
                    "role": p["role"],
                    "x": max(0, min(self.pitch_length, p["x"] + np.random.normal(0, 0.5))),
                    "y": max(0, min(self.pitch_width, p["y"] + np.random.normal(0, 0.5)))
                })
                
            for p in base_frame["away_team"]:
                frame["away_team"].append({
                    "role": p["role"],
                    "x": max(0, min(self.pitch_length, p["x"] + np.random.normal(0, 0.5))),
                    "y": max(0, min(self.pitch_width, p["y"] + np.random.normal(0, 0.5)))
                })
                
            sequence.append(frame)
            
        return sequence
