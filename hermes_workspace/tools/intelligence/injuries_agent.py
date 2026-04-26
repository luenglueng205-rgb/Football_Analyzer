"""
伤停情报 Agent：获取实时伤停/停赛信息

职责：
- 并发获取两队伤停名单
- 识别关键球员缺阵（影响 xG 模型的重要输入）
- 输出关键缺阵球员清单
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


class InjuriesAgent:
    """伤停情报 Agent"""

    async def gather(self, team_a: str, team_b: str) -> dict:
        """
        并发获取两队伤停信息
        
        Returns:
            dict: {
                "team_a_injuries": [...],
                "team_b_injuries": [...],
                "key_players_out": [...]  # 关键球员缺阵（会影响 xG）
            }
        """
        task_a = self._fetch_team_injuries(team_a)
        task_b = self._fetch_team_injuries(team_b)

        inj_a, inj_b = await asyncio.gather(task_a, task_b, return_exceptions=True)

        if isinstance(inj_a, Exception):
            logger.warning(f"伤停抓取异常 {team_a}: {inj_a}")
            inj_a = []
        if isinstance(inj_b, Exception):
            logger.warning(f"伤停抓取异常 {team_b}: {inj_b}")
            inj_b = []

        return {
            "team_a_injuries": inj_a,
            "team_b_injuries": inj_b,
            "key_players_out": self._identify_key_absences(inj_a, inj_b),
        }

    async def _fetch_team_injuries(self, team: str) -> list:
        """
        抓取单队伤停信息
        
        数据源候选：
        - transfermarkt.com (injuries/suspensions API)
        - thephysioroom.com
        - 国内：雷速体育、懂球帝伤停接口
        """
        try:
            # 骨架实现 — 实际应接真实伤停 API
            return [{
                "team": team,
                "injuries": [],
                "suspensions": [],
                "doubtful": [],
                "source": "placeholder",
            }]
        except Exception as e:
            logger.warning(f"伤停抓取失败 {team}: {e}")
            return []

    def _identify_key_absences(self, inj_a: list, inj_b: list) -> list:
        """
        识别关键球员缺阵
        
        关键球员定义：
        - 首发阵容主力
        - xG 贡献 > 队内前 30%
        - 近 5 场进球/助攻者
        
        返回的关键缺阵将直接传入 xG 调整器 (PlayerXgAdjuster)
        """
        # TODO: 对接 PlayerXgAdjuster 的 key_player 判定逻辑
        return []
