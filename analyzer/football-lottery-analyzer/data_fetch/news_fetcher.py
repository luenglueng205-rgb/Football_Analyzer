#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - 新闻舆情抓取模块
抓取球队相关新闻、教练言论、转会动态等
"""

import os
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

from .scraper import BaseScraper


class NewsFetcher(BaseScraper):
    """新闻舆情抓取器"""
    
    def __init__(self, config_file: Optional[str] = "config.json"):
        """
        初始化新闻抓取器
        
        Args:
            config_file: 配置文件路径
        """
        super().__init__(name="NewsFetcher", config_file=config_file)
        
        # 新闻源配置
        self.news_sources = {
            'skysports': {
                'name': 'Sky Sports',
                'base_url': 'https://www.skysports.com',
                'sections': {
                    'football': '/football',
                    'news': '/football/news',
                    'transfers': '/football/transfers',
                    'premier-league': '/premier-league'
                },
                'language': 'en',
                'region': 'uk'
            },
            'espn': {
                'name': 'ESPN',
                'base_url': 'https://www.espn.com',
                'sections': {
                    'soccer': '/soccer',
                    'news': '/soccer/news',
                    'scores': '/soccer/scoreboard'
                },
                'language': 'en',
                'region': 'us'
            },
            'goal': {
                'name': 'Goal.com',
                'base_url': 'https://www.goal.com',
                'sections': {
                    'news': '/en/news',
                    'transfers': '/en/transfer-news',
                    'rumours': '/en/rumours'
                },
                'languages': ['en', 'zh'],
                'region': 'global'
            },
            '新浪体育': {
                'name': '新浪体育',
                'base_url': 'https://sports.sina.com.cn',
                'sections': {
                    'football': '/g/',
                    'news': '/g/news',
                    '中超': '/csl',
                    '英超': '/premierleague'
                },
                'language': 'zh',
                'region': 'cn'
            },
            '腾讯体育': {
                'name': '腾讯体育',
                'base_url': 'https://sports.qq.com',
                'sections': {
                    'football': '/soccer',
                    'news': '/soccer/news.htm',
                    '中超': '/csl'
                },
                'language': 'zh',
                'region': 'cn'
            },
            'bbc': {
                'name': 'BBC Sport',
                'base_url': 'https://www.bbc.com',
                'sections': {
                    'sport': '/sport',
                    'football': '/sport/football',
                    'premier-league': '/sport/football/premier-league'
                },
                'language': 'en',
                'region': 'uk'
            }
        }
        
        # 关键词映射（球队、联赛相关）
        self.keyword_mapping = {
            'premier_league': ['英超', 'Premier League', 'EPL'],
            'la_liga': ['西甲', 'La Liga'],
            'serie_a': ['意甲', 'Serie A'],
            'bundesliga': ['德甲', 'Bundesliga'],
            'ligue_1': ['法甲', 'Ligue 1'],
            
            'manchester_united': ['曼联', 'Manchester United', 'Man Utd'],
            'manchester_city': ['曼城', 'Manchester City', 'Man City'],
            'liverpool': ['利物浦', 'Liverpool'],
            'chelsea': ['切尔西', 'Chelsea'],
            'arsenal': ['阿森纳', 'Arsenal'],
            'tottenham': ['热刺', 'Tottenham', 'Spurs'],
            'real_madrid': ['皇马', 'Real Madrid'],
            'barcelona': ['巴萨', 'Barcelona'],
            'bayern': ['拜仁', 'Bayern Munich'],
            'juventus': ['尤文', 'Juventus']
        }
        
        # 新闻类型
        self.news_types = {
            'transfer': '转会新闻',
            'injury': '伤病新闻',
            'match_preview': '赛前分析',
            'match_report': '赛后报道',
            'rumour': '传闻',
            'official': '官方公告',
            'interview': '采访',
            'tactical': '战术分析'
        }
    
    def fetch_news(self, source: str = 'skysports', 
                  section: str = 'news',
                  max_articles: int = 20) -> Optional[Dict]:
        """
        从指定新闻源获取新闻
        
        Args:
            source: 新闻源名称
            section: 新闻板块
            max_articles: 最大文章数
            
        Returns:
            包含新闻数据的字典
        """
        if source not in self.news_sources:
            self.logger.error(f"不支持的新闻源: {source}")
            return None
        
        source_config = self.news_sources[source]
        
        # 获取板块URL
        if section not in source_config['sections']:
            self.logger.warning(f"新闻源 {source} 不支持板块 {section}，使用默认板块")
            section = list(source_config['sections'].keys())[0]
        
        section_path = source_config['sections'][section]
        url = urljoin(source_config['base_url'], section_path)
        
        self.logger.info(f"开始获取新闻: {source} -> {section}")
        self.logger.debug(f"请求URL: {url}")
        
        # 发送请求
        response = self.make_request(url)
        if not response or response.status_code != 200:
            self.logger.error(f"获取新闻失败: {url}")
            return None
        
        # 解析新闻
        articles = self._parse_news_page(response.text, source, section)
        
        # 限制文章数量
        if len(articles) > max_articles:
            articles = articles[:max_articles]
        
        result = {
            'source': source,
            'section': section,
            'url': url,
            'articles': articles,
            'count': len(articles),
            'scraped_at': datetime.now().isoformat()
        }
        
        self.logger.info(f"获取到 {len(articles)} 篇新闻文章")
        return result
    
    def _parse_news_page(self, html_content: str, source: str, section: str) -> List[Dict]:
        """解析新闻页面"""
        soup = self.parse_html(html_content)
        articles = []
        
        # 根据新闻源使用不同的解析方法
        if source == 'skysports':
            articles = self._parse_skysports(soup)
        elif source == 'espn':
            articles = self._parse_espn(soup)
        elif source == 'goal':
            articles = self._parse_goal(soup)
        elif source == '新浪体育':
            articles = self._parse_sina(soup)
        elif source == '腾讯体育':
            articles = self._parse_tencent(soup)
        elif source == 'bbc':
            articles = self._parse_bbc(soup)
        else:
            # 通用解析
            articles = self._parse_generic(soup)
        
        # 为每篇文章添加元数据
        for article in articles:
            article.update({
                'source': source,
                'section': section,
                'scraped_at': datetime.now().isoformat()
            })
        
        return articles
    
    def _parse_skysports(self, soup) -> List[Dict]:
        """解析Sky Sports新闻"""
        articles = []
        
        try:
            # Sky Sports文章选择器
            article_elements = soup.find_all('div', class_=re.compile(r'news-list__item'))
            
            for article_elem in article_elements:
                try:
                    article = self._extract_skysports_article(article_elem)
                    if article:
                        articles.append(article)
                except Exception as e:
                    self.logger.debug(f"解析Sky Sports文章失败: {e}")
                    continue
            
            # 备用选择器
            if not articles:
                article_links = soup.find_all('a', class_=re.compile(r'news-list__headline'))
                for link in article_links[:20]:  # 限制数量
                    try:
                        article = {
                            'title': link.text.strip(),
                            'url': urljoin('https://www.skysports.com', link.get('href', '')),
                            'summary': '',
                            'source': 'skysports'
                        }
                        articles.append(article)
                    except:
                        continue
        
        except Exception as e:
            self.logger.error(f"解析Sky Sports页面失败: {e}")
        
        return articles
    
    def _extract_skysports_article(self, article_elem) -> Optional[Dict]:
        """提取Sky Sports单篇文章"""
        try:
            # 标题
            title_elem = article_elem.find('h4', class_=re.compile(r'news-list__headline'))
            title = title_elem.text.strip() if title_elem else None
            
            # 链接
            link_elem = article_elem.find('a', href=True)
            url = urljoin('https://www.skysports.com', link_elem['href']) if link_elem else None
            
            # 摘要
            summary_elem = article_elem.find('p', class_=re.compile(r'news-list__snippet'))
            summary = summary_elem.text.strip() if summary_elem else ''
            
            # 发布时间
            time_elem = article_elem.find('time')
            published_time = time_elem.text.strip() if time_elem else None
            
            if title and url:
                article = {
                    'title': title,
                    'url': url,
                    'summary': summary,
                    'published_time': published_time,
                    'source': 'skysports'
                }
                return article
        
        except Exception as e:
            self.logger.debug(f"提取Sky Sports文章失败: {e}")
        
        return None
    
    def _parse_espn(self, soup) -> List[Dict]:
        """解析ESPN新闻"""
        articles = []
        
        try:
            # ESPN文章选择器
            article_elements = soup.find_all('article', class_=re.compile(r'contentItem'))
            
            for article_elem in article_elements:
                try:
                    article = self._extract_espn_article(article_elem)
                    if article:
                        articles.append(article)
                except Exception as e:
                    self.logger.debug(f"解析ESPN文章失败: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"解析ESPN页面失败: {e}")
        
        return articles
    
    def _extract_espn_article(self, article_elem) -> Optional[Dict]:
        """提取ESPN单篇文章"""
        try:
            # 标题
            title_elem = article_elem.find('h2')
            title = title_elem.text.strip() if title_elem else None
            
            # 链接
            link_elem = article_elem.find('a', href=True)
            url = urljoin('https://www.espn.com', link_elem['href']) if link_elem else None
            
            # 摘要
            summary_elem = article_elem.find('p')
            summary = summary_elem.text.strip() if summary_elem else ''
            
            if title and url:
                article = {
                    'title': title,
                    'url': url,
                    'summary': summary,
                    'source': 'espn'
                }
                return article
        
        except Exception as e:
            self.logger.debug(f"提取ESPN文章失败: {e}")
        
        return None
    
    def _parse_goal(self, soup) -> List[Dict]:
        """解析Goal.com新闻"""
        articles = []
        
        try:
            # Goal.com文章选择器
            article_elements = soup.find_all('article', class_=re.compile(r'article'))
            
            for article_elem in article_elements:
                try:
                    article = self._extract_goal_article(article_elem)
                    if article:
                        articles.append(article)
                except Exception as e:
                    self.logger.debug(f"解析Goal.com文章失败: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"解析Goal.com页面失败: {e}")
        
        return articles
    
    def _extract_goal_article(self, article_elem) -> Optional[Dict]:
        """提取Goal.com单篇文章"""
        try:
            # 标题
            title_elem = article_elem.find('h3')
            title = title_elem.text.strip() if title_elem else None
            
            # 链接
            link_elem = article_elem.find('a', href=True)
            url = urljoin('https://www.goal.com', link_elem['href']) if link_elem else None
            
            # 摘要
            summary_elem = article_elem.find('p')
            summary = summary_elem.text.strip() if summary_elem else ''
            
            if title and url:
                article = {
                    'title': title,
                    'url': url,
                    'summary': summary,
                    'source': 'goal'
                }
                return article
        
        except Exception as e:
            self.logger.debug(f"提取Goal.com文章失败: {e}")
        
        return None
    
    def _parse_sina(self, soup) -> List[Dict]:
        """解析新浪体育新闻"""
        articles = []
        
        try:
            # 新浪体育文章选择器
            article_elements = soup.find_all('div', class_=re.compile(r'news-item'))
            
            for article_elem in article_elements:
                try:
                    article = self._extract_sina_article(article_elem)
                    if article:
                        articles.append(article)
                except Exception as e:
                    self.logger.debug(f"解析新浪体育文章失败: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"解析新浪体育页面失败: {e}")
        
        return articles
    
    def _extract_sina_article(self, article_elem) -> Optional[Dict]:
        """提取新浪体育单篇文章"""
        try:
            # 标题
            title_elem = article_elem.find('a', class_=re.compile(r'title'))
            title = title_elem.text.strip() if title_elem else None
            
            # 链接
            url = title_elem.get('href', '') if title_elem else ''
            if url and not url.startswith('http'):
                url = urljoin('https://sports.sina.com.cn', url)
            
            # 摘要
            summary_elem = article_elem.find('p', class_re=re.compile(r'summary'))
            summary = summary_elem.text.strip() if summary_elem else ''
            
            # 发布时间
            time_elem = article_elem.find('span', class_=re.compile(r'time'))
            published_time = time_elem.text.strip() if time_elem else None
            
            if title and url:
                article = {
                    'title': title,
                    'url': url,
                    'summary': summary,
                    'published_time': published_time,
                    'source': '新浪体育'
                }
                return article
        
        except Exception as e:
            self.logger.debug(f"提取新浪体育文章失败: {e}")
        
        return None
    
    def _parse_tencent(self, soup) -> List[Dict]:
        """解析腾讯体育新闻"""
        articles = []
        
        try:
            # 腾讯体育文章选择器
            article_elements = soup.find_all('div', class_=re.compile(r'news-item'))
            
            for article_elem in article_elements:
                try:
                    article = self._extract_tencent_article(article_elem)
                    if article:
                        articles.append(article)
                except Exception as e:
                    self.logger.debug(f"解析腾讯体育文章失败: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"解析腾讯体育页面失败: {e}")
        
        return articles
    
    def _extract_tencent_article(self, article_elem) -> Optional[Dict]:
        """提取腾讯体育单篇文章"""
        try:
            # 标题
            title_elem = article_elem.find('a', class_=re.compile(r'title'))
            title = title_elem.text.strip() if title_elem else None
            
            # 链接
            url = title_elem.get('href', '') if title_elem else ''
            if url and not url.startswith('http'):
                url = urljoin('https://sports.qq.com', url)
            
            # 摘要
            summary_elem = article_elem.find('p')
            summary = summary_elem.text.strip() if summary_elem else ''
            
            if title and url:
                article = {
                    'title': title,
                    'url': url,
                    'summary': summary,
                    'source': '腾讯体育'
                }
                return article
        
        except Exception as e:
            self.logger.debug(f"提取腾讯体育文章失败: {e}")
        
        return None
    
    def _parse_bbc(self, soup) -> List[Dict]:
        """解析BBC Sport新闻"""
        articles = []
        
        try:
            # BBC文章选择器
            article_elements = soup.find_all('div', class_=re.compile(r'gs-c-promo'))
            
            for article_elem in article_elements:
                try:
                    article = self._extract_bbc_article(article_elem)
                    if article:
                        articles.append(article)
                except Exception as e:
                    self.logger.debug(f"解析BBC文章失败: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"解析BBC页面失败: {e}")
        
        return articles
    
    def _extract_bbc_article(self, article_elem) -> Optional[Dict]:
        """提取BBC单篇文章"""
        try:
            # 标题
            title_elem = article_elem.find('h3')
            title = title_elem.text.strip() if title_elem else None
            
            # 链接
            link_elem = article_elem.find('a', href=True)
            url = urljoin('https://www.bbc.com', link_elem['href']) if link_elem else None
            
            # 摘要
            summary_elem = article_elem.find('p')
            summary = summary_elem.text.strip() if summary_elem else ''
            
            if title and url:
                article = {
                    'title': title,
                    'url': url,
                    'summary': summary,
                    'source': 'bbc'
                }
                return article
        
        except Exception as e:
            self.logger.debug(f"提取BBC文章失败: {e}")
        
        return None
    
    def _parse_generic(self, soup) -> List[Dict]:
        """通用新闻解析"""
        articles = []
        
        try:
            # 查找所有文章链接
            article_links = []
            
            # 尝试多种选择器
            selectors = [
                'article a',
                '.news-item a',
                '.article a',
                '.post a',
                'h3 a',
                'h2 a'
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href', '')
                    if href and not href.startswith('#') and 'article' in href.lower():
                        article_links.append(link)
            
            # 去重
            unique_links = {}
            for link in article_links:
                href = link.get('href', '')
                if href and href not in unique_links:
                    unique_links[href] = link
            
            # 提取文章信息
            for link in unique_links.values()[:20]:  # 限制数量
                try:
                    title = link.text.strip()
                    url = link.get('href', '')
                    
                    if title and url:
                        # 确保URL完整
                        if not url.startswith('http'):
                            url = urljoin('https://example.com', url)
                        
                        article = {
                            'title': title,
                            'url': url,
                            'summary': '',
                            'source': 'generic'
                        }
                        articles.append(article)
                except:
                    continue
        
        except Exception as e:
            self.logger.error(f"通用解析失败: {e}")
        
        return articles
    
    def fetch_article_content(self, article_url: str) -> Optional[Dict]:
        """
        获取文章详细内容
        
        Args:
            article_url: 文章URL
            
        Returns:
            文章详细内容
        """
        self.logger.info(f"获取文章内容: {article_url}")
        
        response = self.make_request(article_url)
        if not response or response.status_code != 200:
            self.logger.error(f"获取文章内容失败: {article_url}")
            return None
        
        soup = self.parse_html(response.text)
        
        try:
            # 提取文章内容
            content_elem = soup.find('article') or soup.find('div', class_=re.compile(r'content|article-body'))
            
            if content_elem:
                # 获取所有文本段落
                paragraphs = content_elem.find_all('p')
                content_text = '\n'.join([p.text.strip() for p in paragraphs if p.text.strip()])
                
                # 提取发布时间
                time_elem = soup.find('time') or soup.find('span', class_=re.compile(r'time|date'))
                published_time = time_elem.text.strip() if time_elem else None
                
                # 提取作者
                author_elem = soup.find('span', class_=re.compile(r'author|byline'))
                author = author_elem.text.strip() if author_elem else None
                
                article_content = {
                    'url': article_url,
                    'content': content_text,
                    'published_time': published_time,
                    'author': author,
                    'scraped_at': datetime.now().isoformat(),
                    'word_count': len(content_text.split())
                }
                
                return article_content
            else:
                self.logger.warning(f"无法提取文章内容: {article_url}")
                return None
        
        except Exception as e:
            self.logger.error(f"解析文章内容失败: {article_url}, 错误: {e}")
            return None
    
    def analyze_article(self, article_content: Dict) -> Dict:
        """
        分析文章内容
        
        Args:
            article_content: 文章内容
            
        Returns:
            分析结果
        """
        analysis = {
            'keywords': [],
            'entities': [],
            'sentiment': 'neutral',
            'news_type': 'unknown',
            'relevance_score': 0
        }
        
        content = article_content.get('content', '')
        if not content:
            return analysis
        
        # 提取关键词
        keywords = self._extract_keywords(content)
        analysis['keywords'] = keywords
        
        # 识别实体（球队、球员、联赛）
        entities = self._identify_entities(content)
        analysis['entities'] = entities
        
        # 情感分析（简化版）
        sentiment = self._analyze_sentiment(content)
        analysis['sentiment'] = sentiment
        
        # 新闻类型识别
        news_type = self._identify_news_type(content)
        analysis['news_type'] = news_type
        
        # 相关性评分
        relevance_score = self._calculate_relevance_score(keywords, entities)
        analysis['relevance_score'] = relevance_score
        
        return analysis
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        keywords = []
        
        # 简单关键词提取（实际应该使用更复杂的方法）
        words = text.lower().split()
        word_freq = {}
        
        for word in words:
            # 清理单词
            clean_word = re.sub(r'[^\w]', '', word)
            if len(clean_word) > 3:  # 只考虑长度大于3的单词
                word_freq[clean_word] = word_freq.get(clean_word, 0) + 1
        
        # 获取频率最高的前10个单词
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in sorted_words[:10]]
        
        return keywords
    
    def _identify_entities(self, text: str) -> List[Dict]:
        """识别实体"""
        entities = []
        text_lower = text.lower()
        
        # 检查联赛
        for league_key, keywords in self.keyword_mapping.items():
            if league_key.endswith('_league'):
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        entities.append({
                            'type': 'league',
                            'name': league_key,
                            'keywords': keywords
                        })
                        break
        
        # 检查球队
        for team_key, keywords in self.keyword_mapping.items():
            if not team_key.endswith('_league'):
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        entities.append({
                            'type': 'team',
                            'name': team_key,
                            'keywords': keywords
                        })
                        break
        
        # 去重
        unique_entities = []
        seen = set()
        for entity in entities:
            entity_key = f"{entity['type']}_{entity['name']}"
            if entity_key not in seen:
                seen.add(entity_key)
                unique_entities.append(entity)
        
        return unique_entities
    
    def _analyze_sentiment(self, text: str) -> str:
        """情感分析（简化版）"""
        positive_words = ['win', '胜利', 'good', 'excellent', 'great', 'positive', 'optimistic']
        negative_words = ['loss', '失败', 'bad', 'poor', 'negative', 'injury', '伤病', 'suspended', '禁赛']
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _identify_news_type(self, text: str) -> str:
        """识别新闻类型"""
        text_lower = text.lower()
        
        type_patterns = {
            'transfer': ['transfer', 'sign', '签约', '转会'],
            'injury': ['injury', 'injured', '伤病', '受伤'],
            'match_preview': ['preview', 'pre-match', '赛前', '前瞻'],
            'match_report': ['report', 'result', '赛后', '战报'],
            'rumour': ['rumour', 'rumor', '传闻', '传言'],
            'official': ['official', 'announce', '官方', '宣布'],
            'interview': ['interview', 'said', '表示', '采访']
        }
        
        for news_type, patterns in type_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return self.news_types.get(news_type, news_type)
        
        return 'unknown'
    
    def _calculate_relevance_score(self, keywords: List[str], entities: List[Dict]) -> float:
        """计算相关性评分"""
        score = 0.0
        
        # 基于实体数量
        score += len(entities) * 0.2
        
        # 基于关键词数量
        score += len(keywords) * 0.1
        
        # 基于实体类型
        for entity in entities:
            if entity['type'] == 'team':
                score += 0.3
            elif entity['type'] == 'league':
                score += 0.2
        
        # 限制在0-1之间
        return min(1.0, score)
    
    def fetch_news_by_team(self, team_name: str, hours: int = 24) -> List[Dict]:
        """
        获取指定球队相关新闻
        
        Args:
            team_name: 球队名称
            hours: 时间范围（小时）
            
        Returns:
            新闻列表
        """
        all_articles = []
        
        # 获取球队关键词
        team_keywords = []
        for key, keywords in self.keyword_mapping.items():
            if team_name.lower() in [k.lower() for k in keywords]:
                team_keywords = keywords
                break
        
        if not team_keywords:
            self.logger.warning(f"未找到球队 {team_name} 的关键词映射")
            team_keywords = [team_name]
        
        # 从多个新闻源获取
        sources = ['skysports', 'espn', 'goal', '新浪体育', '腾讯体育']
        
        for source in sources:
            try:
                news_data = self.fetch_news(source, 'news', max_articles=10)
                if news_data and news_data['articles']:
                    # 过滤相关文章
                    relevant_articles = []
                    for article in news_data['articles']:
                        # 检查标题是否包含球队关键词
                        title = article.get('title', '').lower()
                        if any(keyword.lower() in title for keyword in team_keywords):
                            # 获取详细内容
                            content = self.fetch_article_content(article['url'])
                            if content:
                                # 分析文章
                                analysis = self.analyze_article(content)
                                
                                article_data = {
                                    'title': article['title'],
                                    'url': article['url'],
                                    'source': article['source'],
                                    'published_time': article.get('published_time'),
                                    'content_preview': content['content'][:200] + '...',
                                    'analysis': analysis,
                                    'scraped_at': article.get('scraped_at')
                                }
                                relevant_articles.append(article_data)
                    
                    if relevant_articles:
                        self.logger.info(f"从 {source} 获取到 {len(relevant_articles)} 篇相关新闻")
                        all_articles.extend(relevant_articles)
            except Exception as e:
                self.logger.warning(f"从 {source} 获取新闻失败: {e}")
                continue
        
        # 按相关性评分排序
        all_articles.sort(key=lambda x: x.get('analysis', {}).get('relevance_score', 0), reverse=True)
        
        return all_articles
    
    def process_data(self, raw_data: Any) -> List[Dict]:
        """
        处理原始新闻数据
        
        Args:
            raw_data: 原始数据
            
        Returns:
            处理后的新闻数据
        """
        processed_articles = []
        
        if isinstance(raw_data, dict) and 'articles' in raw_data:
            articles = raw_data['articles']
            
            for article in articles:
                try:
                    # 获取详细内容
                    content = self.fetch_article_content(article['url'])
                    if not content:
                        continue
                    
                    # 分析文章
                    analysis = self.analyze_article(content)
                    
                    # 构建处理后的文章数据
                    processed_article = {
                        'title': article.get('title'),
                        'url': article.get('url'),
                        'source': article.get('source', raw_data.get('source')),
                        'section': raw_data.get('section'),
                        'published_time': article.get('published_time'),
                        'scraped_at': raw_data.get('scraped_at'),
                        'content': content['content'],
                        'content_metadata': {
                            'author': content.get('author'),
                            'word_count': content.get('word_count'),
                            'scraped_at': content.get('scraped_at')
                        },
                        'analysis': analysis
                    }
                    
                    processed_articles.append(processed_article)
                    
                except Exception as e:
                    self.logger.warning(f"处理文章失败: {article.get('url')}, 错误: {e}")
                    continue
        
        return processed_articles


if __name__ == "__main__":
    # 测试新闻抓取器
    news_fetcher = NewsFetcher()
    
    print("测试新闻舆情抓取...")
    
    # 测试基本新闻获取
    print("\n1. 测试基本新闻获取:")
    try:
        # 从Sky Sports获取新闻
        news_data = news_fetcher.fetch_news('skysports', 'news', max_articles=5)
        if news_data:
            print(f"  从 {news_data['source']} 获取到 {news_data['count']} 篇新闻")
            for i, article in enumerate(news_data['articles'][:3]):  # 显示前3篇
                print(f"    {i+1}. {article['title'][:50]}...")
                print(f"       链接: {article['url']}")
        else:
            print("  获取新闻失败（可能需要网络连接）")
    except Exception as e:
        print(f"  新闻获取测试失败: {e}")
    
    # 测试球队相关新闻
    print("\n2. 测试球队相关新闻:")
    try:
        team_news = news_fetcher.fetch_news_by_team('Manchester United', hours=24)
        print(f"  获取到 {len(team_news)} 篇曼联相关新闻")
        
        if team_news:
            for i, article in enumerate(team_news[:2]):  # 显示前2篇
                print(f"    {i+1}. {article['title'][:60]}...")
                analysis = article.get('analysis', {})
                print(f"       类型: {analysis.get('news_type', '未知')}")
                print(f"       情感: {analysis.get('sentiment', '中性')}")
                print(f"       相关性: {analysis.get('relevance_score', 0):.2f}")
    except Exception as e:
        print(f"  球队新闻测试失败: {e}")
    
    # 测试文章内容分析
    print("\n3. 测试文章内容分析:")
    try:
        # 使用示例文章（实际应该使用真实URL）
        sample_content = {
            'content': 'Manchester United won their match against Liverpool with a fantastic performance. The team showed great spirit and determination.',
            'url': 'https://example.com/article'
        }
        
        analysis = news_fetcher.analyze_article(sample_content)
        print(f"  分析结果:")
        print(f"    情感: {analysis['sentiment']}")
        print(f"    类型: {analysis['news_type']}")
        print(f"    相关性: {analysis['relevance_score']:.2f}")
        print(f"    实体: {len(analysis['entities'])} 个")
        for entity in analysis['entities']:
            print(f"      - {entity['type']}: {entity['name']}")
        print(f"    关键词: {', '.join(analysis['keywords'][:5])}")
    
    except Exception as e:
        print(f"  文章分析测试失败: {e}")
    
    print("\n新闻舆情抓取器测试完成")