#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - 数据获取模块
Web Scraping数据获取，不使用API
"""

__version__ = "1.0.0"
__author__ = "Football Lottery Analyzer Team"

from .scraper import BaseScraper
from .odds_scraper import OddsScraper
from .match_scraper import MatchScraper
from .news_fetcher import NewsFetcher
from .data_updater import DataUpdater
from .config import DataFetchConfig, get_data_fetch_config

__all__ = [
    'BaseScraper',
    'OddsScraper',
    'MatchScraper',
    'NewsFetcher',
    'DataUpdater',
    'DataFetchConfig',
    'get_data_fetch_config'
]

# 向后兼容别名
ConfigManager = DataFetchConfig

# 初始化配置
def init_config(config_file: str = None) -> DataFetchConfig:
    """
    初始化配置管理器
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        配置管理器实例
    """
    return DataFetchConfig(config_file)


def create_default_config() -> None:
    """创建默认配置文件"""
    import os
    
    config_manager = ConfigManager()
    print(f"默认配置文件已创建: {config_manager.config_file}")
    
    # 确保数据目录存在
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data', 'external'
    )
    os.makedirs(data_dir, exist_ok=True)
    
    print(f"数据目录: {data_dir}")
    print("数据获取模块初始化完成")


if __name__ == "__main__":
    # 模块测试
    print("数据获取模块测试...")
    create_default_config()
    print("模块加载成功")