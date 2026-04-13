#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - 主控Agent (进化版)
集成多Agent协作架构、对话系统、调度器

功能：
1. 协调所有专业Agent（Scout/Analyst/Strategist/RiskManager）
2. 提供统一的分析接口
3. 支持对话式交互
4. 支持定时任务调度
5. 支持Webhook推送通知
"""

import os
import sys
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'chinese_mapped')
sys.path.insert(0, BASE_DIR)

from core import (
    OrchestratorAgent,
    create_orchestrator,
    ConversationManager,
    get_conversation_manager,
    TaskScheduler,
    WebhookServer
)


class FootballLotteryAgent:
    """
    足球彩票分析主控Agent
    
    集成了多Agent协作架构的完整系统，支持：
    - 多Agent并行/串行分析
    - 对话式自然语言交互
    - 定时任务调度
    - Webhook推送通知
    """
    
    def __init__(self):
        """初始化主控Agent"""
        self.name = "足球彩票分析系统"
        self.version = "2.0.0"
        
        # 核心组件
        self.orchestrator: Optional[OrchestratorAgent] = None
        self.conversation: Optional[ConversationManager] = None
        self.scheduler: Optional[TaskScheduler] = None
        self.webhook: Optional[WebhookServer] = None
        
        # 初始化
        self._initialize()
    
    def _initialize(self) -> None:
        """初始化所有组件"""
        print(f"\n{'='*60}")
        print(f"  初始化 {self.name} v{self.version}")
        print(f"{'='*60}")
        
        # 初始化Orchestrator
        print("\n[1/4] 初始化多Agent协作引擎...")
        self.orchestrator = create_orchestrator()
        print("  ✓ Orchestrator 初始化完成")
        
        # 初始化对话系统
        print("[2/4] 初始化对话系统...")
        self.conversation = get_conversation_manager()
        self.conversation.create_session("main_session")
        print("  ✓ 对话系统 初始化完成")
        
        # 初始化调度器
        print("[3/4] 初始化任务调度器...")
        self.scheduler = TaskScheduler()
        print("  ✓ 调度器 初始化完成")
        
        # 初始化Webhook
        print("[4/4] 初始化Webhook推送...")
        self.webhook = WebhookServer()
        print("  ✓ Webhook服务 初始化完成")
        
        print(f"\n{'='*60}")
        print(f"  初始化完成！所有模块就绪")
        print(f"{'='*60}\n")
    
    def analyze(self, 
               workflow: str = "full_analysis",
               matches: list = None,
               budget: float = 100,
               **kwargs) -> Dict[str, Any]:
        """
        执行分析工作流
        
        Args:
            workflow: 工作流类型 (full_analysis/quick_analysis/value_hunt)
            matches: 比赛列表
            budget: 预算
            **kwargs: 其他参数
        
        Returns:
            分析结果
        """
        payload = {
            "budget": budget,
            "matches": matches or [],
            **kwargs
        }
        
        return self.orchestrator.execute_workflow(workflow, payload)
    
    def chat(self, message: str) -> str:
        """
        对话交互
        
        Args:
            message: 用户消息
        
        Returns:
            回复内容
        """
        result = self.conversation.process_input("main_session", message)
        return result.get("response", "")
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        orchestrator_status = self.orchestrator.get_system_status() if self.orchestrator else {}
        scheduler_status = self.scheduler.get_task_status() if self.scheduler else {}
        
        return {
            "system": self.name,
            "version": self.version,
            "orchestrator": orchestrator_status,
            "scheduler": scheduler_status,
            "webhook": {
                "enabled": self.webhook is not None
            }
        }
    
    def start_scheduler(self) -> None:
        """启动定时任务调度器"""
        if self.scheduler:
            self.scheduler.start()
            print("调度器已启动")
    
    def stop_scheduler(self) -> None:
        """停止定时任务调度器"""
        if self.scheduler:
            self.scheduler.stop()
            print("调度器已停止")
    
    def send_notification(self, 
                         notification_type: str,
                         title: str,
                         content: str) -> bool:
        """发送通知"""
        from core.webhook_server import NotificationType
        
        type_map = {
            "value_bet": NotificationType.VALUE_BET,
            "analysis": NotificationType.ANALYSIS_RESULT,
            "bet_result": NotificationType.BET_RESULT,
            "alert": NotificationType.SYSTEM_ALERT,
            "report": NotificationType.DAILY_REPORT
        }
        
        notif_type = type_map.get(notification_type, NotificationType.SYSTEM_ALERT)
        
        if self.webhook:
            return self.webhook.send_notification(notif_type, title, content)
        return False
    
    def run_daily_analysis(self) -> Dict[str, Any]:
        """执行每日分析"""
        print("\n" + "="*60)
        print("  执行每日分析")
        print("="*60)
        
        result = self.analyze("full_analysis", budget=100)
        
        # 发送推送
        self.send_notification(
            "analysis",
            "每日分析报告",
            f"分析了 {len(result.get('results', {}))} 个维度"
        )
        
        return result
    
    def interactive_mode(self) -> None:
        """交互式对话模式"""
        print("\n" + "="*60)
        print("  进入对话模式 (输入 'exit' 退出)")
        print("="*60)
        
        print("\n欢迎！我是足球彩票分析助手。")
        print("您可以这样问我：")
        print("  • '分析今晚的比赛'")
        print("  • '推荐几场价值投注'")
        print("  • '生成3串1方案'")
        print("  • '查看系统状态'")
        print()
        
        while True:
            try:
                user_input = input("\n您: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit', '退出']:
                    print("\n再见！祝您投注顺利！\n")
                    break
                
                response = self.chat(user_input)
                print(f"\n助手: {response}")
                
            except KeyboardInterrupt:
                print("\n\n已退出对话模式")
                break
            except Exception as e:
                print(f"\n错误: {e}")
    
    def get_help(self) -> str:
        """获取使用帮助"""
        return """
【足球彩票分析系统 - 使用帮助】

## 基本用法

```python
from main_agent import FootballLotteryAgent

# 初始化
agent = FootballLotteryAgent()

# 完整分析
result = agent.analyze("full_analysis", budget=100)

# 快速分析
result = agent.analyze("quick_analysis")

# 对话交互
response = agent.chat("推荐几场价值投注")

# 获取系统状态
status = agent.get_system_status()
```

## 工作流类型

1. `full_analysis` - 完整分析（情报+赔率+策略+风控）
2. `quick_analysis` - 快速分析（赔率+策略）
3. `value_hunt` - 价值猎取（情报+赔率）
4. `strategy_generate` - 策略生成（策略+风控）

## 对话命令

- '分析...' - 开始分析
- '推荐...' - 获取推荐
- '状态' - 查看系统状态
- '帮助' - 显示帮助
- '退出' - 退出对话模式

## 定时任务

```python
# 启动调度器
agent.start_scheduler()

# 查看调度状态
status = agent.scheduler.get_status()
```

## 推送通知

```python
# 发送自定义通知
agent.send_notification("alert", "标题", "内容")
```
"""


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="足球彩票分析系统")
    parser.add_argument("--mode", choices=["cli", "chat", "daemon"], 
                       default="cli", help="运行模式")
    parser.add_argument("--workflow", default="full_analysis",
                       help="分析工作流")
    parser.add_argument("--budget", type=float, default=100,
                       help="投注预算")
    
    args = parser.parse_args()
    
    # 初始化Agent
    agent = FootballLotteryAgent()
    
    if args.mode == "cli":
        # CLI模式 - 执行一次分析
        print(f"\n执行工作流: {args.workflow}")
        result = agent.analyze(args.workflow, budget=args.budget)
        print(f"\n分析结果: {result}")
        
    elif args.mode == "chat":
        # 对话模式
        agent.interactive_mode()
        
    elif args.mode == "daemon":
        # 守护进程模式
        print("\n启动守护进程模式...")
        agent.start_scheduler()
        print("\n按 Ctrl+C 停止...")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n正在停止...")
            agent.stop_scheduler()
    
    print("\n系统状态:")
    print(agent.get_system_status())


if __name__ == "__main__":
    main()
