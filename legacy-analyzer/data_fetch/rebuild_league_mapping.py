import json
import os

RAW_PATH = "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/Football/analyzer/football-lottery-analyzer/data/raw/COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json"
CHINESE_DIR = "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/Football/analyzer/football-lottery-analyzer/data/chinese_mapped/"
MAPPING_PATH = "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/Football/analyzer/football-lottery-analyzer/data/league_mapping.json"

# 严格对齐体彩官方的联赛白名单 (2024-2025赛季基准)
JINGCAI_LEAGUES = {
    "英格兰超级联赛", "英格兰冠军联赛", "西班牙甲级联赛", "西班牙乙级联赛",
    "德国甲级联赛", "德国乙级联赛", "意大利甲级联赛", "意大利乙级联赛",
    "法国甲级联赛", "法国乙级联赛", "荷兰甲级联赛", "葡萄牙超级联赛",
    "欧洲冠军联赛", "欧足联欧洲联赛", "欧洲协会联赛", "日本职业足球联赛",
    "日本职业足球乙级联赛", "韩国职业足球甲级联赛", "美国职业大联盟",
    "澳大利亚超级联赛", "瑞典超级联赛", "挪威超级联赛", "巴西甲级联赛",
    "阿根廷甲级联赛", "英格兰足总杯", "西班牙国王杯", "德国杯", "意大利杯"
}

TRADITIONAL_LEAGUES = {
    "英格兰超级联赛", "英格兰冠军联赛", "西班牙甲级联赛", "德国甲级联赛", "德国乙级联赛",
    "意大利甲级联赛", "法国甲级联赛", "荷兰甲级联赛", "瑞典超级联赛", "挪威超级联赛",
    "欧洲冠军联赛", "欧足联欧洲联赛"
}

BEIDAN_LEAGUES = JINGCAI_LEAGUES.union({
    "英格兰甲级联赛", "英格兰乙级联赛", "苏格兰超级联赛", "苏格兰冠军联赛",
    "意大利丙级联赛", "日本职业足球丙级联赛", "韩国职业足球乙级联赛",
    "瑞典甲级联赛", "挪威甲级联赛", "丹麦超级联赛", "瑞士超级联赛",
    "奥地利甲级联赛", "比利时甲级联赛", "土耳其超级联赛", "希腊超级联赛",
    "俄罗斯超级联赛", "中国超级联赛", "中国甲级联赛", "爱尔兰超级联赛"
})

def rebuild_databases():
    print("⏳ 正在读取原始 22 万条历史数据...")
    with open(RAW_PATH, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    with open(MAPPING_PATH, 'r', encoding='utf-8') as f:
        league_mapping = json.load(f)
        
    matches = raw_data.get("matches", [])
    jc_matches, bd_matches, ct_matches = [], [], []
    
    for m in matches:
        l_code = m.get("league", "")
        # 从 league_mapping.json 拿中文名
        mapped_info = league_mapping.get(l_code, {})
        league_cn = mapped_info.get("name", "未知联赛")
        
        # 为了兼容旧的数据格式，我们把字段转成中文
        chinese_match = {
            "联赛中文名": league_cn,
            "联赛代码": l_code,
            "比赛日期": m.get("date", ""),
            "主队": m.get("home_team", ""),
            "客队": m.get("away_team", ""),
            "主队进球": m.get("home_goals", 0),
            "客队进球": m.get("away_goals", 0),
            "比赛结果": m.get("result", ""),
            "主队赔率": m.get("home_odds", 0),
            "平局赔率": m.get("draw_odds", 0),
            "客队赔率": m.get("away_odds", 0)
        }
        
        if league_cn in JINGCAI_LEAGUES:
            jc_matches.append(chinese_match)
        if league_cn in BEIDAN_LEAGUES:
            bd_matches.append(chinese_match)
        if league_cn in TRADITIONAL_LEAGUES:
            ct_matches.append(chinese_match)
            
    print(f"✅ 数据重组完毕:")
    print(f"  - 竞彩足球: {len(jc_matches)} 场 (严选主流)")
    print(f"  - 北京单场: {len(bd_matches)} 场 (全量下沉)")
    print(f"  - 传统足彩: {len(ct_matches)} 场 (14场核心池)")
    
    with open(os.path.join(CHINESE_DIR, "竞彩足球_chinese_data.json"), "w") as f:
        json.dump({"metadata": {"description": "竞彩专属历史库"}, "matches": jc_matches}, f, ensure_ascii=False)
    with open(os.path.join(CHINESE_DIR, "北京单场_chinese_data.json"), "w") as f:
        json.dump({"metadata": {"description": "北单专属历史库"}, "matches": bd_matches}, f, ensure_ascii=False)
    with open(os.path.join(CHINESE_DIR, "传统足彩_chinese_data.json"), "w") as f:
        json.dump({"metadata": {"description": "传统足彩专属历史库"}, "matches": ct_matches}, f, ensure_ascii=False)

if __name__ == "__main__":
    rebuild_databases()
