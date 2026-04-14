import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class AsyncBaseAgent(ABC):
    """
    2026 Next-Gen Async Agent Base Class
    全面拥抱 asyncio，适配 Graph State 模式
    """
    def __init__(self, agent_id: str, name: str, config: Optional[Dict] = None):
        self.agent_id = agent_id
        self.name = name
        self.config = config or {}
        
        # Workspace 路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        skill_dir = os.path.dirname(current_dir)
        self.workspace = os.path.join(skill_dir, 'workspace', agent_id)
        os.makedirs(self.workspace, exist_ok=True)
        
        logger.info(f"[AsyncBaseAgent] {agent_id} initialized")
    
    @abstractmethod
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        接收全局 State，返回需要更新的 State 增量（Delta）。
        这种模式彻底取代了原本的单线 Handoff。
        """
        pass
    
    async def save_context(self, key: str, value: Any):
        # 实际生产中可使用 aiofiles，此处简化
        filepath = os.path.join(self.workspace, f"{key}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
    
    async def load_context(self, key: str) -> Optional[Any]:
        filepath = os.path.join(self.workspace, f"{key}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
