import re

ATOMIC_SKILLS_PATH = "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/Football/agent/openclaw-football-lottery-agent/football-lottery-analyst/tools/atomic_skills.py"
SCHEMA_PATH = "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/Football/agent/openclaw-football-lottery-agent/football-lottery-analyst/tools/openclaw_schema_generator.py"
SOP_PATH = "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/Football/agent/openclaw-football-lottery-agent/football-lottery-analyst/prompts/SOP_PROMPT.md"
MATH_ENGINE_PATH = "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/Football/analyzer/football-lottery-analyzer/skills/lottery_math_engine.py"

def fix_math_engine_payout_caps():
    with open(MATH_ENGINE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找 calculate_jingcai_mxn 的返回组装逻辑
    if "max_prize = sum(" in content and "payout_cap" not in content:
        # 添加官方单注最高奖金截断逻辑
        payout_logic = """
        # 中国体彩单注最高派奖限额规定
        payout_cap = 1000000  # 默认6场100万
        if m <= 3:
            payout_cap = 200000  # 2-3场单注限额20万
        elif m <= 5:
            payout_cap = 500000  # 4-5场单注限额50万
            
        # 对每注奖金进行截断
        capped_max_prize = sum(min(p, payout_cap) for p in [math.prod(comb) * 2 for comb in itertools.product(*max_odds)])
        capped_min_prize = sum(min(p, payout_cap) for p in [math.prod(comb) * 2 for comb in itertools.product(*min_odds)])
        """
        content = content.replace(
            "max_prize = sum([math.prod(comb) * 2 for comb in itertools.product(*max_odds)])",
            "max_prize = sum([math.prod(comb) * 2 for comb in itertools.product(*max_odds)])\n" + payout_logic + "\n        max_prize = capped_max_prize"
        )
        content = content.replace(
            "min_prize = sum([math.prod(comb) * 2 for comb in itertools.product(*min_odds)])",
            "min_prize = sum([math.prod(comb) * 2 for comb in itertools.product(*min_odds)])\n        min_prize = capped_min_prize"
        )
        
        with open(MATH_ENGINE_PATH, 'w', encoding='utf-8') as f:
            f.write(content)

def fix_atomic_skills_handicap():
    with open(ATOMIC_SKILLS_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # 在 calculate_poisson_probability 添加竞彩整数校验提示
    content = content.replace(
        ':param handicap_line: 亚指让球盘口，主队让球为负数，受让为正数 (例如: -0.25)',
        ':param handicap_line: 亚指让球盘口，主队让球为负数，受让为正数。注意：如果是【竞彩让球】，必须输入整数(如 -1, 1)，绝对不能输入小数(-0.25)！'
    )
    with open(ATOMIC_SKILLS_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_schema_handicap():
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
        
    content = content.replace(
        '"handicap_line": {"type": "number", "description": "亚指让球盘口，主队让球为负数，受让为正数 (例如: -0.25)"}',
        '"handicap_line": {"type": "number", "description": "让球盘口，主队让球为负数，受让为正数。注意：【竞彩让球】必须输入整数(如 -1, 1)，绝对不能输入亚指小数(-0.25)！"}'
    )
    with open(SCHEMA_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_sop_bankroll_and_caps():
    with open(SOP_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # 重写部分规则
    new_rules = """# Critical Rule: 动态本金管理 (Dynamic Bankroll Tracking)
你不能假设用户的本金永远是固定的。在给出任何凯利仓位或具体下注金额前，**必须询问或确认用户当前的真实账户余额**。如果没有提供，则强制使用 100% 相对比例，并提示用户代入真实余额。

# Critical Rule: 同场规避原则 (Same-Game Parlay Prohibition)
**中国体彩严禁同一场比赛的不同玩法进行串关**。你绝对不能把“阿森纳胜”和“阿森纳2:0”串在一起。串关方案中的每一场比赛必须是相互独立的！
"""
    if "Dynamic Bankroll Tracking" not in content:
        content = content.replace("---", new_rules + "\n---")
        
    with open(SOP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    fix_math_engine_payout_caps()
    fix_atomic_skills_handicap()
    fix_schema_handicap()
    fix_sop_bankroll_and_caps()
    print("✅ 隐患 6/7/8 修复完毕 (奖金截断, 让球盘口对齐, 本金跟踪, 同场规避)")
