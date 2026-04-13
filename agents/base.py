#!/usr/bin/env python3
"""
Agent基类 - OpenClaw规范版本
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AgentStatus:
    """Agent状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


class Message:
    """Agent间消息"""
    def __init__(self, sender: str, receiver: str, content: Any, msg_type: str = "task"):
        self.sender = sender
        self.receiver = receiver
        self.content = content
        self.type = msg_type
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "type": self.type,
            "timestamp": self.timestamp
        }


class MessageBus:
    """消息总线"""
    def __init__(self):
        self.agents: Dict[str, 'BaseAgent'] = {}
        self.message_queue: List[Message] = []
    
    def register(self, agent: 'BaseAgent'):
        self.agents[agent.agent_id] = agent
        logger.info(f"Agent {agent.agent_id} registered")
    
    def send_direct(self, message: Message):
        self.message_queue.append(message)
        if message.receiver in self.agents:
            self.agents[message.receiver].receive(message)
    
    def dispatch(self) -> int:
        count = 0
        for message in self.message_queue[:]:
            self.send_direct(message)
            self.message_queue.remove(message)
            count += 1
        return count


# 全局消息总线
message_bus = MessageBus()


class BaseAgent(ABC):
    """
    OpenClaw规范Agent基类
    """
    
    def __init__(self, agent_id: str, name: str, config: Optional[Dict] = None):
        self.agent_id = agent_id
        self.name = name
        self.config = config or {}
        self.status = AgentStatus.IDLE
        self.inbox: List[Message] = []
        self.outbox: List[Message] = []
        
        # Workspace路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        skill_dir = os.path.dirname(current_dir)
        self.workspace = os.path.join(skill_dir, 'workspace', agent_id)
        os.makedirs(self.workspace, exist_ok=True)
        
        logger.info(f"Agent {agent_id} initialized")
    
    @abstractmethod
    def process(self, task: Dict) -> Dict:
        pass
    
    def receive(self, message: Message):
        self.inbox.append(message)
    
    def send(self, receiver: str, content: Any, msg_type: str = "task") -> Message:
        message = Message(self.agent_id, receiver, content, msg_type)
        self.outbox.append(message)
        return message
    
    def get_status(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status,
            "inbox_size": len(self.inbox)
        }
    
    def save_context(self, key: str, value: Any):
        filepath = os.path.join(self.workspace, f"{key}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
    
    def load_context(self, key: str) -> Optional[Any]:
        filepath = os.path.join(self.workspace, f"{key}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
