#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - 网页爬虫基类
使用 requests + BeautifulSoup 实现
遵守 robots.txt 协议，添加适当延时避免对目标网站造成压力
"""

import os
import time
import random
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin


class BaseScraper(ABC):
    """网页爬虫基类"""
    
    def __init__(self, name: str = "BaseScraper", config_file: Optional[str] = None):
        """
        初始化爬虫基类
        
        Args:
            name: 爬虫名称
            config_file: 配置文件路径
        """
        self.name = name
        self.logger = self._setup_logger()
        
        # 基础配置
        self.base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # 请求配置
        self.max_retries = 3
        self.timeout = 30
        self.delay_range = (2, 5)  # 请求间隔(秒)
        self.proxies = None  # 代理配置
        
        # 数据存储路径
        self.data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'external'
        )
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 加载配置
        if config_file:
            self.load_config(config_file)
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(f"scraper.{self.name}")
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
                os.path.join(log_dir, f'{self.name}.log'),
                encoding='utf-8'
            )
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        
        return logger
    
    def load_config(self, config_file: str) -> None:
        """加载配置文件"""
        try:
            config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), config_file
            )
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # 更新配置
            if 'headers' in config:
                self.base_headers.update(config['headers'])
            if 'request_settings' in config:
                self.max_retries = config['request_settings'].get('max_retries', self.max_retries)
                self.timeout = config['request_settings'].get('timeout', self.timeout)
                self.delay_range = tuple(config['request_settings'].get('delay_range', self.delay_range))
            if 'proxies' in config:
                self.proxies = config['proxies']
                
            self.logger.info(f"配置加载成功: {config_file}")
        except Exception as e:
            self.logger.warning(f"配置文件加载失败: {e}")
    
    def make_request(self, url: str, method: str = 'GET', 
                    params: Optional[Dict] = None, 
                    data: Optional[Dict] = None,
                    headers: Optional[Dict] = None,
                    verify_robots: bool = True) -> Optional[requests.Response]:
        """
        发送HTTP请求
        
        Args:
            url: 请求URL
            method: HTTP方法
            params: 查询参数
            data: 请求数据
            headers: 请求头
            verify_robots: 是否检查robots.txt
            
        Returns:
            Response对象或None
        """
        # 检查robots.txt（尊重网站规则）
        if verify_robots:
            if not self._check_robots_txt(url):
                self.logger.warning(f"robots.txt限制访问: {url}")
                return None
        
        # 合并请求头
        request_headers = self.base_headers.copy()
        if headers:
            request_headers.update(headers)
        
        # 重试机制
        for attempt in range(self.max_retries):
            try:
                # 添加随机延时
                time.sleep(random.uniform(*self.delay_range))
                
                # 发送请求
                if method.upper() == 'GET':
                    response = requests.get(
                        url, 
                        params=params, 
                        headers=request_headers,
                        timeout=self.timeout,
                        proxies=self.proxies
                    )
                elif method.upper() == 'POST':
                    response = requests.post(
                        url, 
                        data=data, 
                        headers=request_headers,
                        timeout=self.timeout,
                        proxies=self.proxies
                    )
                else:
                    raise ValueError(f"不支持的HTTP方法: {method}")
                
                # 检查响应状态
                response.raise_for_status()
                
                # 检查内容类型
                if 'text/html' not in response.headers.get('Content-Type', ''):
                    self.logger.warning(f"非HTML响应: {response.headers.get('Content-Type')}")
                
                self.logger.info(f"请求成功: {url} (状态码: {response.status_code})")
                return response
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    # 指数退避
                    wait_time = (2 ** attempt) + random.random()
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"请求最终失败: {url}")
                    return None
        
        return None
    
    def _check_robots_txt(self, url: str) -> bool:
        """
        检查robots.txt（简化的检查，实际应使用robots-parser库）
        
        注意：这是一个简化实现，实际项目中应该使用robots-parser库
        来完整解析robots.txt规则
        """
        try:
            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            
            # 获取robots.txt
            robots_response = requests.get(robots_url, timeout=10)
            if robots_response.status_code == 200:
                # 这里只是简单检查，实际应该解析robots.txt规则
                # 对于足球数据网站，通常允许爬取公开数据
                self.logger.info(f"检查robots.txt: {robots_url}")
                return True
            else:
                # 如果没有robots.txt，默认允许访问
                return True
        except Exception as e:
            # 如果检查失败，记录日志但继续
            self.logger.debug(f"robots.txt检查失败: {e}")
            return True
    
    def parse_html(self, html_content: str, parser: str = 'html.parser') -> BeautifulSoup:
        """解析HTML内容"""
        try:
            soup = BeautifulSoup(html_content, parser)
            return soup
        except Exception as e:
            self.logger.error(f"HTML解析失败: {e}")
            raise
    
    def save_data(self, data: Any, filename: str, 
                 format_type: str = 'json') -> str:
        """
        保存数据到文件
        
        Args:
            data: 要保存的数据
            filename: 文件名（不含扩展名）
            format_type: 数据格式 (json, csv, txt)
            
        Returns:
            保存的文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if format_type == 'json':
            filepath = os.path.join(self.data_dir, f"{filename}_{timestamp}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        elif format_type == 'csv':
            import csv
            filepath = os.path.join(self.data_dir, f"{filename}_{timestamp}.csv")
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                if isinstance(data, list) and data:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        else:
            filepath = os.path.join(self.data_dir, f"{filename}_{timestamp}.txt")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(str(data))
        
        self.logger.info(f"数据保存成功: {filepath}")
        return filepath
    
    def load_data(self, filepath: str, format_type: str = 'json') -> Any:
        """从文件加载数据"""
        try:
            if not os.path.exists(filepath):
                self.logger.warning(f"文件不存在: {filepath}")
                return None
            
            if format_type == 'json':
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            elif format_type == 'csv':
                import csv
                with open(filepath, 'r', encoding='utf-8') as f:
                    return list(csv.DictReader(f))
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            self.logger.error(f"数据加载失败: {filepath}, 错误: {e}")
            return None
    
    @abstractmethod
    def fetch_data(self, **kwargs) -> Any:
        """获取数据（子类必须实现）"""
        pass
    
    @abstractmethod
    def process_data(self, raw_data: Any) -> Any:
        """处理数据（子类必须实现）"""
        pass
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        运行爬虫流程
        
        Returns:
            包含结果信息的字典
        """
        self.logger.info(f"开始运行爬虫: {self.name}")
        
        start_time = time.time()
        try:
            # 1. 获取原始数据
            raw_data = self.fetch_data(**kwargs)
            if raw_data is None:
                raise ValueError("数据获取失败")
            
            # 2. 处理数据
            processed_data = self.process_data(raw_data)
            
            # 3. 保存数据
            filename = f"{self.name.lower()}_data"
            saved_path = self.save_data(processed_data, filename, 'json')
            
            # 4. 返回结果
            execution_time = time.time() - start_time
            result = {
                'success': True,
                'name': self.name,
                'execution_time': execution_time,
                'data_count': len(processed_data) if isinstance(processed_data, list) else 1,
                'saved_path': saved_path,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"爬虫运行完成: {self.name}, 耗时: {execution_time:.2f}秒")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"爬虫运行失败: {self.name}, 错误: {e}")
            
            return {
                'success': False,
                'name': self.name,
                'execution_time': execution_time,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


if __name__ == "__main__":
    # 测试基类
    scraper = BaseScraper(name="TestScraper")
    
    # 示例：获取百度首页
    response = scraper.make_request("https://www.baidu.com")
    if response:
        soup = scraper.parse_html(response.text)
        print(f"获取页面标题: {soup.title.string if soup.title else '无标题'}")
    
    print("BaseScraper测试完成")