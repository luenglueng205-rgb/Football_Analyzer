import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from standalone_workspace.skills.spatial_world_model.data_ingestion import SpatialDataIngestion

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
