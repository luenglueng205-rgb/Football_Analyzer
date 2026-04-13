# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - Modern Agent Core
现代化Agent核心模块

整合:
- ReAct Pattern
- Plan-and-Execute
- RAG Knowledge Base
- Structured Logging & Tracing
- Dynamic Tool Selection
- CrewAI Integration
"""

import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# 导入各模块
from core.react_pattern import ReActAgent, get_tool_registry as get_react_tools
from core.plan_execute import PlanAndExecuteAgent, PlanStatus
from core.rag_knowledge import RagKnowledgeBase, get_rag_knowledge_base
from core.logging_tracing import (
    StructuredLogger, TracingManager, traced,
    structured_logger, tracing_manager, configure_logging
)
from core.dynamic_tool_selection import (
    DynamicToolRegistry, ToolExecutor,
    tool_registry, tool_executor
)
from core.crewai_integration import FootballCrewFactory, CREWAI_AVAILABLE


@dataclass
class AgentMode(Enum):
    """Agent运行模式"""
    REACT = "react"              # 推理-行动模式
    PLAN_EXECUTE = "plan_execute"  # 规划-执行模式
    CREWAI = "crewai"           # CrewAI模式
    AUTO = "auto"               # 自动选择最佳模式


class ModernAgentCore:
    """
    现代化Agent核心
    
    提供统一的接口，支持多种Agent模式
    """
    
    def __init__(self, name: str = "ModernFootballAgent"):
        self.name = name
        
        # 初始化各组件
        self.react_agent = ReActAgent(name)
        self.plan_execute_agent = PlanAndExecuteAgent(name)
        self.crewai_factory = FootballCrewFactory()
        
        # RAG 知识库
        self.rag = get_rag_knowledge_base()
        
        # 日志和追踪
        self.logger = structured_logger
        self.tracing = tracing_manager
        
        # 工具注册表
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        
        # 配置
        self._mode = AgentMode.AUTO
        self._initialized = False
    
    def initialize(self, log_dir: str = "logs", 
                    storage_dir: str = "data/memory"):
        """初始化Agent"""
        # 配置日志
        configure_logging(log_dir)
        
        # 初始化RAG知识库
        self.rag.configure_storage(storage_dir)
        
        # 预填充知识
        self._seed_knowledge()
        
        self._initialized = True
        self.logger.info("agent.start", f"{self.name} initialized")
    
    def _seed_knowledge(self):
        """填充初始知识"""
        # 检查是否已有数据
        if self.rag.get_stats()["total_chunks"] > 0:
            return
        
        # 添加联赛知识
        leagues = [
            ("epl", "英超", {"avg_goals": 2.8, "home_win_rate": 0.45, 
                           "suitable_bet_types": ["胜平负", "大小球", "角球"]}),
            ("laliga", "西甲", {"avg_goals": 2.6, "home_win_rate": 0.48,
                              "suitable_bet_types": ["胜平负", "大小球"]}),
            ("bundesliga", "德甲", {"avg_goals": 3.1, "home_win_rate": 0.44,
                                   "suitable_bet_types": ["大小球", "胜平负"]}),
            ("seriea", "意甲", {"avg_goals": 2.7, "home_win_rate": 0.47,
                               "suitable_bet_types": ["胜平负", "半全场"]}),
            (" Ligue1", "法甲", {"avg_goals": 2.5, "home_win_rate": 0.46,
                               "suitable_bet_types": ["胜平负"]}),
        ]
        
        for league_id, league_name, chars in leagues:
            self.rag.add_league_knowledge(league_id, league_name, chars)
    
    def set_mode(self, mode: AgentMode):
        """设置运行模式"""
        self._mode = mode
        self.logger.info("agent.config", f"Mode set to {mode.value}")
    
    def analyze(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        统一分析入口
        
        Args:
            query: 用户查询
            context: 上下文信息
            
        Returns:
            分析结果
        """
        context = context or {}
        context["query"] = query
        
        # 自动模式选择
        mode = self._select_mode(context)
        
        # 开始追踪
        trace = self.tracing.start_trace(f"analyze_{mode.value}")
        
        try:
            if mode == AgentMode.REACT:
                result = self._run_react(query, context)
            elif mode == AgentMode.PLAN_EXECUTE:
                result = self._run_plan_execute(query, context)
            elif mode == AgentMode.CREWAI:
                result = self._run_crewai(query, context)
            else:
                result = self._run_react(query, context)
            
            self.tracing.end_trace(trace, "ok")
            return result
            
        except Exception as e:
            self.tracing.end_trace(trace, "error")
            self.logger.error("agent.error", str(e))
            return {
                "success": False,
                "error": str(e),
                "mode": mode.value
            }
    
    def _select_mode(self, context: Dict[str, Any]) -> AgentMode:
        """自动选择最佳模式"""
        if self._mode != AgentMode.AUTO:
            return self._mode
        
        query = context.get("query", "").lower()
        task_type = context.get("task_type", "")
        
        # 根据查询类型选择模式
        if "完整分析" in query or "full" in task_type:
            return AgentMode.PLAN_EXECUTE  # 复杂任务用规划模式
        elif "快速" in query or "quick" in task_type:
            return AgentMode.REACT  # 快速任务用ReAct
        elif "团队" in query or "crew" in task_type:
            return AgentMode.CREWAI  # 团队协作用CrewAI
        else:
            return AgentMode.REACT  # 默认ReAct
    
    @traced(span_name="react_execution", agent="ReActAgent")
    def _run_react(self, query: str, context: Dict) -> Dict[str, Any]:
        """运行ReAct模式"""
        result = self.react_agent.execute(query, context)
        return {
            "mode": "react",
            "success": result.success,
            "iterations": result.total_iterations,
            "reasoning_chain": result.get_reasoning_chain(),
            "final_answer": result.final_answer,
            "duration_ms": result.execution_time * 1000
        }
    
    @traced(span_name="plan_execute", agent="PlanExecuteAgent")
    def _run_plan_execute(self, query: str, context: Dict) -> Dict[str, Any]:
        """运行Plan-and-Execute模式"""
        result = self.plan_execute_agent.run(query, context)
        return {
            "mode": "plan_execute",
            "success": result["success"],
            "plan": result["plan"],
            "progress": result["progress"],
            "duration": result["duration"]
        }
    
    @traced(span_name="crewai_execution", agent="CrewAI")
    def _run_crewai(self, query: str, context: Dict) -> Dict[str, Any]:
        """运行CrewAI模式"""
        if not CREWAI_AVAILABLE:
            return {
                "mode": "crewai",
                "success": False,
                "error": "CrewAI not installed"
            }
        
        result = self.crewai_factory.run_full_analysis(context)
        return {
            "mode": "crewai",
            **result
        }
    
    def search_knowledge(self, query: str, top_k: int = 5) -> List[Dict]:
        """搜索知识库"""
        return self.rag.search(query, top_k)
    
    def add_knowledge(self, content: str, metadata: Dict[str, Any]) -> str:
        """添加知识"""
        return self.rag.add_knowledge(content, metadata)
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "agent": {
                "name": self.name,
                "mode": self._mode.value,
                "initialized": self._initialized
            },
            "rag": self.rag.get_stats(),
            "tools": {
                "total": len(self.tool_registry._tools),
                "by_category": {
                    cat.value: len(names) 
                    for cat, names in self.tool_registry._categories.items()
                }
            },
            "crewai": {
                "available": CREWAI_AVAILABLE
            }
        }


# 全局实例
modern_agent: Optional[ModernAgentCore] = None

def get_modern_agent() -> ModernAgentCore:
    """获取全局ModernAgent"""
    global modern_agent
    if modern_agent is None:
        modern_agent = ModernAgentCore()
        modern_agent.initialize()
    return modern_agent


# 便捷函数
def analyze(query: str, context: Dict = None) -> Dict[str, Any]:
    """快速分析"""
    agent = get_modern_agent()
    return agent.analyze(query, context)


if __name__ == "__main__":
    # 测试Modern Agent
    agent = ModernAgentCore()
    agent.initialize()
    
    print("=" * 60)
    print("足球彩票分析系统 - Modern Agent")
    print("=" * 60)
    
    # 获取系统状态
    status = agent.get_system_status()
    print(f"\n系统状态:")
    print(f"  Agent: {status['agent']['name']}")
    print(f"  工具数: {status['tools']['total']}")
    print(f"  知识库: {status['rag']['total_chunks']} 条")
    print(f"  CrewAI: {'可用' if status['crewai']['available'] else '不可用'}")
    
    # 测试分析
    print("\n" + "-" * 60)
    print("测试分析: 今晚曼城vs阿森纳的比赛")
    
    result = agent.analyze(
        query="分析今晚曼城vs阿森纳的比赛",
        context={
            "home_team": "曼城",
            "away_team": "阿森纳",
            "league": "英超",
            "odds": {"home": 2.1, "draw": 3.4, "away": 3.5},
            "budget": 100
        }
    )
    
    print(f"\n分析结果:")
    print(f"  模式: {result.get('mode')}")
    print(f"  成功: {result.get('success')}")
    print(f"  耗时: {result.get('duration_ms', result.get('duration', 0)):.2f}ms")
    
    if "reasoning_chain" in result:
        print(f"\n推理链:")
        for item in result["reasoning_chain"]:
            print(f"  - {item}")
    
    if "plan" in result:
        print(f"\n执行计划:")
        print(f"  状态: {result['plan']['status']}")
        print(f"  进度: {result['progress']}")
    
    print("\n" + "=" * 60)
