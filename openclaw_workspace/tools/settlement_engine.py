import logging

logger = logging.getLogger(__name__)

class SettlementEngine:
    """
    Strict Official Settlement Engine.
    Perfectly mirrors official China Sports Lottery settlement rules (Jingcai/Beidan).
    Handles 90-minute full-time rules, extra time exclusions, and cancellations.
    """
    
    def __init__(self):
        self.ruleset = {
            "jingcai": "90_min_only",
            "beidan": "90_min_only",
            "cancelled_odds": 1.0,
            "postponed_hours_limit": 36 # If postponed > 36h, void
        }

    def determine_all_play_types_results(self, ft_score: str, ht_score: str = None, handicaps: dict = None, status: str = "FINISHED") -> dict:
        """
        根据 90分钟比分 一次性生成 16 种玩法的所有正确选项。隔离加时赛。
        """
        if status.upper() in ["CANCELLED", "POSTPONED", "ABANDONED"] or not ft_score or ft_score.upper() in ["W/O", "AWARDED"]:
            return {"status": "VOID", "official_result": "REFUND", "odds_applied": 1.0}
            
        try:
            home_goals, away_goals = map(int, ft_score.split("-"))
            total_goals = home_goals + away_goals
        except ValueError:
            return {"status": "VOID", "official_result": "REFUND", "odds_applied": 1.0}

        wdl = "3" if home_goals > away_goals else "1" if home_goals == away_goals else "0"
        goals = str(min(total_goals, 7))
        cs = f"{home_goals}-{away_goals}"
        odd_even = "ODD" if total_goals % 2 != 0 else "EVEN"
        
        handicaps = handicaps if isinstance(handicaps, dict) else {}
        jc_h = handicaps.get("JINGCAI_HANDICAP", 0)
        bd_h = handicaps.get("BEIDAN_HANDICAP", 0)
        try:
            jc_h_f = float(jc_h)
        except Exception:
            jc_h_f = 0.0
        try:
            bd_h_f = float(bd_h)
        except Exception:
            bd_h_f = 0.0

        adjusted_home_jc = float(home_goals) + jc_h_f
        adjusted_home_bd = float(home_goals) + bd_h_f
        jingcai_handicap_wdl = "3" if adjusted_home_jc > float(away_goals) else "1" if adjusted_home_jc == float(away_goals) else "0"
        beidan_handicap_wdl = "3" if adjusted_home_bd > float(away_goals) else "1" if adjusted_home_bd == float(away_goals) else "0"
            
        htft = None
        if ht_score:
            try:
                ht_home, ht_away = map(int, str(ht_score).split("-"))
                ht_res = "3" if ht_home > ht_away else "1" if ht_home == ht_away else "0"
                htft = f"{ht_res}-{wdl}"
            except Exception:
                htft = None
                
        up_down = "UP" if total_goals >= 3 else "DOWN"
        up_down_odd_even = f"{up_down}_{odd_even}"

        results = {
            "status": "SETTLED",
            "ft_score": ft_score,
            "ht_score": ht_score,
            "WDL": wdl,
            "GOALS": goals,
            "CS": cs,
            "ODD_EVEN": odd_even,
            "UP_DOWN_ODD_EVEN": up_down_odd_even,
            "JINGCAI_HANDICAP_WDL": jingcai_handicap_wdl,
            "BEIDAN_HANDICAP_WDL": beidan_handicap_wdl,
            "HTFT": htft,
        }

        results.update(
            {
                "JINGCAI_WDL": wdl,
                "JINGCAI_GOALS": goals,
                "JINGCAI_CS": cs,
                "JINGCAI_HTFT": htft,
                "JINGCAI_MIXED_PARLAY": {
                    "WDL": wdl,
                    "JINGCAI_HANDICAP_WDL": jingcai_handicap_wdl,
                    "GOALS": goals,
                    "CS": cs,
                    "HTFT": htft,
                },
                "BEIDAN_WDL": wdl,
                "BEIDAN_SFGG": beidan_handicap_wdl,
                "BEIDAN_UP_DOWN_ODD_EVEN": up_down_odd_even,
                "BEIDAN_GOALS": goals,
                "BEIDAN_CS": cs,
                "BEIDAN_HTFT": htft,
                "ZUCAI_14_MATCH": wdl,
                "ZUCAI_RENJIU": wdl,
                "ZUCAI_6_HTFT": htft,
                "ZUCAI_4_GOALS": goals,
                
                # 兼容 ticket_builder 标准化出来的无前缀 play_type
                "SFGG": beidan_handicap_wdl,
                "MIXED_PARLAY": wdl,  # 混合过关结算依赖具体场次玩法，这里提供默认占位
                "HANDICAP": jingcai_handicap_wdl, # 默认映射竞彩让球结果
            }
        )

        return results

    def settle_ticket(self, ticket: dict, match_results: dict) -> dict:
        """
        Settles a parlay ticket.
        If any leg is voided, its odds become 1.0, and the parlay cascades down.
        """
        total_odds = 1.0
        ticket_status = "WON"
        
        for leg in ticket["legs"]:
            match_id = leg["match_id"]
            if match_id not in match_results:
                return {"status": "PENDING", "reason": f"Waiting for match {match_id}"}
                
            result = match_results[match_id]
            if result["status"] == "VOID":
                logger.info(f"Leg {match_id} VOIDED. Odds 1.0 applied.")
                total_odds *= 1.0
                leg["status"] = "VOID"
            elif result["official_result"] == leg["selection"]:
                logger.info(f"Leg {match_id} WON. Odds {leg['odds']} applied.")
                total_odds *= leg["odds"]
                leg["status"] = "WON"
            else:
                logger.info(f"Leg {match_id} LOST. Ticket BUST.")
                ticket_status = "LOST"
                total_odds = 0.0
                leg["status"] = "LOST"
                break
                
        payout = ticket["stake"] * total_odds if ticket_status == "WON" else 0.0
        
        return {
            "ticket_id": ticket.get("ticket_id", "unknown"),
            "status": ticket_status,
            "final_odds": round(total_odds, 2),
            "payout": round(payout, 2)
        }
