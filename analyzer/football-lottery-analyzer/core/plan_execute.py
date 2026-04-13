# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - Plan-and-Execute 模式
先规划后执行的Agent架构

Plan-and-Execute vs ReAct:
- ReAct: 边想边做，动态调整
- Plan-and-Execute: 先制定完整计划，再按计划执行

适用场景:
- 复杂的多步骤任务
- 需要全局规划的分析流程
- 明确的任务目标和步骤
"""

import json
import uuid
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class PlanStatus(Enum):
    """计划状态"""
    DRAFT = "draft"           # 草稿
    APPROVED = "approved"     # 已批准
    EXECUTING = "executing"   # 执行中
    COMPLETED = "completed"   # 完成
    FAILED = "failed"         # 失败
    ABORTED = "aborted"       # 中止


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"       # 待执行
    READY = "ready"           # 就绪
    RUNNING = "running"       # 执行中
    COMPLETED = "completed"   # 完成
    SKIPPED = "skipped"       # 跳过
    FAILED = "failed"         # 失败


@dataclass
class ExecutionStep:
    """执行步骤"""
    step_id: str
    name: str
    description: str
    agent: str                    # 执行此步骤的Agent
    tool: str                     # 使用的工具
    parameters: Dict[str, Any]    # 工具参数
    dependencies: List[str] = field(default_factory=list)  # 依赖的前置步骤ID
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def can_execute(self, completed_steps: List[str]) -> bool:
        """检查是否可以执行"""
        if self.status != StepStatus.PENDING:
            return False
        # 检查依赖是否都已完成
        for dep_id in self.dependencies:
            if dep_id not in completed_steps:
                return False
        return True
    
    def to_dict(self) -> Dict:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "description": self.description,
            "agent": self.agent,
            "tool": self.tool,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count
        }


@dataclass
class Plan:
    """执行计划"""
    plan_id: str
    query: str
    context: Dict[str, Any]
    steps: List[ExecutionStep]
    status: PlanStatus = PlanStatus.DRAFT
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    estimated_duration: float = 0.0  # 预估执行时间(秒)
    actual_duration: float = 0.0
    total_cost: float = 0.0
    
    def get_step(self, step_id: str) -> Optional[ExecutionStep]:
        """获取步骤"""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def get_ready_steps(self, completed_steps: List[str]) -> List[ExecutionStep]:
        """获取就绪的步骤"""
        return [s for s in self.steps if s.can_execute(completed_steps)]
    
    def get_progress(self) -> Dict[str, Any]:
        """获取执行进度"""
        total = len(self.steps)
        completed = len([s for s in self.steps if s.status == StepStatus.COMPLETED])
        failed = len([s for s in self.steps if s.status == StepStatus.FAILED])
        pending = len([s for s in self.steps if s.status == StepStatus.PENDING])
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "progress_percent": (completed / total * 100) if total > 0 else 0
        }
    
    def to_dict(self) -> Dict:
        return {
            "plan_id": self.plan_id,
            "query": self.query,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": self.get_progress(),
            "steps": [s.to_dict() for s in self.steps]
        }


class PlanGenerator:
    """
    计划生成器
    基于用户查询和上下文，自动生成执行计划
    """
    
    # 预定义的任务模板
    TASK_TEMPLATES = {
        "full_analysis": [
            {"name": "情报搜集", "agent": "ScoutAgent", "tool": "fetch_intelligence",
             "deps": [], "description": "搜集比赛双方情报"},
            {"name": "赔率分析", "agent": "AnalystAgent", "tool": "analyze_odds",
             "deps": ["情报搜集"], "description": "分析赔率和价值"},
            {"name": "策略生成", "agent": "StrategistAgent", "tool": "generate_strategy",
             "deps": ["赔率分析"], "description": "生成投注策略"},
            {"name": "风控审核", "agent": "RiskManager", "tool": "risk_check",
             "deps": ["策略生成"], "description": "风控审核"}
        ],
        "quick_analysis": [
            {"name": "快速赔率分析", "agent": "AnalystAgent", "tool": "quick_analyze",
             "deps": [], "description": "快速分析赔率"},
            {"name": "策略建议", "agent": "StrategistAgent", "tool": "quick_strategy",
             "deps": ["快速赔率分析"], "description": "给出策略建议"}
        ],
        "value_hunt": [
            {"name": "市场扫描", "agent": "ScoutAgent", "tool": "scan_markets",
             "deps": [], "description": "扫描市场机会"},
            {"name": "价值识别", "agent": "AnalystAgent", "tool": "identify_value",
             "deps": ["市场扫描"], "description": "识别价值投注"}
        ],
        "strategy_optimize": [
            {"name": "历史分析", "agent": "ScoutAgent", "tool": "analyze_history",
             "deps": [], "description": "分析历史表现"},
            {"name": "策略优化", "agent": "StrategistAgent", "tool": "optimize_strategy",
             "deps": ["历史分析"], "description": "优化投注策略"},
            {"name": "风险评估", "agent": "RiskManager", "tool": "assess_risk",
             "deps": ["策略优化"], "description": "评估策略风险"}
        ]
    }
    
    def generate(self, query: str, context: Dict[str, Any]) -> Plan:
        """生成执行计划"""
        plan_id = str(uuid.uuid4())[:8]
        
        # 确定任务类型
        task_type = context.get("task_type", "full_analysis")
        
        # 获取模板
        template = self.TASK_TEMPLATES.get(task_type, self.TASK_TEMPLATES["full_analysis"])
        
        # 生成步骤
        steps = []
        completed_ids = []
        
        for i, step_template in enumerate(template):
            step_id = f"step_{i+1}"
            
            # 解析依赖
            deps = []
            for dep_name in step_template.get("deps", []):
                for s in steps:
                    if s.name == dep_name:
                        deps.append(s.step_id)
                        break
            
            step = ExecutionStep(
                step_id=step_id,
                name=step_template["name"],
                description=step_template["description"],
                agent=step_template["agent"],
                tool=step_template["tool"],
                parameters=context,
                dependencies=deps
            )
            steps.append(step)
        
        return Plan(
            plan_id=plan_id,
            query=query,
            context=context,
            steps=steps,
            status=PlanStatus.DRAFT
        )
    
    def refine_plan(self, plan: Plan, additional_context: Dict[str, Any]) -> Plan:
        """根据额外上下文优化计划"""
        # 可以添加条件步骤、调整参数等
        return plan


class PlanExecutor:
    """
    计划执行器
    按计划顺序执行步骤，支持并行和依赖管理
    """
    
    def __init__(self):
        self._step_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认处理器"""
        # ScoutAgent 处理器
        self._step_handlers["fetch_intelligence"] = self._handle_scout
        self._step_handlers["scan_markets"] = self._handle_scout
        self._step_handlers["analyze_history"] = self._handle_scout
        
        # AnalystAgent 处理器
        self._step_handlers["analyze_odds"] = self._handle_analyst
        self._step_handlers["quick_analyze"] = self._handle_analyst
        self._step_handlers["identify_value"] = self._handle_analyst
        
        # StrategistAgent 处理器
        self._step_handlers["generate_strategy"] = self._handle_strategist
        self._step_handlers["quick_strategy"] = self._handle_strategist
        self._step_handlers["optimize_strategy"] = self._handle_strategist
        
        # RiskManager 处理器
        self._step_handlers["risk_check"] = self._handle_risk
        self._step_handlers["assess_risk"] = self._handle_risk
    
    def register_handler(self, tool_name: str, handler: Callable):
        """注册工具处理器"""
        self._step_handlers[tool_name] = handler
    
    def execute_plan(self, plan: Plan, 
                     max_parallel: int = 2) -> Plan:
        """执行计划"""
        plan.status = PlanStatus.EXECUTING
        plan.started_at = datetime.now().isoformat()
        
        completed_steps = []
        failed_steps = []
        
        while True:
            # 获取就绪步骤
            ready_steps = plan.get_ready_steps(completed_steps)
            
            if not ready_steps:
                # 检查是否全部完成或有失败
                if len(completed_steps) + len(failed_steps) == len(plan.steps):
                    break
                continue
            
            # 执行就绪步骤（可以并行）
            for step in ready_steps[:max_parallel]:
                result = self._execute_step(step)
                
                if result:
                    step.status = StepStatus.COMPLETED
                    step.completed_at = datetime.now().isoformat()
                    step.result = result
                    completed_steps.append(step.step_id)
                else:
                    step.status = StepStatus.FAILED
                    failed_steps.append(step.step_id)
        
        # 更新计划状态
        if failed_steps:
            plan.status = PlanStatus.FAILED
        else:
            plan.status = PlanStatus.COMPLETED
        
        plan.completed_at = datetime.now().isoformat()
        
        # 计算实际执行时间
        if plan.started_at:
            start = datetime.fromisoformat(plan.started_at)
            end = datetime.fromisoformat(plan.completed_at)
            plan.actual_duration = (end - start).total_seconds()
        
        return plan
    
    def _execute_step(self, step: ExecutionStep) -> Optional[Dict]:
        """执行单个步骤"""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now().isoformat()
        
        handler = self._step_handlers.get(step.tool)
        
        try:
            if handler:
                result = handler(step.parameters)
                return result
            else:
                return {"status": "skipped", "message": f"No handler for tool {step.tool}"}
        except Exception as e:
            step.error = str(e)
            return None
    
    def _handle_scout(self, params: Dict) -> Dict:
        """ScoutAgent 处理器"""
        return {
            "status": "success",
            "agent": "ScoutAgent",
            "data": {
                "team_news": [],
                "formations": [],
                "head_to_head": []
            }
        }
    
    def _handle_analyst(self, params: Dict) -> Dict:
        """AnalystAgent 处理器"""
        return {
            "status": "success",
            "agent": "AnalystAgent",
            "data": {
                "odds_analysis": {},
                "value_bets": []
            }
        }
    
    def _handle_strategist(self, params: Dict) -> Dict:
        """StrategistAgent 处理器"""
        return {
            "status": "success",
            "agent": "StrategistAgent",
            "data": {
                "strategy": {},
                "bets": []
            }
        }
    
    def _handle_risk(self, params: Dict) -> Dict:
        """RiskManager 处理器"""
        return {
            "status": "success",
            "agent": "RiskManager",
            "data": {
                "approved": True,
                "risk_score": 0.3
            }
        }


class PlanAndExecuteAgent:
    """
    Plan-and-Execute Agent
    
    核心流程:
    1. 分析查询 → 生成计划 (PlanGenerator)
    2. 验证计划 → 执行计划 (PlanExecutor)
    3. 收集结果 → 返回最终答案
    """
    
    def __init__(self, name: str = "PlanExecuteAgent"):
        self.name = name
        self.plan_generator = PlanGenerator()
        self.plan_executor = PlanExecutor()
    
    def run(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """运行完整流程"""
        context = context or {}
        
        # 1. 生成计划
        plan = self.plan_generator.generate(query, context)
        
        # 2. 执行计划
        plan = self.plan_executor.execute_plan(plan)
        
        # 3. 收集结果
        return {
            "query": query,
            "plan": plan.to_dict(),
            "results": [step.result for step in plan.steps if step.result],
            "success": plan.status == PlanStatus.COMPLETED,
            "duration": plan.actual_duration,
            "progress": plan.get_progress()
        }
    
    def run_with_replan(self, query: str, 
                        context: Dict[str, Any] = None,
                        max_replans: int = 2) -> Dict[str, Any]:
        """带重规划的执行"""
        context = context or {}
        
        replan_count = 0
        
        while replan_count <= max_replans:
            # 生成计划
            plan = self.plan_generator.generate(query, context)
            
            # 执行计划
            plan = self.plan_executor.execute_plan(plan)
            
            # 检查是否成功
            if plan.status == PlanStatus.COMPLETED:
                return {
                    "query": query,
                    "plan": plan.to_dict(),
                    "results": [step.result for step in plan.steps if step.result],
                    "success": True,
                    "replans": replan_count
                }
            
            # 分析失败原因，重规划
            failed_steps = [s for s in plan.steps if s.status == StepStatus.FAILED]
            context["failed_steps"] = [s.to_dict() for s in failed_steps]
            replan_count += 1
        
        return {
            "query": query,
            "success": False,
            "error": "Max replans exceeded",
            "last_plan": plan.to_dict()
        }


# 便捷函数
def create_plan(query: str, task_type: str = "full_analysis") -> Plan:
    """创建计划"""
    generator = PlanGenerator()
    return generator.generate(query, {"task_type": task_type})


def execute_plan(plan: Plan) -> Plan:
    """执行计划"""
    executor = PlanExecutor()
    return executor.execute_plan(plan)


if __name__ == "__main__":
    # 测试 Plan-and-Execute
    agent = PlanAndExecuteAgent()
    
    result = agent.run(
        query="分析今晚的英超比赛",
        context={"task_type": "full_analysis", "league": "英超"}
    )
    
    print(f"执行结果:")
    print(f"  查询: {result['query']}")
    print(f"  成功: {result['success']}")
    print(f"  耗时: {result['duration']:.2f}s")
    print(f"  进度: {result['progress']}")
    print(f"\n计划详情:")
    print(json.dumps(result["plan"], indent=2, ensure_ascii=False))
