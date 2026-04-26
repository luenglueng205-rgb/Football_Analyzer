# GWM Phase 1: Spatial Data Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a Spatial Data Ingestion module to simulate and load optical tracking data (like StatsBomb 360) for 22 players, acting as the foundation for the Spatio-Temporal Graph Neural Network (ST-GNN) and Generative World Model (GWM).

**Architecture:** A new module `SpatialDataIngestion` will be created in `core_system/skills/spatial_world_model`. It will generate/mock realistic frame-by-frame 2D spatial coordinates (X, Y) for 22 players and the ball. This will later be used by the MCP tools.

**Tech Stack:** Python, Numpy.

---

### Task 1: Implement Spatial Data Simulator

**Files:**
- Create: `core_system/skills/spatial_world_model/data_ingestion.py`

- [ ] **Step 1: Write the simulator implementation**

```python
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
```

### Task 2: Test Spatial Data Ingestion

**Files:**
- Create: `test_gwm_spatial_data.py`

- [ ] **Step 1: Write the test script**

```python
from core_system.skills.spatial_world_model.data_ingestion import SpatialDataIngestion

def test_spatial_ingestion():
    ingestion = SpatialDataIngestion()
    
    print("1. 测试单帧光学追踪数据生成...")
    frame = ingestion.fetch_current_frame(match_id="TEST_MATCH_001")
    
    assert len(frame["home_team"]) == 11, "Home team must have 11 players"
    assert len(frame["away_team"]) == 11, "Away team must have 11 players"
    assert "x" in frame["ball"] and "y" in frame["ball"], "Ball must have coordinates"
    
    print(f"✅ 单帧生成成功！延迟: {frame['latency_ms']}ms")
    print(f"足球位置: ({frame['ball']['x']}, {frame['ball']['y']})")
    print(f"主队门将位置: ({frame['home_team'][0]['x']}, {frame['home_team'][0]['y']})")
    
    print("\n2. 测试连续多帧(时空序列)生成...")
    sequence = ingestion.fetch_tracking_sequence(match_id="TEST_MATCH_001", frames=5)
    
    assert len(sequence) == 5, "Sequence must have 5 frames"
    assert len(sequence[0]["home_team"]) == 11, "Frame must have 11 home players"
    
    print(f"✅ 连续 5 帧生成成功！")
    for i, f in enumerate(sequence):
        print(f"  Frame {i}: Ball ({f['ball']['x']:.2f}, {f['ball']['y']:.2f})")

if __name__ == "__main__":
    test_spatial_ingestion()
```

- [ ] **Step 2: Run the test**

Run: `PYTHONPATH=. python3 test_gwm_spatial_data.py`
Expected: Output showing successful generation of 11v11 coordinates and continuous frames.

- [ ] **Step 3: Commit changes**

```bash
git add core_system/skills/spatial_world_model/data_ingestion.py test_gwm_spatial_data.py
git commit -m "feat(gwm): implement spatial data ingestion for tracking coordinates"
```
