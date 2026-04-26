import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import time
import os
from standalone_workspace.skills.news_arbitrage.social_listener import SocialNewsListener

def test_slm_latency():
    # 强制启用本地 SLM 和关闭 Mock
    os.environ["USE_LOCAL_SLM"] = "true"
    os.environ["NEWS_LISTENER_MOCK"] = "false"
    
    print("初始化 SocialNewsListener，等待模型加载...")
    listener = SocialNewsListener()
    
    if not getattr(listener, 'slm_classifier', None):
        print("❌ 模型未加载成功，跳过测试。")
        return
        
    test_news = "BREAKING: Arsenal star striker suffers severe hamstring injury during warm-up and is out of the match."
    team = "Arsenal"
    
    print(f"\n测试新闻: {test_news}")
    
    # 第一次推理可能会稍微慢一点 (JIT 编译/内存加载)
    print("\n--- 预热推理 ---")
    listener._analyze_with_local_slm(team, test_news)
    
    # 第二次真实的性能测试
    print("\n--- 真实性能测试 ---")
    start = time.perf_counter()
    impact = listener._analyze_with_local_slm(team, test_news)
    end = time.perf_counter()
    
    latency_ms = (end - start) * 1000
    
    assert impact < 0, "The model failed to classify this as an injury/negative impact."
    assert latency_ms < 500.0, f"Latency is too high for ZSA fast-path! ({latency_ms:.2f}ms)"
    print("\n✅ SLM 极速推理测试通过！")

if __name__ == "__main__":
    test_slm_latency()