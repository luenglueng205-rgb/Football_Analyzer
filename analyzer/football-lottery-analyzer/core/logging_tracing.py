# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - Structured Logging & Tracing
结构化日志与分布式追踪

功能:
- 结构化JSON日志
- 请求链路追踪(Trace ID)
- Agent执行Span
- 性能指标监控
"""

import os
import sys
import json
import uuid
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field, asdict
from contextvars import ContextVar
from functools import wraps
import traceback


# ============ 上下文变量 ============
trace_id_var: ContextVar[str] = ContextVar('trace_id', default='')
span_id_var: ContextVar[str] = ContextVar('span_id', default='')


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventType(Enum):
    """事件类型"""
    AGENT_START = "agent.start"
    AGENT_END = "agent.end"
    AGENT_ERROR = "agent.error"
    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"
    WORKFLOW_START = "workflow.start"
    WORKFLOW_END = "workflow.end"
    MEMORY_ACCESS = "memory.access"
    RAG_QUERY = "rag.query"
    RAG_RESULT = "rag.result"


@dataclass
class LogRecord:
    """结构化日志记录"""
    timestamp: str
    level: str
    trace_id: str
    span_id: str
    event: str
    message: str
    agent: Optional[str] = None
    tool: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class Span:
    """追踪Span"""
    span_id: str
    trace_id: str
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "running"
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict] = field(default_factory=list)
    spans: List['Span'] = field(default_factory=list)
    
    def end(self, status: str = "ok"):
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
    
    def add_tag(self, key: str, value: Any):
        self.tags[key] = value
    
    def add_log(self, message: str, metadata: Optional[Dict] = None):
        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "metadata": metadata or {}
        })
    
    def add_child(self, name: str) -> 'Span':
        child_span = Span(
            span_id=f"{self.span_id}.{len(self.spans) + 1}",
            trace_id=self.trace_id,
            name=name,
            start_time=time.time()
        )
        self.spans.append(child_span)
        return child_span
    
    def to_dict(self) -> Dict:
        result = {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "tags": self.tags,
            "logs": self.logs
        }
        if self.spans:
            result["spans"] = [s.to_dict() for s in self.spans]
        return result


class StructuredLogger:
    """
    结构化日志记录器
    
    输出格式:
    {
        "timestamp": "2024-01-01T12:00:00.000Z",
        "level": "INFO",
        "trace_id": "abc123",
        "span_id": "1.2.3",
        "event": "agent.start",
        "message": "Agent started",
        "agent": "ScoutAgent",
        "duration_ms": 123.45,
        "metadata": {...}
    }
    """
    
    def __init__(self, name: str = "football_lottery"):
        self.name = name
        self._log_file: Optional[str] = None
        self._trace_file: Optional[str] = None
        self._min_level = LogLevel.INFO
        
        # 事件处理器
        self._event_handlers: Dict[EventType, List[Callable]] = {}
    
    def configure(self, log_file: Optional[str] = None,
                  trace_file: Optional[str] = None,
                  min_level: LogLevel = LogLevel.INFO):
        """配置日志器"""
        self._log_file = log_file
        self._trace_file = trace_file
        self._min_level = min_level
        
        if self._log_file:
            os.makedirs(os.path.dirname(self._log_file) or '.', exist_ok=True)
        if self._trace_file:
            os.makedirs(os.path.dirname(self._trace_file) or '.', exist_ok=True)
    
    def set_level(self, level: LogLevel):
        """设置日志级别"""
        self._min_level = level
    
    def _should_log(self, level: LogLevel) -> bool:
        """检查是否应该记录"""
        levels = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, 
                  LogLevel.ERROR, LogLevel.CRITICAL]
        return levels.index(level) >= levels.index(self._min_level)
    
    def _write_log(self, record: LogRecord):
        """写入日志"""
        # 控制台输出
        print(record.to_json())
        
        # 文件输出
        if self._log_file:
            with open(self._log_file, 'a', encoding='utf-8') as f:
                f.write(record.to_json() + '\n')
        
        # 触发事件处理器
        if record.event:
            try:
                event_type = EventType(record.event)
                handlers = self._event_handlers.get(event_type, [])
                for handler in handlers:
                    try:
                        handler(record)
                    except Exception:
                        pass
            except ValueError:
                pass
    
    def log(self, level: LogLevel, event: str, message: str,
            agent: Optional[str] = None, tool: Optional[str] = None,
            duration_ms: Optional[float] = None,
            metadata: Optional[Dict] = None):
        """记录日志"""
        if not self._should_log(level):
            return
        
        record = LogRecord(
            timestamp=datetime.now().isoformat() + "Z",
            level=level.value,
            trace_id=trace_id_var.get() or str(uuid.uuid4())[:8],
            span_id=span_id_var.get() or "root",
            event=event,
            message=message,
            agent=agent,
            tool=tool,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        
        self._write_log(record)
    
    def debug(self, message: str, **kwargs):
        self.log(LogLevel.DEBUG, "", message, **kwargs)
    
    def info(self, event: str, message: str, **kwargs):
        self.log(LogLevel.INFO, event, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log(LogLevel.WARNING, "", message, **kwargs)
    
    def error(self, event: str, message: str, **kwargs):
        self.log(LogLevel.ERROR, event, message, **kwargs)
    
    def critical(self, event: str, message: str, **kwargs):
        self.log(LogLevel.CRITICAL, event, message, **kwargs)
    
    def on_event(self, event_type: EventType, handler: Callable):
        """注册事件处理器"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)


class TracingManager:
    """
    分布式追踪管理器
    
    支持:
    - 创建Trace
    - Span管理
    - 链路传播
    """
    
    def __init__(self, logger: Optional[StructuredLogger] = None):
        self.logger = logger or structured_logger
        self._traces: Dict[str, Span] = {}
        self._current_span: Optional[Span] = None
    
    def start_trace(self, name: str, trace_id: Optional[str] = None,
                   tags: Optional[Dict] = None) -> Span:
        """开始追踪"""
        trace_id = trace_id or str(uuid.uuid4())[:8]
        
        span = Span(
            span_id=f"{trace_id}.1",
            trace_id=trace_id,
            name=name,
            start_time=time.time(),
            tags=tags or {}
        )
        
        self._traces[trace_id] = span
        self._current_span = span
        
        # 设置上下文变量
        trace_id_var.set(trace_id)
        span_id_var.set(span.span_id)
        
        self.logger.info(EventType.WORKFLOW_START.value, 
                        f"Trace started: {name}",
                        agent=name, metadata=span.to_dict())
        
        return span
    
    def end_trace(self, span: Optional[Span] = None, 
                  status: str = "ok"):
        """结束追踪"""
        span = span or self._current_span
        if not span:
            return
        
        span.end(status)
        
        self.logger.info(EventType.WORKFLOW_END.value,
                        f"Trace ended: {span.name}",
                        duration_ms=span.duration_ms,
                        metadata={"status": status})
        
        # 保存到文件
        if self.logger._trace_file:
            self._save_trace(span)
        
        self._current_span = None
        trace_id_var.set('')
        span_id_var.set('')
    
    def start_span(self, name: str, 
                   tags: Optional[Dict] = None) -> Span:
        """开始Span"""
        if not self._current_span:
            # 如果没有活跃trace，创建一个
            self.start_trace(name)
            return self._current_span
        
        child_span = self._current_span.add_child(name)
        span_id_var.set(child_span.span_id)
        
        self.logger.debug(f"Span started: {name}", 
                         metadata={"parent": self._current_span.span_id})
        
        return child_span
    
    def end_span(self, span: Optional[Span] = None,
                 status: str = "ok"):
        """结束Span"""
        if not span:
            return
        
        parent = self._find_parent_span(span)
        
        span.end(status)
        
        self.logger.debug(f"Span ended: {span.name}",
                         duration_ms=span.duration_ms,
                         metadata={"status": status})
        
        if parent:
            span_id_var.set(parent.span_id)
        else:
            span_id_var.set('')
    
    def _find_parent_span(self, child: Span) -> Optional[Span]:
        """查找父Span"""
        parent_id = '.'.join(child.span_id.split('.')[:-1])
        if parent_id == child.trace_id:
            return self._traces.get(child.trace_id)
        
        for trace in self._traces.values():
            for s in trace.spans:
                if s.span_id == parent_id:
                    return s
        return None
    
    def _save_trace(self, span: Span):
        """保存追踪记录"""
        filepath = self.logger._trace_file
        if not filepath:
            return
        
        trace_data = span.to_dict()
        
        # 追加到文件
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(json.dumps(trace_data, ensure_ascii=False) + '\n')
    
    def get_trace(self, trace_id: str) -> Optional[Span]:
        """获取追踪"""
        return self._traces.get(trace_id)
    
    def get_current_span(self) -> Optional[Span]:
        """获取当前Span"""
        return self._current_span


# 全局实例
structured_logger = StructuredLogger("football_lottery")
tracing_manager = TracingManager(structured_logger)


def traced(span_name: Optional[str] = None, 
           agent: Optional[str] = None):
    """追踪装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = span_name or func.__name__
            
            span = tracing_manager.start_span(name, {"agent": agent})
            
            start_time = time.time()
            error = None
            result = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                
                if error:
                    span.add_log("error", {"error": str(error)})
                    tracing_manager.end_span(span, "error")
                    structured_logger.error(
                        EventType.AGENT_ERROR.value if agent else "error",
                        f"{name} failed: {str(error)}",
                        agent=agent,
                        duration_ms=duration_ms,
                        metadata={"error_type": type(error).__name__}
                    )
                else:
                    tracing_manager.end_span(span, "ok")
                    structured_logger.info(
                        EventType.AGENT_END.value if agent else "info",
                        f"{name} completed",
                        agent=agent,
                        duration_ms=duration_ms
                    )
        
        return wrapper
    return decorator


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self._metrics: Dict[str, List[float]] = {}
        self._counters: Dict[str, int] = {}
    
    def record_duration(self, metric_name: str, duration_ms: float):
        """记录执行时长"""
        if metric_name not in self._metrics:
            self._metrics[metric_name] = []
        self._metrics[metric_name].append(duration_ms)
    
    def increment(self, counter_name: str, value: int = 1):
        """递增计数器"""
        self._counters[counter_name] = self._counters.get(counter_name, 0) + value
    
    def get_stats(self, metric_name: str) -> Dict[str, float]:
        """获取统计信息"""
        values = self._metrics.get(metric_name, [])
        if not values:
            return {}
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "p50": sorted(values)[len(values) // 2],
            "p95": sorted(values)[int(len(values) * 0.95)] if len(values) > 1 else values[0],
            "p99": sorted(values)[int(len(values) * 0.99)] if len(values) > 1 else values[0]
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        return {
            "durations": {name: self.get_stats(name) 
                         for name in self._metrics},
            "counters": self._counters.copy()
        }


# 全局指标收集器
metrics_collector = MetricsCollector()


def configure_logging(log_dir: str = "logs"):
    """配置日志系统"""
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "football_lottery.jsonl")
    trace_file = os.path.join(log_dir, "traces.jsonl")
    
    structured_logger.configure(
        log_file=log_file,
        trace_file=trace_file,
        min_level=LogLevel.INFO
    )


if __name__ == "__main__":
    # 配置日志
    configure_logging("/Volumes/J ZAO 9 SER 1/Python/CodeBuddy/football-lottery-analyzer/logs")
    
    # 测试追踪
    trace = tracing_manager.start_trace("full_analysis")
    
    with tracing_manager.start_span("scout") as span:
        span.add_tag("league", "英超")
        time.sleep(0.1)
    
    with tracing_manager.start_span("analyze"):
        time.sleep(0.2)
    
    tracing_manager.end_trace(trace)
    
    print(f"\n指标: {metrics_collector.get_all_metrics()}")
