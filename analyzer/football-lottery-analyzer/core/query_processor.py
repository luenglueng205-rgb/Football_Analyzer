#!/usr/bin/env python3
"""
查询处理器 - 支持多种查询类型并处理查询历史记录
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """查询类型枚举"""
    ANALYZE_MATCHES = "analyze_matches"
    RECOMMEND_BETS = "recommend_bets"
    PARLAY_STRATEGY = "parlay_strategy"
    VIEW_LEAGUE = "view_league"
    VIEW_HISTORY = "view_history"
    COMPARE_TYPES = "compare_types"
    RISK_RECOMMEND = "risk_recommend"
    ODDS_ANALYSIS = "odds_analysis"
    COOL_HOT_ANALYSIS = "cool_hot"
    UNKNOWN = "unknown"


@dataclass
class QueryRecord:
    """查询记录"""
    query_id: str
    session_id: str
    query_type: str
    query_text: str
    timestamp: str
    result_summary: str = ""
    result_data: Dict = field(default_factory=dict)
    feedback: Optional[str] = None


class QueryProcessor:
    """
    查询处理器
    负责处理各类查询、管理查询历史
    """

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, 'data')
        self.history_dir = os.path.join(self.data_dir, 'query_history')
        
        os.makedirs(self.history_dir, exist_ok=True)
        
        self.query_history: List[QueryRecord] = []
        self.query_counter = 0
        self.query_config = self._init_query_config()
        self._load_history()
        
        logger.info("查询处理器初始化完成")

    def _init_query_config(self) -> Dict[str, Dict]:
        """初始化查询配置"""
        return {
            "analyze_matches": {
                "keywords": ["分析", "今晚", "比赛", "今晚比赛", "今日赛事", "今晚赛事"],
                "handler": "handle_analyze_matches",
                "requires_data": True
            },
            "recommend_bets": {
                "keywords": ["推荐", "价值投注", "稳胆", "高胜率", "胜率"],
                "handler": "handle_recommend_bets",
                "requires_data": True
            },
            "parlay_strategy": {
                "keywords": ["串关", "2串1", "3串1", "多串", "过关"],
                "handler": "handle_parlay",
                "requires_data": True
            },
            "view_league": {
                "keywords": ["联赛", "英超", "德甲", "意甲", "西甲", "法甲", "中超"],
                "handler": "handle_view_league",
                "requires_data": True
            },
            "view_history": {
                "keywords": ["历史", "投注记录", "我的记录", "历史记录"],
                "handler": "handle_view_history",
                "requires_data": False
            },
            "compare_types": {
                "keywords": ["对比", "比较", "区别", "哪个好"],
                "handler": "handle_compare",
                "requires_data": False
            },
            "risk_recommend": {
                "keywords": ["风险", "低风险", "高风险", "稳健", "保守"],
                "handler": "handle_risk_recommend",
                "requires_data": False
            },
            "odds_analysis": {
                "keywords": ["赔率", "水位", "盘口"],
                "handler": "handle_odds_analysis",
                "requires_data": True
            },
            "cool_hot": {
                "keywords": ["冷热", "热度", "热门", "冷门"],
                "handler": "handle_cool_hot",
                "requires_data": True
            }
        }

    def _load_history(self):
        """加载历史查询记录"""
        history_file = os.path.join(self.history_dir, 'query_history.json')
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.query_history = [QueryRecord(**r) for r in data]
                    self.query_counter = len(self.query_history)
                logger.info(f"已加载 {len(self.query_history)} 条历史记录")
            except Exception as e:
                logger.warning(f"加载历史记录失败: {e}")

    def _save_history(self):
        """保存查询历史"""
        history_file = os.path.join(self.history_dir, 'query_history.json')
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(r) for r in self.query_history], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存历史记录失败: {e}")

    def identify_query_type(self, query_text: str) -> QueryType:
        """识别查询类型"""
        query_text_lower = query_text.lower()
        
        for qtype, config in self.query_config.items():
            for keyword in config['keywords']:
                if keyword.lower() in query_text_lower:
                    return QueryType(qtype)
                    
        return QueryType.UNKNOWN

    def process(self, session_id: str, query_text: str, 
                parsed_data: Dict = None) -> Dict[str, Any]:
        """处理查询"""
        self.query_counter += 1
        query_id = f"q_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self.query_counter}"
        
        query_type = self.identify_query_type(query_text)
        
        record = QueryRecord(
            query_id=query_id,
            session_id=session_id,
            query_type=query_type.value,
            query_text=query_text,
            timestamp=datetime.now().isoformat()
        )
        
        handler_name = self.query_config.get(query_type.value, {}).get('handler')
        if handler_name and hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            result = handler(query_text, parsed_data)
            record.result_summary = result.get('summary', '')
            record.result_data = result.get('data', {})
        else:
            result = self.handle_unknown(query_text)
            
        self.query_history.append(record)
        self._save_history()
        
        return {
            'query_id': query_id,
            'query_type': query_type.value,
            'query_text': query_text,
            'result': result,
            'record': asdict(record)
        }

    def handle_analyze_matches(self, query_text: str, 
                              parsed_data: Dict = None) -> Dict[str, Any]:
        """处理比赛分析查询"""
        time_ref = "today"
        if "今晚" in query_text or "今夜" in query_text:
            time_ref = "tonight"
        elif "明天" in query_text:
            time_ref = "tomorrow"
        elif "本周" in query_text or "这周" in query_text:
            time_ref = "this_week"
            
        lottery_type = "jingcai"
        if "北单" in query_text:
            lottery_type = "beijing"
        elif "传统" in query_text:
            lottery_type = "traditional"
            
        return {
            'summary': f'正在分析{time_ref}的比赛...',
            'data': {
                'time_reference': time_ref,
                'lottery_type': lottery_type,
                'status': 'processing'
            },
            'suggestions': ['基本面分析', '赔率分析', '盘口分析', '冷热分析']
        }

    def handle_recommend_bets(self, query_text: str,
                             parsed_data: Dict = None) -> Dict[str, Any]:
        """处理投注推荐查询"""
        odds_min = 1.5
        if "高赔" in query_text or "高赔率" in query_text:
            odds_min = 2.0
            
        return {
            'summary': '正在为您筛选价值投注...',
            'data': {
                'filters': {'odds_min': odds_min, 'win_rate_min': 0.6},
                'lottery_type': 'jingcai',
                'status': 'processing'
            },
            'recommendations': []
        }

    def handle_parlay(self, query_text: str,
                     parsed_data: Dict = None) -> Dict[str, Any]:
        """处理串关查询"""
        parlay_match = re.search(r'(\d+)串(\d+)', query_text)
        if parlay_match:
            m, n = int(parlay_match.group(1)), int(parlay_match.group(2))
        else:
            simple_match = re.search(r'(\d+)串', query_text)
            if simple_match:
                n = int(simple_match.group(1))
                m = 1
            else:
                n, m = 2, 1
                
        budget = 100
        budget_match = re.search(r'(\d+)\s*(元|块)', query_text)
        if budget_match:
            budget = int(budget_match.group(1))
            
        return {
            'summary': f'正在为您计算{n}串{m}方案...',
            'data': {'parlay_m': m, 'parlay_n': n, 'budget': budget, 'status': 'processing'},
            'calculations': []
        }

    def handle_view_league(self, query_text: str,
                          parsed_data: Dict = None) -> Dict[str, Any]:
        """处理联赛查询"""
        leagues = []
        league_keywords = {
            '英超': ['英超'], '德甲': ['德甲'], '意甲': ['意甲'],
            '西甲': ['西甲'], '法甲': ['法甲'], '中超': ['中超'],
            'J联赛': ['J联赛', '日职'], 'K联赛': ['K联赛', '韩职']
        }
        
        for league, keywords in league_keywords.items():
            for kw in keywords:
                if kw in query_text:
                    leagues.append(league)
                    break
                    
        if not leagues:
            leagues = ['英超']
            
        return {
            'summary': f'正在查询{", ".join(leagues)}数据...',
            'data': {'leagues': leagues, 'status': 'processing'}
        }

    def handle_view_history(self, query_text: str,
                           parsed_data: Dict = None) -> Dict[str, Any]:
        """处理历史查询"""
        session_history = [asdict(r) for r in self.query_history[-10:]]
        
        return {
            'summary': f'共找到 {len(session_history)} 条历史记录',
            'data': {'total_records': len(self.query_history), 'recent_records': session_history}
        }

    def handle_compare(self, query_text: str,
                      parsed_data: Dict = None) -> Dict[str, Any]:
        """处理对比查询"""
        return {
            'summary': '彩票类型对比',
            'data': {
                '竞彩足球': {'name': '竞彩足球', 'pros': ['固定赔率', '支持混合过关', '最多8关串关'], 
                          'cons': ['需要分析多场比赛'], 'difficulty': '中等'},
                '北京单场': {'name': '北京单场', 'pros': ['单场投注', '最多15关'], 
                          'cons': ['SP值赛后公布'], 'difficulty': '中等'},
                '传统足彩': {'name': '传统足彩', 'pros': ['奖池累积', '支持胆拖复式'], 
                          'cons': ['14场全对难度极大'], 'difficulty': '极高'}
            }
        }

    def handle_risk_recommend(self, query_text: str,
                             parsed_data: Dict = None) -> Dict[str, Any]:
        """处理风险推荐查询"""
        risk_level = "medium"
        if "低" in query_text or "稳健" in query_text or "保守" in query_text:
            risk_level = "low"
        elif "高" in query_text or "激进" in query_text or "博冷" in query_text:
            risk_level = "high"
            
        recommendations = {
            'low': {'lottery': '竞彩足球', 'strategy': '低赔稳胆', 
                   'description': '选择赔率1.3-1.5的主队', 'expected_roi': '~5%'},
            'medium': {'lottery': '竞彩足球 + 北京单场', 'strategy': '混合投注',
                      'description': '竞彩做稳胆 + 北单做博冷', 'expected_roi': '视情况'},
            'high': {'lottery': '传统足彩', 'strategy': '胆拖大包围',
                    'description': '使用复式/胆拖覆盖多场', 'expected_roi': '大奖概率低但奖金高'}
        }
        
        return {
            'summary': f'{risk_level}风险偏好推荐',
            'data': {'risk_level': risk_level, 'recommendation': recommendations.get(risk_level, recommendations['medium'])}
        }

    def handle_odds_analysis(self, query_text: str, parsed_data: Dict = None) -> Dict[str, Any]:
        return {'summary': '正在分析赔率...', 'data': {'analysis_type': 'odds', 'status': 'processing'}}

    def handle_cool_hot(self, query_text: str, parsed_data: Dict = None) -> Dict[str, Any]:
        return {'summary': '正在分析冷热分布...', 'data': {'analysis_type': 'cool_hot', 'status': 'processing'}}

    def handle_unknown(self, query_text: str) -> Dict[str, Any]:
        return {
            'summary': '抱歉，暂时无法理解您的查询',
            'data': {'original_query': query_text},
            'suggestions': ['尝试: "分析今晚的比赛"', '尝试: "推荐价值投注"', 
                          '尝试: "2串1方案"', '输入"帮助"查看所有命令']
        }

    def get_history(self, session_id: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """获取查询历史"""
        history = self.query_history
        
        if session_id:
            history = [r for r in history if r.session_id == session_id]
            
        history = history[-limit:]
        
        return [asdict(r) for r in history]

    def get_statistics(self) -> Dict[str, Any]:
        """获取查询统计"""
        total = len(self.query_history)
        
        type_counts = {}
        for record in self.query_history:
            qt = record.query_type
            type_counts[qt] = type_counts.get(qt, 0) + 1
            
        date_counts = {}
        for record in self.query_history:
            date = record.timestamp.split('T')[0]
            date_counts[date] = date_counts.get(date, 0) + 1
            
        return {
            'total_queries': total,
            'by_type': type_counts,
            'by_date': date_counts,
            'most_common_type': max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else None
        }

    def add_feedback(self, query_id: str, feedback: str) -> bool:
        """添加查询反馈"""
        for record in self.query_history:
            if record.query_id == query_id:
                record.feedback = feedback
                self._save_history()
                return True
        return False


def demo():
    """演示函数"""
    print("=" * 60)
    print("查询处理器演示")
    print("=" * 60)
    
    processor = QueryProcessor()
    
    test_queries = [
        "分析今晚的比赛", "推荐几场价值投注", "帮我看看2串1方案",
        "查看英超联赛数据", "我的投注历史", "对比三种彩票",
        "低风险投资建议", "赔率分析", "冷热分布怎么样"
    ]
    
    print("\n" + "-" * 60)
    print("查询处理测试")
    print("-" * 60)
    
    for query in test_queries:
        result = processor.process("demo_session", query)
        print(f"\n查询: {query}")
        print(f"类型: {result['query_type']}")
        print(f"结果: {result['result']['summary']}")
        
    print("\n" + "-" * 60)
    print("查询统计")
    print("-" * 60)
    stats = processor.get_statistics()
    print(f"总查询数: {stats['total_queries']}")
    print(f"按类型统计: {stats['by_type']}")


if __name__ == "__main__":
    demo()
