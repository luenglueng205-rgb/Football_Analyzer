# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - Tool 动态选择机制
基于上下文智能选择最优工具组合

功能:
- 动态工具发现
- 上下文感知选择
- 工具链编排
- 工具性能优化
"""

import json
import uuid
from typing import Dict, List, Any, Optional, Callable, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class ToolCategory(Enum):
    """工具类别"""
    SCOUT = "scout"           # 情报搜集
    ANALYSIS = "analysis"     # 数据分析
    STRATEGY = "strategy"     # 策略生成
    RISK = "risk"             # 风险管理
    MEMORY = "memory"         # 记忆存储
    RAG = "rag"               # 知识检索
    NOTIFICATION = "notification"  # 通知推送


@dataclass
class Tool:
    """工具定义"""
    name: str
    category: ToolCategory
    description: str
    keywords: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable] = None
    enabled: bool = True
    priority: int = 0  # 优先级，数值越大优先级越高
    
    def match_score(self, context: Dict[str, Any]) -> float:
        """计算匹配分数"""
        score = 0.0
        
        query = context.get("query", "").lower()
        task_type = context.get("task_type", "")
        
        # 类别匹配
        if task_type == self.category.value:
            score += 10.0
        
        # 关键词匹配
        for keyword in self.keywords:
            if keyword.lower() in query:
                score += 3.0
        
        # 描述匹配
        desc_lower = self.description.lower()
        for keyword in query.split():
            if keyword in desc_lower:
                score += 1.0
        
        # 优先级加成
        score += self.priority * 0.1
        
        return score


@dataclass
class ToolChain:
    """工具链"""
    chain_id: str
    name: str
    description: str
    tools: List[Tool]
    execution_mode: str = "sequential"  # sequential, parallel, conditional
    
    def total_estimated_time(self) -> float:
        """估算总执行时间"""
        # 假设每个工具平均执行时间
        base_time = 0.5
        return len(self.tools) * base_time


class DynamicToolRegistry:
    """
    动态工具注册表
    
    支持:
    - 工具自动发现
    - 上下文匹配
    - 工具链编排
    - 性能监控
    """
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[ToolCategory, List[str]] = {
            cat: [] for cat in ToolCategory
        }
        self._tool_chains: Dict[str, ToolChain] = {}
        
        # 性能追踪
        self._usage_stats: Dict[str, Dict[str, Any]] = {}
        
        # 注册默认工具
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册默认工具"""
        # Scout 工具
        self.register_tool(Tool(
            name="fetch_team_news",
            category=ToolCategory.SCOUT,
            description="获取球队最新新闻和动态",
            keywords=["新闻", "动态", "消息", "news"],
            priority=5
        ))
        
        self.register_tool(Tool(
            name="fetch_formations",
            category=ToolCategory.SCOUT,
            description="获取球队阵容和伤病信息",
            keywords=["阵容", "伤病", "首发", "formation"],
            priority=5
        ))
        
        self.register_tool(Tool(
            name="fetch_head_to_head",
            category=ToolCategory.SCOUT,
            description="获取两队历史对战数据",
            keywords=["历史", "对战", "交锋", "h2h"],
            priority=4
        ))
        
        self.register_tool(Tool(
            name="fetch_team_form",
            category=ToolCategory.SCOUT,
            description="获取球队近期表现",
            keywords=["近期", "状态", "战绩", "form"],
            priority=4
        ))
        
        # Analysis 工具
        self.register_tool(Tool(
            name="analyze_odds",
            category=ToolCategory.ANALYSIS,
            description="分析赔率异常和价值",
            keywords=["赔率", "盘口", "odds"],
            priority=5
        ))
        
        self.register_tool(Tool(
            name="calculate_ev",
            category=ToolCategory.ANALYSIS,
            description="计算期望值",
            keywords=["期望值", "EV", "value", "expected"],
            priority=5
        ))
        
        self.register_tool(Tool(
            name="detect_anomaly",
            category=ToolCategory.ANALYSIS,
            description="检测赔率异常",
            keywords=["异常", "anomaly", "异常检测"],
            priority=4
        ))
        
        self.register_tool(Tool(
            name="analyze_market_sentiment",
            category=ToolCategory.ANALYSIS,
            description="分析市场情绪",
            keywords=["市场", "情绪", "热度", "market"],
            priority=3
        ))
        
        # Strategy 工具
        self.register_tool(Tool(
            name="generate_mxn_strategy",
            category=ToolCategory.STRATEGY,
            description="生成M串N投注策略",
            keywords=["串关", "策略", "mxn", "combo"],
            priority=5
        ))
        
        self.register_tool(Tool(
            name="allocate_budget",
            category=ToolCategory.STRATEGY,
            description="分配投注资金",
            keywords=["资金", "预算", "分配", "budget"],
            priority=4
        ))
        
        self.register_tool(Tool(
            name="optimize_strategy",
            category=ToolCategory.STRATEGY,
            description="优化投注策略",
            keywords=["优化", "优化策略"],
            priority=3
        ))
        
        # Risk 工具
        self.register_tool(Tool(
            name="check_risk_limits",
            category=ToolCategory.RISK,
            description="检查风控限额",
            keywords=["风控", "限额", "限制", "risk"],
            priority=5
        ))
        
        self.register_tool(Tool(
            name="assess_variance",
            category=ToolCategory.RISK,
            description="评估投注方差",
            keywords=["方差", "波动", "variance"],
            priority=3
        ))
        
        self.register_tool(Tool(
            name="calculate_kelly",
            category=ToolCategory.RISK,
            description="Kelly公式计算",
            keywords=["Kelly", "凯利"],
            priority=4
        ))
        
        # Memory 工具
        self.register_tool(Tool(
            name="store_betting_record",
            category=ToolCategory.MEMORY,
            description="存储投注记录",
            keywords=["存储", "记录", "保存"],
            priority=3
        ))
        
        self.register_tool(Tool(
            name="retrieve_history",
            category=ToolCategory.MEMORY,
            description="检索历史投注",
            keywords=["历史", "检索", "查询"],
            priority=4
        ))
        
        # RAG 工具
        self.register_tool(Tool(
            name="rag_search_knowledge",
            category=ToolCategory.RAG,
            description="向量知识库检索",
            keywords=["知识", "检索", "知识库"],
            priority=4
        ))
        
        self.register_tool(Tool(
            name="rag_search_similar_cases",
            category=ToolCategory.RAG,
            description="相似案例搜索",
            keywords=["相似", "案例", "历史案例"],
            priority=4
        ))
        
        # Notification 工具
        self.register_tool(Tool(
            name="send_notification",
            category=ToolCategory.NOTIFICATION,
            description="发送通知",
            keywords=["通知", "提醒", "推送"],
            priority=2
        ))
    
    def register_tool(self, tool: Tool):
        """注册工具"""
        self._tools[tool.name] = tool
        self._categories[tool.category].append(tool.name)
        self._usage_stats[tool.name] = {
            "total_calls": 0,
            "success_calls": 0,
            "avg_duration": 0.0
        }
    
    def unregister_tool(self, name: str) -> bool:
        """注销工具"""
        if name in self._tools:
            tool = self._tools[name]
            self._categories[tool.category].remove(name)
            del self._tools[name]
            return True
        return False
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)
    
    def get_tools_by_category(self, category: ToolCategory) -> List[Tool]:
        """获取类别下的所有工具"""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def select_tools(self, context: Dict[str, Any], 
                    max_tools: int = 5,
                    min_score: float = 1.0) -> List[Tool]:
        """
        基于上下文选择工具
        
        Args:
            context: 上下文信息，包含 query, task_type 等
            max_tools: 最大选择数量
            min_score: 最低匹配分数
        
        Returns:
            排序后的工具列表
        """
        scored_tools = []
        
        for tool in self._tools.values():
            if not tool.enabled:
                continue
            
            score = tool.match_score(context)
            
            if score >= min_score:
                scored_tools.append((tool, score))
        
        # 按分数排序
        scored_tools.sort(key=lambda x: x[1], reverse=True)
        
        return [tool for tool, _ in scored_tools[:max_tools]]
    
    def select_tool_chain(self, context: Dict[str, Any]) -> ToolChain:
        """
        选择最优工具链
        
        根据上下文自动编排工具链
        """
        task_type = context.get("task_type", "")
        query = context.get("query", "").lower()
        
        # 确定需要的工具类别
        required_categories = set()
        
        if "analysis" in task_type or "analyze" in query:
            required_categories.add(ToolCategory.ANALYSIS)
        if "scout" in task_type or "情报" in query or "news" in query:
            required_categories.add(ToolCategory.SCOUT)
        if "strategy" in task_type or "策略" in query:
            required_categories.add(ToolCategory.STRATEGY)
        if "risk" in task_type or "风控" in query:
            required_categories.add(ToolCategory.RISK)
        if "memory" in task_type or "历史" in query:
            required_categories.add(ToolCategory.MEMORY)
        
        # 选择每个类别的最佳工具
        selected_tools = []
        for category in required_categories:
            tools = self.get_tools_by_category(category)
            if tools:
                # 选择分数最高的
                best = max(tools, key=lambda t: t.match_score(context))
                selected_tools.append(best)
        
        # 如果没有匹配，按默认顺序添加
        if not selected_tools:
            for cat in ToolCategory:
                if cat in required_categories:
                    continue
                tools = self.get_tools_by_category(cat)
                if tools and len(selected_tools) < 3:
                    selected_tools.append(tools[0])
        
        return ToolChain(
            chain_id=str(uuid.uuid4())[:8],
            name=f"Auto Chain for {task_type}",
            description="基于上下自动编排的工具链",
            tools=selected_tools,
            execution_mode="sequential"
        )
    
    def create_tool_chain(self, name: str, 
                         tool_names: List[str],
                         execution_mode: str = "sequential") -> Optional[ToolChain]:
        """创建自定义工具链"""
        tools = []
        for name in tool_names:
            tool = self._tools.get(name)
            if tool:
                tools.append(tool)
        
        if not tools:
            return None
        
        return ToolChain(
            chain_id=str(uuid.uuid4())[:8],
            name=name,
            description="",
            tools=tools,
            execution_mode=execution_mode
        )
    
    def record_tool_usage(self, tool_name: str, 
                          success: bool, duration: float):
        """记录工具使用情况"""
        if tool_name in self._usage_stats:
            stats = self._usage_stats[tool_name]
            stats["total_calls"] += 1
            if success:
                stats["success_calls"] += 1
            
            # 更新平均执行时间
            old_avg = stats["avg_duration"]
            old_count = stats["total_calls"] - 1
            if old_count > 0:
                stats["avg_duration"] = (old_avg * old_count + duration) / stats["total_calls"]
            else:
                stats["avg_duration"] = duration
    
    def get_tool_stats(self, tool_name: str) -> Optional[Dict]:
        """获取工具统计"""
        stats = self._usage_stats.get(tool_name)
        if not stats:
            return None
        
        success_rate = 0.0
        if stats["total_calls"] > 0:
            success_rate = stats["success_calls"] / stats["total_calls"]
        
        return {
            "tool_name": tool_name,
            "total_calls": stats["total_calls"],
            "success_calls": stats["success_calls"],
            "success_rate": success_rate,
            "avg_duration_ms": stats["avg_duration"] * 1000
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有工具统计"""
        return {
            "tools": {name: self.get_tool_stats(name) 
                     for name in self._usage_stats},
            "by_category": {}
        }
    
    def get_recommended_tools(self, limit: int = 5) -> List[Tool]:
        """获取推荐工具（基于使用统计）"""
        tool_stats = [
            (name, stats["success_rate"], stats["total_calls"])
            for name, stats in self._usage_stats.items()
            if stats["total_calls"] > 0
        ]
        
        # 综合评分：成功率 * log(调用次数)
        import math
        scored = [
            (name, rate * math.log(max(calls, 1) + 1))
            for name, rate, calls in tool_stats
        ]
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [
            self._tools[name] 
            for name, _ in scored[:limit]
            if name in self._tools
        ]


class ToolExecutor:
    """工具执行器"""
    
    def __init__(self, registry: DynamicToolRegistry):
        self.registry = registry
    
    def execute(self, tool: Tool, 
                parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        import time
        start_time = time.time()
        success = False
        result = None
        error = None
        
        try:
            if tool.handler:
                result = tool.handler(parameters)
                success = True
            else:
                # 默认处理：返回参数
                result = {"status": "ok", "tool": tool.name, "params": parameters}
                success = True
        except Exception as e:
            error = str(e)
            result = {"status": "error", "error": error}
        
        duration = time.time() - start_time
        self.registry.record_tool_usage(tool.name, success, duration)
        
        return {
            "tool": tool.name,
            "success": success,
            "result": result,
            "duration_ms": duration * 1000,
            "error": error
        }
    
    def execute_chain(self, chain: ToolChain,
                     initial_params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具链"""
        import time
        start_time = time.time()
        
        results = []
        params = initial_params.copy()
        
        for tool in chain.tools:
            result = self.execute(tool, params)
            results.append(result)
            
            if result["success"]:
                # 将结果合并到参数中，供下一个工具使用
                if "result" in result and isinstance(result["result"], dict):
                    params.update(result["result"])
            else:
                # 工具执行失败，停止链
                break
        
        return {
            "chain_id": chain.chain_id,
            "chain_name": chain.name,
            "total_tools": len(chain.tools),
            "executed_tools": len(results),
            "success": all(r["success"] for r in results),
            "results": results,
            "total_duration_ms": (time.time() - start_time) * 1000
        }


# 全局工具注册表
tool_registry = DynamicToolRegistry()
tool_executor = ToolExecutor(tool_registry)


def get_tool_registry() -> DynamicToolRegistry:
    """获取全局工具注册表"""
    return tool_registry


def get_tool_executor() -> ToolExecutor:
    """获取全局工具执行器"""
    return tool_executor


def register_tool_handler(tool_name: str, handler: Callable):
    """注册工具处理器"""
    tool = tool_registry.get_tool(tool_name)
    if tool:
        tool.handler = handler


if __name__ == "__main__":
    # 测试工具选择
    
    # 场景1: 赔率分析
    context1 = {"task_type": "analysis", "query": "分析今晚比赛的赔率"}
    tools1 = tool_registry.select_tools(context1, max_tools=3)
    print("赔率分析工具:")
    for t in tools1:
        print(f"  - {t.name} ({t.category.value})")
    
    # 场景2: 情报搜集
    context2 = {"task_type": "scout", "query": "获取球队最新动态"}
    tools2 = tool_registry.select_tools(context2, max_tools=3)
    print("\n情报搜集工具:")
    for t in tools2:
        print(f"  - {t.name} ({t.category.value})")
    
    # 场景3: 自动工具链
    chain = tool_registry.select_tool_chain({"task_type": "full_analysis"})
    print(f"\n自动工具链: {chain.name}")
    for t in chain.tools:
        print(f"  - {t.name}")
    
    print(f"\n推荐工具: {[t.name for t in tool_registry.get_recommended_tools()]}")
