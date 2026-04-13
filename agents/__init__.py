"""
OpenClaw Football Lottery Multi-Agent System
符合 OpenClaw 规范的多Agent足球彩票分析系统
"""

from .orchestrator import OrchestratorAgent
from .scout import ScoutAgent
from .analyst import AnalystAgent
from .strategist import StrategistAgent
from .risk_manager import RiskManagerAgent
from .base import BaseAgent, AgentStatus, Message, message_bus

__version__ = "1.0.0"

__all__ = [
    "OrchestratorAgent",
    "ScoutAgent",
    "AnalystAgent",
    "StrategistAgent",
    "RiskManagerAgent",
    "BaseAgent",
    "AgentStatus",
    "Message",
    "message_bus",
]
