#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - 数据获取配置模块
配置数据源URL、爬取频率等
"""

import os
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class DataSource:
    """数据源配置"""
    name: str
    url: str
    enabled: bool = True
    rate_limit: int = 5  # 请求间隔(秒)
    headers: Dict[str, str] = field(default_factory=dict)
    description: str = ""


class DataFetchConfig:
    """数据获取配置"""
    
    # 默认配置
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_dir = os.path.join(base_dir, "config")
        
        self.config_dir = config_dir
        os.makedirs(config_dir, exist_ok=True)
        
        self.config_file = os.path.join(config_dir, "data_fetch_config.json")
        self.config = self._load_config()
        
        # 初始化默认数据源
        if not self.config:
            self.config = self._get_default_config()
            self._save_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "version": "1.0.0",
            "last_updated": "",
            "request_settings": {
                "max_retries": 3,
                "timeout": 30,
                "delay_range": [2, 5],
                "headers": self.DEFAULT_HEADERS
            },
            "data_sources": {
                "odds": [
                    {
                        "name": "oddsportal",
                        "url": "https://www.oddsportal.com",
                        "enabled": False,
                        "rate_limit": 10,
                        "description": "赔率比较网站"
                    }
                ],
                "fixtures": [
                    {
                        "name": "football-data",
                        "url": "https://www.football-data.co.uk",
                        "enabled": False,
                        "rate_limit": 10,
                        "description": "足球历史数据"
                    }
                ],
                "news": [
                    {
                        "name": "google-news",
                        "url": "https://news.google.com",
                        "enabled": False,
                        "rate_limit": 30,
                        "description": "新闻聚合"
                    }
                ]
            },
            "storage": {
                "data_dir": "data/external",
                "cache_ttl": 3600,
                "max_cache_size": 1000
            }
        }
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"配置加载失败: {e}")
        return {}
    
    def _save_config(self) -> bool:
        """保存配置"""
        try:
            self.config["last_updated"] = str(int(os.path.getmtime(__file__))) if os.path.exists(__file__) else ""
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"配置保存失败: {e}")
            return False
    
    def get_data_sources(self, category: str) -> List[DataSource]:
        """获取数据源列表"""
        sources = self.config.get("data_sources", {}).get(category, [])
        return [DataSource(**s) for s in sources if s.get("enabled", False)]
    
    def enable_source(self, category: str, name: str) -> bool:
        """启用数据源"""
        sources = self.config.get("data_sources", {}).get(category, [])
        for source in sources:
            if source.get("name") == name:
                source["enabled"] = True
                return self._save_config()
        return False
    
    def disable_source(self, category: str, name: str) -> bool:
        """禁用数据源"""
        sources = self.config.get("data_sources", {}).get(category, [])
        for source in sources:
            if source.get("name") == name:
                source["enabled"] = False
                return self._save_config()
        return False
    
    def get_request_settings(self) -> Dict:
        """获取请求设置"""
        return self.config.get("request_settings", {
            "max_retries": 3,
            "timeout": 30,
            "delay_range": [2, 5],
            "headers": self.DEFAULT_HEADERS
        })
    
    def set_rate_limit(self, category: str, name: str, rate_limit: int) -> bool:
        """设置请求频率"""
        sources = self.config.get("data_sources", {}).get(category, [])
        for source in sources:
            if source.get("name") == name:
                source["rate_limit"] = rate_limit
                return self._save_config()
        return False
    
    def get_all_sources(self) -> Dict[str, List[DataSource]]:
        """获取所有数据源"""
        result = {}
        for category, sources in self.config.get("data_sources", {}).items():
            result[category] = [DataSource(**s) for s in sources]
        return result
    
    def add_custom_source(self, category: str, source: DataSource) -> bool:
        """添加自定义数据源"""
        if category not in self.config.get("data_sources", {}):
            self.config.setdefault("data_sources", {})[category] = []
        
        self.config["data_sources"][category].append({
            "name": source.name,
            "url": source.url,
            "enabled": source.enabled,
            "rate_limit": source.rate_limit,
            "headers": source.headers,
            "description": source.description
        })
        
        return self._save_config()
    
    def get_storage_config(self) -> Dict:
        """获取存储配置"""
        return self.config.get("storage", {
            "data_dir": "data/external",
            "cache_ttl": 3600,
            "max_cache_size": 1000
        })


# 全局单例
_config_instance: Optional[DataFetchConfig] = None

def get_data_fetch_config() -> DataFetchConfig:
    """获取配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = DataFetchConfig()
    return _config_instance


if __name__ == "__main__":
    # 测试配置
    config = DataFetchConfig()
    
    print("=" * 50)
    print("数据获取配置测试")
    print("=" * 50)
    
    # 查看所有数据源
    all_sources = config.get_all_sources()
    print("\n【数据源配置】")
    for category, sources in all_sources.items():
        print(f"\n{category}:")
        for source in sources:
            status = "启用" if source.enabled else "禁用"
            print(f"  • {source.name} ({status}) - {source.description}")
            print(f"    URL: {source.url}")
    
    # 查看请求设置
    req_settings = config.get_request_settings()
    print(f"\n【请求设置】")
    print(f"  最大重试: {req_settings['max_retries']}")
    print(f"  超时: {req_settings['timeout']}秒")
    print(f"  延迟范围: {req_settings['delay_range']}秒")
    
    # 查看存储配置
    storage = config.get_storage_config()
    print(f"\n【存储设置】")
    print(f"  数据目录: {storage['data_dir']}")
    print(f"  缓存TTL: {storage['cache_ttl']}秒")
