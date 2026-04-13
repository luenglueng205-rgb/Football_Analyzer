#!/usr/bin/env python3
"""
调度Agent (Orchestrator)
功能：
1. 负责任务分发、结果汇总、流程控制
2. 支持并行调用多个专业Agent
3. 具备任务队列和优先级机制
"""

import os
import sys
import json
import uuid
import threading
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
import queue

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from core.base_agent import (
    BaseAgent, AgentStatus, Task, TaskPriority, 
    MessageBus, AgentRegistry, get_registry
)
from core.scout_agent import ScoutAgent, create_scout_agent
from core.analyst_agent import AnalystAgent, create_analyst_agent
from core.strategist_agent import StrategistAgent, create_strategist_agent
from core.risk_manager import RiskManagerAgent, create_risk_manager_agent


class WorkflowStep(Enum):
    """工作流步骤"""
    SCOUT = "scout"          # 情报搜集
    ANALYZE = "analyze"       # 赔率分析
    STRATEGIZE = "strategize" # 策略制定
    RISK_CHECK = "risk_check" # 风控检查
    EXECUTE = "execute"       # 执行


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowTask:
    """工作流任务"""
    task_id: str
    workflow_type: str
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    steps_completed: List[str] = field(default_factory=list)


class OrchestratorAgent(BaseAgent):
    """调度Agent - 负责协调和管理所有专业Agent"""
    
    def __init__(self, message_bus: Optional[MessageBus] = None):
        super().__init__("OrchestratorAgent", message_bus)
        
        # Agent实例
        self.scout: Optional[ScoutAgent] = None
        self.analyst: Optional[AnalystAgent] = None
        self.strategist: Optional[StrategistAgent] = None
        self.risk_manager: Optional[RiskManagerAgent] = None
        
        # 任务队列
        self._task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self._active_tasks: Dict[str, WorkflowTask] = {}
        self._completed_tasks: Dict[str, WorkflowTask] = {}
        
        # 线程池
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._lock = threading.RLock()
        
        # 工作流模板
        self._workflow_templates: Dict[str, List[WorkflowStep]] = {
            "full_analysis": [
                WorkflowStep.SCOUT,
                WorkflowStep.ANALYZE,
                WorkflowStep.STRATEGIZE,
                WorkflowStep.RISK_CHECK
            ],
            "quick_analysis": [
                WorkflowStep.ANALYZE,
                WorkflowStep.STRATEGIZE
            ],
            "value_hunt": [
                WorkflowStep.SCOUT,
                WorkflowStep.ANALYZE
            ],
            "strategy_generate": [
                WorkflowStep.STRATEGIZE,
                WorkflowStep.RISK_CHECK
            ]
        }
        
        # 回调函数
        self._callbacks: Dict[str, List[Callable]] = {}
    
    def initialize(self) -> bool:
        """初始化Orchestrator和所有子Agent"""
        self.set_status(AgentStatus.IDLE)
        
        # 创建消息总线
        message_bus = self.message_bus
        
        # 初始化所有专业Agent
        try:
            self.scout = create_scout_agent(message_bus)
            self.analyst = create_analyst_agent(message_bus)
            self.strategist = create_strategist_agent(message_bus)
            self.risk_manager = create_risk_manager_agent(message_bus)
            
            print(f"✓ Orchestrator initialized with agents:")
            print(f"  - ScoutAgent: {self.scout.name}")
            print(f"  - AnalystAgent: {self.analyst.name}")
            print(f"  - StrategistAgent: {self.strategist.name}")
            print(f"  - RiskManagerAgent: {self.risk_manager.name}")
            
        except Exception as e:
            print(f"Error initializing agents: {e}")
            return False
        
        # 注册到全局注册表
        get_registry().register(self)
        
        return True
    
    def process(self, task: Task) -> Dict[str, Any]:
        """处理任务（兼容BaseAgent接口）"""
        return self.execute_workflow(
            task.task_type,
            task.payload,
            task.priority
        )
    
    def execute_workflow(self, workflow_type: str, payload: Dict, 
                         priority: TaskPriority = TaskPriority.NORMAL) -> Dict:
        """执行完整工作流"""
        task_id = str(uuid.uuid4())[:8]
        
        # 创建工作流任务
        workflow_task = WorkflowTask(
            task_id=task_id,
            workflow_type=workflow_type,
            payload=payload,
            priority=priority
        )
        
        with self._lock:
            self._active_tasks[task_id] = workflow_task
        
        self.set_status(AgentStatus.RUNNING)
        workflow_task.status = TaskStatus.RUNNING
        workflow_task.started_at = datetime.now()
        
        try:
            # 获取工作流步骤
            steps = self._workflow_templates.get(workflow_type, self._workflow_templates["full_analysis"])
            
            results = {}
            
            for step in steps:
                step_result = self._execute_step(step, payload, results)
                workflow_task.steps_completed.append(step.value)
                
                if step_result.get("status") == "error":
                    raise Exception(f"Step {step.value} failed: {step_result.get('error')}")
                
                results[step.value] = step_result.get("result", {})
            
            workflow_task.results = results
            workflow_task.status = TaskStatus.COMPLETED
            workflow_task.completed_at = datetime.now()
            
            # 触发回调
            self._trigger_callbacks(workflow_type, results)
            
            return {
                "status": "success",
                "task_id": task_id,
                "workflow_type": workflow_type,
                "results": results,
                "duration": (workflow_task.completed_at - workflow_task.started_at).total_seconds()
            }
            
        except Exception as e:
            workflow_task.status = TaskStatus.FAILED
            workflow_task.error = str(e)
            workflow_task.completed_at = datetime.now()
            
            return {
                "status": "error",
                "task_id": task_id,
                "error": str(e),
                "completed_steps": workflow_task.steps_completed
            }
        finally:
            with self._lock:
                self._completed_tasks[task_id] = workflow_task
                if task_id in self._active_tasks:
                    del self._active_tasks[task_id]
            
            self.set_status(AgentStatus.COMPLETED)
    
    def _execute_step(self, step: WorkflowStep, payload: Dict, 
                       previous_results: Dict) -> Dict:
        """执行单个工作流步骤"""
        
        if step == WorkflowStep.SCOUT:
            # 情报搜集
            return self.scout.process(Task(
                task_id="scout_task",
                agent_name=self.scout.name,
                task_type="scout_report",
                payload=payload
            ))
            
        elif step == WorkflowStep.ANALYZE:
            # 赔率分析
            matches = previous_results.get("scout", {}).get("matches", [])
            if not matches:
                matches = payload.get("matches", [])
            
            return self.analyst.process(Task(
                task_id="analyze_task",
                agent_name=self.analyst.name,
                task_type="value_bets",
                payload={"matches": matches}
            ))
            
        elif step == WorkflowStep.STRATEGIZE:
            # 策略制定
            value_bets = previous_results.get("analyze", {}).get("value_bets", [])
            if not value_bets:
                value_bets = payload.get("bets", [])
            
            return self.strategist.process(Task(
                task_id="strategy_task",
                agent_name=self.strategist.name,
                task_type="risk_assessment",
                payload={
                    "bets": value_bets,
                    "budget": payload.get("budget", 100)
                }
            ))
            
        elif step == WorkflowStep.RISK_CHECK:
            # 风控检查
            risk_assessment = previous_results.get("strategize", {})
            bets = risk_assessment.get("bets", [])
            
            return self.risk_manager.process(Task(
                task_id="risk_task",
                agent_name=self.risk_manager.name,
                task_type="risk_report",
                payload={}
            ))
        
        return {"status": "error", "error": f"Unknown step: {step}"}
    
    def execute_parallel(self, tasks: List[Dict]) -> Dict:
        """并行执行多个任务"""
        futures = []
        
        for task in tasks:
            agent_name = task.get("agent")
            task_type = task.get("task_type")
            payload = task.get("payload", {})
            
            agent = self._get_agent_by_name(agent_name)
            if agent:
                future = self._executor.submit(
                    agent.process,
                    Task(task_id=str(uuid.uuid4()), agent_name=agent_name, 
                         task_type=task_type, payload=payload)
                )
                futures.append((agent_name, task_type, future))
        
        results = {}
        for agent_name, task_type, future in futures:
            try:
                result = future.result(timeout=30)
                results[f"{agent_name}_{task_type}"] = result
            except Exception as e:
                results[f"{agent_name}_{task_type}"] = {"status": "error", "error": str(e)}
        
        return results
    
    def _get_agent_by_name(self, name: str) -> Optional[BaseAgent]:
        """根据名称获取Agent"""
        agents = {
            "ScoutAgent": self.scout,
            "AnalystAgent": self.analyst,
            "StrategistAgent": self.strategist,
            "RiskManagerAgent": self.risk_manager
        }
        return agents.get(name)
    
    def add_task(self, workflow_type: str, payload: Dict, 
                 priority: TaskPriority = TaskPriority.NORMAL) -> str:
        """添加任务到队列"""
        task_id = str(uuid.uuid4())[:8]
        
        task = WorkflowTask(
            task_id=task_id,
            workflow_type=workflow_type,
            payload=payload,
            priority=priority
        )
        
        # 优先级队列：数值越小优先级越高
        self._task_queue.put((priority.value, task))
        
        return task_id
    
    def process_queue(self) -> Dict:
        """处理队列中的所有任务"""
        results = []
        
        while not self._task_queue.empty():
            try:
                priority, task = self._task_queue.get_nowait()
                result = self.execute_workflow(task.workflow_type, task.payload, task.priority)
                results.append(result)
            except queue.Empty:
                break
        
        return {
            "tasks_processed": len(results),
            "results": results
        }
    
    def register_callback(self, workflow_type: str, callback: Callable) -> None:
        """注册回调函数"""
        if workflow_type not in self._callbacks:
            self._callbacks[workflow_type] = []
        self._callbacks[workflow_type].append(callback)
    
    def _trigger_callbacks(self, workflow_type: str, results: Dict) -> None:
        """触发回调"""
        callbacks = self._callbacks.get(workflow_type, [])
        for callback in callbacks:
            try:
                callback(results)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        if task_id in self._active_tasks:
            task = self._active_tasks[task_id]
            return task.to_dict()
        elif task_id in self._completed_tasks:
            task = self._completed_tasks[task_id]
            return task.to_dict()
        return None
    
    def get_all_tasks(self) -> Dict:
        """获取所有任务"""
        return {
            "active": [t.to_dict() for t in self._active_tasks.values()],
            "completed": [t.to_dict() for t in list(self._completed_tasks.values())[-10:]]
        }
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        return {
            "orchestrator": {
                "name": self.name,
                "status": self.status.value,
                "active_tasks": len(self._active_tasks),
                "completed_tasks": len(self._completed_tasks),
                "queue_size": self._task_queue.qsize()
            },
            "agents": {
                "scout": self.scout.get_info() if self.scout else None,
                "analyst": self.analyst.get_info() if self.analyst else None,
                "strategist": self.strategist.get_info() if self.strategist else None,
                "risk_manager": self.risk_manager.get_info() if self.risk_manager else None
            },
            "workflows": list(self._workflow_templates.keys())
        }
    
    def shutdown(self) -> None:
        """关闭Orchestrator"""
        self._executor.shutdown(wait=True)
        self.set_status(AgentStatus.IDLE)
        print("Orchestrator shutdown complete")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取Agent能力"""
        return {
            "name": self.name,
            "type": "orchestrator",
            "functions": [
                "execute_workflow - 执行工作流",
                "execute_parallel - 并行执行任务",
                "add_task - 添加任务到队列",
                "process_queue - 处理队列",
                "get_task_status - 获取任务状态",
                "get_system_status - 获取系统状态"
            ],
            "workflows": list(self._workflow_templates.keys()),
            "agents": ["ScoutAgent", "AnalystAgent", "StrategistAgent", "RiskManagerAgent"],
            "status": self.status.value
        }


def create_orchestrator(message_bus: Optional[MessageBus] = None) -> OrchestratorAgent:
    """创建Orchestrator实例"""
    orchestrator = OrchestratorAgent(message_bus)
    orchestrator.initialize()
    return orchestrator


# 便捷函数
def quick_analysis(matches: List[Dict], budget: float = 100) -> Dict:
    """快速分析接口"""
    orchestrator = create_orchestrator()
    return orchestrator.execute_workflow(
        "quick_analysis",
        {"matches": matches, "budget": budget}
    )


def full_analysis(match_ids: List[str], budget: float = 100) -> Dict:
    """完整分析接口"""
    orchestrator = create_orchestrator()
    return orchestrator.execute_workflow(
        "full_analysis",
        {"match_ids": match_ids, "budget": budget}
    )


__all__ = [
    'OrchestratorAgent', 
    'create_orchestrator',
    'WorkflowStep',
    'WorkflowTask',
    'TaskStatus',
    'quick_analysis',
    'full_analysis'
]