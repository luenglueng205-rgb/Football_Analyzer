# -*- coding: utf-8 -*-
"""
足球彩票专业分析统一入口 v3.0 Pro
整合三大玩法（竞彩足球、北京单场、传统足彩）的专业分析模块

v3.0 Pro 升级:
- 集成历史数据库 (221,415条比赛数据)
- 联赛参数基于完整历史数据校准
- 赔率模型基于Bet365等博彩公司数据
"""

import json
import os
import sys
from typing import Dict, List, Optional, Any

# 路径设置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PROJECT_ROOT)
DATA_DIR = os.path.join(BASE_DIR, 'data', 'chinese_mapped')
RULES_DIR = PROJECT_ROOT

# 导入专业模块
sys.path.insert(0, SCRIPT_DIR)

# 尝试导入历史数据库
try:
    sys.path.insert(0, os.path.join(PROJECT_ROOT, 'data'))
    from historical_database import get_historical_database, HistoricalDatabase
    HISTORICAL_DB_AVAILABLE = True
except ImportError as e:
    HISTORICAL_DB_AVAILABLE = False
    HistoricalDatabase = None
    get_historical_database = None
    print(f"Warning: Historical database not available: {e}")

try:
    from jingcai_professional import (
        PoissonGoalPredictor,
        HandicapAnalyzer,
        ParlayOptimizer,
        HalfFullTimePredictor
    )
    from beijing_analyzer_v2 import (
        BeijingSPFOddsAnalyzer,
        BeijingZJQAnalyzer,
        BeijingBFAnalyzer,
        BeijingBQCAnalyzer,
        BeijingSXDAnalyzer,
        BeijingSPValueAnalyzer,
        BeijingParlayOptimizer
    )
    from traditional_professional import (
        Traditional14Analyzer,
        RX9Optimizer,
        SixBQCPredictor,
        FourJQCPredictor,
        PrizePoolAnalyzer
    )
    from cross_play_strategy import (
        CrossPlayAnalyzer,
        ArbitrageDetector,
        IntegratedRecommendationEngine
    )
    PROFESSIONAL_MODULES_LOADED = True
except ImportError as e:
    print(f"Warning: Some professional modules not loaded: {e}")
    PROFESSIONAL_MODULES_LOADED = False


def load_all_data() -> Dict:
    """加载所有数据"""
    data = {}
    
    files = {
        "竞彩足球": "竞彩足球_chinese_data.json",
        "北京单场": "北京单场_chinese_data.json",
        "传统足彩": "传统足彩_chinese_data.json"
    }
    
    for name, filename in files.items():
        filepath = os.path.join(DATA_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data[name] = json.load(f)
    
    return data


def load_rules() -> Dict:
    """加载官方规则"""
    with open(os.path.join(RULES_DIR, 'official_rules.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


class ProfessionalAnalyzer:
    """
    足球彩票专业分析统一入口 v3.0 Pro
    
    支持三大玩法：
    - 竞彩足球
    - 北京单场
    - 传统足彩
    
    提供专业分析：
    - 泊松进球预测 (基于221,415条历史数据)
    - 盘口深度分析
    - 跨玩法协同策略
    - SP值挖掘
    - 奖池分析
    
    v3.0 Pro 升级：
    - 集成历史数据库
    - 联赛参数自动校准
    """
    
    def __init__(self):
        self.data = load_all_data()
        self.rules = load_rules()
        
        # 初始化历史数据库
        self.historical_db = None
        if HISTORICAL_DB_AVAILABLE and get_historical_database:
            try:
                self.historical_db = get_historical_database(lazy_load=False)
                print(f"✅ 历史数据库已加载: {self.historical_db.raw_data.get('metadata', {}).get('total_matches', 0)} 条比赛")
            except Exception as e:
                print(f"⚠️ 历史数据库加载失败: {e}")
        
        self.__init_analyzers()
    
    @property
    def modules_loaded(self) -> bool:
        """检查模块是否加载"""
        return PROFESSIONAL_MODULES_LOADED
    
    @property
    def historical_db_loaded(self) -> bool:
        """检查历史数据库是否加载"""
        return self.historical_db is not None
    
    def get_league_stats(self, league_code: str) -> Dict:
        """获取联赛统计信息"""
        if self.historical_db:
            return self.historical_db.get_league_stats(league_code)
        return {}
    
    def get_league_recommendations(self, league_code: str) -> List[str]:
        """获取联赛推荐玩法"""
        if self.historical_db:
            return self.historical_db.get_league_recommendations(league_code)
        return []
    
    def __init_analyzers(self):
        """初始化所有分析器"""
        if not PROFESSIONAL_MODULES_LOADED:
            print("Warning: Professional modules not fully loaded")
            return
        
        # 竞彩足球分析器 (传入历史数据库支持)
        self.jingcai_poisson = PoissonGoalPredictor(
            self.data.get("竞彩足球", {}),
            use_historical=self.historical_db is not None
        )
        self.jingcai_handicap = HandicapAnalyzer(self.data.get("竞彩足球", {}))
        self.jingcai_parlay = ParlayOptimizer(self.data.get("竞彩足球", {}))
        self.jingcai_bqc = HalfFullTimePredictor(self.data.get("竞彩足球", {}))
        
        # 北京单场分析器
        beijing_data = self.data.get("北京单场", {})
        self.beijing_spf = BeijingSPFOddsAnalyzer(beijing_data)
        self.beijing_zjq = BeijingZJQAnalyzer(beijing_data)
        self.beijing_bf = BeijingBFAnalyzer(beijing_data)
        self.beijing_bqc = BeijingBQCAnalyzer(beijing_data)
        self.beijing_sxd = BeijingSXDAnalyzer(beijing_data)
        self.beijing_sp = BeijingSPValueAnalyzer(beijing_data)
        self.beijing_parlay = BeijingParlayOptimizer(beijing_data)
        
        # 传统足彩分析器
        traditional_data = self.data.get("传统足彩", {})
        self.traditional_14 = Traditional14Analyzer(traditional_data)
        self.rx9 = RX9Optimizer(traditional_data)
        self.bqc6 = SixBQCPredictor(traditional_data)
        self.jqc4 = FourJQCPredictor(traditional_data)
        self.prize_pool = PrizePoolAnalyzer()
        
        # 跨玩法分析器
        self.cross_play = CrossPlayAnalyzer(self.data)
        self.arbitrage = ArbitrageDetector(self.data)
        self.integrated_engine = IntegratedRecommendationEngine(self.data)
    
    def get_system_overview(self) -> Dict:
        """获取系统概览"""
        return {
            "name": "足球彩票专业分析系统 v3.0",
            "supported_lotteries": ["竞彩足球", "北京单场", "传统足彩"],
            "professional_modules": {
                "竞彩足球": {
                    "泊松进球预测": "✅",
                    "盘口深度分析": "✅",
                    "串关优化": "✅",
                    "半全场预测": "✅"
                },
                "北京单场": {
                    "胜平负(含让球)": "✅",
                    "总进球": "✅",
                    "比分": "✅",
                    "半全场": "✅",
                    "上下单双": "✅",
                    "SP值挖掘": "✅",
                    "串关优化": "✅"
                },
                "传统足彩": {
                    "14场胜负分析": "✅",
                    "任选9场优化": "✅",
                    "6场半全场预测": "✅",
                    "4场进球预测": "✅",
                    "奖池分析": "✅"
                },
                "跨玩法": {
                    "赔率对比": "✅",
                    "套利检测": "✅",
                    "协同策略": "✅"
                }
            },
            "modules_loaded": PROFESSIONAL_MODULES_LOADED
        }
    
    # ==================== 竞彩足球分析 ====================
    
    def analyze_jingcai_goal_prediction(
        self,
        home_team: str,
        away_team: str,
        league: str = "unknown",
        home_strength: float = 1.0,
        away_strength: float = 1.0
    ) -> Dict:
        """
        竞彩足球进球预测分析
        
        Args:
            home_team: 主队
            away_team: 客队
            league: 联赛
            home_strength: 主队实力 (0.5-1.5)
            away_strength: 客队实力 (0.5-1.5)
        """
        return self.jingcai_poisson.predict_single_match(
            home_team, away_team, league, home_strength, away_strength
        )
    
    def analyze_jingcai_handicap(
        self,
        home_team: str,
        away_team: str,
        concession: int,
        home_odds: float,
        draw_odds: float,
        away_odds: float
    ) -> Dict:
        """
        竞彩足球盘口深度分析
        
        Args:
            concession: 让球数
        """
        return self.jingcai_handicap.analyze_concession(
            home_team, away_team, concession, home_odds, draw_odds, away_odds
        )
    
    def analyze_jingcai_bqc(
        self,
        home_team: str,
        away_team: str,
        expected_home_goals: float,
        expected_away_goals: float
    ) -> Dict:
        """竞彩足球半全场预测"""
        return self.jingcai_bqc.predict_half_full(
            home_team, away_team, expected_home_goals, expected_away_goals
        )
    
    def optimize_jingcai_parlay(
        self,
        matches: List[Dict],
        budget: float,
        risk_level: str = "medium"
    ) -> Dict:
        """竞彩足球串关优化"""
        return self.jingcai_parlay.optimize_mxn(matches, budget, risk_level)
    
    # ==================== 北京单场分析 ====================
    
    def analyze_beijing_spf(self) -> Dict:
        """北京单场胜平负分析"""
        return self.beijing_spf.analyze_win_draw_lose()
    
    def analyze_beijing_zjq(self) -> Dict:
        """北京单场总进球分析"""
        return self.beijing_zjq.analyze_total_goals_distribution()
    
    def analyze_beijing_bf(self) -> Dict:
        """北京单场比分分析"""
        return self.beijing_bf.analyze_score_distribution()
    
    def analyze_beijing_bqc(self) -> Dict:
        """北京单场半全场分析"""
        return self.beijing_bqc.analyze_half_full_distribution()
    
    def analyze_beijing_sxd(self) -> Dict:
        """北京单场上下单双分析"""
        return self.beijing_sxd.analyze_sxd_distribution()
    
    def analyze_beijing_sp(self) -> Dict:
        """北京单场SP值挖掘"""
        return self.beijing_sp.analyze_sp_patterns()
    
    def recommend_beijing_parlay(
        self,
        m: int,
        budget: float,
        play_types: List[str]
    ) -> Dict:
        """北京单场串关推荐"""
        return self.beijing_parlay.optimize_parlay(m, budget, play_types)
    
    # ==================== 传统足彩分析 ====================
    
    def analyze_traditional_14(self, matches: List[Dict] = None) -> Dict:
        """传统足彩14场分析"""
        if matches is None:
            return self.traditional_14.analyze_current_round(
                self.data.get("传统足彩", {}).get("matches", [])[:14]
            )
        return self.traditional_14.analyze_current_round(matches)
    
    def optimize_rx9(
        self,
        matches: List[Dict] = None,
        budget: float = 500,
        confidence: List[float] = None
    ) -> Dict:
        """任选9场优化"""
        if matches is None:
            matches = [
                {"主队": f"H{i}", "客队": f"A{i}"}
                for i in range(14)
            ]
        return self.rx9.optimize_rx9(matches, budget, confidence)
    
    def analyze_bqc6(self, matches: List[Dict] = None) -> Dict:
        """6场半全场预测"""
        if matches is None:
            matches = [
                {"主队": f"H{i}", "客队": f"A{i}"}
                for i in range(6)
            ]
        return self.bqc6.predict_6bqc(matches)
    
    def analyze_jqc4(self, matches: List[Dict] = None) -> Dict:
        """4场进球预测"""
        if matches is None:
            matches = [
                {"主队": f"H{i}", "客队": f"A{i}"}
                for i in range(4)
            ]
        return self.jqc4.predict_4jqc(matches)
    
    def estimate_prize(
        self,
        total_sales: float,
        winners: int = 1,
        pool_balance: float = 0
    ) -> Dict:
        """奖池奖金估算"""
        return self.prize_pool.estimate_prize(total_sales, winners, pool_balance)
    
    # ==================== 跨玩法分析 ====================
    
    def compare_cross_lottery_odds(
        self,
        home_team: str,
        away_team: str
    ) -> Dict:
        """跨玩法赔率对比"""
        return self.cross_play.compare_odds_between_lotteries(home_team, away_team)
    
    def detect_arbitrage(
        self,
        home_team: str,
        away_team: str
    ) -> Dict:
        """套利机会检测"""
        return self.arbitrage.detect_arbitrage(home_team, away_team)
    
    def generate_integrated_recommendation(
        self,
        home_team: str,
        away_team: str,
        preference: str = "balanced"
    ) -> Dict:
        """生成综合推荐"""
        return self.integrated_engine.generate_integrated_recommendation(
            home_team, away_team, preference
        )
    
    def recommend_cross_play_parlay(
        self,
        matches: List[Dict],
        play_types: List[str],
        target_odds: float = 10.0
    ) -> Dict:
        """跨玩法串关推荐"""
        return self.integrated_engine.recommend_multi_play_parlay(
            matches, play_types, target_odds
        )
    
    # ==================== 完整分析报告 ====================
    
    def generate_full_report(
        self,
        lottery_type: str,
        home_team: str = None,
        away_team: str = None,
        **kwargs
    ) -> Dict:
        """
        生成完整分析报告
        
        Args:
            lottery_type: 彩票类型 (竞彩足球/北京单场/传统足彩)
            home_team: 主队
            away_team: 客队
        """
        report = {
            "lottery_type": lottery_type,
            "timestamp": "2026-04-03",
            "analyses": {}
        }
        
        if lottery_type == "竞彩足球":
            report["analyses"] = self._generate_jingcai_report(
                home_team, away_team, kwargs
            )
        elif lottery_type == "北京单场":
            report["analyses"] = self._generate_beijing_report()
        elif lottery_type == "传统足彩":
            report["analyses"] = self._generate_traditional_report()
        else:
            report["error"] = f"不支持的彩票类型: {lottery_type}"
        
        return report
    
    def _generate_jingcai_report(
        self,
        home: str,
        away: str,
        kwargs: Dict
    ) -> Dict:
        """生成竞彩足球报告"""
        report = {
            "overview": {
                "name": "竞彩足球专业分析",
                "supported_plays": ["胜平负", "让球胜平负", "比分", "总进球", "半全场"]
            }
        }
        
        if home and away:
            # 进球预测
            report["goal_prediction"] = self.analyze_jingcai_goal_prediction(
                home, away,
                kwargs.get("league", "unknown"),
                kwargs.get("home_strength", 1.0),
                kwargs.get("away_strength", 1.0)
            )
            
            # 半全场预测
            expected_home = kwargs.get("expected_home_goals", 1.5)
            expected_away = kwargs.get("expected_away_goals", 1.2)
            report["half_full_prediction"] = self.analyze_jingcai_bqc(
                home, away, expected_home, expected_away
            )
        
        # 串关优化
        report["parlay_optimization"] = self.jingcai_parlay.optimize_mxn(
            kwargs.get("matches", []),
            kwargs.get("budget", 100),
            kwargs.get("risk_level", "medium")
        )
        
        return report
    
    def _generate_beijing_report(self) -> Dict:
        """生成北京单场报告"""
        return {
            "overview": {
                "name": "北京单场专业分析",
                "supported_plays": ["胜平负", "总进球", "比分", "半全场", "上下单双", "胜负过关"]
            },
            "spf_analysis": self.analyze_beijing_spf(),
            "zjq_analysis": self.analyze_beijing_zjq(),
            "bf_analysis": self.analyze_beijing_bf(),
            "bqc_analysis": self.analyze_beijing_bqc(),
            "sxd_analysis": self.analyze_beijing_sxd(),
            "sp_analysis": self.analyze_beijing_sp()
        }
    
    def _generate_traditional_report(self) -> Dict:
        """生成传统足彩报告"""
        return {
            "overview": {
                "name": "传统足彩专业分析",
                "supported_plays": ["14场胜负", "任选9场", "6场半全场", "4场进球"]
            },
            "14_match_analysis": self.analyze_traditional_14(),
            "rx9_optimization": self.optimize_rx9(),
            "bqc6_prediction": self.analyze_bqc6(),
            "jqc4_prediction": self.analyze_jqc4()
        }


def main():
    """测试统一入口"""
    print("=" * 60)
    print("足球彩票专业分析系统 v3.0")
    print("=" * 60)
    
    analyzer = ProfessionalAnalyzer()
    
    # 系统概览
    print("\n【系统概览】")
    overview = analyzer.get_system_overview()
    print(f"系统名称: {overview['name']}")
    print(f"支持的彩票: {', '.join(overview['supported_lotteries'])}")
    print(f"模块加载: {'成功' if overview['modules_loaded'] else '部分失败'}")
    
    # 竞彩足球分析
    print("\n【竞彩足球进球预测】")
    jingcai_data = analyzer.data.get("竞彩足球", {})
    if jingcai_data.get("matches"):
        sample = jingcai_data["matches"][0]
        result = analyzer.analyze_jingcai_goal_prediction(
            sample.get("主队", "主队"),
            sample.get("客队", "客队")
        )
        print(f"比赛: {result['match']}")
        print(f"预期进球: {result['expected_goals']}")
        print(f"最可能比分: {result['most_likely_scores'][:2]}")
    
    # 北京单场分析
    print("\n【北京单场胜平负分析】")
    beijing_result = analyzer.analyze_beijing_spf()
    if "error" not in beijing_result:
        print(f"主胜率: {beijing_result.get('home_win_rate', 'N/A')}%")
        print(f"平局率: {beijing_result.get('draw_rate', 'N/A')}%")
        print(f"客胜率: {beijing_result.get('away_win_rate', 'N/A')}%")
    
    # 传统足彩分析
    print("\n【传统足彩14场分析】")
    traditional_result = analyzer.analyze_traditional_14()
    if "error" not in traditional_result:
        print(f"期次比赛数: {traditional_result.get('total_matches', 'N/A')}")
    
    # 跨玩法对比
    print("\n【跨玩法赔率对比】")
    if analyzer.data.get("竞彩足球", {}).get("matches"):
        sample = analyzer.data["竞彩足球"]["matches"][0]
        cross_result = analyzer.compare_cross_lottery_odds(
            sample.get("主队", ""),
            sample.get("客队", "")
        )
        print(f"竞彩可用: {cross_result.get('jingcai_available', False)}")
        print(f"北单可用: {cross_result.get('beijing_available', False)}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
