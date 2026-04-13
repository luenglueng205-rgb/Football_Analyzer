import json

ATOMIC_SKILLS_PATH = "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/Football/agent/openclaw-football-lottery-agent/football-lottery-analyst/tools/atomic_skills.py"
SOP_PATH = "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/Football/agent/openclaw-football-lottery-agent/football-lottery-analyst/prompts/SOP_PROMPT.md"
MATH_ENGINE_PATH = "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/Football/analyzer/football-lottery-analyzer/skills/lottery_math_engine.py"
LEARNING_ENGINE_PATH = "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/Football/analyzer/football-lottery-analyzer/memory/learning_engine.py"

def fix_atomic_skills_poisson_push():
    with open(ATOMIC_SKILLS_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 修复 calculate_poisson_probability 中的 push 概念，明确其在竞彩中是"让平"
    content = content.replace(
        '"push": round(p_push_hc, 4),',
        '"push_or_handicap_draw": round(p_push_hc, 4), # 注意：在竞彩中，这就是【让平】的概率！'
    )
    
    # 2. 修改 evaluate_betting_value 中的 push_probability 解释
    content = content.replace(
        ':param push_probability: 走水(退款)的概率，针对亚指整球盘口有效，竞彩胜平负填 0.0',
        ':param push_probability: 走水(退款)的概率。【极度重要】：在竞彩让球(RQSPF)中，让球平(让平)是一个独立的赢钱选项，绝对不是走水！计算竞彩让球EV时，此项必须填 0.0！只有海外亚盘退本金才填入此项。'
    )

    with open(ATOMIC_SKILLS_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_sop_mutual_exclusion():
    with open(SOP_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # 在 Critical Rule 部分增加互斥原则
    mutual_exclusion_rule = """
# Critical Rule: 单场互斥与凯利聚合 (Single-Match Mutual Exclusion)
同一场比赛中，即使你算出了多个正 EV 的玩法（例如：主胜 EV 0.05，总进球2-3球 EV 0.08），你**绝对不允许**对这同一场比赛推荐多头单关下注（这会导致凯利风险成倍放大）。
你必须在这些正 EV 玩法中进行“优中选优”，**只挑选 EV 最高且方差最小的一个玩法**作为该场比赛的【唯一最佳玩法】。

# Critical Rule: 竞彩让平的数学错位 (Handicap Tie Misunderstanding)
在竞彩的“让球胜平负 (RQSPF)”玩法中，如果让 -1 球最终刚好赢 1 球，这叫**【让平】**，它是有独立高赔率的！你绝对不能把它当做海外亚盘的“走水(Push)退本金”来算 EV。计算竞彩让球 EV 时，`push_probability` 必须严格填 0.0。
"""
    if "Single-Match Mutual Exclusion" not in content:
        content = content.replace("---", mutual_exclusion_rule + "\n---")

    with open(SOP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_math_engine_postponement():
    with open(MATH_ENGINE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # 增加对赔率为 1.0 (延期/作废) 的处理说明，虽然目前是算最大最小奖金，但为后续扩展提供支持
    # 在 calculate_jingcai_mxn 中，如果有比赛取消，体彩官方规定该场所有选项赔率为 1.0
    postponement_logic = """
        # 处理延期/腰斩比赛 (体彩规则：延期比赛赔率按 1.0 计算)
        # 如果传入的 matches 中包含 'status': 'postponed' 或赔率强制为 [1.0]
        for match in formatted_matches:
            if match.get('status') in ['postponed', 'cancelled']:
                match['odds'] = [1.0] # 强制替换为 1.0
    """
    
    if "处理延期/腰斩比赛" not in content:
        content = content.replace(
            "def calculate_jingcai_mxn(formatted_matches: List[Dict], m: int, n: int) -> Dict:",
            "def calculate_jingcai_mxn(formatted_matches: List[Dict], m: int, n: int) -> Dict:\n" + postponement_logic
        )

    with open(MATH_ENGINE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_learning_engine_postponement():
    with open(LEARNING_ENGINE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # 在 bayesian_update 中，如果比赛取消，不能惩罚模型
    postponed_check = """
        # 如果比赛延期或腰斩，不进行置信度更新 (避免错杀模型)
        if actual_result == "postponed" or actual_result == "cancelled":
            self.logger.info("比赛延期/取消，跳过贝叶斯置信度更新。")
            return self.confidence_scores.get(team_name, 0.5)
    """
    
    if "postponed" not in content and "def bayesian_update" in content:
        content = content.replace(
            'def bayesian_update(self, team_name: str, predicted_prob: float, actual_result: str) -> float:',
            'def bayesian_update(self, team_name: str, predicted_prob: float, actual_result: str) -> float:\n' + postponed_check
        )
        
        with open(LEARNING_ENGINE_PATH, 'w', encoding='utf-8') as f:
            f.write(content)

if __name__ == "__main__":
    fix_atomic_skills_poisson_push()
    fix_sop_mutual_exclusion()
    fix_math_engine_postponement()
    try:
        fix_learning_engine_postponement()
    except FileNotFoundError:
        print("未找到 learning_engine.py，可能是路径不同，跳过该文件的修复。")
    print("✅ 隐患 9/10/11 修复完毕 (互斥原则, 竞彩让平错位纠正, 延期作废容错)")
