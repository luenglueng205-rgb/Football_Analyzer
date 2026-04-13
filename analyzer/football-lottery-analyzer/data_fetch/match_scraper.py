#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - 比赛信息爬取模块
抓取球队阵容、伤病情况、比赛时间场地等信息
"""

import os
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum

from .scraper import BaseScraper


class MatchStatus(Enum):
    """比赛状态枚举"""
    SCHEDULED = "scheduled"  # 已安排
    LIVE = "live"            # 进行中
    FINISHED = "finished"    # 已结束
    POSTPONED = "postponed"  # 推迟
    CANCELLED = "cancelled"  # 取消


class MatchScraper(BaseScraper):
    """比赛信息爬取器"""
    
    def __init__(self, config_file: Optional[str] = "config.json"):
        """
        初始化比赛信息爬取器
        
        Args:
            config_file: 配置文件路径
        """
        super().__init__(name="MatchScraper", config_file=config_file)
        
        # 数据源配置
        self.data_sources = {
            'transfermarkt': {
                'name': 'Transfermarkt',
                'base_url': 'https://www.transfermarkt.com',
                'supported_features': ['lineups', 'injuries', 'transfers', 'statistics']
            },
            'sofascore': {
                'name': 'SofaScore',
                'base_url': 'https://www.sofascore.com',
                'supported_features': ['lineups', 'statistics', 'h2h', 'form', 'injuries']
            },
            'premierleague': {
                'name': 'Premier League',
                'base_url': 'https://www.premierleague.com',
                'league_specific': True,
                'supported_features': ['lineups', 'stats', 'news', 'table']
            },
            'flashscore': {
                'name': 'FlashScore',
                'base_url': 'https://www.flashscore.com',
                'supported_features': ['lineups', 'results', 'standings']
            }
        }
        
        # 位置映射
        self.position_mapping = {
            'GK': 'Goalkeeper',
            'DF': 'Defender',
            'MF': 'Midfielder',
            'FW': 'Forward',
            'CB': 'Center Back',
            'RB': 'Right Back',
            'LB': 'Left Back',
            'DM': 'Defensive Midfielder',
            'CM': 'Central Midfielder',
            'AM': 'Attacking Midfielder',
            'LW': 'Left Winger',
            'RW': 'Right Winger',
            'ST': 'Striker'
        }
        
        # 伤病类型映射
        self.injury_type_mapping = {
            'muscle': '肌肉伤病',
            'ankle': '脚踝伤病',
            'knee': '膝盖伤病',
            'hamstring': '腿筋伤病',
            'groin': '腹股沟伤病',
            'shoulder': '肩部伤病',
            'head': '头部伤病',
            'illness': '疾病',
            'unknown': '未知'
        }
    
    def fetch_data(self, match_id: Optional[str] = None,
                  home_team: Optional[str] = None,
                  away_team: Optional[str] = None,
                  match_date: Optional[str] = None,
                  source: str = 'sofascore') -> Optional[Dict]:
        """
        获取比赛信息
        
        Args:
            match_id: 比赛ID
            home_team: 主队名称
            away_team: 客队名称
            match_date: 比赛日期
            source: 数据源
            
        Returns:
            包含原始数据的字典
        """
        if source not in self.data_sources:
            self.logger.error(f"不支持的数据源: {source}")
            return None
        
        source_config = self.data_sources[source]
        
        # 构建URL
        url = self._build_match_url(source, match_id, home_team, away_team, match_date)
        if not url:
            self.logger.error("无法构建URL，请提供足够的参数")
            return None
        
        self.logger.info(f"开始获取比赛信息: {source} -> {url}")
        
        # 发送请求
        response = self.make_request(url)
        if response and response.status_code == 200:
            result = {
                'source': source,
                'url': url,
                'html': response.text,
                'scraped_at': datetime.now().isoformat(),
                'match_info': {
                    'match_id': match_id,
                    'home_team': home_team,
                    'away_team': away_team,
                    'match_date': match_date
                }
            }
            return result
        else:
            self.logger.error(f"获取比赛信息失败: {url}")
            return None
    
    def _build_match_url(self, source: str, match_id: Optional[str],
                        home_team: Optional[str], away_team: Optional[str],
                        match_date: Optional[str]) -> Optional[str]:
        """构建比赛URL"""
        base_url = self.data_sources[source]['base_url']
        
        if source == 'sofascore':
            # SofaScore使用比赛ID
            if match_id:
                return f"{base_url}/football/match/{match_id}"
            else:
                # 尝试通过球队和日期搜索
                # 这里简化处理，实际应该调用搜索接口
                return None
        
        elif source == 'transfermarkt':
            # Transfermarkt需要具体比赛页面
            if match_id:
                return f"{base_url}/spielbericht/index/spielbericht/{match_id}"
            else:
                # 可以通过搜索构建
                return None
        
        elif source == 'premierleague':
            # 英超官网
            if match_id:
                return f"{base_url}/match/{match_id}"
            else:
                # 英超官网有具体的URL模式
                return None
        
        elif source == 'flashscore':
            if match_id:
                return f"{base_url}/match/{match_id}/#/match-summary/match-summary"
            else:
                return None
        
        return None
    
    def fetch_lineups(self, match_info: Dict, source: str = 'sofascore') -> Optional[Dict]:
        """获取阵容信息"""
        raw_data = self.fetch_data(
            match_id=match_info.get('match_id'),
            home_team=match_info.get('home_team'),
            away_team=match_info.get('away_team'),
            match_date=match_info.get('match_date'),
            source=source
        )
        
        if not raw_data:
            return None
        
        # 解析阵容
        if source == 'sofascore':
            lineups = self._parse_sofascore_lineups(raw_data['html'])
        elif source == 'transfermarkt':
            lineups = self._parse_transfermarkt_lineups(raw_data['html'])
        elif source == 'premierleague':
            lineups = self._parse_premierleague_lineups(raw_data['html'])
        else:
            lineups = None
        
        if lineups:
            lineups.update({
                'source': source,
                'scraped_at': raw_data['scraped_at'],
                'match_info': match_info
            })
        
        return lineups
    
    def _parse_sofascore_lineups(self, html_content: str) -> Optional[Dict]:
        """解析SofaScore阵容"""
        soup = self.parse_html(html_content)
        lineups = {'home_team': {}, 'away_team': {}}
        
        try:
            # SofaScore的阵容选择器（可能需要根据实际页面调整）
            lineup_sections = soup.find_all('div', class_=re.compile(r'lineup'))
            
            if len(lineup_sections) >= 2:
                # 假设前两个是主客队阵容
                home_lineup = self._extract_sofascore_players(lineup_sections[0])
                away_lineup = self._extract_sofascore_players(lineup_sections[1])
                
                lineups['home_team'] = home_lineup
                lineups['away_team'] = away_lineup
                
                # 提取阵型
                formation_elements = soup.find_all('div', class_=re.compile(r'formation'))
                if len(formation_elements) >= 2:
                    lineups['home_formation'] = formation_elements[0].text.strip()
                    lineups['away_formation'] = formation_elements[1].text.strip()
            
            return lineups
            
        except Exception as e:
            self.logger.error(f"解析SofaScore阵容失败: {e}")
            return None
    
    def _extract_sofascore_players(self, lineup_section) -> Dict:
        """从SofaScore阵容区域提取球员信息"""
        players = []
        
        try:
            player_elements = lineup_section.find_all('div', class_=re.compile(r'player'))
            
            for player_elem in player_elements:
                try:
                    # 球员名称
                    name_elem = player_elem.find('a', class_=re.compile(r'player-name'))
                    name = name_elem.text.strip() if name_elem else None
                    
                    # 球员号码
                    number_elem = player_elem.find('div', class_=re.compile(r'player-number'))
                    number = number_elem.text.strip() if number_elem else None
                    
                    # 位置
                    position_elem = player_elem.find('div', class_=re.compile(r'position'))
                    position = position_elem.text.strip() if position_elem else None
                    
                    if name:
                        player_info = {
                            'name': name,
                            'number': number,
                            'position': position,
                            'position_full': self.position_mapping.get(position, position)
                        }
                        players.append(player_info)
                except Exception as e:
                    self.logger.debug(f"解析单个球员失败: {e}")
                    continue
        
        except Exception as e:
            self.logger.debug(f"提取球员失败: {e}")
        
        return {'players': players, 'count': len(players)}
    
    def _parse_transfermarkt_lineups(self, html_content: str) -> Optional[Dict]:
        """解析Transfermarkt阵容"""
        soup = self.parse_html(html_content)
        lineups = {'home_team': {}, 'away_team': {}}
        
        try:
            # Transfermarkt阵容表格
            lineup_tables = soup.find_all('table', class_=re.compile(r'aufstellung'))
            
            if len(lineup_tables) >= 2:
                home_lineup = self._extract_transfermarkt_players(lineup_tables[0])
                away_lineup = self._extract_transfermarkt_players(lineup_tables[1])
                
                lineups['home_team'] = home_lineup
                lineups['away_team'] = away_lineup
            
            return lineups
            
        except Exception as e:
            self.logger.error(f"解析Transfermarkt阵容失败: {e}")
            return None
    
    def _extract_transfermarkt_players(self, lineup_table) -> Dict:
        """从Transfermarkt表格提取球员信息"""
        players = []
        
        try:
            rows = lineup_table.find_all('tr')
            
            for row in rows:
                try:
                    # 球员名称单元格
                    name_cell = row.find('td', class_=re.compile(r'name'))
                    if not name_cell:
                        continue
                    
                    # 球员名称链接
                    name_link = name_cell.find('a')
                    name = name_link.text.strip() if name_link else name_cell.text.strip()
                    
                    # 位置
                    position_cell = row.find('td', class_=re.compile(r'pos'))
                    position = position_cell.text.strip() if position_cell else None
                    
                    # 号码
                    number_cell = row.find('td', class_=re.compile(r'rnr'))
                    number = number_cell.text.strip() if number_cell else None
                    
                    if name:
                        player_info = {
                            'name': name,
                            'number': number,
                            'position': position,
                            'position_full': self.position_mapping.get(position, position)
                        }
                        players.append(player_info)
                except Exception as e:
                    self.logger.debug(f"解析Transfermarkt球员行失败: {e}")
                    continue
        
        except Exception as e:
            self.logger.debug(f"提取Transfermarkt球员失败: {e}")
        
        return {'players': players, 'count': len(players)}
    
    def _parse_premierleague_lineups(self, html_content: str) -> Optional[Dict]:
        """解析英超官网阵容"""
        soup = self.parse_html(html_content)
        lineups = {'home_team': {}, 'away_team': {}}
        
        try:
            # 英超官网阵容区域
            lineup_containers = soup.find_all('div', class_=re.compile(r'startingLineup'))
            
            if len(lineup_containers) >= 2:
                home_lineup = self._extract_premierleague_players(lineup_containers[0])
                away_lineup = self._extract_premierleague_players(lineup_containers[1])
                
                lineups['home_team'] = home_lineup
                lineups['away_team'] = away_lineup
            
            # 提取阵型
            formation_elements = soup.find_all('div', class_=re.compile(r'formation'))
            if len(formation_elements) >= 2:
                lineups['home_formation'] = formation_elements[0].text.strip()
                lineups['away_formation'] = formation_elements[1].text.strip()
            
            return lineups
            
        except Exception as e:
            self.logger.error(f"解析英超官网阵容失败: {e}")
            return None
    
    def _extract_premierleague_players(self, lineup_container) -> Dict:
        """从英超官网阵容容器提取球员信息"""
        players = []
        
        try:
            player_items = lineup_container.find_all('li', class_=re.compile(r'player'))
            
            for player_item in player_items:
                try:
                    # 球员名称
                    name_elem = player_item.find('span', class_=re.compile(r'name'))
                    name = name_elem.text.strip() if name_elem else None
                    
                    # 球员号码
                    number_elem = player_item.find('span', class_=re.compile(r'number'))
                    number = number_elem.text.strip() if number_elem else None
                    
                    # 位置
                    position_elem = player_item.find('span', class_=re.compile(r'position'))
                    position = position_elem.text.strip() if position_elem else None
                    
                    if name:
                        player_info = {
                            'name': name,
                            'number': number,
                            'position': position,
                            'position_full': self.position_mapping.get(position, position)
                        }
                        players.append(player_info)
                except Exception as e:
                    self.logger.debug(f"解析英超球员项失败: {e}")
                    continue
        
        except Exception as e:
            self.logger.debug(f"提取英超球员失败: {e}")
        
        return {'players': players, 'count': len(players)}
    
    def fetch_injuries(self, team_name: str, source: str = 'transfermarkt') -> Optional[List[Dict]]:
        """获取伤病信息"""
        if source not in self.data_sources:
            self.logger.error(f"不支持的数据源: {source}")
            return None
        
        # 构建URL
        if source == 'transfermarkt':
            # Transfermarkt伤病页面
            # 需要先获取球队ID，这里简化处理
            url = f"{self.data_sources[source]['base_url']}/verletzungen/verein/xxx"  # 需要实际ID
        elif source == 'sofascore':
            # SofaScore伤病信息
            url = f"{self.data_sources[source]['base_url']}/team/football/xxx/injuries"  # 需要实际ID
        else:
            self.logger.warning(f"数据源 {source} 不支持伤病信息")
            return None
        
        self.logger.info(f"开始获取伤病信息: {team_name} -> {source}")
        
        # 发送请求
        response = self.make_request(url)
        if not response or response.status_code != 200:
            return None
        
        # 解析伤病信息
        if source == 'transfermarkt':
            injuries = self._parse_transfermarkt_injuries(response.text, team_name)
        elif source == 'sofascore':
            injuries = self._parse_sofascore_injuries(response.text, team_name)
        else:
            injuries = []
        
        return injuries
    
    def _parse_transfermarkt_injuries(self, html_content: str, team_name: str) -> List[Dict]:
        """解析Transfermarkt伤病信息"""
        soup = self.parse_html(html_content)
        injuries = []
        
        try:
            # Transfermarkt伤病表格
            injury_table = soup.find('table', class_=re.compile(r'verletzungen'))
            if not injury_table:
                return injuries
            
            rows = injury_table.find_all('tr')[1:]  # 跳过标题行
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 4:
                        continue
                    
                    # 球员名称
                    player_cell = cells[0]
                    player_link = player_cell.find('a')
                    player_name = player_link.text.strip() if player_link else player_cell.text.strip()
                    
                    # 伤病类型
                    injury_type_cell = cells[1]
                    injury_type = injury_type_cell.text.strip()
                    
                    # 预计回归时间
                    return_date_cell = cells[2]
                    return_date = return_date_cell.text.strip()
                    
                    # 状态
                    status_cell = cells[3]
                    status = status_cell.text.strip()
                    
                    injury_info = {
                        'player_name': player_name,
                        'team': team_name,
                        'injury_type': injury_type,
                        'injury_type_cn': self.injury_type_mapping.get(
                            injury_type.lower(), '未知'
                        ),
                        'expected_return': return_date,
                        'status': status,
                        'source': 'transfermarkt',
                        'scraped_at': datetime.now().isoformat()
                    }
                    injuries.append(injury_info)
                except Exception as e:
                    self.logger.debug(f"解析伤病行失败: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"解析Transfermarkt伤病失败: {e}")
        
        return injuries
    
    def _parse_sofascore_injuries(self, html_content: str, team_name: str) -> List[Dict]:
        """解析SofaScore伤病信息"""
        soup = self.parse_html(html_content)
        injuries = []
        
        try:
            # SofaScore伤病项目
            injury_items = soup.find_all('div', class_=re.compile(r'injury-item'))
            
            for item in injury_items:
                try:
                    # 球员名称
                    player_elem = item.find('a', class_=re.compile(r'player-name'))
                    player_name = player_elem.text.strip() if player_elem else None
                    
                    # 伤病信息
                    injury_elem = item.find('div', class_=re.compile(r'injury-info'))
                    injury_text = injury_elem.text.strip() if injury_elem else ''
                    
                    # 解析伤病文本
                    injury_type = 'unknown'
                    return_date = None
                    
                    # 简单解析（实际应更复杂）
                    if 'muscle' in injury_text.lower():
                        injury_type = 'muscle'
                    elif 'ankle' in injury_text.lower():
                        injury_type = 'ankle'
                    elif 'knee' in injury_text.lower():
                        injury_type = 'knee'
                    
                    # 尝试提取日期
                    date_pattern = r'\d{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2}'
                    date_matches = re.findall(date_pattern, injury_text)
                    if date_matches:
                        return_date = date_matches[0]
                    
                    if player_name:
                        injury_info = {
                            'player_name': player_name,
                            'team': team_name,
                            'injury_type': injury_type,
                            'injury_type_cn': self.injury_type_mapping.get(injury_type, '未知'),
                            'injury_description': injury_text,
                            'expected_return': return_date,
                            'source': 'sofascore',
                            'scraped_at': datetime.now().isoformat()
                        }
                        injuries.append(injury_info)
                except Exception as e:
                    self.logger.debug(f"解析SofaScore伤病项失败: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"解析SofaScore伤病失败: {e}")
        
        return injuries
    
    def fetch_match_details(self, match_info: Dict, include_all: bool = False) -> Dict:
        """
        获取比赛详细信息
        
        Args:
            match_info: 比赛基本信息
            include_all: 是否包含所有详细信息
            
        Returns:
            比赛详细信息字典
        """
        result = {
            'match_info': match_info.copy(),
            'scraped_at': datetime.now().isoformat(),
            'sources': []
        }
        
        # 尝试从多个数据源获取信息
        sources_to_try = ['sofascore', 'transfermarkt', 'flashscore']
        
        for source in sources_to_try:
            try:
                source_data = self.fetch_data(
                    match_id=match_info.get('match_id'),
                    home_team=match_info.get('home_team'),
                    away_team=match_info.get('away_team'),
                    match_date=match_info.get('match_date'),
                    source=source
                )
                
                if source_data:
                    # 解析基础信息
                    match_details = self._extract_match_details(source_data['html'], source)
                    if match_details:
                        result['sources'].append({
                            'name': source,
                            'url': source_data['url'],
                            'details': match_details
                        })
                        
                        # 合并信息（优先使用第一个成功的数据源）
                        if 'basic_info' not in result:
                            result['basic_info'] = match_details.get('basic_info', {})
                        
                        # 获取阵容信息
                        if include_all:
                            lineups = self.fetch_lineups(match_info, source)
                            if lineups and 'lineups' not in result:
                                result['lineups'] = lineups
            except Exception as e:
                self.logger.warning(f"从 {source} 获取比赛详情失败: {e}")
                continue
        
        # 获取伤病信息
        if include_all and 'home_team' in match_info and 'away_team' in match_info:
            try:
                home_injuries = self.fetch_injuries(match_info['home_team'], 'transfermarkt')
                away_injuries = self.fetch_injuries(match_info['away_team'], 'transfermarkt')
                
                if home_injuries or away_injuries:
                    result['injuries'] = {
                        'home_team': home_injuries or [],
                        'away_team': away_injuries or []
                    }
            except Exception as e:
                self.logger.warning(f"获取伤病信息失败: {e}")
        
        return result
    
    def _extract_match_details(self, html_content: str, source: str) -> Optional[Dict]:
        """提取比赛详情"""
        soup = self.parse_html(html_content)
        details = {'basic_info': {}, 'additional_info': {}}
        
        try:
            # 提取基础信息
            if source == 'sofascore':
                # 比赛状态
                status_elem = soup.find('div', class_=re.compile(r'match-status'))
                if status_elem:
                    status_text = status_elem.text.strip().lower()
                    if 'finished' in status_text:
                        details['basic_info']['status'] = MatchStatus.FINISHED.value
                    elif 'live' in status_text:
                        details['basic_info']['status'] = MatchStatus.LIVE.value
                    else:
                        details['basic_info']['status'] = MatchStatus.SCHEDULED.value
                
                # 比分
                score_elem = soup.find('div', class_=re.compile(r'scoreboard'))
                if score_elem:
                    details['basic_info']['score'] = score_elem.text.strip()
                
                # 比赛时间
                time_elem = soup.find('div', class_=re.compile(r'start-time'))
                if time_elem:
                    details['basic_info']['match_time'] = time_elem.text.strip()
            
            elif source == 'transfermarkt':
                # Transfermarkt详情提取
                info_cells = soup.find_all('td', class_=re.compile(r'daten'))
                for cell in info_cells:
                    label = cell.find_previous('td', class_=re.compile(r'label'))
                    if label:
                        label_text = label.text.strip().lower()
                        value_text = cell.text.strip()
                        
                        if 'date' in label_text:
                            details['basic_info']['match_date'] = value_text
                        elif 'time' in label_text:
                            details['basic_info']['match_time'] = value_text
                        elif 'venue' in label_text:
                            details['basic_info']['venue'] = value_text
                        elif 'referee' in label_text:
                            details['basic_info']['referee'] = value_text
            
            # 提取统计数据
            stats = self._extract_match_stats(soup, source)
            if stats:
                details['additional_info']['statistics'] = stats
            
            return details
            
        except Exception as e:
            self.logger.error(f"提取比赛详情失败 ({source}): {e}")
            return None
    
    def _extract_match_stats(self, soup, source: str) -> Dict:
        """提取比赛统计数据"""
        stats = {}
        
        try:
            if source == 'sofascore':
                # SofaScore统计数据
                stat_items = soup.find_all('div', class_=re.compile(r'stat-item'))
                
                for item in stat_items:
                    try:
                        label_elem = item.find('div', class_=re.compile(r'stat-label'))
                        value_elem = item.find('div', class_=re.compile(r'stat-value'))
                        
                        if label_elem and value_elem:
                            label = label_elem.text.strip().lower()
                            value = value_elem.text.strip()
                            stats[label] = value
                    except:
                        continue
            
            elif source == 'flashscore':
                # FlashScore统计数据
                stat_rows = soup.find_all('div', class_=re.compile(r'stat-row'))
                
                for row in stat_rows:
                    try:
                        label_elem = row.find('div', class_=re.compile(r'stat-name'))
                        home_elem = row.find('div', class_=re.compile(r'homeValue'))
                        away_elem = row.find('div', class_=re.compile(r'awayValue'))
                        
                        if label_elem and home_elem and away_elem:
                            label = label_elem.text.strip().lower()
                            stats[f'{label}_home'] = home_elem.text.strip()
                            stats[f'{label}_away'] = away_elem.text.strip()
                    except:
                        continue
        
        except Exception as e:
            self.logger.debug(f"提取统计数据失败: {e}")
        
        return stats
    
    def process_data(self, raw_data: Any) -> Dict:
        """
        处理原始比赛数据
        
        Args:
            raw_data: 原始数据
            
        Returns:
            处理后的比赛数据
        """
        if isinstance(raw_data, dict) and 'sources' in raw_data:
            # 已经是处理过的数据
            return raw_data
        
        # 处理单个数据源的情况
        if isinstance(raw_data, dict) and 'html' in raw_data:
            source = raw_data.get('source', 'unknown')
            match_info = raw_data.get('match_info', {})
            
            # 提取详情
            details = self._extract_match_details(raw_data['html'], source)
            if not details:
                details = {'basic_info': {}, 'additional_info': {}}
            
            result = {
                'match_info': match_info,
                'scraped_at': raw_data.get('scraped_at', datetime.now().isoformat()),
                'sources': [{
                    'name': source,
                    'url': raw_data.get('url'),
                    'details': details
                }],
                'basic_info': details.get('basic_info', {})
            }
            
            return result
        
        return {'error': '无法处理的数据格式'}
    
    def get_matches_for_team(self, team_name: str, days: int = 30) -> List[Dict]:
        """
        获取球队未来几天的比赛
        
        Args:
            team_name: 球队名称
            days: 天数
            
        Returns:
            比赛列表
        """
        # 这里简化实现，实际应该调用具体API或搜索
        self.logger.info(f"获取球队 {team_name} 未来 {days} 天的比赛")
        
        # 模拟数据
        matches = []
        today = datetime.now()
        
        for i in range(days):
            match_date = today + timedelta(days=i)
            
            # 模拟比赛安排
            if i % 3 == 0:  # 每3天一场比赛
                match_info = {
                    'match_id': f"match_{team_name.lower().replace(' ', '_')}_{match_date.strftime('%Y%m%d')}",
                    'home_team': team_name if i % 6 == 0 else f"Opponent {i}",
                    'away_team': f"Opponent {i}" if i % 6 == 0 else team_name,
                    'match_date': match_date.strftime('%Y-%m-%d'),
                    'match_time': '15:00',
                    'venue': 'Home Stadium' if i % 6 == 0 else 'Away Stadium',
                    'competition': 'Premier League'
                }
                matches.append(match_info)
        
        return matches


if __name__ == "__main__":
    # 测试比赛信息爬取器
    match_scraper = MatchScraper()
    
    print("测试比赛信息爬取...")
    
    # 测试阵容获取（模拟）
    print("\n1. 测试阵容信息获取:")
    test_match_info = {
        'match_id': '12345',
        'home_team': 'Manchester United',
        'away_team': 'Liverpool',
        'match_date': '2024-12-25'
    }
    
    try:
        # 注意：实际测试需要真实的比赛ID和数据源可用
        print(f"  比赛: {test_match_info['home_team']} vs {test_match_info['away_team']}")
        print(f"  日期: {test_match_info['match_date']}")
        
        # 由于没有真实数据源，这里演示数据处理
        sample_lineups = {
            'home_team': {
                'players': [
                    {'name': 'Player 1', 'number': '1', 'position': 'GK'},
                    {'name': 'Player 2', 'number': '4', 'position': 'DF'}
                ],
                'count': 2
            },
            'away_team': {
                'players': [
                    {'name': 'Player A', 'number': '1', 'position': 'GK'},
                    {'name': 'Player B', 'number': '5', 'position': 'DF'}
                ],
                'count': 2
            },
            'home_formation': '4-3-3',
            'away_formation': '4-4-2',
            'source': 'test',
            'scraped_at': datetime.now().isoformat()
        }
        
        print(f"  主队阵型: {sample_lineups.get('home_formation')}")
        print(f"  客队阵型: {sample_lineups.get('away_formation')}")
        print(f"  主队球员数: {sample_lineups['home_team']['count']}")
        print(f"  客队球员数: {sample_lineups['away_team']['count']}")
        
    except Exception as e:
        print(f"  阵容测试失败: {e}")
    
    # 测试伤病信息获取
    print("\n2. 测试伤病信息获取:")
    try:
        # 模拟伤病数据
        sample_injuries = [
            {
                'player_name': 'John Doe',
                'team': 'Manchester United',
                'injury_type': 'muscle',
                'injury_type_cn': '肌肉伤病',
                'expected_return': '2024-12-30',
                'status': 'recovering'
            }
        ]
        
        print(f"  球队: Manchester United")
        print(f"  伤病球员数: {len(sample_injuries)}")
        for injury in sample_injuries:
            print(f"    - {injury['player_name']}: {injury['injury_type_cn']} (预计回归: {injury['expected_return']})")
        
    except Exception as e:
        print(f"  伤病测试失败: {e}")
    
    # 测试球队比赛安排
    print("\n3. 测试球队比赛安排:")
    try:
        matches = match_scraper.get_matches_for_team('Manchester United', days=14)
        print(f"  Manchester United 未来14天比赛安排:")
        for i, match in enumerate(matches[:3]):  # 只显示前3场
            home_away = "主场" if match['home_team'] == 'Manchester United' else "客场"
            print(f"    {i+1}. {match['match_date']} {home_away} vs {match['away_team'] if home_away == '主场' else match['home_team']}")
        
        if len(matches) > 3:
            print(f"    ... 还有 {len(matches) - 3} 场比赛")
    
    except Exception as e:
        print(f"  比赛安排测试失败: {e}")
    
    print("\n比赛信息爬取器测试完成")