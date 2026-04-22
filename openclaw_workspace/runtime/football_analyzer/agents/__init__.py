"""
OpenClaw Football Lottery Multi-Agent System
符合 OpenClaw 规范的多Agent足球彩票分析系统
"""

from .base import BaseAgent
from .data_parser import DataParserAgent
from .publisher_agent import PublisherAgent
from .ai_native_core import AINativeCoreAgent

__version__ = "1.0.0"

__all__ = [
    "BaseAgent",
    "DataParserAgent",
    "PublisherAgent",
    "AINativeCoreAgent"
]
