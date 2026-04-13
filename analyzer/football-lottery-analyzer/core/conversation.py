#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - 对话式交互系统
支持中文自然语言查询，对话上下文管理
"""

import os
import sys
import json
import re
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)


class Intent(Enum):
    """意图类型"""
    GREETING = "greeting"
    ANALYSIS = "analysis"
    RECOMMENDATION = "recommendation"
    QUERY = "query"
    HISTORY = "history"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class ConversationContext:
    """对话上下文"""
    session_id: str
    user_id: Optional[str] = None
    history: List[Dict] = field(default_factory=list)
    current_topic: Optional[str] = None
    preferences: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ParsedQuery:
    """解析后的查询"""
    intent: Intent
    entities: Dict[str, Any]
    original_text: str
    confidence: float = 0.0


class QueryParser:
    """查询解析器"""
    
    # 意图关键词映射
    INTENT_PATTERNS = {
        Intent.GREETING: [r"你好", r"hi|hello|嗨", r"早上好", r"晚上好"],
        Intent.ANALYSIS: [r"分析", r"看看", r"研究"],
        Intent.RECOMMENDATION: [r"推荐", r"建议", r"怎么买", r"投注"],
        Intent.QUERY: [r"查询", r"查看", r"有什么", r"哪些"],
        Intent.HISTORY: [r"历史", r"记录", r"之前", r"上次"],
        Intent.HELP: [r"帮助", r"怎么用", r"使用", r"功能"]
    }
    
    # 联赛名称映射
    LEAGUE_ALIASES = {
        "英超": ["英格兰超级联赛", "epl", "premier league"],
        "西甲": ["西班牙甲级联赛", "laliga", "la liga"],
        "德甲": ["德国甲级联赛", "bundesliga"],
        "意甲": ["意大利甲级联赛", "serie a"],
        "法甲": ["法国甲级联赛", "ligue 1"],
        "中超": ["中国超级联赛", "csl"],
        "欧冠": ["欧洲冠军联赛", "champions league"],
        "世界杯": ["world cup"]
    }
    
    def __init__(self):
        self.compiled_patterns = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            self.compiled_patterns[intent] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    def parse(self, text: str) -> ParsedQuery:
        """解析用户输入"""
        # 识别意图
        intent = self._recognize_intent(text)
        
        # 提取实体
        entities = self._extract_entities(text)
        
        # 计算置信度
        confidence = self._calculate_confidence(intent, entities)
        
        return ParsedQuery(
            intent=intent,
            entities=entities,
            original_text=text,
            confidence=confidence
        )
    
    def _recognize_intent(self, text: str) -> Intent:
        """识别意图"""
        for intent, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    return intent
        return Intent.UNKNOWN
    
    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """提取实体"""
        entities = {}
        
        # 提取联赛
        for league, aliases in self.LEAGUE_ALIASES.items():
            if league in text:
                entities["league"] = league
                break
            for alias in aliases:
                if alias.lower() in text.lower():
                    entities["league"] = league
                    break
        
        # 提取串关类型
        parlay_match = re.search(r"(\d+)串(\d+)", text)
        if parlay_match:
            entities["parlay"] = {"m": int(parlay_match.group(1)), "n": int(parlay_match.group(2))}
        
        # 提取赔率范围
        odds_match = re.search(r"赔率?[\s大于]*([\d.]+)", text)
        if odds_match:
            entities["min_odds"] = float(odds_match.group(1))
        
        # 提取预算
        budget_match = re.search(r"(?:预算|花|投)[^\d]*(\d+)", text)
        if budget_match:
            entities["budget"] = float(budget_match.group(1))
        
        # 提取球队名称（简化版）
        teams = re.findall(r"[\u4e00-\u9fa5a-zA-Z]+(?=队|主场|客场|对阵)", text)
        if teams:
            entities["teams"] = teams[:2]
        
        return entities
    
    def _calculate_confidence(self, intent: Intent, entities: Dict) -> float:
        """计算解析置信度"""
        base = 0.5
        if intent != Intent.UNKNOWN:
            base += 0.3
        if entities:
            base += len(entities) * 0.1
        return min(base, 1.0)


class ConversationManager:
    """对话管理器"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationContext] = {}
        self.query_parser = QueryParser()
        self._response_templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, str]:
        """加载响应模板"""
        return {
            "greeting": "您好！我是足球彩票分析助手。可以帮您：\n- 分析比赛和赔率\n- 推荐价值投注\n- 生成串关方案\n- 查看投注历史",
            "help": "【使用帮助】\n• 分析比赛：'分析今晚的比赛'\n• 推荐投注：'推荐几场价值投注'\n• 串关方案：'生成3串1方案'\n• 查询联赛：'查看英超数据'\n• 历史记录：'查看我的投注历史'"
        }
    
    def create_session(self, session_id: str, user_id: str = None) -> ConversationContext:
        """创建对话会话"""
        context = ConversationContext(
            session_id=session_id,
            user_id=user_id
        )
        self.sessions[session_id] = context
        return context
    
    def get_session(self, session_id: str) -> Optional[ConversationContext]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def process_input(self, session_id: str, user_input: str) -> Dict[str, Any]:
        """处理用户输入"""
        # 获取或创建会话
        context = self.sessions.get(session_id)
        if not context:
            context = self.create_session(session_id)
        
        # 解析查询
        parsed = self.query_parser.parse(user_input)
        
        # 生成响应
        response = self._generate_response(parsed, context)
        
        # 更新历史
        context.history.append({
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "parsed_intent": parsed.intent.value,
            "entities": parsed.entities,
            "response": response
        })
        
        return {
            "session_id": session_id,
            "intent": parsed.intent.value,
            "entities": parsed.entities,
            "response": response,
            "confidence": parsed.confidence
        }
    
    def _generate_response(self, parsed: ParsedQuery, context: ConversationContext) -> str:
        """生成响应"""
        intent = parsed.intent
        entities = parsed.entities
        
        if intent == Intent.GREETING:
            return self._response_templates["greeting"]
        
        if intent == Intent.HELP:
            return self._response_templates["help"]
        
        if intent == Intent.ANALYSIS or intent == Intent.RECOMMENDATION:
            return self._generate_analysis_response(entities)
        
        if intent == Intent.QUERY:
            return self._generate_query_response(entities)
        
        if intent == Intent.HISTORY:
            return self._generate_history_response(context)
        
        # 默认响应
        return f"我理解了您的需求。让我分析一下..."
    
    def _generate_analysis_response(self, entities: Dict) -> str:
        """生成分析响应"""
        league = entities.get("league", "所有联赛")
        parlay = entities.get("parlay")
        
        response = f"好的，正在为您分析{league}的比赛...\n\n"
        
        if parlay:
            response += f"串关方案：{parlay['m']}串{parlay['n']}\n"
        
        # 这里调用实际的分析逻辑
        response += "\n【分析结果】\n"
        response += "• 价值投注：待分析\n"
        response += "• 风险评估：待评估\n"
        response += "• 推荐策略：待生成"
        
        return response
    
    def _generate_query_response(self, entities: Dict) -> str:
        """生成查询响应"""
        league = entities.get("league")
        
        if league:
            return f"查询{league}的数据...\n\n【{league}统计】\n• 数据加载中..."
        
        return "正在查询数据..."
    
    def _generate_history_response(self, context: ConversationContext) -> str:
        """生成历史响应"""
        if not context.history:
            return "暂无投注记录"
        
        recent = context.history[-5:]
        response = f"【最近{len(recent)}条记录】\n"
        
        for i, h in enumerate(recent, 1):
            response += f"{i}. {h.get('user_input', '')[:30]}...\n"
        
        return response


# 全局单例
_conversation_manager: Optional[ConversationManager] = None

def get_conversation_manager() -> ConversationManager:
    """获取对话管理器"""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager


if __name__ == "__main__":
    # 测试对话系统
    manager = get_conversation_manager()
    session_id = "test_session"
    
    # 创建会话
    manager.create_session(session_id)
    
    # 测试对话
    test_inputs = [
        "你好",
        "分析今晚英超的比赛",
        "推荐几场价值投注",
        "生成3串1方案，预算200元",
        "查看我的投注历史"
    ]
    
    print("=" * 50)
    print("足球彩票对话系统测试")
    print("=" * 50)
    
    for text in test_inputs:
        result = manager.process_input(session_id, text)
        print(f"\n【用户】{text}")
        print(f"【意图】{result['intent']} (置信度: {result['confidence']:.2f})")
        print(f"【实体】{result['entities']}")
        print(f"【回复】{result['response']}")
