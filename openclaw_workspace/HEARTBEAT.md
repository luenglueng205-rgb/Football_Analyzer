# Heartbeat Instructions
# 你的守护进程配置 (Daemon Configuration)

[Cron: "*/15 14-23 * * *"] # 每天 14:00 - 23:00（比赛高峰期），每 15 分钟醒来一次

1. 获取当天晚上即将开赛的热门联赛（五大联赛）。
2. 并行调用 `get_global_arbitrage_data` 提取平博(Pinnacle)、必发(Betfair) 实时活水赔率和资金量。
3. 调取官方竞彩开出的赔率。
4. 如果 `detect_latency_arbitrage` 返回 `True`，且套利空间 > 2%：
   - 生成出票方案 (`generate_simulated_ticket`)。
   - 推送消息到网关：“发现绝对时差套利机会，平博已退水，竞彩尚未跟进，请立刻买入！”
5. 每次执行完毕，将遇到的“诱盘球队”写入你的 SQLite 记忆库，下次同联赛时参考。
