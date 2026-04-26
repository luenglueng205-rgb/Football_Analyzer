import time
from typing import Dict
from core_system.tools.betting_ledger import BettingLedger
from core_system.agents.grandmaster_router import GrandmasterRouter
from core_system.skills.news_arbitrage.social_listener import SocialNewsListener

class ZSAFrontRunner:
    """
    Zero-Shot Arbitrage (ZSA) 截胡执行器。
    监听 SocialNewsListener 的内存总线，一旦发现改变基本面的重大情报（如核心受伤），
    绕过所有慢速的 LangGraph 节点和复杂数学计算，直接向底层账本发起做空出票请求。
    """
    def __init__(self, listener: SocialNewsListener):
        self.listener = listener
        self.ledger = BettingLedger()
        self.router = GrandmasterRouter()
        
        # 注册回调
        self.listener.register_callback(self.handle_extreme_news)
        
        # 模拟的实时走地盘口 (In-Play Live Odds Feed)
        # 实际生产中这里会是一个高速 WebSocket 订阅庄家盘口
        self.live_markets = {
            "Arsenal": {
                "match_id": "EPL_LIVE_1001",
                "opponent": "Chelsea",
                "odds": {
                    "home_win": 2.10,
                    "draw": 3.40,
                    "away_win": 3.50  # 切尔西胜
                },
                "is_home": True
            },
            "Manchester City": {
                "match_id": "EPL_LIVE_1002",
                "opponent": "Liverpool",
                "odds": {
                    "home_win": 1.80,
                    "draw": 3.60,
                    "away_win": 4.20
                },
                "is_home": True
            }
        }
        
    def handle_extreme_news(self, team: str, news: str, impact: float):
        print(f"\n🚨🚨🚨 [ZSA 截胡系统触发] 🚨🚨🚨")
        print(f"   -> 接收到极端情报: {team} | Impact: {impact}")
        print(f"   -> 准备进行内存总线阻断与极速执行...")
        
        market = self.live_markets.get(team)
        if not market:
            print(f"   -> ❌ 未找到 {team} 的走地盘口，取消截胡。")
            return
            
        start_t = time.perf_counter()
        
        # 极速决策逻辑
        if impact <= -0.8:
            # 球队遭遇重大负面打击，果断做空 (买对手赢)
            target_selection = "away_win" if market["is_home"] else "home_win"
            target_team = market["opponent"]
            target_odds = market["odds"][target_selection]
            stake = 500.0  # 固定截胡仓位
            
            print(f"   -> ⚡ 决策: {team} 遭遇重创，极速做空！买入 {target_team} 胜 (赔率 {target_odds})")
            
            # 极速出票 (绕过图流转)
            res = self.ledger.execute_bet(
                agent_id="zsa_front_runner",
                match_id=market["match_id"],
                lottery_type="jingcai",  # 使用竞彩单关模拟
                selection=f"WDL_{target_selection}",
                odds=target_odds,
                stake=stake
            )
            
            end_t = time.perf_counter()
            latency = (end_t - start_t) * 1000
            
            if res.get("status") == "success":
                print(f"   -> ✅ [ZSA 截胡成功] 耗时: {latency:.2f}ms | 凭证: {res['ticket_code']} | 余额: ${res['remaining_balance']:.2f}")
                # 物理路由分发
                self.router.dispatch_matches({}, {f"WDL_{target_selection}": 0.99}, {"jingcai_odds": {f"WDL_{target_selection}": target_odds}})
            else:
                print(f"   -> ❌ [ZSA 截胡失败] 耗时: {latency:.2f}ms | 原因: {res.get('message')}")
