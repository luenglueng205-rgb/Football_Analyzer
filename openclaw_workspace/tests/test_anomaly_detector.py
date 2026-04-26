import os
import sys
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.anomaly_detector import AnomalyDetector


def test_detect_bookmaker_anomaly():
    detector = AnomalyDetector()

    res_normal = detector.detect_anomaly(
        home_odds=1.5, draw_odds=4.0, away_odds=6.0, odds_drop_ratio=0.01
    )
    assert res_normal["is_trap"] is False

    res_trap = detector.detect_anomaly(
        home_odds=1.2, draw_odds=5.5, away_odds=10.0, odds_drop_ratio=0.16
    )
    assert res_trap["is_trap"] is True
    assert "TRAP" in res_trap["reason"]
