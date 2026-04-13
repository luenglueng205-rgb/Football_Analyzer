#!/usr/bin/env python3
"""
足球彩票分析Agent - OpenClaw规范版本
Football Lottery Analysis Agent - OpenClaw Compliant

版本: 1.0.0
规范: OpenClaw Agent Specification v2.0
"""

__version__ = "1.0.0"
__author__ = "Football Lottery Analyst Team"

from .orchestrator import OrchestratorAgent
from .scout import ScoutAgent
from .analyst import AnalystAgent
from .strategist import StrategistAgent
from .risk_manager import RiskManagerAgent

__all__ = [
    "OrchestratorAgent",
    "ScoutAgent", 
    "AnalystAgent",
    "StrategistAgent",
    "RiskManagerAgent"
]
