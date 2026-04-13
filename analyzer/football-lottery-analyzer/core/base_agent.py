#!/usr/bin/env python3
"""
多Agent协作架构 - 基类模块
定义所有Agent的通用接口和消息系统
"""

import os
import sys
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import queue
import threading

# 路径处理
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PROJECT_ROOT)
DATA_DIR = os.path.join(BASE_DIR, 'data', 'chinese_mapped')
sys.path.insert(0, PROJECT_ROOT)


class AgentStatus(Enum):
    """Agent状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class AgentMessage:
    """Agent间消息"""
    sender: str
    recipient: str
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    msg_type: str = "info"
    
    def to_dict(self) -> Dict:
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "msg_type": self.msg_type
        }


@dataclass
class Task:
    """任务单元"""
    task_id: str
    agent_name: str
    task_type: str
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    status: AgentStatus = AgentStatus.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    result: Optional[Dict] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "task_type": self.task_type,
            "payload": self.payload,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "result": self.result,
            "error": self.error
        }


class MessageBus:
    """Agent消息总线"""
    
    def __init__(self):
        self._inbox: Dict[str, List[AgentMessage]] = {}
        self._lock = threading.Lock()
    
    def send(self, message: AgentMessage) -> None:
        """发送消息"""
        with self._lock:
            if message.recipient not in self._inbox:
                self._inbox[message.recipient] = []
            self._inbox[message.recipient].append(message)
    
    def receive(self, recipient: str) -> List[AgentMessage]:
        """接收消息"""
        with self._lock:
            messages = self._inbox.get(recipient, [])
            self._inbox[recipient] = []
            return messages
    
    def broadcast(self, sender: str, content: Dict, recipients: List[str]) -> None:
        """广播消息"""
        for recipient in recipients:
            msg = AgentMessage(
                sender=sender,
                recipient=recipient,
                content=content,
                msg_type="broadcast"
            )
            self.send(msg)


class BaseAgent(ABC):
    """所有Agent的基类"""
    
    def __init__(self, name: str, message_bus: Optional[MessageBus] = None):
        self.name = name
        self.status = AgentStatus.IDLE
        self.message_bus = message_bus or MessageBus()
        self._tasks: List[Task] = []
        self._results: Dict[str, Any] = {}
        self._last_error: Optional[str] = None
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化Agent"""
        pass
    
    @abstractmethod
    def process(self, task: Task) -> Dict[str, Any]:
        """处理任务"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """获取Agent能力"""
        pass
    
    def send_message(self, recipient: str, content: Dict, msg_type: str = "info") -> None:
        """发送消息到其他Agent"""
        message = AgentMessage(
            sender=self.name,
            recipient=recipient,
            content=content,
            msg_type=msg_type
        )
        self.message_bus.send(message)
    
    def receive_messages(self) -> List[AgentMessage]:
        """接收消息"""
        return self.message_bus.receive(self.name)
    
    def set_status(self, status: AgentStatus) -> None:
        """设置状态"""
        self.status = status
    
    def get_results(self) -> Dict[str, Any]:
        """获取结果"""
        return self._results
    
    def set_result(self, key: str, value: Any) -> None:
        """设置结果"""
        self._results[key] = value
    
    def get_info(self) -> Dict:
        """获取Agent信息"""
        return {
            "name": self.name,
            "status": self.status.value,
            "capabilities": self.get_capabilities(),
            "task_count": len(self._tasks)
        }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, status={self.status.value})>"


class AgentRegistry:
    """Agent注册中心"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._agents: Dict[str, BaseAgent] = {}
                    cls._instance._message_bus = MessageBus()
        return cls._instance
    
    def register(self, agent: BaseAgent) -> None:
        """注册Agent"""
        self._agents[agent.name] = agent
    
    def unregister(self, agent_name: str) -> None:
        """注销Agent"""
        if agent_name in self._agents:
            del self._agents[agent_name]
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """获取Agent"""
        return self._agents.get(agent_name)
    
    def get_all_agents(self) -> Dict[str, BaseAgent]:
        """获取所有Agent"""
        return self._agents.copy()
    
    def get_message_bus(self) -> MessageBus:
        """获取消息总线"""
        return self._message_bus
    
    def list_agents(self) -> List[Dict]:
        """列出所有Agent"""
        return [agent.get_info() for agent in self._agents.values()]


def get_registry() -> AgentRegistry:
    """获取Agent注册中心单例"""
    return AgentRegistry()


# 导出
__all__ = [
    'AgentStatus',
    'TaskPriority', 
    'AgentMessage',
    'Task',
    'MessageBus',
    'BaseAgent',
    'AgentRegistry',
    'get_registry'
]
