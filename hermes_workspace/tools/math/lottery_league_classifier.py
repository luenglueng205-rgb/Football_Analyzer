class LotteryLeagueClassifier:
    """
    2026 AI-Native: 中国体彩赛事分发路由器 (League Classifier)
    严格按照官方规则，判断一场比赛是否有资格进入竞彩、北单或足彩的奖池。
    防止 AI 在竞彩里买英甲，或者在足彩里买日丙这种违背客观物理定律的幻觉。
    """

    # 1. 传统足彩 (Toto 14) 核心赛事库 (最严格，必须是大众赛事以支撑奖池)
    TOTO_14_LEAGUES = {
        "英超", "西甲", "意甲", "德甲", "法甲", 
        "欧冠", "欧罗巴", "欧协联", "欧国联",
        "世界杯", "欧洲杯", "美洲杯", "亚洲杯",
        "英冠", "荷甲", "葡超", "瑞典超", "挪超", "日职"
    }

    # 2. 竞彩足球 (Jingcai) 主流与次主流赛事库 (防范操纵风险)
    JINGCAI_LEAGUES = TOTO_14_LEAGUES.union({
        "比甲", "苏超", "俄超", "土超", "丹超", "瑞士超",
        "巴甲", "阿甲", "美职足", "墨超",
        "日职乙", "韩职", "澳超",
        "英足总杯", "国王杯", "意大利杯", "德国杯", "亚冠", "解放者杯"
    })

    # 3. 北京单场 (Beidan) 全量赛事库 (65%返奖率转移了风险，包含大量低级别/野鸡比赛)
    BEIDAN_EXCLUSIVE_LEAGUES = {
        "英甲", "英乙", "英议联", "意乙", "意丙", "西乙", "德乙", "德丙", "法乙", "法丙", "苏冠",
        "芬超", "爱超", "冰岛超", "波甲", "罗甲", "捷甲", "奥甲", "智甲", "哥超", "日丙", "韩K2",
        "俱乐部友谊赛", "女足世界杯", "U23联赛", "U21联赛"
    }
    
    # 4. 全系统最高红线 (物理禁区)
    BANNED_LEAGUES = {
        "中超", "中甲", "中乙", "中国足协杯"
    }

    @classmethod
    def get_available_lotteries(cls, league_name: str) -> list:
        """
        输入联赛名称，返回该比赛在哪些中国体彩玩法中合法开售。
        包含关系: 北单 ⊃ 竞彩 ⊃ 足彩14场
        """
        # 1. 触发最高红线
        if league_name in cls.BANNED_LEAGUES:
            return []
            
        available = []
        
        # 2. 足彩判断
        if league_name in cls.TOTO_14_LEAGUES:
            available.append("TOTO_14")
            
        # 3. 竞彩判断
        if league_name in cls.JINGCAI_LEAGUES:
            available.append("JINGCAI")
            
        # 4. 北单判断 (所有竞彩和足彩的比赛，北单基本都开；加上北单独占的野鸡比赛)
        if league_name in cls.JINGCAI_LEAGUES or league_name in cls.BEIDAN_EXCLUSIVE_LEAGUES:
            available.append("BEIDAN")
            
        return available

if __name__ == "__main__":
    print("==================================================")
    print("🇨🇳 [Official Rules] 中国体彩联赛资格审查器自检...")
    print("==================================================")
    
    test_leagues = ["英超", "日职乙", "英甲", "中超", "俱乐部友谊赛"]
    
    for league in test_leagues:
        lotteries = LotteryLeagueClassifier.get_available_lotteries(league)
        print(f"   -> 🏟️ 联赛: 【{league}】 | 合法开售玩法: {lotteries if lotteries else '❌ 全线禁售 (触发红线)'}")
