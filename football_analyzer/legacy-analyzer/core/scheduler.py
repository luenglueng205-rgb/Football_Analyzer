#!/usr/bin/env python3
"""
自动化调度器 - 定时任务配置，每日自动分析，赛后结果更新，反思日志生成
使用APScheduler实现定时任务调度
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# 尝试导入APScheduler
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler未安装，部分调度功能可能不可用")


class TaskType(Enum):
    """任务类型"""
    MATCH_ANALYSIS = "match_analysis"       # 比赛分析
    ODDS_UPDATE = "odds_update"             # 赔率更新
    RESULT_UPDATE = "result_update"         # 赛果更新
    REFLECTION_LOG = "reflection_log"        # 反思日志
    DAILY_REPORT = "daily_report"            # 日报生成
    WEEKLY_REPORT = "weekly_report"          # 周报生成
    DATA_CLEANUP = "data_cleanup"            # 数据清理
    BACKUP = "backup"                       # 数据备份
    CUSTOM = "custom"                        # 自定义任务


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """调度任务"""
    task_id: str
    task_type: TaskType
    name: str
    description: str
    schedule: Dict[str, Any]  # 调度配置
    handler: str = ""         # 处理函数名
    enabled: bool = True
    status: TaskStatus = TaskStatus.PENDING
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskExecution:
    """任务执行记录"""
    execution_id: str
    task_id: str
    start_time: str
    end_time: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict] = None
    error: Optional[str] = None


class TaskScheduler:
    """
    自动化调度器
    负责定时任务配置与管理
    """

    def __init__(self, base_dir: str = None):
        """
        初始化调度器
        
        Args:
            base_dir: 基础目录路径
        """
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir
        
        self.scheduler = None
        if APSCHEDULER_AVAILABLE:
            self.scheduler = BackgroundScheduler()
            self.scheduler.start()
            logger.info("APScheduler已启动")
        else:
            logger.warning("APScheduler未安装，使用简化调度模式")
        
        # 任务存储
        self.tasks: Dict[str, ScheduledTask] = {}
        self.executions: List[TaskExecution] = []
        
        # 任务处理器映射
        self.handlers: Dict[str, Callable] = {}
        
        # 加载配置
        self.config = self._load_config()
        
        # 注册默认任务
        self._register_default_tasks()
        self._register_default_handlers()
        
        logger.info("任务调度器初始化完成")

    def _load_config(self) -> Dict[str, Any]:
        """加载调度配置"""
        config_file = os.path.join(self.base_dir, 'config', 'scheduler_config.json')
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载调度配置失败: {e}")
                
        return {
            "enabled": True,
            "max_executions": 1000,
            "default_timeout": 3600,
            "retry_failed_tasks": True,
            "max_retries": 3
        }

    def _save_config(self):
        """保存调度配置"""
        config_file = os.path.join(self.base_dir, 'config', 'scheduler_config.json')
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存调度配置失败: {e}")

    def _register_default_tasks(self):
        """注册默认任务"""
        self.register_task(ScheduledTask(
            task_id="daily_analysis",
            task_type=TaskType.MATCH_ANALYSIS,
            name="每日比赛分析",
            description="每天早9点自动分析当日比赛",
            schedule={"hour": 9, "minute": 0, "trigger": "cron"},
            handler="run_daily_analysis"
        ))
        
        self.register_task(ScheduledTask(
            task_id="odds_update",
            task_type=TaskType.ODDS_UPDATE,
            name="赔率更新",
            description="每小时更新一次赔率数据",
            schedule={"hours": 1, "trigger": "interval"},
            handler="run_odds_update"
        ))
        
        self.register_task(ScheduledTask(
            task_id="result_update",
            task_type=TaskType.RESULT_UPDATE,
            name="赛果更新",
            description="每小时检查并更新赛果",
            schedule={"minutes": 30, "trigger": "interval"},
            handler="run_result_update"
        ))
        
        self.register_task(ScheduledTask(
            task_id="reflection_log",
            task_type=TaskType.REFLECTION_LOG,
            name="反思日志",
            description="每天23点生成反思日志",
            schedule={"hour": 23, "minute": 0, "trigger": "cron"},
            handler="run_reflection_log"
        ))
        
        self.register_task(ScheduledTask(
            task_id="daily_report",
            task_type=TaskType.DAILY_REPORT,
            name="日报生成",
            description="每天22点生成当日分析报告",
            schedule={"hour": 22, "minute": 0, "trigger": "cron"},
            handler="run_daily_report"
        ))
        
        self.register_task(ScheduledTask(
            task_id="weekly_report",
            task_type=TaskType.WEEKLY_REPORT,
            name="周报生成",
            description="每周一9点生成上周分析报告",
            schedule={"day_of_week": 0, "hour": 9, "minute": 0, "trigger": "cron"},
            handler="run_weekly_report"
        ))
        
        self.register_task(ScheduledTask(
            task_id="data_cleanup",
            task_type=TaskType.DATA_CLEANUP,
            name="数据清理",
            description="每天凌晨2点清理过期数据",
            schedule={"hour": 2, "minute": 0, "trigger": "cron"},
            handler="run_data_cleanup"
        ))
        
        logger.info(f"已注册 {len(self.tasks)} 个默认任务")

    def _register_default_handlers(self):
        """注册默认任务处理器"""
        self.handlers['run_daily_analysis'] = self._handle_daily_analysis
        self.handlers['run_odds_update'] = self._handle_odds_update
        self.handlers['run_result_update'] = self._handle_result_update
        self.handlers['run_reflection_log'] = self._handle_reflection_log
        self.handlers['run_daily_report'] = self._handle_daily_report
        self.handlers['run_weekly_report'] = self._handle_weekly_report
        self.handlers['run_data_cleanup'] = self._handle_data_cleanup

    def register_task(self, task: ScheduledTask) -> bool:
        """
        注册任务
        
        Args:
            task: 任务配置
            
        Returns:
            bool: 是否成功
        """
        if task.task_id in self.tasks:
            logger.warning(f"任务已存在: {task.task_id}")
            return False
            
        self.tasks[task.task_id] = task
        
        # 如果调度器可用，添加任务
        if self.scheduler and task.enabled:
            self._schedule_task(task)
            
        logger.info(f"已注册任务: {task.name} ({task.task_id})")
        return True

    def _schedule_task(self, task: ScheduledTask):
        """将任务添加到调度器"""
        if not self.scheduler:
            return
            
        trigger_type = task.schedule.get('trigger', 'cron')
        
        try:
            if trigger_type == 'cron':
                trigger = CronTrigger(
                    hour=task.schedule.get('hour'),
                    minute=task.schedule.get('minute'),
                    day=task.schedule.get('day'),
                    day_of_week=task.schedule.get('day_of_week')
                )
            elif trigger_type == 'interval':
                trigger = IntervalTrigger(
                    hours=task.schedule.get('hours', 0),
                    minutes=task.schedule.get('minutes', 0)
                )
            else:
                return
                
            self.scheduler.add_job(
                func=self._execute_task_wrapper,
                trigger=trigger,
                args=[task.task_id],
                id=task.task_id,
                replace_existing=True
            )
            
            logger.debug(f"任务已调度: {task.task_id}")
            
        except Exception as e:
            logger.error(f"调度任务失败 [{task.task_id}]: {e}")

    def _execute_task_wrapper(self, task_id: str):
        """任务执行包装器"""
        task = self.tasks.get(task_id)
        if not task:
            return
            
        # 更新状态
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now().isoformat()
        
        # 创建执行记录
        execution = TaskExecution(
            execution_id=f"exec_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            task_id=task_id,
            start_time=datetime.now().isoformat(),
            status=TaskStatus.RUNNING
        )
        
        try:
            # 调用处理器
            handler = self.handlers.get(task.handler)
            if handler:
                result = handler(task.config)
                execution.result = result
                execution.status = TaskStatus.COMPLETED
                task.status = TaskStatus.COMPLETED
            else:
                raise ValueError(f"未找到处理器: {task.handler}")
                
        except Exception as e:
            logger.error(f"任务执行失败 [{task_id}]: {e}")
            execution.error = str(e)
            execution.status = TaskStatus.FAILED
            task.status = TaskStatus.FAILED
            
        finally:
            execution.end_time = datetime.now().isoformat()
            self.executions.append(execution)
            task.run_count += 1
            
            # 清理旧的执行记录
            if len(self.executions) > self.config.get('max_executions', 1000):
                self.executions = self.executions[-self.config.get('max_executions', 1000):]

    def unregister_task(self, task_id: str) -> bool:
        """
        注销任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功
        """
        if task_id not in self.tasks:
            return False
            
        # 从调度器移除
        if self.scheduler:
            self.scheduler.remove_job(task_id)
            
        # 从存储移除
        del self.tasks[task_id]
        
        logger.info(f"已注销任务: {task_id}")
        return True

    def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False
            
        task.enabled = True
        self._schedule_task(task)
        logger.info(f"已启用任务: {task_id}")
        return True

    def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False
            
        task.enabled = False
        if self.scheduler:
            self.scheduler.remove_job(task_id)
            
        logger.info(f"已禁用任务: {task_id}")
        return True

    def run_task_now(self, task_id: str) -> bool:
        """
        立即执行任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功
        """
        if task_id not in self.tasks:
            return False
            
        self._execute_task_wrapper(task_id)
        return True

    # 默认任务处理器
    def _handle_daily_analysis(self, config: Dict) -> Dict[str, Any]:
        """处理每日分析任务"""
        logger.info("执行每日比赛分析...")
        # TODO: 调用实际的分析逻辑
        return {
            'status': 'completed',
            'matches_analyzed': 0,
            'timestamp': datetime.now().isoformat()
        }

    def _handle_odds_update(self, config: Dict) -> Dict[str, Any]:
        """处理赔率更新任务"""
        logger.info("执行赔率更新...")
        return {
            'status': 'completed',
            'odds_updated': 0,
            'timestamp': datetime.now().isoformat()
        }

    def _handle_result_update(self, config: Dict) -> Dict[str, Any]:
        """处理赛果更新任务"""
        logger.info("执行赛果更新...")
        return {
            'status': 'completed',
            'results_updated': 0,
            'timestamp': datetime.now().isoformat()
        }

    def _handle_reflection_log(self, config: Dict) -> Dict[str, Any]:
        """处理反思日志任务"""
        logger.info("生成反思日志...")
        
        # 生成反思日志
        log_dir = os.path.join(self.base_dir, 'reports', 'reflection')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"reflection_{datetime.now().strftime('%Y%m%d')}.md")
        
        log_content = f"""# 反思日志 - {datetime.now().strftime('%Y-%m-%d')}

## 今日分析回顾

### 比赛分析
- 分析场次: 待统计
- 推荐准确率: 待统计

### 投注回顾
- 投注场次: 待统计
- 盈亏情况: 待统计

### 问题识别
-

### 改进方向
-

## 明日计划
-

---
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(log_content)
            
        return {
            'status': 'completed',
            'log_file': log_file,
            'timestamp': datetime.now().isoformat()
        }

    def _handle_daily_report(self, config: Dict) -> Dict[str, Any]:
        """处理日报任务"""
        logger.info("生成日报...")
        
        report_dir = os.path.join(self.base_dir, 'reports', 'daily')
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = os.path.join(report_dir, f"daily_report_{datetime.now().strftime('%Y%m%d')}.md")
        
        report_content = f"""# 每日分析报告 - {datetime.now().strftime('%Y-%m-%d')}

## 今日赛事概览

### 竞彩足球
- 比赛数量: 待统计
- 推荐场次: 待统计

### 北京单场
- 比赛数量: 待统计
- 推荐场次: 待统计

### 传统足彩
- 比赛数量: 待统计
- 推荐场次: 待统计

## 价值投注推荐

## 串关方案

## 风险提示

---
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
            
        return {
            'status': 'completed',
            'report_file': report_file,
            'timestamp': datetime.now().isoformat()
        }

    def _handle_weekly_report(self, config: Dict) -> Dict[str, Any]:
        """处理周报任务"""
        logger.info("生成周报...")
        
        report_dir = os.path.join(self.base_dir, 'reports', 'weekly')
        os.makedirs(report_dir, exist_ok=True)
        
        # 获取上周的日期范围
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday() + 7)
        week_end = week_start + timedelta(days=6)
        
        report_file = os.path.join(report_dir, f"weekly_report_{week_start.strftime('%Y%m%d')}.md")
        
        report_content = f"""# 周报 - {week_start.strftime('%Y-%m-%d')} 至 {week_end.strftime('%Y-%m-%d')}

## 本周总结

### 数据统计
- 总分析场次:
- 推荐准确率:
- 收益率:

### 最佳推荐
-

### 问题分析
-

## 下周展望

---
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
            
        return {
            'status': 'completed',
            'report_file': report_file,
            'timestamp': datetime.now().isoformat()
        }

    def _handle_data_cleanup(self, config: Dict) -> Dict[str, Any]:
        """处理数据清理任务"""
        logger.info("执行数据清理...")
        
        # 清理旧的临时文件
        temp_dir = os.path.join(self.base_dir, 'temp')
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                try:
                    if os.path.isfile(file_path):
                        # 删除超过7天的文件
                        mtime = os.path.getmtime(file_path)
                        if (datetime.now() - datetime.fromtimestamp(mtime)).days > 7:
                            os.remove(file_path)
                except Exception as e:
                    logger.warning(f"清理文件失败: {file_path}")
                    
        return {
            'status': 'completed',
            'timestamp': datetime.now().isoformat()
        }

    def get_task_status(self, task_id: str = None) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id: 可选的任务ID
            
        Returns:
            Dict: 状态信息
        """
        if task_id:
            task = self.tasks.get(task_id)
            if not task:
                return {'error': 'Task not found'}
                
            return {
                'task_id': task.task_id,
                'name': task.name,
                'type': task.task_type.value,
                'enabled': task.enabled,
                'status': task.status.value,
                'last_run': task.last_run,
                'next_run': task.next_run,
                'run_count': task.run_count
            }
        else:
            # 返回所有任务状态
            return {
                'tasks': [
                    self.get_task_status(tid) 
                    for tid in self.tasks.keys()
                ],
                'total_tasks': len(self.tasks),
                'enabled_tasks': sum(1 for t in self.tasks.values() if t.enabled)
            }

    def get_execution_history(self, task_id: str = None, 
                              limit: int = 20) -> List[Dict]:
        """
        获取执行历史
        
        Args:
            task_id: 可选的任务ID过滤
            limit: 返回数量限制
            
        Returns:
            List: 执行历史
        """
        history = self.executions
        
        if task_id:
            history = [e for e in history if e.task_id == task_id]
            
        history = history[-limit:]
        
        return [
            {
                'execution_id': e.execution_id,
                'task_id': e.task_id,
                'start_time': e.start_time,
                'end_time': e.end_time,
                'status': e.status.value,
                'error': e.error
            }
            for e in history
        ]

    def shutdown(self):
        """关闭调度器"""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("调度器已关闭")


def demo():
    """演示函数"""
    print("=" * 60)
    print("任务调度器演示")
    print("=" * 60)
    
    scheduler = TaskScheduler()
    
    print("\n" + "-" * 60)
    print("任务列表")
    print("-" * 60)
    
    status = scheduler.get_task_status()
    print(f"总任务数: {status['total_tasks']}")
    print(f"已启用: {status['enabled_tasks']}")
    
    for task_status in status['tasks']:
        print(f"\n  {task_status['name']}")
        print(f"    ID: {task_status['task_id']}")
        print(f"    类型: {task_status['type']}")
        print(f"    状态: {task_status['status']}")
        print(f"    已执行: {task_status['run_count']} 次")
        
    # 测试执行反思日志
    print("\n" + "-" * 60)
    print("立即执行反思日志任务")
    print("-" * 60)
    
    result = scheduler.run_task_now('reflection_log')
    print(f"执行结果: {result}")
    

if __name__ == "__main__":
    demo()
