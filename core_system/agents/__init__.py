"""
OpenClaw Football Lottery Multi-Agent System
符合 OpenClaw 规范的多Agent足球彩票分析系统
"""

__version__ = "1.0.0"

__all__ = [
    "BaseAgent",
    "DataParserAgent",
    "PublisherAgent",
    "AINativeCoreAgent"
]


def __getattr__(name):
    if name == "BaseAgent":
        from .base import BaseAgent

        return BaseAgent
    if name == "DataParserAgent":
        from .data_parser import DataParserAgent

        return DataParserAgent
    if name == "PublisherAgent":
        from .publisher_agent import PublisherAgent

        return PublisherAgent
    if name == "AINativeCoreAgent":
        from .ai_native_core import AINativeCoreAgent

        return AINativeCoreAgent
    raise AttributeError(name)
