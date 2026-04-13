import json
import os

# 真实的 2026 赛季中国体彩联赛白名单知识库 (基于官方停售和开盘规律)
# 修复：已更新至 2026 年最新基准

# 1. 传统足彩 (14场/任九)：极度严格，仅限顶级和次顶级，防默契球
TRADITIONAL_CODES = {
    "E0": "英格兰超级联赛", "E1": "英格兰冠军联赛",
    "SP1": "西班牙甲级联赛", "SP2": "西班牙乙级联赛",
    "D1": "德国甲级联赛", "D2": "德国乙级联赛",
    "I1": "意大利甲级联赛", "I2": "意大利乙级联赛",
    "F1": "法国甲级联赛", "F2": "法国乙级联赛",
    "N1": "荷兰甲级联赛",
    "P1": "葡萄牙超级联赛",
    "SWE": "瑞典超级联赛", "NOR": "挪威超级联赛", # 夏季足彩主力
    "CL": "欧洲冠军联赛", "EL": "欧足联欧洲联赛", "WCP": "世界杯" # 2026是世界杯年
}

# 2. 竞彩足球：主流及部分次级，必须有良好的转播和公信力
JINGCAI_CODES = TRADITIONAL_CODES.copy()
JINGCAI_CODES.update({
    "B1": "比利时甲级联赛", "T1": "土耳其超级联赛",
    "SC0": "苏格兰超级联赛", "G1": "希腊超级联赛",
    "ARG": "阿根廷甲级联赛", "BRA": "巴西甲级联赛",
    "USA": "美国职业大联盟",
    "J1": "日本职业足球甲级联赛", "J2": "日本职业足球乙级联赛",
    "K1": "韩国职业足球甲级联赛",
    "AUS": "澳大利亚超级联赛",
    "DEN": "丹麦超级联赛", "SUI": "瑞士超级联赛",
    "RUS": "俄罗斯超级联赛",
    "ECL": "欧洲协会联赛", "FAC": "英格兰足总杯"
})

# 3. 北京单场：包容万象，包含大量第三级别、低级别和冷门国家联赛
BEIDAN_CODES = JINGCAI_CODES.copy()
BEIDAN_CODES.update({
    "E2": "英格兰甲级联赛", "E3": "英格兰乙级联赛", "EC": "英格兰足球议会全国联赛",
    "SC1": "苏格兰冠军联赛", "SC2": "苏格兰甲级联赛", "SC3": "苏格兰乙级联赛",
    "I3": "意大利丙级联赛",
    "D3": "德国丙级联赛",
    "F3": "法国全国联赛",
    "J3": "日本职业足球丙级联赛",
    "K2": "韩国职业足球乙级联赛",
    "SWE2": "瑞典甲级联赛", "NOR2": "挪威甲级联赛",
    "IRE": "爱尔兰超级联赛",
    "FIN": "芬兰超级联赛",
    "POL": "波兰超级联赛",
    "CHN": "中国超级联赛", "CHN2": "中国甲级联赛",
    "MEX": "墨西哥超级联赛",
    "COL": "墨西哥秋季联赛",
    "CHL": "智利甲级联赛",
    "PER": "秘鲁甲级联赛"
})

def create_mapping_json():
    mapping = {
        "竞彩足球": {"description": "竞彩官方支持联赛(2026基准)", "leagues": {}},
        "北京单场": {"description": "北单官方支持联赛(含大量低级别)(2026基准)", "leagues": {}},
        "传统足彩": {"description": "14场/任九官方支持联赛(核心五大+夏季北欧+2026世界杯)", "leagues": {}}
    }
    
    for k, v in JINGCAI_CODES.items():
        mapping["竞彩足球"]["leagues"][k] = {"name": v}
    for k, v in BEIDAN_CODES.items():
        mapping["北京单场"]["leagues"][k] = {"name": v}
    for k, v in TRADITIONAL_CODES.items():
        mapping["传统足彩"]["leagues"][k] = {"name": v}
        
    path = "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/Football/analyzer/football-lottery-analyzer/data/league_mapping.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print("✅ league_mapping.json 重建成功，已更新至 2026 年最新基准！")

if __name__ == "__main__":
    create_mapping_json()
