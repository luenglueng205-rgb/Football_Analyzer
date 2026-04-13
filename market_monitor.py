import json
import logging
import time
from typing import Dict, Any, List
import os

from tools.smart_money_tracker import SmartMoneyTracker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ActiveMarketMonitor:
    """
    聪明资金后台主动监控守护进程 (Daemon)。
    定期轮询今日赛事的赔率接口，发现异常剧烈震荡时，
    主动向系统风控师 (RiskManager) 的消息队列推送最高级别警报。
    """
    
    def __init__(self, check_interval_seconds: int = 300):
        self.tracker = SmartMoneyTracker(alert_threshold=0.05) # 提高阈值至5%，过滤日常波动
        self.check_interval = check_interval_seconds
        self.alert_queue_file = "workspace/risk-manager/smart_money_alerts.json"
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.alert_queue_file), exist_ok=True)
        if not os.path.exists(self.alert_queue_file):
            with open(self.alert_queue_file, 'w') as f:
                json.dump([], f)

    def _mock_fetch_live_odds(self) -> List[Dict[str, Any]]:
        """模拟从外部接口(如API-Sports/Pinnacle)批量获取今日赛事的即时赔率"""
        # 实战中这里应该调用真实的 API
        return [
            {
                "match_id": "JINGCAI_001",
                "home_team": "曼联",
                "away_team": "切尔西",
                "opening_odds": {"home": 2.10, "draw": 3.40, "away": 3.50},
                "current_odds": {"home": 2.15, "draw": 3.40, "away": 3.40} # 正常波动
            },
            {
                "match_id": "JINGCAI_002",
                "home_team": "阿森纳",
                "away_team": "热刺",
                "opening_odds": {"home": 1.95, "draw": 3.50, "away": 3.80},
                "current_odds": {"home": 1.55, "draw": 4.20, "away": 6.50} # 极其异常的暴跌 (主队大概率有内幕利好)
            }
        ]

    def _push_alert_to_risk_manager(self, alert_data: Dict[str, Any]):
        """将高危警报写入风控师的工作区队列 (增加文件锁保护)"""
        import fcntl
        lock_file = self.alert_queue_file + ".lock"
        
        try:
            with open(lock_file, 'w') as lock:
                # 阻塞式获取排他锁
                fcntl.flock(lock, fcntl.LOCK_EX)
                
                with open(self.alert_queue_file, 'r') as f:
                    alerts = json.load(f)
                    
                # 避免重复推送相同比赛的警报
                if not any(a["match_id"] == alert_data["match_id"] for a in alerts):
                    alert_data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    alerts.append(alert_data)
                    
                    with open(self.alert_queue_file, 'w') as f:
                        json.dump(alerts, f, ensure_ascii=False, indent=2)
                    logger.critical(f"🚨 [主动风控拦截] 已向风控师推送高危警报: {alert_data['match_id']}")
                    
                # 释放锁
                fcntl.flock(lock, fcntl.LOCK_UN)
                
        except json.JSONDecodeError:
             logger.error("队列文件损坏，正在重置...")
             with open(self.alert_queue_file, 'w') as f:
                 json.dump([alert_data], f, ensure_ascii=False, indent=2)
             if 'lock' in locals(): fcntl.flock(lock, fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"推送警报失败: {e}")
            if 'lock' in locals(): fcntl.flock(lock, fcntl.LOCK_UN)

    def run_monitor_loop(self, max_iterations: int = 1):
        """运行监控循环 (实战中 max_iterations 应为无穷大)"""
        logger.info("启动聪明资金后台监控守护进程...")
        iterations = 0
        
        while iterations < max_iterations:
            matches = self._mock_fetch_live_odds()
            
            for match in matches:
                result = self.tracker.track_odds_movement(
                    match["match_id"], 
                    match["opening_odds"], 
                    match["current_odds"]
                )
                
                # 如果检测到聪明资金 (CRITICAL 级别)
                if result.get("is_volatile_market"):
                    for alert in result.get("smart_money_alerts", []):
                        if alert["alert_level"] in ["HIGH", "CRITICAL"]:
                            logger.warning(f"检测到异常资金流向: {match['home_team']} vs {match['away_team']} -> {alert['signal']}")
                            self._push_alert_to_risk_manager({
                                "match_id": match["match_id"],
                                "teams": f"{match['home_team']} vs {match['away_team']}",
                                "alert_detail": alert
                            })
            
            iterations += 1
            if iterations < max_iterations:
                time.sleep(self.check_interval)

if __name__ == "__main__":
    monitor = ActiveMarketMonitor()
    monitor.run_monitor_loop(max_iterations=1)