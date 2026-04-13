#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - Core模块
多Agent协作架构核心模块
"""

from core.base_agent import (
    BaseAgent,
    AgentStatus,
    TaskPriority,
    AgentMessage,
    Task,
    MessageBus,
    AgentRegistry,
    get_registry
)

from core.orchestrator import (
    OrchestratorAgent,
    create_orchestrator,
    WorkflowStep,
    WorkflowTask,
    TaskStatus,
    quick_analysis,
    full_analysis
)

from core.scout_agent import ScoutAgent, create_scout_agent
from core.analyst_agent import AnalystAgent, create_analyst_agent
from core.strategist_agent import StrategistAgent, create_strategist_agent
from core.risk_manager import RiskManagerAgent, create_risk_manager_agent, Position

from core.conversation import (
    ConversationManager,
    ConversationContext,
    QueryParser,
    ParsedQuery,
    Intent,
    get_conversation_manager
)

from core.webhook_server import (
    NotificationType,
    WebhookMessage,
    NotificationConfig,
    NotificationSender,
    WechatNotifier,
    TelegramNotifier,
    DingTalkNotifier,
    WebhookServer
)

from core.scheduler import (
    TaskScheduler,
    ScheduledTask,
    TaskType,
    TaskStatus as SchedulerTaskStatus
)

# === v3.0 现代化模块 ===
from core.react_pattern import (
    ReActAgent,
    ReActResult,
    Thought,
    Action,
    Observation,
    ThoughtType,
    ActionType,
    ToolRegistry,
    get_tool_registry
)

from core.plan_execute import (
    PlanAndExecuteAgent,
    Plan,
    PlanStatus,
    ExecutionStep,
    StepStatus,
    PlanGenerator,
    PlanExecutor,
    create_plan,
    execute_plan
)

from core.rag_knowledge import (
    RagKnowledgeBase,
    KnowledgeChunk,
    SearchResult,
    EmbeddingGenerator,
    VectorStoreType,
    get_rag_knowledge_base,
    init_rag_knowledge_base
)

from core.logging_tracing import (
    StructuredLogger,
    TracingManager,
    LogRecord,
    LogLevel,
    EventType,
    Span,
    MetricsCollector,
    traced,
    structured_logger,
    tracing_manager,
    metrics_collector,
    configure_logging
)

from core.dynamic_tool_selection import (
    DynamicToolRegistry,
    ToolExecutor,
    Tool,
    ToolChain,
    ToolCategory,
    tool_registry,
    tool_executor,
    register_tool_handler
)

from core.crewai_integration import (
    CREWAI_AVAILABLE,
    FootballCrewFactory,
    CrewAIIntegration,
    BettingProcess,
    AgentConfig,
    TaskConfig,
    create_football_crew,
    run_analysis
)

from core.modern_agent import (
    ModernAgentCore,
    AgentMode,
    get_modern_agent,
    analyze
)

__all__ = [
    # Base
    'BaseAgent',
    'AgentStatus',
    'TaskPriority',
    'AgentMessage',
    'Task',
    'MessageBus',
    'AgentRegistry',
    'get_registry',
    
    # Orchestrator
    'OrchestratorAgent',
    'create_orchestrator',
    'WorkflowStep',
    'WorkflowTask',
    'TaskStatus',
    'quick_analysis',
    'full_analysis',
    
    # Agents
    'ScoutAgent',
    'create_scout_agent',
    'AnalystAgent',
    'create_analyst_agent',
    'StrategistAgent',
    'create_strategist_agent',
    'RiskManagerAgent',
    'create_risk_manager_agent',
    'Position',
    
    # Conversation
    'ConversationManager',
    'ConversationContext',
    'QueryParser',
    'ParsedQuery',
    'Intent',
    'get_conversation_manager',
    
    # Webhook
    'NotificationType',
    'WebhookMessage',
    'NotificationConfig',
    'NotificationSender',
    'WechatNotifier',
    'TelegramNotifier',
    'DingTalkNotifier',
    'WebhookServer',
    
    # Scheduler
    'TaskScheduler',
    'ScheduledTask',
    'TaskType',
    'SchedulerTaskStatus',
    'get_scheduler',
    
    # === v3.0 现代化模块 ===
    # ReAct Pattern
    'ReActAgent',
    'ReActResult',
    'Thought',
    'Action',
    'Observation',
    'ThoughtType',
    'ActionType',
    'ToolRegistry',
    
    # Plan-and-Execute
    'PlanAndExecuteAgent',
    'Plan',
    'PlanStatus',
    'ExecutionStep',
    'StepStatus',
    'PlanGenerator',
    'PlanExecutor',
    'create_plan',
    'execute_plan',
    
    # RAG Knowledge Base
    'RagKnowledgeBase',
    'KnowledgeChunk',
    'SearchResult',
    'EmbeddingGenerator',
    'VectorStoreType',
    'init_rag_knowledge_base',
    
    # Structured Logging
    'LogRecord',
    'LogLevel',
    'EventType',
    'Span',
    'MetricsCollector',
    'traced',
    'configure_logging',
    
    # Dynamic Tool Selection
    'Tool',
    'ToolChain',
    'ToolCategory',
    'register_tool_handler',
    
    # CrewAI
    'FootballCrewFactory',
    'CrewAIIntegration',
    'BettingProcess',
    'AgentConfig',
    'TaskConfig',
    'create_football_crew',
    'run_analysis',
    
    # Modern Agent Core
    'ModernAgentCore',
    'AgentMode',
    'get_modern_agent',
]
