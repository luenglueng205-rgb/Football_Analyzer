import json

def get_league_persona(league_name: str) -> str:
    """
    Retrieve the tactical persona, historical variance, and referee leniency of a specific football league.
    Use this to adjust Poisson distributions and Kelly Criterion calculations.
    """
    profiles = {
        "premier league": {"persona": "High intensity, physical, fast transitions.", "variance": "High", "tactical_style": "Attacking, high pressing."},
        "英超": {"persona": "高强度、身体对抗激烈、攻防转换极快。", "variance": "高 (High)", "tactical_style": "重进攻、高位压迫。"},
        
        "serie a": {"persona": "Tactical, defensive rigidity, slow buildup.", "variance": "Low", "tactical_style": "Defensive blocks, counter-attack."},
        "意甲": {"persona": "战术严密、防守极其坚固、进攻推进缓慢。", "variance": "低 (Low)", "tactical_style": "密集防守、伺机反击。弱队极大概率摆大巴。"},
        
        "la liga": {"persona": "Technical, possession-based.", "variance": "Medium", "tactical_style": "Tiki-taka, high ball retention."},
        "西甲": {"persona": "技术细腻、极致的控球与短传渗透。", "variance": "中 (Medium)", "tactical_style": "Tiki-taka 控球流。"},
        
        "eredivisie": {"persona": "Open play, development league, poor defending.", "variance": "Very High", "tactical_style": "Total football, high scoring."},
        "荷甲": {"persona": "极其开放的比赛风格、防守形同虚设。", "variance": "极高 (Very High)", "tactical_style": "全攻全守、大比分频出。"},
        
        "j1 league": {"persona": "Technical but physically weak, home advantage is less pronounced.", "variance": "High", "tactical_style": "Possession, vulnerable to counter-attacks."},
        "日职联": {"persona": "技术流但身体对抗偏弱，主场优势不明显，冷门频出。", "variance": "高 (High)", "tactical_style": "传控为主，容易被防反打穿。"},
        
        "default": {"persona": "Standard professional league.", "variance": "Medium", "tactical_style": "Balanced."}
    }
    
    key = league_name.lower().strip()
    profile = profiles.get(key, profiles["default"])
    
    return json.dumps({
        "league": league_name,
        "profile": profile,
        "ai_strategist_instruction": f"【联赛降维打击】：当前联赛方差特性为[{profile['variance']}]。如果是高方差联赛，强烈建议规避胜平负（极易爆冷），转而寻找总进球数或让球胜平负的下注价值。如果是低方差联赛（如意甲），可以大胆下注小球（Under 2.5）或强队1球小胜。"
    }, ensure_ascii=False)
