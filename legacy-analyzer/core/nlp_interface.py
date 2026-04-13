#!/usr/bin/env python3
"""
NLP接口模块 - 中文自然语言查询解析与结果转换
支持自然语言查询转换为结构化命令，结果转换为自然语言输出
"""

import os
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParsedQuery:
    """解析后的查询结构"""
    action: str              # 操作类型
    subject: str            # 查询主体
    filters: Dict[str, Any] = field(default_factory=dict)  # 过滤条件
    parameters: Dict[str, Any] = field(default_factory=dict)  # 参数
    raw_text: str = ""      # 原始文本


@dataclass
class NaturalLanguageResult:
    """自然语言转换结果"""
    summary: str           # 简短摘要
    details: List[str] = field(default_factory=list)  # 详细信息列表
    data: Any = None        # 结构化数据
    suggestions: List[str] = field(default_factory=list)  # 建议


class NLPInterface:
    """
    NLP接口类
    负责中文自然语言查询解析和结果转换
    """

    def __init__(self, base_dir: str = None):
        """
        初始化NLP接口
        
        Args:
            base_dir: 基础目录路径
        """
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir
        
        # 查询动作映射
        self.action_mapping = self._init_action_mapping()
        
        # 查询主体映射
        self.subject_mapping = self._init_subject_mapping()
        
        # 动作同义词词典
        self.action_synonyms = self._init_action_synonyms()
        
        logger.info("NLP接口初始化完成")

    def _init_action_mapping(self) -> Dict[str, List[str]]:
        """初始化动作映射"""
        return {
            'analyze': ['分析', '看看', '查看', '了解一下'],
            'recommend': ['推荐', '建议', '选', '挑'],
            'compare': ['对比', '比较', '区别', '不同'],
            'calculate': ['计算', '算', '多少钱', '收益'],
            'query': ['查询', '搜索', '找', '有没有'],
            'report': ['报告', '总结', '汇总'],
            'strategy': ['策略', '方案', '怎么投']
        }

    def _init_subject_mapping(self) -> Dict[str, List[str]]:
        """初始化查询主体映射"""
        return {
            'matches': ['比赛', '赛事', '球赛', '赛事'],
            'bets': ['投注', '下注', '买', '竞猜'],
            'leagues': ['联赛', '联赛数据'],
            'odds': ['赔率', '指数', '水位'],
            'history': ['历史', '记录', '战绩'],
            'wallet': ['钱包', '余额', '资金'],
            'portfolio': ['组合', '方案', '串关']
        }

    def _init_action_synonyms(self) -> Dict[str, str]:
        """初始化动作同义词（归一化到标准动作）"""
        return {
            # analyze
            '分析': 'analyze',
            '看看': 'analyze',
            '查看': 'analyze',
            '了解一下': 'analyze',
            '看一下': 'analyze',
            '查': 'analyze',
            
            # recommend
            '推荐': 'recommend',
            '建议': 'recommend',
            '选': 'recommend',
            '挑': 'recommend',
            '给': 'recommend',
            
            # compare
            '对比': 'compare',
            '比较': 'compare',
            '区别': 'compare',
            '不同': 'compare',
            
            # calculate
            '计算': 'calculate',
            '算': 'calculate',
            '多少钱': 'calculate',
            '收益': 'calculate',
            '能赚': 'calculate',
            
            # query
            '查询': 'query',
            '搜索': 'query',
            '找': 'query',
            '有没有': 'query',
            '哪些': 'query',
            
            # report
            '报告': 'report',
            '总结': 'report',
            '汇总': 'report',
            
            # strategy
            '策略': 'strategy',
            '方案': 'strategy',
            '怎么投': 'strategy'
        }

    def parse(self, text: str) -> ParsedQuery:
        """
        解析自然语言查询
        
        Args:
            text: 用户输入的自然语言文本
            
        Returns:
            ParsedQuery: 解析后的查询结构
        """
        text = text.strip()
        
        # 1. 提取动作
        action = self._extract_action(text)
        
        # 2. 提取主体
        subject = self._extract_subject(text)
        
        # 3. 提取过滤器
        filters = self._extract_filters(text)
        
        # 4. 提取参数
        parameters = self._extract_parameters(text, action, subject)
        
        return ParsedQuery(
            action=action,
            subject=subject,
            filters=filters,
            parameters=parameters,
            raw_text=text
        )

    def _extract_action(self, text: str) -> str:
        """提取动作类型"""
        # 按动作同义词长度降序排列，优先匹配长词
        sorted_actions = sorted(
            self.action_synonyms.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )
        
        for synonym, action in sorted_actions:
            if synonym in text:
                return action
        return 'query'  # 默认动作

    def _extract_subject(self, text: str) -> str:
        """提取查询主体"""
        for subject, keywords in self.subject_mapping.items():
            for keyword in keywords:
                if keyword in text:
                    return subject
        return 'matches'  # 默认主体

    def _extract_filters(self, text: str) -> Dict[str, Any]:
        """提取过滤条件"""
        filters = {}
        
        # 时间过滤
        time_filter = self._extract_time_filter(text)
        if time_filter:
            filters['time'] = time_filter
            
        # 彩票类型过滤
        lottery_filter = self._extract_lottery_filter(text)
        if lottery_filter:
            filters['lottery_type'] = lottery_filter
            
        # 联赛过滤
        league_filter = self._extract_league_filter(text)
        if league_filter:
            filters['leagues'] = league_filter
            
        # 风险级别
        risk_filter = self._extract_risk_filter(text)
        if risk_filter:
            filters['risk_level'] = risk_filter
            
        # 赔率范围
        odds_filter = self._extract_odds_filter(text)
        if odds_filter:
            filters['odds_range'] = odds_filter
            
        return filters

    def _extract_time_filter(self, text: str) -> Optional[str]:
        """提取时间过滤"""
        time_patterns = [
            (r'(今晚|今天晚上|今夜)', 'tonight'),
            (r'(今天|今日|本日)', 'today'),
            (r'(明天|明日)', 'tomorrow'),
            (r'(后天)', 'day_after_tomorrow'),
            (r'(本周|这周|这星期)', 'this_week'),
            (r'(周末|周六周日)', 'weekend'),
            (r'(本月|这个月)', 'this_month'),
        ]
        
        for pattern, time_value in time_patterns:
            if re.search(pattern, text):
                return time_value
        return None

    def _extract_lottery_filter(self, text: str) -> Optional[str]:
        """提取彩票类型过滤"""
        lottery_patterns = [
            (r'竞彩足球?', 'jingcai'),
            (r'竞彩', 'jingcai'),
            (r'北京单场?|北单', 'beijing'),
            (r'传统足彩|14场|任9|任选九', 'traditional'),
        ]
        
        for pattern, lottery_value in lottery_patterns:
            if re.search(pattern, text):
                return lottery_value
        return None

    def _extract_league_filter(self, text: str) -> List[str]:
        """提取联赛过滤"""
        league_patterns = {
            '英超': [r'英超', r'英格兰.*联赛'],
            '德甲': [r'德甲', r'德国.*联赛'],
            '意甲': [r'意甲', r'意大利.*联赛'],
            '西甲': [r'西甲', r'西班牙.*联赛'],
            '法甲': [r'法甲', r'法国.*联赛'],
            '中超': [r'中超', r'中国.*联赛'],
            'J联赛': [r'J联赛', r'日职', r'日职联'],
            'K联赛': [r'K联赛', r'韩职'],
            '澳超': [r'澳超', r'A联赛'],
            '欧冠': [r'欧冠', r'欧洲冠军'],
            '欧联': [r'欧联', r'欧罗巴'],
            '世界杯': [r'世界杯'],
        }
        
        found = []
        for league, patterns in league_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    found.append(league)
                    break
        return found

    def _extract_risk_filter(self, text: str) -> Optional[str]:
        """提取风险级别"""
        risk_patterns = [
            (r'低风险|稳健|保守|安全', 'low'),
            (r'中风险|平衡|中等', 'medium'),
            (r'高风险|激进|博冷', 'high'),
        ]
        
        for pattern, risk_value in risk_patterns:
            if re.search(pattern, text):
                return risk_value
        return None

    def _extract_odds_filter(self, text: str) -> Optional[Tuple[float, float]]:
        """提取赔率范围"""
        # 匹配 "赔率1.5-2.0" 或 "1.5以上" 等模式
        range_pattern = r'赔率?(\d+\.?\d*)\s*[-~至]\s*(\d+\.?\d*)'
        match = re.search(range_pattern, text)
        if match:
            return (float(match.group(1)), float(match.group(2)))
            
        # 匹配 "以上" 模式
        above_pattern = r'赔率?(\d+\.?\d*)\s*(以上|以上)'
        match = re.search(above_pattern, text)
        if match:
            return (float(match.group(1)), 10.0)
            
        # 匹配 "以下" 模式
        below_pattern = r'赔率?(\d+\.?\d*)\s*(以下|以内)'
        match = re.search(below_pattern, text)
        if match:
            return (0.0, float(match.group(1)))
            
        return None

    def _extract_parameters(self, text: str, action: str, subject: str) -> Dict[str, Any]:
        """提取参数"""
        params = {}
        
        # 串关参数
        if '串' in text:
            parlay_match = re.search(r'(\d+)串(\d+)', text)
            if parlay_match:
                params['parlay_m'] = int(parlay_match.group(1))
                params['parlay_n'] = int(parlay_match.group(2))
            else:
                simple_match = re.search(r'(\d+)串', text)
                if simple_match:
                    params['parlay_n'] = int(simple_match.group(1))
                    
        # 预算参数
        budget_match = re.search(r'(\d+)\s*(元|块|块钱)', text)
        if budget_match:
            params['budget'] = int(budget_match.group(1))
            
        # 数量参数
        count_match = re.search(r'(\d+)\s*(场|场次|注)', text)
        if count_match:
            params['count'] = int(count_match.group(1))
            
        # 胆码参数（用于传统足彩）
        if '胆' in text:
            dan_match = re.search(r'(\d+)\s*胆', text)
            if dan_match:
                params['dan_count'] = int(dan_match.group(1))
                
        return params

    def to_natural_language(self, data: Any, template: str = None) -> NaturalLanguageResult:
        """
        将结构化数据转换为自然语言
        
        Args:
            data: 结构化数据
            template: 可选的模板类型
            
        Returns:
            NaturalLanguageResult: 自然语言结果
        """
        if isinstance(data, dict):
            return self._dict_to_nl(data, template)
        elif isinstance(data, list):
            return self._list_to_nl(data, template)
        elif isinstance(data, str):
            return NaturalLanguageResult(summary=data)
        else:
            return NaturalLanguageResult(summary=str(data))

    def _dict_to_nl(self, data: Dict, template: str = None) -> NaturalLanguageResult:
        """将字典数据转换为自然语言"""
        # 根据数据结构选择不同的转换模板
        if template == 'match_analysis':
            return self._match_analysis_to_nl(data)
        elif template == 'bet_recommendation':
            return self._bet_recommendation_to_nl(data)
        elif template == 'parlay':
            return self._parlay_to_nl(data)
        elif template == 'league':
            return self._league_to_nl(data)
        elif template == 'comparison':
            return self._comparison_to_nl(data)
        else:
            return self._generic_dict_to_nl(data)

    def _match_analysis_to_nl(self, data: Dict) -> NaturalLanguageResult:
        """比赛分析结果转自然语言"""
        summary_parts = []
        details = []
        
        if 'home_team' in data and 'away_team' in data:
            summary_parts.append(f"{data['home_team']} vs {data['away_team']}")
            
        if 'recommended_odds' in data:
            summary_parts.append(f"推荐赔率: {data['recommended_odds']}")
            
        if 'win_probability' in data:
            prob = data['win_probability']
            prob_pct = prob * 100 if prob <= 1 else prob
            summary_parts.append(f"胜率估计: {prob_pct:.1f}%")
            
        if 'analysis' in data:
            details.append(f"分析: {data['analysis']}")
            
        if 'factors' in data:
            details.append("关键因素:")
            for factor in data['factors']:
                details.append(f"  • {factor}")
                
        return NaturalLanguageResult(
            summary=" | ".join(summary_parts) if summary_parts else "分析完成",
            details=details,
            data=data
        )

    def _bet_recommendation_to_nl(self, data: Dict) -> NaturalLanguageResult:
        """投注推荐结果转自然语言"""
        summary_parts = []
        details = []
        suggestions = []
        
        if 'recommendations' in data:
            recs = data['recommendations']
            summary_parts.append(f"为您推荐 {len(recs)} 场比赛")
            
            for i, rec in enumerate(recs[:5], 1):
                detail = f"{i}. {rec.get('home', '?')} vs {rec.get('away', '?')}"
                if 'pick' in rec:
                    detail += f" → 推荐 {rec['pick']}"
                if 'odds' in rec:
                    detail += f" (赔率{rec['odds']})"
                details.append(detail)
                
        if 'expected_value' in data:
            ev = data['expected_value']
            summary_parts.append(f"预期价值: {ev:.2f}")
            
        if 'risk_level' in data:
            risk_text = {'low': '低风险', 'medium': '中风险', 'high': '高风险'}
            suggestions.append(f"风险等级: {risk_text.get(data['risk_level'], '未知')}")
            
        return NaturalLanguageResult(
            summary=" ".join(summary_parts),
            details=details,
            data=data,
            suggestions=suggestions
        )

    def _parlay_to_nl(self, data: Dict) -> NaturalLanguageResult:
        """串关方案转自然语言"""
        summary_parts = []
        details = []
        suggestions = []
        
        if 'parlay_type' in data:
            summary_parts.append(f"{data['parlay_type']}串关方案")
            
        if 'total_matches' in data:
            summary_parts.append(f"共 {data['total_matches']} 场比赛")
            
        if 'options' in data:
            details.append("推荐组合:")
            for i, option in enumerate(data['options'][:3], 1):
                matches = option.get('matches', [])
                match_str = " × ".join([m.get('short_name', m.get('name', '?')) for m in matches])
                odds = option.get('total_odds', 0)
                details.append(f"  方案{i}: {match_str}")
                details.append(f"         总赔率: {odds:.2f}")
                
        if 'total_cost' in data:
            details.append(f"投入金额: {data['total_cost']}元")
            
        if 'potential_return' in data:
            details.append(f"最高收益: {data['potential_return']:.2f}元")
            
        return NaturalLanguageResult(
            summary=" ".join(summary_parts),
            details=details,
            data=data,
            suggestions=suggestions
        )

    def _league_to_nl(self, data: Dict) -> NaturalLanguageResult:
        """联赛数据转自然语言"""
        summary_parts = []
        details = []
        
        if 'name' in data:
            summary_parts.append(f"{data['name']}联赛")
            
        if 'total_teams' in data:
            summary_parts.append(f"共 {data['total_teams']} 支球队")
            
        if 'total_matches' in data:
            details.append(f"总比赛场次: {data['total_matches']}")
            
        if 'top_teams' in data:
            details.append(f"劲旅: {', '.join(data['top_teams'][:5])}")
            
        if 'recent_form' in data:
            details.append(f"近期状态: {data['recent_form']}")
            
        return NaturalLanguageResult(
            summary=" ".join(summary_parts),
            details=details,
            data=data
        )

    def _comparison_to_nl(self, data: Dict) -> NaturalLanguageResult:
        """对比结果转自然语言"""
        summary_parts = []
        details = []
        
        summary_parts.append("彩票类型对比结果")
        
        if isinstance(data, dict):
            for key, value in data.items():
                details.append(f"\n【{key}】")
                if isinstance(value, dict):
                    if 'pros' in value:
                        details.append(f"  优点: {', '.join(value['pros'][:3])}")
                    if 'cons' in value:
                        details.append(f"  缺点: {', '.join(value['cons'][:2])}")
                    if 'difficulty' in value:
                        details.append(f"  难度: {value['difficulty']}")
                    if 'recommended_for' in value:
                        details.append(f"  适合: {value['recommended_for']}")
                        
        return NaturalLanguageResult(
            summary=" ".join(summary_parts),
            details=details,
            data=data
        )

    def _generic_dict_to_nl(self, data: Dict) -> NaturalLanguageResult:
        """通用字典转自然语言"""
        details = []
        for key, value in data.items():
            if isinstance(value, (str, int, float, bool)):
                details.append(f"{key}: {value}")
            elif isinstance(value, list) and len(value) <= 5:
                details.append(f"{key}: {', '.join(str(v) for v in value)}")
                
        return NaturalLanguageResult(
            summary="查询结果",
            details=details,
            data=data
        )

    def _list_to_nl(self, data: List, template: str = None) -> NaturalLanguageResult:
        """列表数据转自然语言"""
        details = []
        for i, item in enumerate(data[:10], 1):
            if isinstance(item, dict):
                # 取第一个有意义的字段作为描述
                desc = item.get('name', item.get('title', item.get('home_team', f'项目{i}')))
                details.append(f"{i}. {desc}")
            else:
                details.append(f"{i}. {item}")
                
        total = len(data)
        summary = f"共找到 {total} 个结果"
        if total > 10:
            summary += f"，显示前10条"
            
        return NaturalLanguageResult(
            summary=summary,
            details=details,
            data=data
        )

    def format_response(self, result: NaturalLanguageResult) -> str:
        """
        格式化自然语言响应
        
        Args:
            result: 自然语言结果
            
        Returns:
            str: 格式化后的响应文本
        """
        lines = []
        
        # 摘要
        if result.summary:
            lines.append(result.summary)
            
        # 详细信息
        if result.details:
            lines.append("")
            lines.extend(result.details)
            
        # 建议
        if result.suggestions:
            lines.append("")
            lines.append("💡 建议:")
            for suggestion in result.suggestions:
                lines.append(f"   {suggestion}")
                
        return "\n".join(lines)

    def build_command(self, parsed_query: ParsedQuery) -> Dict[str, Any]:
        """
        将解析后的查询构建为系统命令
        
        Args:
            parsed_query: 解析后的查询
            
        Returns:
            Dict: 系统命令
        """
        command = {
            'action': parsed_query.action,
            'subject': parsed_query.subject,
            'filters': parsed_query.filters,
            'parameters': parsed_query.parameters,
            'timestamp': datetime.now().isoformat()
        }
        
        # 根据动作和主体构建具体的命令
        if parsed_query.action == 'analyze' and parsed_query.subject == 'matches':
            command['method'] = 'analyze_matches'
        elif parsed_query.action == 'recommend' and parsed_query.subject == 'bets':
            command['method'] = 'recommend_bets'
        elif parsed_query.action == 'strategy' and parsed_query.subject == 'portfolio':
            command['method'] = 'generate_parlay'
        elif parsed_query.action == 'query' and parsed_query.subject == 'leagues':
            command['method'] = 'query_leagues'
        elif parsed_query.action == 'compare':
            command['method'] = 'compare_types'
            
        return command


def demo():
    """演示函数"""
    print("=" * 60)
    print("NLP接口演示")
    print("=" * 60)
    
    nlp = NLPInterface()
    
    # 测试查询解析
    test_queries = [
        "分析今晚英超的比赛",
        "推荐几场高胜率的投注",
        "帮我看看2串1方案，预算100元",
        "竞彩足球有哪些稳胆",
        "对比三种彩票类型的区别",
        "低风险投资有什么建议",
        "查询英超联赛数据",
        "计算一下3串3能赚多少钱"
    ]
    
    print("\n" + "-" * 60)
    print("查询解析测试")
    print("-" * 60)
    
    for query in test_queries:
        parsed = nlp.parse(query)
        print(f"\n原始: {query}")
        print(f"动作: {parsed.action}")
        print(f"主体: {parsed.subject}")
        print(f"过滤: {parsed.filters}")
        print(f"参数: {parsed.parameters}")
        
        # 构建命令
        cmd = nlp.build_command(parsed)
        print(f"命令: {cmd['method']}")
        
    print("\n" + "-" * 60)
    print("自然语言生成测试")
    print("-" * 60)
    
    # 测试结果转换
    sample_data = {
        'home_team': '曼联',
        'away_team': '利物浦',
        'recommended_odds': 1.85,
        'win_probability': 0.65,
        'analysis': '主队近期状态良好',
        'factors': ['主场优势', '阵容完整', '战意强烈']
    }
    
    result = nlp.to_natural_language(sample_data, 'match_analysis')
    print(f"\n比赛分析结果:")
    print(nlp.format_response(result))


if __name__ == "__main__":
    demo()
