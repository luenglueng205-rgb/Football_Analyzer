# standalone_workspace/qa_engine/coverage_matrix.py
import json
import os
from pathlib import Path

# 16 Play Types
PLAY_TYPES = [
    "JINGCAI_WDL", "JINGCAI_HANDICAP_WDL", "JINGCAI_CS", "JINGCAI_GOALS", "JINGCAI_HTFT", "JINGCAI_MIXED_PARLAY",
    "BEIDAN_WDL", "BEIDAN_SFGG", "BEIDAN_UP_DOWN_ODD_EVEN", "BEIDAN_GOALS", "BEIDAN_HTFT", "BEIDAN_CS",
    "ZUCAI_14_MATCH", "ZUCAI_RENJIU", "ZUCAI_6_HTFT", "ZUCAI_4_GOALS"
]

# 6 Lifecycle Stages
STAGES = ["ANALYSIS", "SELECTION", "BETTING", "PARLAY", "LIVE_CHECK", "SETTLEMENT"]

class CoverageTracker:
    def __init__(self):
        self.matrix = {pt: {st: False for st in STAGES} for pt in PLAY_TYPES}
        
    def mark_covered(self, play_type: str, stage: str):
        if play_type in self.matrix and stage in self.matrix[play_type]:
            self.matrix[play_type][stage] = True
            
    def get_coverage_report(self) -> dict:
        total_nodes = len(PLAY_TYPES) * len(STAGES)
        covered_nodes = sum(sum(1 for st in self.matrix[pt].values() if st) for pt in PLAY_TYPES)
        
        missing = []
        for pt in PLAY_TYPES:
            for st in STAGES:
                if not self.matrix[pt][st]:
                    missing.append(f"{pt} -> {st}")
                    
        return {
            "total_nodes": total_nodes,
            "covered_nodes": covered_nodes,
            "coverage_percentage": round((covered_nodes / total_nodes) * 100, 2),
            "is_complete": covered_nodes == total_nodes,
            "missing_nodes": missing,
            "matrix_data": self.matrix
        }

# Global instance for tests to register coverage
_tracker = CoverageTracker()

def matrix_cover(play_type: str, stage: str):
    """
    Decorator for pytest functions to register that they test a specific matrix node.
    """
    def decorator(func):
        # Register immediately upon import/collection
        _tracker.mark_covered(play_type, stage)
        return func
    return decorator

def get_global_tracker():
    return _tracker
