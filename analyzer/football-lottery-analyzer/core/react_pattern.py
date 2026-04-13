# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - ReAct Pattern 实现
增强Agent推理能力：Thought → Action → Observation循环

ReAct (Reasoning + Acting) 模式:
1. Thought: 思考当前状态和目标
2. Action: 选择并执行工具/技能
3. Observation: 观察执行结果
4. 循环直到得到最终答案
"""

import json
import uuid
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class ThoughtType(Enum):
    """思考类型"""
    OBSERVATION = "observation"      # 观察分析
    REASONING = "reasoning"          # 推理分析
    PLANNING = "planning"            # 规划下一步
    REFLECTION = "reflection"        # 反思总结
    DECISION = "decision"            # 决策判断
    HYPOTHESIS = "hypothesis"        # 假设验证


class ActionType(Enum):
    """行动类型"""
    # 情报类
    FETCH_NEWS = "fetch_news"           # 获取新闻
    FETCH_FORMATIONS = "fetch_formations"  # 获取阵容
    FETCH_HISTORY = "fetch_history"     # 历史对战
    
    # 分析类
    ANALYZE_ODDS = "analyze_odds"       # 赔率分析
    DETECT_ANOMALY = "detect_anomaly"   # 异常检测
    CALCULATE_EV = "calculate_expected_value"  # 期望值计算
    
    # 策略类
    GENERATE_STRATEGY = "generate_strategy"  # 生成策略
    ALLOCATE_BUDGET = "allocate_budget"   # 分配资金
    CALCULATE_KELLY = "calculate_kelly"  # Kelly计算
    
    # 风控类
    CHECK_RISK = "check_risk"           # 风控检查
    VALIDATE_BETS = "validate_bets"     # 验证投注
    
    # 记忆类
    RETRIEVE_MEMORY = "retrieve_memory"  # 记忆检索
    STORE_RESULT = "store_result"       # 存储结果
    
    # 搜索类
    SEARCH_KNOWLEDGE = "search_knowledge"  # RAG知识检索
    
    # 特殊
    FINAL_ANSWER = "final_answer"       # 最终答案


@dataclass
class Thought:
    """思考步骤"""
    thought_id: str
    timestamp: str
    thought_type: ThoughtType
    content: str
    confidence: float = 0.5
    related_facts: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "thought_id": self.thought_id,
            "timestamp": self.timestamp,
            "type": self.thought_type.value,
            "content": self.content,
            "confidence": self.confidence,
            "related_facts": self.related_facts
        }


@dataclass
class Action:
    """行动步骤"""
    action_id: str
    timestamp: str
    action_type: ActionType
    tool_name: str
    parameters: Dict[str, Any]
    expected_outcome: str
    
    def to_dict(self) -> Dict:
        return {
            "action_id": self.action_id,
            "timestamp": self.timestamp,
            "type": self.action_type.value,
            "tool": self.tool_name,
            "parameters": self.parameters,
            "expected": self.expected_outcome
        }


@dataclass
class Observation:
    """观察结果"""
    observation_id: str
    timestamp: str
    action_id: str
    result: Any
    success: bool
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "observation_id": self.observation_id,
            "timestamp": self.timestamp,
            "action_id": self.action_id,
            "success": self.success,
            "result": str(self.result)[:200] if self.result else None,
            "error": self.error
        }


@dataclass
class ReActStep:
    """完整的ReAct步骤"""
    step_id: str
    iteration: int
    thought: Thought
    action: Action
    observation: Observation
    next_action: Optional[str] = None  # continue, final_answer, error
    
    def to_dict(self) -> Dict:
        return {
            "step_id": self.step_id,
            "iteration": self.iteration,
            "thought": self.thought.to_dict(),
            "action": self.action.to_dict(),
            "observation": self.observation.to_dict(),
            "next_action": self.next_action
        }


@dataclass
class ReActResult:
    """ReAct执行结果"""
    trace_id: str
    query: str
    steps: List[ReActStep]
    final_answer: Optional[Dict] = None
    success: bool = True
    error: Optional[str] = None
    total_iterations: int = 0
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "query": self.query,
            "steps": [s.to_dict() for s in self.steps],
            "final_answer": self.final_answer,
            "success": self.success,
            "error": self.error,
            "iterations": self.total_iterations,
            "execution_time": self.execution_time
        }
    
    def get_reasoning_chain(self) -> str:
        """获取推理链摘要"""
        chain = []
        for step in self.steps:
            chain.append(f"[{step.iteration}] {step.thought.thought_type.value}: {step.thought.content[:50]}...")
        return "\n".join(chain)


class ToolRegistry:
    """工具注册表 - 支持动态工具发现和选择"""
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._tool_metadata: Dict[str, Dict] = {}
        self._tool_categories: Dict[str, List[str]] = {
            "scout": [],      # 情报搜集
            "analysis": [],   # 分析工具
            "strategy": [],   # 策略工具
            "risk": [],       # 风控工具
            "memory": [],     # 记忆工具
            "rag": []         # RAG工具
        }
    
    def register(self, name: str, func: Callable, 
                 category: str, description: str = "",
                 parameters_schema: Optional[Dict] = None) -> None:
        """注册工具"""
        self._tools[name] = func
        self._tool_metadata[name] = {
            "category": category,
            "description": description,
            "parameters": parameters_schema or {}
        }
        if category in self._tool_categories:
            self._tool_categories[category].append(name)
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """获取工具"""
        return self._tools.get(name)
    
    def get_tools_by_category(self, category: str) -> List[Dict]:
        """按类别获取工具"""
        tools = []
        for name in self._tool_categories.get(category, []):
            tools.append({
                "name": name,
                **self._tool_metadata.get(name, {})
            })
        return tools
    
    def get_all_tools(self) -> List[Dict]:
        """获取所有工具"""
        return [
            {"name": name, **meta}
            for name, meta in self._tool_metadata.items()
        ]
    
    def select_best_tools(self, context: Dict[str, Any], 
                          max_tools: int = 3) -> List[str]:
        """基于上下文动态选择最佳工具"""
        query = context.get("query", "").lower()
        task_type = context.get("task_type", "")
        
        selected = []
        scored = []
        
        for name, meta in self._tool_metadata.items():
            score = 0
            
            # 任务类型匹配
            if task_type == "scout" and meta["category"] == "scout":
                score += 10
            elif task_type == "analysis" and meta["category"] == "analysis":
                score += 10
            elif task_type == "strategy" and meta["category"] == "strategy":
                score += 10
            elif task_type == "risk" and meta["category"] == "risk":
                score += 10
            
            # 关键词匹配
            desc = meta["description"].lower()
            if "odds" in query and "odds" in desc:
                score += 5
            if "history" in query and "history" in desc:
                score += 5
            if "value" in query and "value" in desc:
                score += 5
            if "risk" in query and "risk" in desc:
                score += 5
            
            if score > 0:
                scored.append((name, score))
        
        # 按分数排序，选择top N
        scored.sort(key=lambda x: x[1], reverse=True)
        selected = [name for name, _ in scored[:max_tools]]
        
        # 确保至少有工具被选中
        if not selected and self._tools:
            selected = list(self._tools.keys())[:max_tools]
        
        return selected


class ReActAgent:
    """
    ReAct Pattern Agent
    
    实现完整的推理-行动循环:
    - 维护推理链
    - 动态工具选择
    - 支持多轮反思
    """
    
    def __init__(self, name: str = "ReActAgent"):
        self.name = name
        self.trace_id = str(uuid.uuid4())[:8]
        self.tool_registry = ToolRegistry()
        self.max_iterations = 10
        
        # 初始化工具注册
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册默认工具"""
        # 情报工具
        self.tool_registry.register(
            "fetch_team_news",
            lambda ctx: {"news": []},
            "scout",
            "获取球队最新新闻和动态"
        )
        self.tool_registry.register(
            "fetch_formations",
            lambda ctx: {"formations": []},
            "scout", 
            "获取球队阵容和伤病信息"
        )
        self.tool_registry.register(
            "fetch_head_to_head",
            lambda ctx: {"history": []},
            "scout",
            "获取历史对战数据"
        )
        
        # 分析工具
        self.tool_registry.register(
            "analyze_odds_anomaly",
            lambda ctx: {"anomaly_score": 0.0},
            "analysis",
            "分析赔率异常"
        )
        self.tool_registry.register(
            "calculate_expected_value",
            lambda ctx: {"ev": 0.0},
            "analysis",
            "计算期望值"
        )
        
        # 策略工具
        self.tool_registry.register(
            "generate_mxn_strategy",
            lambda ctx: {"strategy": {}},
            "strategy",
            "生成M串N投注策略"
        )
        
        # 风控工具
        self.tool_registry.register(
            "check_risk_limits",
            lambda ctx: {"passed": True},
            "risk",
            "检查风控限额"
        )
        
        # 记忆工具
        self.tool_registry.register(
            "retrieve_betting_history",
            lambda ctx: {"records": []},
            "memory",
            "检索投注历史"
        )
        
        # RAG工具
        self.tool_registry.register(
            "rag_knowledge_search",
            lambda ctx: {"results": []},
            "rag",
            "向量知识库检索"
        )
    
    def think(self, context: Dict[str, Any], 
              previous_observations: List[Observation]) -> Thought:
        """思考下一步"""
        query = context.get("query", "")
        
        # 基于已有观察进行推理
        relevant_facts = []
        for obs in previous_observations:
            if obs.success and obs.result:
                relevant_facts.append(str(obs.result)[:100])
        
        # 简单的思考逻辑（可扩展为LLM调用）
        if len(previous_observations) == 0:
            thought_type = ThoughtType.PLANNING
            content = f"分析查询'{query}'，需要先获取情报数据"
        elif len(previous_observations) == 1:
            thought_type = ThoughtType.REASONING
            content = f"基于情报分析赔率数据，寻找价值投注"
        elif len(previous_observations) == 2:
            thought_type = ThoughtType.HYPOTHESIS
            content = f"验证假设：存在正期望值投注机会"
        else:
            thought_type = ThoughtType.DECISION
            content = f"综合分析结果，做出最终决策"
        
        return Thought(
            thought_id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            thought_type=thought_type,
            content=content,
            confidence=0.7,
            related_facts=relevant_facts[-3:]
        )
    
    def select_action(self, thought: Thought, 
                      context: Dict[str, Any]) -> Action:
        """选择行动"""
        task_type = context.get("task_type", "analysis")
        
        # 动态选择工具
        best_tools = self.tool_registry.select_best_tools(context, max_tools=1)
        
        if best_tools:
            tool_name = best_tools[0]
        else:
            tool_name = "analyze_odds_anomaly"
        
        # 根据思考类型选择行动
        action_type_map = {
            ThoughtType.PLANNING: ActionType.FETCH_NEWS,
            ThoughtType.REASONING: ActionType.ANALYZE_ODDS,
            ThoughtType.HYPOTHESIS: ActionType.CALCULATE_EV,
            ThoughtType.DECISION: ActionType.FINAL_ANSWER,
            ThoughtType.REFLECTION: ActionType.RETRIEVE_MEMORY,
            ThoughtType.OBSERVATION: ActionType.SEARCH_KNOWLEDGE
        }
        
        return Action(
            action_id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            action_type=action_type_map.get(thought.thought_type, ActionType.ANALYZE_ODDS),
            tool_name=tool_name,
            parameters=context,
            expected_outcome="获取分析结果"
        )
    
    def execute_action(self, action: Action) -> Observation:
        """执行行动"""
        tool = self.tool_registry.get_tool(action.tool_name)
        
        try:
            if tool:
                result = tool(action.parameters)
                return Observation(
                    observation_id=str(uuid.uuid4())[:8],
                    timestamp=datetime.now().isoformat(),
                    action_id=action.action_id,
                    result=result,
                    success=True
                )
            else:
                return Observation(
                    observation_id=str(uuid.uuid4())[:8],
                    timestamp=datetime.now().isoformat(),
                    action_id=action.action_id,
                    result=None,
                    success=False,
                    error=f"Tool {action.tool_name} not found"
                )
        except Exception as e:
            return Observation(
                observation_id=str(uuid.uuid4())[:8],
                timestamp=datetime.now().isoformat(),
                action_id=action.action_id,
                result=None,
                success=False,
                error=str(e)
            )
    
    def should_continue(self, steps: List[ReActStep], 
                        max_iterations: int = None) -> str:
        """判断是否继续循环"""
        if max_iterations is None:
            max_iterations = self.max_iterations
        
        if len(steps) >= max_iterations:
            return "final_answer"
        
        # 检查最后一步是否是最终答案
        if steps and steps[-1].action.action_type == ActionType.FINAL_ANSWER:
            return "final_answer"
        
        # 检查是否有错误
        if steps and not steps[-1].observation.success:
            return "error"
        
        return "continue"
    
    def execute(self, query: str, context: Dict[str, Any] = None) -> ReActResult:
        """执行ReAct循环"""
        start_time = datetime.now()
        context = context or {}
        context["query"] = query
        
        steps = []
        observations = []
        
        iteration = 0
        while True:
            iteration += 1
            
            # 1. Thought
            thought = self.think(context, observations)
            
            # 2. Action
            action = self.select_action(thought, context)
            
            # 3. Observation
            observation = self.execute_action(action)
            observations.append(observation)
            
            # 4. 构建完整步骤
            step = ReActStep(
                step_id=str(uuid.uuid4())[:8],
                iteration=iteration,
                thought=thought,
                action=action,
                observation=observation
            )
            steps.append(step)
            
            # 5. 检查是否继续
            next_action = self.should_continue(steps)
            step.next_action = next_action
            
            if next_action in ["final_answer", "error"]:
                break
        
        # 构建最终结果
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # 如果是最终答案，生成结论
        final_answer = None
        if steps and steps[-1].action.action_type == ActionType.FINAL_ANSWER:
            final_answer = {
                "conclusion": "分析完成",
                "confidence": sum(s.thought.confidence for s in steps) / len(steps),
                "reasoning_chain": self.get_reasoning_chain(steps)
            }
        
        return ReActResult(
            trace_id=self.trace_id,
            query=query,
            steps=steps,
            final_answer=final_answer,
            success=next_action != "error",
            total_iterations=iteration,
            execution_time=execution_time
        )
    
    def get_reasoning_chain(self, steps: List[ReActStep]) -> List[Dict]:
        """获取推理链"""
        return [
            {
                "iteration": s.iteration,
                "thought": s.thought.content,
                "action": s.action.tool_name,
                "result": "成功" if s.observation.success else "失败"
            }
            for s in steps
        ]


# 全局工具注册表
_global_tool_registry = ToolRegistry()

def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册表"""
    return _global_tool_registry


def register_tool(name: str, func: Callable, 
                  category: str, description: str = ""):
    """便捷的全局工具注册"""
    _global_tool_registry.register(name, func, category, description)


if __name__ == "__main__":
    # 测试ReAct Agent
    agent = ReActAgent("足球分析Agent")
    
    result = agent.execute(
        query="分析今晚曼城vs阿森纳的比赛",
        context={"task_type": "analysis", "home_team": "曼城", "away_team": "阿森纳"}
    )
    
    print(f"ReAct执行结果:")
    print(f"  查询: {result.query}")
    print(f"  迭代次数: {result.total_iterations}")
    print(f"  执行时间: {result.execution_time:.2f}s")
    print(f"  成功: {result.success}")
    print(f"\n推理链:")
    for step in result.steps:
        print(f"  [{step.iteration}] {step.thought.thought_type.value}: {step.thought.content}")
