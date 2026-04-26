import time
import os
from core_system.skills.news_arbitrage.social_listener import SocialNewsListener
from core_system.skills.news_arbitrage.front_runner import ZSAFrontRunner
from core_system.tools.betting_ledger import BettingLedger

def test_front_running():
    # 使用本地 SLM，关闭真实轮询
    os.environ["USE_LOCAL_SLM"] = "true"
    os.environ["NEWS_LISTENER_MOCK"] = "true"
    
    print("1. 初始化组件...")
    listener = SocialNewsListener(use_mock=True)
    runner = ZSAFrontRunner(listener)
    ledger = BettingLedger()
    
    # 充值 ZSA 专用资金池
    ledger.reset_economy(agent_id="zsa_front_runner", initial_balance=10000.0)
    
    print("\n2. 模拟系统正在安静运行...")
    time.sleep(1)
    
    print("\n3. 突然！突发新闻爆发 (Arsenal star injured)...")
    test_news = "BREAKING: Arsenal star striker suffers severe hamstring injury during warm-up and is out of the match."
    
    # 先做一次预热推理，防止第一次加载耗时影响我们观察截胡延迟
    listener._analyze_with_local_slm("Arsenal", test_news)
    
    print("\n--- 真实事件注入 ---")
    # 这会触发 SLM 推理，然后发现 impact <= -0.8，触发回调
    impact = listener._analyze_with_local_slm("Arsenal", test_news)
    listener.inject_mock_news("Arsenal", test_news, impact)
    
    # 给异步线程一点时间执行
    time.sleep(1)
    
    print("\n4. 验证账本...")
    status = ledger.check_bankroll(agent_id="zsa_front_runner")
    print(f"ZSA Agent 余额: ${status['current_bankroll']:.2f}")
    assert status['current_bankroll'] == 9500.0, "Bet was not placed!"
    print("\n✅ ZSA Phase 3 内存总线截胡测试通过！")

if __name__ == "__main__":
    test_front_running()
