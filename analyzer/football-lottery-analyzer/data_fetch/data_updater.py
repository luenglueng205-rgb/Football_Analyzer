#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - 数据更新器
定时更新机制，与现有JSON数据合并，历史数据追加
"""

import os
import json
import time
import shutil
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from threading import Thread, Lock
from queue import Queue
import schedule

from .config import DataFetchConfig as ConfigManager
from .odds_scraper import OddsScraper
from .match_scraper import MatchScraper
from .news_fetcher import NewsFetcher


class DataUpdater:
    """数据更新器"""
    
    def __init__(self, config_file: Optional[str] = "config.json"):
        """
        初始化数据更新器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_manager = ConfigManager(config_file)
        self.config = self.config_manager.config
        
        # 数据存储路径
        self.data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            self.config['storage']['base_dir']
        )
        
        # 子目录
        self.subdirs = self.config['storage']['subdirectories']
        
        # 初始化数据爬取器
        self.odds_scraper = OddsScraper(config_file)
        self.match_scraper = MatchScraper(config_file)
        self.news_fetcher = NewsFetcher(config_file)
        
        # 日志
        self.logger = self._setup_logger()
        
        # 任务队列
        self.task_queue = Queue()
        self.running = False
        self.lock = Lock()
        
        # 监控数据
        self.metrics = {
            'last_run': {},
            'success_count': {},
            'error_count': {},
            'total_updates': 0
        }
    
    def _setup_logger(self):
        """设置日志记录器"""
        import logging
        
        logger = logging.getLogger("data_updater")
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
            # 控制台输出
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            logger.addHandler(ch)
            
            # 文件输出
            log_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'logs'
            )
            os.makedirs(log_dir, exist_ok=True)
            
            fh = logging.FileHandler(
                os.path.join(log_dir, 'data_updater.log'),
                encoding='utf-8'
            )
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        
        return logger
    
    def update_odds_data(self, leagues: Optional[List[str]] = None,
                        force_update: bool = False) -> Dict:
        """
        更新赔率数据
        
        Args:
            leagues: 要更新的联赛列表，None表示使用配置中的所有联赛
            force_update: 是否强制更新（即使未到更新时间）
            
        Returns:
            更新结果
        """
        self.logger.info("开始更新赔率数据")
        
        # 检查是否需要更新
        if not self._should_update('odds', force_update):
            self.logger.info("赔率数据无需更新，跳过")
            return {'status': 'skipped', 'reason': 'not_due_for_update'}
        
        result = {
            'type': 'odds',
            'start_time': datetime.now().isoformat(),
            'leagues': [],
            'success_count': 0,
            'error_count': 0,
            'files_created': []
        }
        
        # 确定要更新的联赛
        if leagues is None:
            # 使用配置中的联赛
            leagues_config = self.config['data_sources']['odds']['oddsportal']['leagues']
            leagues = [league['id'] for league in leagues_config]
        
        for league in leagues:
            try:
                self.logger.info(f"更新联赛赔率数据: {league}")
                
                # 获取赔率数据
                matches = self.odds_scraper.get_odds_for_league(league, days=7)
                
                if matches:
                    # 保存数据
                    filename = f"odds_{league.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    filepath = self._save_data(matches, 'odds', filename)
                    
                    # 合并到历史数据
                    self._merge_with_history(matches, 'odds', league)
                    
                    result['leagues'].append({
                        'league': league,
                        'match_count': len(matches),
                        'filepath': filepath
                    })
                    result['success_count'] += 1
                    result['files_created'].append(filepath)
                    
                    self.logger.info(f"联赛 {league} 更新完成: {len(matches)} 场比赛")
                else:
                    self.logger.warning(f"联赛 {league} 未获取到赔率数据")
                    result['error_count'] += 1
            
            except Exception as e:
                self.logger.error(f"更新联赛 {league} 赔率数据失败: {e}")
                result['error_count'] += 1
        
        result['end_time'] = datetime.now().isoformat()
        result['duration'] = (datetime.fromisoformat(result['end_time']) - 
                            datetime.fromisoformat(result['start_time'])).total_seconds()
        
        # 更新监控数据
        with self.lock:
            self.metrics['last_run']['odds'] = result['end_time']
            self.metrics['success_count']['odds'] = self.metrics['success_count'].get('odds', 0) + result['success_count']
            self.metrics['error_count']['odds'] = self.metrics['error_count'].get('odds', 0) + result['error_count']
            self.metrics['total_updates'] += 1
        
        self.logger.info(f"赔率数据更新完成: {result['success_count']} 成功, {result['error_count']} 失败")
        return result
    
    def update_match_data(self, matches: Optional[List[Dict]] = None,
                         force_update: bool = False) -> Dict:
        """
        更新比赛数据
        
        Args:
            matches: 要更新的比赛列表，None表示从现有数据获取需要更新的比赛
            force_update: 是否强制更新
            
        Returns:
            更新结果
        """
        self.logger.info("开始更新比赛数据")
        
        # 检查是否需要更新
        if not self._should_update('matches', force_update):
            self.logger.info("比赛数据无需更新，跳过")
            return {'status': 'skipped', 'reason': 'not_due_for_update'}
        
        result = {
            'type': 'matches',
            'start_time': datetime.now().isoformat(),
            'matches_updated': [],
            'success_count': 0,
            'error_count': 0,
            'files_created': []
        }
        
        # 如果没有提供比赛列表，从现有数据获取需要更新的比赛
        if matches is None:
            matches = self._get_matches_needing_update()
        
        for match_info in matches:
            try:
                self.logger.info(f"更新比赛数据: {match_info.get('home_team')} vs {match_info.get('away_team')}")
                
                # 获取比赛详情
                match_details = self.match_scraper.fetch_match_details(match_info, include_all=True)
                
                if match_details and 'sources' in match_details:
                    # 保存数据
                    match_id = match_info.get('match_id', 'unknown')
                    filename = f"match_{match_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    filepath = self._save_data(match_details, 'matches', filename)
                    
                    # 合并到历史数据
                    self._merge_with_history(match_details, 'matches', match_id)
                    
                    result['matches_updated'].append({
                        'match_id': match_id,
                        'home_team': match_info.get('home_team'),
                        'away_team': match_info.get('away_team'),
                        'filepath': filepath
                    })
                    result['success_count'] += 1
                    result['files_created'].append(filepath)
                    
                    self.logger.info(f"比赛 {match_id} 更新完成")
                else:
                    self.logger.warning(f"比赛 {match_info.get('match_id')} 未获取到数据")
                    result['error_count'] += 1
            
            except Exception as e:
                self.logger.error(f"更新比赛 {match_info.get('match_id')} 数据失败: {e}")
                result['error_count'] += 1
        
        result['end_time'] = datetime.now().isoformat()
        result['duration'] = (datetime.fromisoformat(result['end_time']) - 
                            datetime.fromisoformat(result['start_time'])).total_seconds()
        
        # 更新监控数据
        with self.lock:
            self.metrics['last_run']['matches'] = result['end_time']
            self.metrics['success_count']['matches'] = self.metrics['success_count'].get('matches', 0) + result['success_count']
            self.metrics['error_count']['matches'] = self.metrics['error_count'].get('matches', 0) + result['error_count']
            self.metrics['total_updates'] += 1
        
        self.logger.info(f"比赛数据更新完成: {result['success_count']} 成功, {result['error_count']} 失败")
        return result
    
    def update_news_data(self, teams: Optional[List[str]] = None,
                        force_update: bool = False) -> Dict:
        """
        更新新闻数据
        
        Args:
            teams: 要获取新闻的球队列表，None表示使用配置中的重要球队
            force_update: 是否强制更新
            
        Returns:
            更新结果
        """
        self.logger.info("开始更新新闻数据")
        
        # 检查是否需要更新
        if not self._should_update('news', force_update):
            self.logger.info("新闻数据无需更新，跳过")
            return {'status': 'skipped', 'reason': 'not_due_for_update'}
        
        result = {
            'type': 'news',
            'start_time': datetime.now().isoformat(),
            'teams_updated': [],
            'articles_found': 0,
            'success_count': 0,
            'error_count': 0,
            'files_created': []
        }
        
        # 确定要更新的球队
        if teams is None:
            # 使用重要球队
            teams = ['Manchester United', 'Manchester City', 'Liverpool', 
                    'Chelsea', 'Arsenal', 'Real Madrid', 'Barcelona', 
                    'Bayern Munich', 'Juventus']
        
        for team in teams:
            try:
                self.logger.info(f"更新球队新闻数据: {team}")
                
                # 获取球队新闻
                articles = self.news_fetcher.fetch_news_by_team(team, hours=24)
                
                if articles:
                    # 保存数据
                    filename = f"news_{team.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    filepath = self._save_data(articles, 'news', filename)
                    
                    # 合并到历史数据
                    self._merge_with_history(articles, 'news', team)
                    
                    result['teams_updated'].append({
                        'team': team,
                        'article_count': len(articles),
                        'filepath': filepath
                    })
                    result['articles_found'] += len(articles)
                    result['success_count'] += 1
                    result['files_created'].append(filepath)
                    
                    self.logger.info(f"球队 {team} 新闻更新完成: {len(articles)} 篇文章")
                else:
                    self.logger.warning(f"球队 {team} 未获取到新闻数据")
                    result['error_count'] += 1
            
            except Exception as e:
                self.logger.error(f"更新球队 {team} 新闻数据失败: {e}")
                result['error_count'] += 1
        
        result['end_time'] = datetime.now().isoformat()
        result['duration'] = (datetime.fromisoformat(result['end_time']) - 
                            datetime.fromisoformat(result['start_time'])).total_seconds()
        
        # 更新监控数据
        with self.lock:
            self.metrics['last_run']['news'] = result['end_time']
            self.metrics['success_count']['news'] = self.metrics['success_count'].get('news', 0) + result['success_count']
            self.metrics['error_count']['news'] = self.metrics['error_count'].get('news', 0) + result['error_count']
            self.metrics['total_updates'] += 1
        
        self.logger.info(f"新闻数据更新完成: {result['success_count']} 成功, {result['error_count']} 失败, {result['articles_found']} 篇文章")
        return result
    
    def _should_update(self, data_type: str, force_update: bool) -> bool:
        """
        检查是否需要更新
        
        Args:
            data_type: 数据类型
            force_update: 是否强制更新
            
        Returns:
            是否需要更新
        """
        if force_update:
            return True
        
        # 检查最后更新时间
        last_run = self.metrics['last_run'].get(data_type)
        if not last_run:
            return True
        
        try:
            last_run_time = datetime.fromisoformat(last_run)
            now = datetime.now()
            
            # 获取配置的更新间隔
            schedule_config = self.config['crawl_schedule'].get(data_type, {})
            interval_minutes = schedule_config.get('interval_minutes', 60)
            
            # 检查是否过了更新时间
            return (now - last_run_time).total_seconds() >= interval_minutes * 60
            
        except Exception as e:
            self.logger.error(f"检查更新时间失败: {e}")
            return True
    
    def _get_matches_needing_update(self) -> List[Dict]:
        """获取需要更新的比赛列表"""
        matches_needing_update = []
        
        try:
            # 从赔率数据中获取近期比赛
            leagues_config = self.config['data_sources']['odds']['oddsportal']['leagues']
            leagues = [league['id'] for league in leagues_config if league.get('priority', 3) <= 2]
            
            for league in leagues[:3]:  # 只处理前3个联赛
                try:
                    # 获取最近赔率数据
                    league_dir = os.path.join(self.data_dir, self.subdirs['odds'])
                    if not os.path.exists(league_dir):
                        continue
                    
                    # 查找最新的赔率文件
                    latest_file = self._find_latest_file(league_dir, f"odds_{league.replace('/', '_')}")
                    if not latest_file:
                        continue
                    
                    # 加载赔率数据
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        odds_data = json.load(f)
                    
                    # 提取比赛信息
                    for match in odds_data[:10]:  # 只处理前10场比赛
                        match_info = {
                            'match_id': match.get('match_id', f"match_{len(matches_needing_update)}"),
                            'home_team': match.get('home_team'),
                            'away_team': match.get('away_team'),
                            'match_date': match.get('match_time')  # 使用比赛时间作为日期
                        }
                        matches_needing_update.append(match_info)
                        
                        if len(matches_needing_update) >= 20:  # 限制数量
                            return matches_needing_update
                
                except Exception as e:
                    self.logger.warning(f"处理联赛 {league} 比赛失败: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"获取需要更新的比赛失败: {e}")
        
        return matches_needing_update
    
    def _find_latest_file(self, directory: str, prefix: str) -> Optional[str]:
        """查找指定前缀的最新文件"""
        if not os.path.exists(directory):
            return None
        
        latest_file = None
        latest_time = None
        
        for filename in os.listdir(directory):
            if filename.startswith(prefix) and filename.endswith('.json'):
                filepath = os.path.join(directory, filename)
                try:
                    file_time = os.path.getmtime(filepath)
                    if latest_time is None or file_time > latest_time:
                        latest_time = file_time
                        latest_file = filepath
                except:
                    continue
        
        return latest_file
    
    def _save_data(self, data: Any, data_type: str, filename: str) -> str:
        """
        保存数据到文件
        
        Args:
            data: 要保存的数据
            data_type: 数据类型
            filename: 文件名
            
        Returns:
            保存的文件路径
        """
        # 确保目录存在
        save_dir = os.path.join(self.data_dir, self.subdirs.get(data_type, data_type))
        os.makedirs(save_dir, exist_ok=True)
        
        filepath = os.path.join(save_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.logger.debug(f"数据保存到: {filepath}")
        return filepath
    
    def _merge_with_history(self, new_data: Any, data_type: str, key: str) -> None:
        """
        将新数据合并到历史数据
        
        Args:
            new_data: 新数据
            data_type: 数据类型
            key: 数据键（联赛、比赛ID、球队等）
        """
        try:
            # 历史文件路径
            history_dir = os.path.join(self.data_dir, 'history')
            os.makedirs(history_dir, exist_ok=True)
            
            history_file = os.path.join(history_dir, f"{data_type}_{key}.json")
            
            # 加载现有历史数据
            history_data = []
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
            
            # 添加时间戳
            timestamped_data = new_data
            if isinstance(new_data, dict):
                timestamped_data = new_data.copy()
                timestamped_data['_merged_at'] = datetime.now().isoformat()
            elif isinstance(new_data, list):
                timestamped_data = []
                for item in new_data:
                    if isinstance(item, dict):
                        item_copy = item.copy()
                        item_copy['_merged_at'] = datetime.now().isoformat()
                        timestamped_data.append(item_copy)
                    else:
                        timestamped_data.append(item)
            
            # 添加新数据
            if isinstance(history_data, list):
                history_data.append(timestamped_data)
            elif isinstance(history_data, dict):
                # 如果是字典，按时间戳作为键
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                history_data[timestamp] = timestamped_data
            
            # 限制历史数据大小
            retention_days = self.config['storage']['retention_days'].get(data_type, 30)
            
            if isinstance(history_data, list):
                # 过滤过期的数据
                cutoff_date = datetime.now() - timedelta(days=retention_days)
                history_data = [
                    item for item in history_data
                    if self._get_data_timestamp(item) >= cutoff_date
                ]
            
            # 保存历史数据
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"历史数据合并完成: {history_file}")
            
        except Exception as e:
            self.logger.error(f"合并历史数据失败: {e}")
    
    def _get_data_timestamp(self, data_item: Any) -> datetime:
        """从数据项中提取时间戳"""
        try:
            if isinstance(data_item, dict):
                # 尝试各种时间戳字段
                timestamp_str = (
                    data_item.get('scraped_at') or
                    data_item.get('_merged_at') or
                    data_item.get('timestamp') or
                    data_item.get('date')
                )
                
                if timestamp_str:
                    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # 默认返回当前时间减去保留天数（这样会被过滤掉）
            return datetime.now() - timedelta(days=self.config['storage']['retention_days'].get('default', 30) + 1)
        
        except Exception as e:
            self.logger.debug(f"提取时间戳失败: {e}")
            return datetime.now() - timedelta(days=365)  # 返回很久以前的时间
    
    def run_scheduled_update(self, data_types: Optional[List[str]] = None) -> Dict:
        """
        运行定时更新
        
        Args:
            data_types: 要更新的数据类型列表，None表示更新所有类型
            
        Returns:
            更新结果汇总
        """
        if data_types is None:
            data_types = ['odds', 'matches', 'news']
        
        self.logger.info(f"开始定时更新: {', '.join(data_types)}")
        
        results = {}
        total_start = datetime.now()
        
        for data_type in data_types:
            try:
                if data_type == 'odds':
                    result = self.update_odds_data()
                elif data_type == 'matches':
                    result = self.update_match_data()
                elif data_type == 'news':
                    result = self.update_news_data()
                else:
                    self.logger.warning(f"未知的数据类型: {data_type}")
                    continue
                
                results[data_type] = result
                
            except Exception as e:
                self.logger.error(f"更新 {data_type} 数据失败: {e}")
                results[data_type] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        total_duration = (datetime.now() - total_start).total_seconds()
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'data_types_updated': list(results.keys()),
            'results': results,
            'total_duration': total_duration,
            'metrics': self.get_metrics()
        }
        
        # 保存更新摘要
        self._save_update_summary(summary)
        
        self.logger.info(f"定时更新完成，总耗时: {total_duration:.2f}秒")
        return summary
    
    def _save_update_summary(self, summary: Dict) -> None:
        """保存更新摘要"""
        try:
            summary_dir = os.path.join(self.data_dir, 'updates')
            os.makedirs(summary_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"update_summary_{timestamp}.json"
            filepath = os.path.join(summary_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"更新摘要保存到: {filepath}")
            
        except Exception as e:
            self.logger.error(f"保存更新摘要失败: {e}")
    
    def start_scheduler(self) -> None:
        """启动定时调度器"""
        if self.running:
            self.logger.warning("调度器已经在运行")
            return
        
        self.running = True
        self.logger.info("启动数据更新调度器")
        
        # 配置调度任务
        schedule_config = self.config['crawl_schedule']
        
        # 赔率数据更新
        if schedule_config['odds']['enabled']:
            interval = schedule_config['odds']['interval_minutes']
            schedule.every(interval).minutes.do(self._schedule_task, 'odds')
            self.logger.info(f"赔率数据更新计划: 每 {interval} 分钟")
        
        # 比赛数据更新
        if schedule_config['matches']['enabled']:
            interval = schedule_config['matches']['interval_minutes']
            schedule.every(interval).minutes.do(self._schedule_task, 'matches')
            self.logger.info(f"比赛数据更新计划: 每 {interval} 分钟")
        
        # 新闻数据更新
        if schedule_config['news']['enabled']:
            interval = schedule_config['news']['interval_minutes']
            schedule.every(interval).minutes.do(self._schedule_task, 'news')
            self.logger.info(f"新闻数据更新计划: 每 {interval} 分钟")
        
        # 启动调度线程
        scheduler_thread = Thread(target=self._scheduler_loop, daemon=True)
        scheduler_thread.start()
        
        self.logger.info("调度器启动完成")
    
    def _schedule_task(self, data_type: str) -> None:
        """调度任务"""
        self.logger.info(f"调度执行 {data_type} 数据更新")
        self.task_queue.put(data_type)
    
    def _scheduler_loop(self) -> None:
        """调度器循环"""
        while self.running:
            try:
                # 检查调度任务
                schedule.run_pending()
                
                # 处理任务队列
                while not self.task_queue.empty():
                    data_type = self.task_queue.get()
                    try:
                        self.logger.info(f"执行 {data_type} 数据更新任务")
                        if data_type == 'odds':
                            self.update_odds_data()
                        elif data_type == 'matches':
                            self.update_match_data()
                        elif data_type == 'news':
                            self.update_news_data()
                    except Exception as e:
                        self.logger.error(f"执行 {data_type} 任务失败: {e}")
                    finally:
                        self.task_queue.task_done()
                
                time.sleep(1)  # 每秒检查一次
                
            except Exception as e:
                self.logger.error(f"调度器循环错误: {e}")
                time.sleep(5)
    
    def stop_scheduler(self) -> None:
        """停止定时调度器"""
        self.running = False
        self.logger.info("停止数据更新调度器")
    
    def get_metrics(self) -> Dict:
        """获取监控指标"""
        with self.lock:
            return self.metrics.copy()
    
    def cleanup_old_data(self) -> Dict:
        """清理旧数据"""
        self.logger.info("开始清理旧数据")
        
        result = {
            'start_time': datetime.now().isoformat(),
            'files_deleted': [],
            'total_size_freed': 0,
            'errors': []
        }
        
        retention_days = self.config['storage']['retention_days']
        
        for data_type, days in retention_days.items():
            try:
                type_dir = os.path.join(self.data_dir, self.subdirs.get(data_type, data_type))
                if not os.path.exists(type_dir):
                    continue
                
                cutoff_time = time.time() - (days * 24 * 60 * 60)
                
                for filename in os.listdir(type_dir):
                    filepath = os.path.join(type_dir, filename)
                    
                    # 检查文件时间
                    if os.path.getmtime(filepath) < cutoff_time:
                        try:
                            file_size = os.path.getsize(filepath)
                            os.remove(filepath)
                            
                            result['files_deleted'].append(filepath)
                            result['total_size_freed'] += file_size
                            
                            self.logger.debug(f"删除旧文件: {filepath}")
                        except Exception as e:
                            result['errors'].append(f"删除文件 {filepath} 失败: {e}")
            
            except Exception as e:
                result['errors'].append(f"清理 {data_type} 数据失败: {e}")
        
        # 清理历史目录
        try:
            history_dir = os.path.join(self.data_dir, 'history')
            if os.path.exists(history_dir):
                # 历史数据保留更长时间
                history_days = retention_days.get('history', 180)
                cutoff_time = time.time() - (history_days * 24 * 60 * 60)
                
                for filename in os.listdir(history_dir):
                    filepath = os.path.join(history_dir, filename)
                    
                    if os.path.getmtime(filepath) < cutoff_time:
                        try:
                            file_size = os.path.getsize(filepath)
                            os.remove(filepath)
                            
                            result['files_deleted'].append(filepath)
                            result['total_size_freed'] += file_size
                        except Exception as e:
                            result['errors'].append(f"删除历史文件 {filepath} 失败: {e}")
        except Exception as e:
            result['errors'].append(f"清理历史数据失败: {e}")
        
        result['end_time'] = datetime.now().isoformat()
        result['duration'] = (datetime.fromisoformat(result['end_time']) - 
                            datetime.fromisoformat(result['start_time'])).total_seconds()
        
        self.logger.info(f"数据清理完成: 删除 {len(result['files_deleted'])} 个文件, 释放 {result['total_size_freed']} 字节")
        return result
    
    def backup_data(self, backup_dir: Optional[str] = None) -> Dict:
        """备份数据"""
        self.logger.info("开始数据备份")
        
        if backup_dir is None:
            backup_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'backups'
            )
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f"data_backup_{timestamp}")
        
        result = {
            'start_time': datetime.now().isoformat(),
            'backup_path': backup_path,
            'success': False
        }
        
        try:
            os.makedirs(backup_path, exist_ok=True)
            
            # 复制数据目录
            shutil.copytree(self.data_dir, os.path.join(backup_path, 'data'))
            
            # 复制配置文件
            config_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
            if os.path.exists(config_source):
                shutil.copy2(config_source, os.path.join(backup_path, 'config.json'))
            
            # 创建备份信息文件
            backup_info = {
                'timestamp': datetime.now().isoformat(),
                'data_dir': self.data_dir,
                'metrics': self.get_metrics(),
                'file_count': len(os.listdir(os.path.join(backup_path, 'data')))
            }
            
            info_file = os.path.join(backup_path, 'backup_info.json')
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)
            
            result['success'] = True
            result['backup_info'] = backup_info
            self.logger.info(f"数据备份完成: {backup_path}")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"数据备份失败: {e}")
        
        result['end_time'] = datetime.now().isoformat()
        result['duration'] = (datetime.fromisoformat(result['end_time']) - 
                            datetime.fromisoformat(result['start_time'])).total_seconds()
        
        return result


if __name__ == "__main__":
    # 测试数据更新器
    print("测试数据更新器...")
    
    updater = DataUpdater()
    
    # 测试配置加载
    print("\n1. 测试配置加载:")
    metrics = updater.get_metrics()
    print(f"  监控指标: {metrics}")
    
    # 测试赔率数据更新（模拟）
    print("\n2. 测试赔率数据更新（模拟）:")
    try:
        result = updater.update_odds_data(['england/premier-league'], force_update=True)
        print(f"  更新结果: {result.get('success_count', 0)} 成功, {result.get('error_count', 0)} 失败")
        if result.get('leagues'):
            for league_info in result['leagues']:
                print(f"    联赛: {league_info['league']}, 比赛数: {league_info.get('match_count', 0)}")
    except Exception as e:
        print(f"  赔率更新测试失败: {e}")
    
    # 测试比赛数据更新（模拟）
    print("\n3. 测试比赛数据更新（模拟）:")
    try:
        test_matches = [
            {
                'match_id': 'test_1',
                'home_team': 'Manchester United',
                'away_team': 'Liverpool',
                'match_date': '2024-12-25'
            }
        ]
        result = updater.update_match_data(test_matches, force_update=True)
        print(f"  更新结果: {result.get('success_count', 0)} 成功, {result.get('error_count', 0)} 失败")
    except Exception as e:
        print(f"  比赛更新测试失败: {e}")
    
    # 测试新闻数据更新（模拟）
    print("\n4. 测试新闻数据更新（模拟）:")
    try:
        result = updater.update_news_data(['Manchester United'], force_update=True)
        print(f"  更新结果: {result.get('success_count', 0)} 成功, {result.get('error_count', 0)} 失败, {result.get('articles_found', 0)} 篇文章")
    except Exception as e:
        print(f"  新闻更新测试失败: {e}")
    
    # 测试定时更新
    print("\n5. 测试定时更新:")
    try:
        summary = updater.run_scheduled_update(['odds'])
        print(f"  定时更新完成，数据类型: {summary.get('data_types_updated', [])}")
        print(f"  总耗时: {summary.get('total_duration', 0):.2f}秒")
    except Exception as e:
        print(f"  定时更新测试失败: {e}")
    
    # 测试数据清理
    print("\n6. 测试数据清理:")
    try:
        cleanup_result = updater.cleanup_old_data()
        print(f"  清理结果: 删除 {len(cleanup_result.get('files_deleted', []))} 个文件")
        print(f"  释放空间: {cleanup_result.get('total_size_freed', 0)} 字节")
    except Exception as e:
        print(f"  数据清理测试失败: {e}")
    
    # 测试调度器（不实际启动）
    print("\n7. 调度器配置检查:")
    schedule_config = updater.config['crawl_schedule']
    for data_type, config in schedule_config.items():
        if config.get('enabled'):
            print(f"  {data_type}: 每 {config.get('interval_minutes', 60)} 分钟更新")
    
    print("\n数据更新器测试完成")