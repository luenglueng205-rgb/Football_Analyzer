# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - CrewAI 现代化框架集成

集成 CrewAI 框架，提供:
- Crew 多Agent协作
- Process 流程编排
- Task 任务定义
- Agent 角色定义

注意: 需要安装 crewai
pip install crewai crewai-tools
"""

import os
import sys
import json
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass

# 尝试导入 crewai，如果不可用则使用兼容实现
try:
    from crewai import Agent, Crew, Task, Process
    from crewai_tools import SerpDevTool, FileReadTool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    print("CrewAI not installed. Using compatible implementation.")


class BettingProcess(Enum):
    """投注分析流程"""
    HIERARCHICAL = "hierarchical"    # 层级流程
    PARALLEL = "parallel"             # 并行流程
    CONSENSUS = "consensus"           # 共识流程


@dataclass
class AgentConfig:
    """Agent配置"""
    role: str
    goal: str
    backstory: str
    verbose: bool = True
    allow_delegation: bool = False


@dataclass 
class TaskConfig:
    """任务配置"""
    description: str
    expected_output: str
    agent_role: str


class CrewAIIntegration:
    """
    CrewAI 集成模块
    
    提供与 CrewAI 框架的对接能力
    """
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.tasks: List[Any] = []
        self._available_tools: List[Any] = []
        
        if CREWAI_AVAILABLE:
            self._setup_tools()
    
    def _setup_tools(self):
        """设置可用工具"""
        if not CREWAI_AVAILABLE:
            return
        
        # 基础工具
        # self._available_tools = [
        #     SerpDevTool(api_key=os.getenv("SERP_API_KEY")),
        #     FileReadTool()
        # ]
    
    def create_agent(self, name: str, config: AgentConfig) -> Any:
        """创建Agent"""
        if CREWAI_AVAILABLE:
            return Agent(
                role=config.role,
                goal=config.goal,
                backstory=config.backstory,
                verbose=config.verbose,
                allow_delegation=config.allow_delegation,
                tools=self._available_tools
            )
        else:
            # 兼容实现
            return {
                "name": name,
                "role": config.role,
                "goal": config.goal,
                "backstory": config.backstory
            }
    
    def create_task(self, description: str, 
                   expected_output: str,
                   agent_name: str) -> Any:
        """创建任务"""
        if CREWAI_AVAILABLE:
            agent = self.agents.get(agent_name)
            if not agent:
                raise ValueError(f"Agent {agent_name} not found")
            
            return Task(
                description=description,
                expected_output=expected_output,
                agent=agent
            )
        else:
            return {
                "description": description,
                "expected_output": expected_output,
                "agent": agent_name
            }
    
    def create_crew(self, agents: List[Any], 
                    tasks: List[Any],
                    process: BettingProcess = BettingProcess.HIERARCHICAL) -> Any:
        """创建Crew"""
        if CREWAI_AVAILABLE:
            crew_process = Process.HIERARCHICAL if process == BettingProcess.HIERARCHICAL else Process.PARALLEL
            
            return Crew(
                agents=agents,
                tasks=tasks,
                process=crew_process,
                verbose=True
            )
        else:
            return {
                "agents": [a if isinstance(a, dict) else {"name": name} 
                          for name, a in self.agents.items()],
                "tasks": tasks,
                "process": process.value
            }
    
    def run(self, crew: Any, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """运行Crew"""
        if CREWAI_AVAILABLE:
            result = crew.kickoff(inputs=inputs)
            return {
                "success": True,
                "result": str(result),
                "raw_result": result
            }
        else:
            return {
                "success": True,
                "message": "CrewAI not available, simulated run"
            }


class FootballCrewFactory:
    """
    足球分析Crew工厂
    
    预定义的Agent和Task配置
    """
    
    def __init__(self):
        self.integration = CrewAIIntegration()
    
    def create_scout_agent(self) -> Any:
        """创建情报Agent"""
        config = AgentConfig(
            role="情报分析专家",
            goal="搜集并分析球队情报，提供准确的数据支持",
            backstory="""你是一位经验丰富的足球情报分析专家。
            擅长从多个渠道搜集球队信息，包括:
            - 球队最新新闻和动态
            - 首发阵容和伤病情况
            - 历史对战记录
            - 近期表现趋势
            - 天气和场地因素
            
            你的分析总是客观、数据驱动，为投注决策提供坚实基础。""",
            verbose=True,
            allow_delegation=False
        )
        return self.integration.create_agent("scout", config)
    
    def create_analyst_agent(self) -> Any:
        """创建赔率分析Agent"""
        config = AgentConfig(
            role="赔率分析专家",
            goal="分析赔率变化，识别价值投注机会",
            backstory="""你是一位资深的足球赔率分析专家。
            精通各种赔率分析技术:
            - 亚盘、欧赔、初盘、终盘分析
            - 赔率异常检测
            - 市场资金流向分析
            - 盘口解读与水位分析
            - 期望值(EV)计算
            
            你能够从复杂的赔率数据中发现隐藏的价值机会。""",
            verbose=True,
            allow_delegation=False
        )
        return self.integration.create_agent("analyst", config)
    
    def create_strategist_agent(self) -> Any:
        """创建策略制定Agent"""
        config = AgentConfig(
            role="投注策略专家",
            goal="制定科学的投注策略，优化资金分配",
            backstory="""你是一位专业的投注策略专家。
            擅长制定各种投注方案:
            - M串N串关策略优化
            - 资金管理与分配
            - Kelly公式应用
            - 风险收益平衡分析
            - 多方案对比选优
            
            你的策略总是兼顾收益与风险，追求长期稳定回报。""",
            verbose=True,
            allow_delegation=True
        )
        return self.integration.create_agent("strategist", config)
    
    def create_risk_manager_agent(self) -> Any:
        """创建风控Agent"""
        config = AgentConfig(
            role="风险管理专家",
            goal="全面审核投注方案，控制风险敞口",
            backstory="""你是一位严格的风险管理专家。
            你的职责是确保每一笔投注都在可控风险范围内:
            - 每日投注限额检查
            - 单场投注上限审核
            - 资金曲线监控
            - 连输熔断机制
            - 异常投注识别
            
            你是球队最后一道防线，确保系统长期稳定运行。""",
            verbose=True,
            allow_delegation=False
        )
        return self.integration.create_agent("risk_manager", config)
    
    def create_full_analysis_crew(self, match_info: Dict) -> Any:
        """创建完整分析Crew"""
        # 创建Agent
        scout = self.create_scout_agent()
        analyst = self.create_analyst_agent()
        strategist = self.create_strategist_agent()
        risk_manager = self.create_risk_manager_agent()
        
        self.integration.agents["scout"] = scout
        self.integration.agents["analyst"] = analyst
        self.integration.agents["strategist"] = strategist
        self.integration.agents["risk_manager"] = risk_manager
        
        # 创建Task
        tasks = []
        
        # 情报搜集任务
        tasks.append(self.integration.create_task(
            description=f"""搜集 {match_info.get('home_team', '主队')} vs {match_info.get('away_team', '客队')} 的情报:
            1. 球队最新新闻和伤停信息
            2. 双方历史对战记录(近10场)
            3. 双方近期状态和表现趋势
            4. 首发阵容预测
            
            联赛: {match_info.get('league', '未知')}
            """,
            expected_output="详细的情报报告，包含数据和分析",
            agent_name="scout"
        ))
        
        # 赔率分析任务
        tasks.append(self.integration.create_task(
            description=f"""基于情报报告和赔率数据进行分析:
            1. 分析当前赔率结构
            2. 识别赔率异常和价值点
            3. 计算各选项期望值
            4. 评估市场情绪
            
            赔率: {json.dumps(match_info.get('odds', {}), ensure_ascii=False)}
            """,
            expected_output="赔率分析报告，包含价值投注建议",
            agent_name="analyst"
        ))
        
        # 策略制定任务
        tasks.append(self.integration.create_task(
            description=f"""基于分析结果制定投注策略:
            1. 推荐投注选项和金额
            2. 设计串关方案(如适用)
            3. 设定止损和止盈点
            
            可用预算: {match_info.get('budget', 100)}元
            """,
            expected_output="具体可执行的投注方案",
            agent_name="strategist"
        ))
        
        # 风控审核任务
        tasks.append(self.integration.create_task(
            description="""审核投注策略是否符合风控要求:
            1. 检查是否超出每日限额
            2. 评估风险收益比
            3. 给出最终审核意见
            """,
            expected_output="风控审核报告，通过/拒绝/修改意见",
            agent_name="risk_manager"
        ))
        
        # 创建Crew
        return self.integration.create_crew(
            agents=[scout, analyst, strategist, risk_manager],
            tasks=tasks,
            process=BettingProcess.HIERARCHICAL
        )
    
    def run_full_analysis(self, match_info: Dict) -> Dict[str, Any]:
        """运行完整分析"""
        crew = self.create_full_analysis_crew(match_info)
        return self.integration.run(crew, match_info)


# 便捷函数
def create_football_crew(match_info: Dict) -> Dict[str, Any]:
    """创建足球分析Crew"""
    factory = FootballCrewFactory()
    return factory.create_full_analysis_crew(match_info)


def run_analysis(match_info: Dict) -> Dict[str, Any]:
    """运行完整分析"""
    factory = FootballCrewFactory()
    return factory.run_full_analysis(match_info)


if __name__ == "__main__":
    # 测试CrewAI集成
    match_info = {
        "league": "英超",
        "home_team": "曼联",
        "away_team": "利物浦",
        "odds": {"home": 2.1, "draw": 3.4, "away": 3.5},
        "budget": 100
    }
    
    if CREWAI_AVAILABLE:
        print("Running with CrewAI...")
        result = run_analysis(match_info)
        print(f"Result: {result}")
    else:
        print("CrewAI not available. Using compatible mode.")
        factory = FootballCrewFactory()
        
        # 创建测试Crew
        crew = factory.create_full_analysis_crew(match_info)
        print(f"Crew created: {json.dumps(crew, indent=2, ensure_ascii=False, default=str)}")
