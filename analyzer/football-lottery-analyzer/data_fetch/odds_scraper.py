#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - 赔率数据爬取模块
从多个公开赔率网站抓取数据，支持数据清洗和标准化
"""

import os
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from decimal import Decimal

from .scraper import BaseScraper


class OddsScraper(BaseScraper):
    """赔率数据爬取器"""
    
    def __init__(self, config_file: Optional[str] = "config.json"):
        """
        初始化赔率爬取器
        
        Args:
            config_file: 配置文件路径
        """
        super().__init__(name="OddsScraper", config_file=config_file)
        
        # 赔率数据源配置
        self.data_sources = {
            'oddsportal': {
                'name': 'OddsPortal',
                'url_template': 'https://www.oddsportal.com/football/{country}/{league}/',
                'supported_leagues': ['england/premier-league', 'spain/laliga', 
                                     'italy/serie-a', 'germany/bundesliga', 
                                     'france/ligue-1']
            },
            'flashscore': {
                'name': 'FlashScore',
                'url_template': 'https://www.flashscore.com/football/{country}/{league}/',
                'supported_leagues': ['england/premier-league', 'spain/spain-laliga',
                                     'italy/serie-a', 'germany/bundesliga']
            },
            'bet365': {
                'name': 'Bet365',
                'url_template': 'https://www.bet365.com/#/AC/B1/C1/D8/E{FIXTURE_ID}/F3/',
                'requires_fixture_id': True
            }
        }
        
        # 赔率类型映射
        self.odds_type_mapping = {
            '1': 'home_win',
            'X': 'draw',
            '2': 'away_win',
            '1X': 'home_win_or_draw',
            'X2': 'away_win_or_draw',
            '12': 'home_win_or_away_win',
            'over_2.5': 'over_2.5_goals',
            'under_2.5': 'under_2.5_goals',
            'btts_yes': 'both_teams_to_score_yes',
            'btts_no': 'both_teams_to_score_no'
        }
        
        # 公司映射
        self.bookmaker_mapping = {
            'bet365': 'Bet365',
            'william hill': 'William Hill',
            'ladbrokes': 'Ladbrokes',
            'pinnacle': 'Pinnacle',
            'betfair': 'Betfair',
            'unibet': 'Unibet',
            '888sport': '888Sport',
            'bwin': 'Bwin'
        }
    
    def fetch_data(self, source: str = 'oddsportal', league: str = 'england/premier-league',
                   date_range: Optional[Tuple[str, str]] = None) -> Optional[str]:
        """
        从指定数据源获取赔率数据
        
        Args:
            source: 数据源名称
            league: 联赛标识
            date_range: 日期范围 (开始日期, 结束日期)
            
        Returns:
            原始HTML数据或None
        """
        if source not in self.data_sources:
            self.logger.error(f"不支持的数据源: {source}")
            return None
        
        source_config = self.data_sources[source]
        
        # 构建URL
        if source == 'oddsportal':
            if league not in source_config['supported_leagues']:
                self.logger.warning(f"联赛 {league} 可能不被 {source} 支持")
            
            # 使用模板构建URL
            url = source_config['url_template'].format(
                country=league.split('/')[0],
                league=league.split('/')[1] if '/' in league else league
            )
            
            # 添加日期参数
            if date_range:
                url += f"results/#/page/{date_range[0]}/{date_range[1]}/"
            
        elif source == 'flashscore':
            url = source_config['url_template'].format(
                country=league.split('/')[0],
                league=league.split('/')[1] if '/' in league else league
            )
            
            # 添加日期参数
            if date_range:
                url += f"results/?date={date_range[0]}-{date_range[1]}"
                
        elif source == 'bet365':
            # Bet365需要具体的比赛ID
            if 'requires_fixture_id' in source_config and source_config['requires_fixture_id']:
                self.logger.warning("Bet365需要具体的比赛ID，请提供fixture_id参数")
                return None
            url = source_config['url_template']
        
        self.logger.info(f"开始获取赔率数据: {source} -> {league}")
        self.logger.debug(f"请求URL: {url}")
        
        # 发送请求
        response = self.make_request(url)
        if response and response.status_code == 200:
            return response.text
        else:
            self.logger.error(f"获取数据失败: {url}")
            return None
    
    def parse_oddsportal(self, html_content: str) -> List[Dict]:
        """解析OddsPortal网站数据"""
        soup = self.parse_html(html_content)
        matches = []
        
        try:
            # 查找比赛表格（根据OddsPortal的实际结构）
            # 注意：实际使用时需要根据网站结构调整选择器
            tables = soup.find_all('table', class_=re.compile(r'table-main'))
            
            for table in tables:
                # 查找比赛行
                rows = table.find_all('tr', class_=re.compile(r'deactivate'))
                
                for row in rows:
                    try:
                        # 解析比赛信息
                        match_info = self._parse_oddsportal_match(row)
                        if match_info:
                            matches.append(match_info)
                    except Exception as e:
                        self.logger.warning(f"解析比赛行失败: {e}")
                        continue
            
        except Exception as e:
            self.logger.error(f"解析OddsPortal数据失败: {e}")
        
        return matches
    
    def _parse_oddsportal_match(self, row) -> Optional[Dict]:
        """解析OddsPortal单个比赛行"""
        try:
            # 球队名称
            teams_cell = row.find('td', class_=re.compile(r'name'))
            if not teams_cell:
                return None
            
            team_elements = teams_cell.find_all('a')
            if len(team_elements) >= 2:
                home_team = team_elements[0].text.strip()
                away_team = team_elements[1].text.strip()
            else:
                # 备用解析方法
                teams_text = teams_cell.text.strip()
                if ' - ' in teams_text:
                    home_team, away_team = teams_text.split(' - ', 1)
                else:
                    return None
            
            # 比赛时间
            time_cell = row.find('td', class_=re.compile(r'time'))
            match_time = time_cell.text.strip() if time_cell else None
            
            # 赔率数据
            odds_cells = row.find_all('td', class_=re.compile(r'odds'))
            odds_data = {}
            
            if len(odds_cells) >= 3:
                # 主胜、平局、客胜
                odds_data['home_win'] = self._parse_odds_value(odds_cells[0].text)
                odds_data['draw'] = self._parse_odds_value(odds_cells[1].text)
                odds_data['away_win'] = self._parse_odds_value(odds_cells[2].text)
            
            # 构建比赛数据
            match_data = {
                'home_team': home_team,
                'away_team': away_team,
                'match_time': match_time,
                'odds': odds_data,
                'source': 'oddsportal',
                'scraped_at': datetime.now().isoformat()
            }
            
            return match_data
            
        except Exception as e:
            self.logger.debug(f"解析比赛行详细失败: {e}")
            return None
    
    def parse_flashscore(self, html_content: str) -> List[Dict]:
        """解析FlashScore网站数据"""
        soup = self.parse_html(html_content)
        matches = []
        
        try:
            # FlashScore比赛选择器
            match_elements = soup.find_all('div', class_=re.compile(r'event__match'))
            
            for match_element in match_elements:
                try:
                    match_info = self._parse_flashscore_match(match_element)
                    if match_info:
                        matches.append(match_info)
                except Exception as e:
                    self.logger.warning(f"解析FlashScore比赛失败: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"解析FlashScore数据失败: {e}")
        
        return matches
    
    def _parse_flashscore_match(self, match_element) -> Optional[Dict]:
        """解析FlashScore单个比赛"""
        try:
            # 球队信息
            home_team_elem = match_element.find('div', class_=re.compile(r'event__participant--home'))
            away_team_elem = match_element.find('div', class_=re.compile(r'event__participant--away'))
            
            home_team = home_team_elem.text.strip() if home_team_elem else None
            away_team = away_team_elem.text.strip() if away_team_elem else None
            
            if not home_team or not away_team:
                return None
            
            # 比赛时间
            time_elem = match_element.find('div', class_=re.compile(r'event__time'))
            match_time = time_elem.text.strip() if time_elem else None
            
            # 比分（如果有）
            score_elem = match_element.find('div', class_=re.compile(r'event__score'))
            score = score_elem.text.strip() if score_elem else None
            
            # 赔率数据（FlashScore可能需要点击查看）
            odds_data = {}
            
            # 构建比赛数据
            match_data = {
                'home_team': home_team,
                'away_team': away_team,
                'match_time': match_time,
                'score': score,
                'odds': odds_data,
                'source': 'flashscore',
                'scraped_at': datetime.now().isoformat()
            }
            
            return match_data
            
        except Exception as e:
            self.logger.debug(f"解析FlashScore比赛详细失败: {e}")
            return None
    
    def fetch_live_odds(self, home_team: str, away_team: str) -> Dict:
        """
        获取实时的盘口和水位变动数据 (Water Changes)
        首选尝试从真实网页抓取数据，如果失败则回退到基于哈希的稳定模拟数据。
        """
        import random
        import requests
        from bs4 import BeautifulSoup
        
        # --- 尝试真实抓取 澳客网 竞彩数据 ---
        try:
            url = 'http://www.okooo.com/jingcai/'
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, proxies={'http': None, 'https': None}, timeout=5)
            res.encoding = 'gb2312'
            soup = BeautifulSoup(res.text, 'html.parser')
            matches = soup.find_all('div', class_='touzhu_1')
            
            # 简单名称匹配 (真实场景可以加模糊匹配)
            for m in matches:
                h_name = m.get('data-hname', '')
                a_name = m.get('data-aname', '')
                
                # 如果包含关键字就认为是我们要找的比赛
                if (h_name and h_name in home_team) or (home_team in h_name) or (a_name and a_name in away_team) or (away_team in a_name):
                    rq = m.get('data-rq', '0')
                    
                    # 提取不让球胜平负 (wf=0)
                    spf_odds = []
                    for opt in m.find_all('div', attrs={'data-wf': '0'}):
                        sp = opt.get('data-sp')
                        if sp and float(sp) > 0: spf_odds.append(float(sp))
                    
                    # 提取让球胜平负 (wf=1)
                    rqspf_odds = []
                    for opt in m.find_all('div', attrs={'data-wf': '1'}):
                        sp = opt.get('data-sp')
                        if sp and float(sp) > 0: rqspf_odds.append(float(sp))
                        
                    if len(spf_odds) == 3:
                        return {
                            "match": f"{home_team} vs {away_team}",
                            "bookmaker": "Okooo (Real Data)",
                            "update_time": datetime.now().isoformat(),
                            "european_odds": {
                                "initial": {
                                    "home": spf_odds[0], "draw": spf_odds[1], "away": spf_odds[2]
                                },
                                "live": {
                                    "home": spf_odds[0], "draw": spf_odds[1], "away": spf_odds[2]
                                },
                                "home_water_trend": "stable",
                                "home_drop_amplitude": 0
                            },
                            "asian_handicap": {
                                "line": float(rq) if rq else 0,
                                "home_odds": rqspf_odds[0] if len(rqspf_odds) == 3 else 0,
                                "away_odds": rqspf_odds[2] if len(rqspf_odds) == 3 else 0
                            }
                        }
        except Exception as e:
            self.logger.warning(f"真实数据抓取失败, 回退到智能模拟: {e}")
            pass
            
        # --- 回退到基于球队名称 Hash 的智能模拟 (保证流程完整) ---
        base_hash = hash(home_team + away_team)
        
        # 模拟初盘 (Initial Odds)
        # 假设主队稍占优
        initial_home = round(random.Random(base_hash).uniform(1.8, 2.5), 2)
        initial_draw = round(random.Random(base_hash + 1).uniform(3.0, 3.5), 2)
        
        # 保证隐含概率和在 1.05 左右 (庄家抽水 5%)
        implied_home = 1 / initial_home
        implied_draw = 1 / initial_draw
        implied_away = 1.05 - implied_home - implied_draw
        
        if implied_away <= 0.1:
            implied_away = 0.1
        initial_away = round(1 / implied_away, 2)
        
        # 模拟即时盘 (Live Odds) - 产生随机的水位波动
        # 假设受到资金影响，主队可能降水(赔率下降)或升水(赔率上升)
        water_change_factor = random.Random(base_hash + 2).uniform(-0.15, 0.15)
        
        live_home = round(initial_home + water_change_factor, 2)
        live_draw = round(initial_draw + random.Random(base_hash + 3).uniform(-0.05, 0.05), 2)
        
        implied_live_home = 1 / live_home
        implied_live_draw = 1 / live_draw
        implied_live_away = 1.05 - implied_live_home - implied_live_draw
        if implied_live_away <= 0.1:
            implied_live_away = 0.1
        live_away = round(1 / implied_live_away, 2)
        
        # 分析水位趋势
        trend = "dropping" if live_home < initial_home else "rising" if live_home > initial_home else "stable"
        
        # 模拟让球盘 (Asian Handicap)
        # 简单的让球逻辑：如果主胜赔率约2.0，让球大概是 0 或 -0.25
        if live_home < 1.5:
            handicap_line = -1.0
        elif live_home < 1.8:
            handicap_line = -0.5
        elif live_home < 2.2:
            handicap_line = -0.25
        elif live_home < 2.6:
            handicap_line = 0.0
        else:
            handicap_line = 0.25
            
        handicap_home_odds = 1.90
        handicap_away_odds = 1.90
        
        return {
            "match": f"{home_team} vs {away_team}",
            "bookmaker": "Pinnacle (Simulated)",
            "update_time": datetime.now().isoformat(),
            "european_odds": {
                "initial": {
                    "home": initial_home,
                    "draw": initial_draw,
                    "away": initial_away
                },
                "live": {
                    "home": live_home,
                    "draw": live_draw,
                    "away": live_away
                },
                "home_water_trend": trend,
                "home_drop_amplitude": round(initial_home - live_home, 2)
            },
            "asian_handicap": {
                "line": handicap_line,
                "home_odds": handicap_home_odds,
                "away_odds": handicap_away_odds
            }
        }

    def _parse_odds_value(self, odds_text: str) -> Optional[float]:
        """解析赔率值"""
        try:
            # 清理文本
            clean_text = odds_text.strip()
            if not clean_text or clean_text == '-':
                return None
            
            # 移除可能的分母格式
            if '/' in clean_text:
                numerator, denominator = clean_text.split('/')
                return float(numerator) / float(denominator) + 1
            
            # 直接转换为浮点数
            return float(clean_text)
        except Exception as e:
            self.logger.debug(f"解析赔率值失败: {odds_text}, 错误: {e}")
            return None
    
    def process_data(self, raw_data: Any) -> List[Dict]:
        """
        处理原始赔率数据
        
        Args:
            raw_data: 原始HTML数据
            
        Returns:
            处理后的赔率数据列表
        """
        if isinstance(raw_data, str):
            # 假设是OddsPortal的数据
            matches = self.parse_oddsportal(raw_data)
        elif isinstance(raw_data, dict) and 'source' in raw_data:
            # 已解析的数据
            source = raw_data['source']
            html_content = raw_data.get('html')
            
            if source == 'oddsportal' and html_content:
                matches = self.parse_oddsportal(html_content)
            elif source == 'flashscore' and html_content:
                matches = self.parse_flashscore(html_content)
            else:
                matches = []
        else:
            matches = []
        
        # 标准化数据
        standardized_matches = []
        for match in matches:
            standardized_match = self._standardize_match_data(match)
            if standardized_match:
                standardized_matches.append(standardized_match)
        
        # 计算附加指标
        enriched_matches = []
        for match in standardized_matches:
            enriched_match = self._enrich_odds_data(match)
            enriched_matches.append(enriched_match)
        
        return enriched_matches
    
    def _standardize_match_data(self, match_data: Dict) -> Optional[Dict]:
        """标准化比赛数据"""
        try:
            # 基础验证
            required_fields = ['home_team', 'away_team']
            for field in required_fields:
                if field not in match_data or not match_data[field]:
                    return None
            
            # 标准化球队名称
            standardized_data = {
                'home_team': self._standardize_team_name(match_data['home_team']),
                'away_team': self._standardize_team_name(match_data['away_team']),
                'match_time': match_data.get('match_time'),
                'source': match_data.get('source', 'unknown'),
                'scraped_at': match_data.get('scraped_at', datetime.now().isoformat())
            }
            
            # 处理赔率数据
            if 'odds' in match_data and match_data['odds']:
                standardized_odds = {}
                for odds_key, odds_value in match_data['odds'].items():
                    if odds_value is not None:
                        # 转换为标准格式
                        standardized_odds[odds_key] = {
                            'value': float(odds_value),
                            'type': self.odds_type_mapping.get(odds_key, odds_key)
                        }
                
                if standardized_odds:
                    standardized_data['odds'] = standardized_odds
            
            # 如果有比分，也保存
            if 'score' in match_data:
                standardized_data['score'] = match_data['score']
            
            return standardized_data
            
        except Exception as e:
            self.logger.warning(f"标准化比赛数据失败: {e}")
            return None
    
    def _standardize_team_name(self, team_name: str) -> str:
        """标准化球队名称"""
        # 移除多余空格
        name = team_name.strip()
        
        # 常见球队名称映射
        team_mapping = {
            'man united': 'Manchester United',
            'man utd': 'Manchester United',
            'man city': 'Manchester City',
            'chelsea fc': 'Chelsea',
            'liverpool fc': 'Liverpool',
            'arsenal fc': 'Arsenal',
            'tottenham': 'Tottenham Hotspur',
            'spurs': 'Tottenham Hotspur',
            'real madrid': 'Real Madrid',
            'barcelona': 'FC Barcelona',
            'bayern munich': 'Bayern Munich',
            'juventus': 'Juventus',
            'milan': 'AC Milan',
            'inter': 'Inter Milan'
        }
        
        lower_name = name.lower()
        for key, value in team_mapping.items():
            if key in lower_name:
                return value
        
        return name
    
    def _enrich_odds_data(self, match_data: Dict) -> Dict:
        """丰富赔率数据，计算附加指标"""
        enriched_data = match_data.copy()
        
        if 'odds' in match_data:
            odds = match_data['odds']
            
            # 计算隐含概率
            if 'home_win' in odds and 'draw' in odds and 'away_win' in odds:
                home_odds = odds['home_win']['value']
                draw_odds = odds['draw']['value']
                away_odds = odds['away_win']['value']
                
                # 计算隐含概率
                home_prob = 1 / home_odds if home_odds > 0 else 0
                draw_prob = 1 / draw_odds if draw_odds > 0 else 0
                away_prob = 1 / away_odds if away_odds > 0 else 0
                
                total_prob = home_prob + draw_prob + away_prob
                
                # 调整概率（博彩公司抽水）
                if total_prob > 0:
                    adjustment = 1 / total_prob
                    home_prob_adj = home_prob * adjustment
                    draw_prob_adj = draw_prob * adjustment
                    away_prob_adj = away_prob * adjustment
                    
                    enriched_data['probabilities'] = {
                        'home_win': home_prob_adj,
                        'draw': draw_prob_adj,
                        'away_win': away_prob_adj,
                        'total_prob_before_adjustment': total_prob,
                        'bookmaker_margin': total_prob - 1 if total_prob > 1 else 0
                    }
            
            # 计算期望值（如果赔率明显偏离）
            # 这里可以根据历史数据计算期望值
            
            # 识别价值投注机会
            # 这里可以添加基于模型的识别逻辑
        
        return enriched_data
    
    def get_odds_for_league(self, league: str, days: int = 7) -> List[Dict]:
        """
        获取指定联赛未来几天的赔率数据
        
        Args:
            league: 联赛标识
            days: 天数
            
        Returns:
            赔率数据列表
        """
        end_date = datetime.now() + timedelta(days=days)
        date_range = (
            datetime.now().strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        
        results = []
        
        # 从多个数据源获取数据
        for source in ['oddsportal', 'flashscore']:
            try:
                raw_data = self.fetch_data(source, league, date_range)
                if raw_data:
                    processed_data = self.process_data(raw_data)
                    results.extend(processed_data)
                    self.logger.info(f"从 {source} 获取到 {len(processed_data)} 场比赛赔率")
            except Exception as e:
                self.logger.error(f"从 {source} 获取数据失败: {e}")
        
        # 去重（基于球队和比赛时间）
        unique_matches = {}
        for match in results:
            key = f"{match['home_team']}_{match['away_team']}_{match.get('match_time', '')}"
            if key not in unique_matches:
                unique_matches[key] = match
            else:
                # 合并赔率数据
                existing_match = unique_matches[key]
                if 'odds' in match and 'odds' in existing_match:
                    existing_match['odds'].update(match['odds'])
                    existing_match['source'] = f"{existing_match['source']},{match['source']}"
        
        return list(unique_matches.values())


if __name__ == "__main__":
    # 测试赔率爬取器
    odds_scraper = OddsScraper()
    
    print("测试赔率数据爬取...")
    
    # 获取英超赔率数据
    try:
        matches = odds_scraper.get_odds_for_league('england/premier-league', days=3)
        print(f"成功获取 {len(matches)} 场比赛赔率")
        
        if matches:
            print("\n前3场比赛信息:")
            for i, match in enumerate(matches[:3]):
                print(f"\n{i+1}. {match['home_team']} vs {match['away_team']}")
                print(f"   时间: {match.get('match_time', '未知')}")
                if 'odds' in match:
                    for odds_type, odds_info in match['odds'].items():
                        print(f"   {odds_info['type']}: {odds_info['value']:.2f}")
                
                if 'probabilities' in match:
                    probs = match['probabilities']
                    print(f"   隐含概率: 主胜 {probs['home_win']:.2%}, 平 {probs['draw']:.2%}, 客胜 {probs['away_win']:.2%}")
                    print(f"   庄家抽水: {probs['bookmaker_margin']:.2%}")
    except Exception as e:
        print(f"测试失败: {e}")
    
    print("\n赔率爬取器测试完成")