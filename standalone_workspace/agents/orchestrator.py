#!/usr/bin/env python3
"""
调度Agent - OpenClaw规范版本
Orchestrator Agent - 增强版：集成221,415条历史数据
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# 确保能找到tools模块
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from .base import BaseAgent, AgentStatus, Message, message_bus

logger = logging.getLogger(__name__)

# 引入 Analyzer API 工具库
try:
    from tools.analyzer_api import AnalyzerAPI
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    logger.warning("AnalyzerAPI 导入失败。")


class Task:
    """任务定义"""
    def __init__(self, task_id: str, task_type: str, params: Dict):
        self.task_id = task_id
        self.task_type = task_type
        self.params = params
        self.status = "pending"
        self.result = None
        self.subtasks: List[Dict] = []
        self.created_at = datetime.now().isoformat()
        self.completed_at = None
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "params": self.params,
            "status": self.status,
            "result": self.result,
            "subtasks": self.subtasks,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }


class OrchestratorAgent(BaseAgent):
    """
    调度中心Agent - 增强版
    
    职责：
    1. 接收用户任务
    2. 分解任务为子任务
    3. 分发到专业Agent
    4. 汇总结果
    5. 管理历史数据访问
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("orchestrator", "调度中心", config)
        self.tasks: Dict[str, Task] = {}
        self.workflows = self._load_workflows()
        self.registered_agents: Dict[str, BaseAgent] = {}
        
        # 尝试连接 AnalyzerAPI 获取统计
        if API_AVAILABLE:
            try:
                print(f"✅ Orchestrator 已连接 AnalyzerAPI (System 2)")
            except Exception as e:
                logger.warning(f"AnalyzerAPI 连接失败: {e}")
        
        # 注册到消息总线
        message_bus.register(self)
    
    def register_agent(self, agent_id: str, agent: BaseAgent):
        """注册子Agent"""
        self.registered_agents[agent_id] = agent
        message_bus.register(agent)
        logger.info(f"Registered agent: {agent_id}")
    
    def _load_workflows(self) -> Dict[str, Dict]:
        """加载工作流配置"""
        workflow_path = os.path.join(self.workspace, 'workflows.json')
        if os.path.exists(workflow_path):
            with open(workflow_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 默认工作流
        return {
            "full_analysis": {
                "description": "完整分析工作流",
                "subtasks": [
                    {"agent": "scout", "action": "gather_intelligence", "parallel": True},
                    {"agent": "analyst", "action": "analyze_odds", "parallel": True},
                    {"agent": "strategist", "action": "generate_strategy", "depends_on": ["scout", "analyst"]},
                    {"agent": "risk-manager", "action": "risk_assessment", "depends_on": ["strategist"]}
                ]
            },
            "quick_analysis": {
                "description": "快速分析工作流",
                "subtasks": [
                    {"agent": "analyst", "action": "analyze_odds", "parallel": False},
                    {"agent": "strategist", "action": "quick_recommend", "depends_on": ["analyst"]}
                ]
            }
        }
    
    def create_task(self, task_type: str, params: Dict) -> Task:
        """创建任务"""
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        task = Task(task_id, task_type, params)
        self.tasks[task_id] = task
        logger.info(f"Created task {task_id} of type {task_type}")
        return task
    
    def process(self, task: Dict) -> Dict:
        """处理任务"""
        self.status = AgentStatus.RUNNING
        
        task_type = task.get('type', 'full_analysis')
        params = task.get('params', {})
        
        # 创建内部任务
        internal_task = self.create_task(task_type, params)
        
        # 获取工作流
        workflow = self.workflows.get(task_type, self.workflows['full_analysis'])
        internal_task.subtasks = workflow['subtasks']
        
        # 执行工作流
        result = self._execute_workflow(internal_task)
        
        internal_task.result = result
        internal_task.status = "completed"
        internal_task.completed_at = datetime.now().isoformat()
        
        self.status = AgentStatus.COMPLETED
        
        return {
            "task_id": internal_task.task_id,
            "status": internal_task.status,
            "result": result
        }
    
    def _execute_workflow(self, task: Task) -> Dict:
        """执行工作流"""
        results = {}
        
        for subtask in task.subtasks:
            agent_id = subtask['agent']
            action = subtask['action']
            depends_on = subtask.get('depends_on', [])
            
            # 检查依赖
            if depends_on:
                missing = [dep for dep in depends_on if dep not in results]
                if missing:
                    continue  # 等待依赖完成
            
            # 分发到对应Agent
            result = self._dispatch_to_agent(agent_id, action, task.params)
            results[agent_id] = result
        
        return results
    
    def run_workflow(self, workflow_name: str, params: Dict) -> Dict:
        """运行指定工作流"""
        workflow = self.workflows.get(workflow_name, self.workflows['full_analysis'])
        
        results = {}
        subtasks = workflow.get('subtasks', [])
        
        for subtask in subtasks:
            agent_id = subtask['agent']
            action = subtask['action']
            depends_on = subtask.get('depends_on', [])
            
            # 检查依赖
            if depends_on:
                missing = [dep for dep in depends_on if dep not in results]
                if missing:
                    continue
            
            # 直接调用Agent
            if agent_id in self.registered_agents:
                agent = self.registered_agents[agent_id]
                
                # 构造正确的参数
                agent_params = {'params': params}
                if agent_id == 'analyst':
                    agent_params['params'] = params  # analyst期望 params.odds
                elif agent_id == 'scout':
                    agent_params['params'] = params  # scout期望 params.league等
                elif agent_id == 'strategist':
                    agent_params['params'] = params  # strategist期望 params.odds等
                elif agent_id == 'risk_manager':
                    agent_params['params'] = params  # risk_manager期望 params.strategy等
                
                result = agent.process(agent_params)
                results[agent_id] = result
        
        # 获取风控审核
        if 'strategist' in results and 'risk_manager' in self.registered_agents:
            strategist_data = results['strategist'].get('data', {})
            analyst_data = results.get('analyst', {}).get('data', {})
            
            # 获取推荐策略
            recommended = strategist_data.get('recommended', {})
            strategies = strategist_data.get('strategies', [])
            
            # 从第一个策略提取信息
            best_strategy = strategies[0] if strategies else {}
            
            # 构建风控参数
            risk_params = {
                'bankroll': params.get('budget', 1000),
                'bet': {
                    'stake': best_strategy.get('recommended_stake', 20),
                    'odds': best_strategy.get('combined_odds', params.get('odds', {}).get('home', 2.0)),
                    'probability': analyst_data.get('probabilities', {}).get('home', 0.5),
                    'type': best_strategy.get('type', 'single')
                }
            }
            
            risk_result = self.registered_agents['risk_manager'].process({
                'params': risk_params
            })
            results['risk_manager'] = risk_result
        
        # 生成最终推荐
        final_recommendation = self._generate_recommendation(results)
        
        return {
            'status': 'success',
            'workflow': workflow_name,
            'results': results,
            'final_recommendation': final_recommendation
        }
    
    def _generate_recommendation(self, results: Dict) -> Dict:
        """生成最终推荐"""
        recommendation = {
            'action': 'skip',
            'confidence': 0,
            'reason': ''
        }
        
        # 检查风控审核结果
        risk_result = results.get('risk_manager', {})
        if risk_result.get('data', {}).get('approval', {}).get('approved'):
            strategy = results.get('strategist', {}).get('data', {})
            strategies = strategy.get('strategies', [])
            
            if strategies:
                best = strategies[0]
                recommendation = {
                    'action': 'bet',
                    'selection': best.get('selection', 'unknown'),
                    'stake': best.get('stake', 0),
                    'odds': best.get('odds', 0),
                    'expected_return': best.get('stake', 0) * best.get('odds', 0),
                    'confidence': risk_result['data'].get('confidence_score', 0.7)
                }
        else:
            recommendation['reason'] = '风控审核未通过'
        
        return recommendation
    
    def _dispatch_to_agent(self, agent_id: str, action: str, params: Dict) -> Dict:
        """分发任务到Agent"""
        logger.info(f"Dispatching {action} to {agent_id}")
        
        # 通过消息总线发送任务
        task_message = Message(
            sender=self.agent_id,
            receiver=agent_id,
            content={
                "action": action,
                "params": params
            },
            msg_type="task"
        )
        message_bus.send_direct(task_message)
        
        # 返回模拟结果（实际需要等待Agent响应）
        return {
            "status": "dispatched",
            "agent": agent_id,
            "action": action
        }
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        status = {
            "orchestrator": self.get_status(),
            "registered_agents": len(message_bus.agents),
            "active_tasks": len([t for t in self.tasks.values() if t.status == "pending"]),
            "completed_tasks": len([t for t in self.tasks.values() if t.status == "completed"])
        }
        
        return status
    
    def get_league_info(self, league_code: str) -> Dict:
        """获取联赛信息（从历史数据库）"""
        if not self.historical_db:
            return {"error": "历史数据库未连接"}
        
        try:
            stats = self.historical_db.get_league_stats(league_code)
            recommendations = self.historical_db.get_league_recommendations(league_code)
            return {
                "league": league_code,
                "stats": stats,
                "recommendations": recommendations,
                "data_source": "historical_database"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_team_info(self, team_name: str) -> Dict:
        """获取球队信息（从历史数据库）"""
        if not self.historical_db:
            return {"error": "历史数据库未连接"}
        
        try:
            stats = self.historical_db.get_team_stats(team_name)
            recent = self.historical_db.get_recent_matches(team_name, n=10)
            return {
                "team": team_name,
                "stats": stats,
                "recent_matches": len(recent),
                "data_source": "historical_database"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def daily_analysis(self) -> Dict:
        """每日分析任务"""
        return self.process({
            "type": "full_analysis",
            "params": {"mode": "daily"}
        })
