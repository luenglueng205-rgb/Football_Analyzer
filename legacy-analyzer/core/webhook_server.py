#!/usr/bin/env python3
"""
Webhook推送系统 - HTTP服务器接收外部触发，支持微信/Telegram等通知方式
"""

import os
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import hashlib
import hmac

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """通知类型"""
    WECHAT = "wechat"
    TELEGRAM = "telegram"
    DINGTALK = "dingtalk"
    FEISHU = "feishu"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    CUSTOM = "custom"


@dataclass
class WebhookMessage:
    """Webhook消息结构"""
    event_type: str
    timestamp: str
    data: Dict[str, Any]
    signature: Optional[str] = None
    retry_count: int = 0


@dataclass
class NotificationConfig:
    """通知配置"""
    notification_type: str
    enabled: bool = True
    webhook_url: Optional[str] = None
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    custom_headers: Dict[str, str] = field(default_factory=dict)
    retry_times: int = 3
    timeout: int = 30


class NotificationSender:
    """通知发送器基类"""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
        self.enabled = config.enabled
        
    def send(self, message: str, title: str = None, data: Dict = None) -> bool:
        """发送通知"""
        raise NotImplementedError
        
    def format_message(self, message: str, title: str = None, data: Dict = None) -> str:
        """格式化消息"""
        if title:
            return f"{title}\n{message}"
        return message


class WechatNotifier(NotificationSender):
    """微信通知器（预留接口）"""
    
    def __init__(self, config: NotificationConfig):
        super().__init__(config)
        self.corp_id = config.api_key
        self.corp_secret = config.secret_key
        self.agent_id = config.custom_headers.get('agent_id')
        
    def send(self, message: str, title: str = None, data: Dict = None) -> bool:
        """
        发送微信通知
        
        Args:
            message: 消息内容
            title: 标题
            data: 附加数据
            
        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            logger.warning("微信通知未启用")
            return False
            
        # TODO: 实现企业微信API调用
        # 这里预留接口，实际使用时需要替换为真实的企业微信API调用
        
        webhook_url = self.config.webhook_url
        if not webhook_url:
            logger.error("未配置微信Webhook URL")
            return False
            
        payload = {
            "msgtype": "text",
            "text": {
                "content": self.format_message(message, title)
            }
        }
        
        # 这里应该调用实际的HTTP请求
        # requests.post(webhook_url, json=payload)
        
        logger.info(f"微信通知已发送: {message[:50]}...")
        return True


class TelegramNotifier(NotificationSender):
    """Telegram通知器（预留接口）"""
    
    def __init__(self, config: NotificationConfig):
        super().__init__(config)
        self.bot_token = config.api_key
        self.chat_id = config.custom_headers.get('chat_id')
        
    def send(self, message: str, title: str = None, data: Dict = None) -> bool:
        """
        发送Telegram通知
        
        Args:
            message: 消息内容
            title: 标题
            data: 附加数据
            
        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            logger.warning("Telegram通知未启用")
            return False
            
        webhook_url = self.config.webhook_url
        if not webhook_url:
            logger.error("未配置Telegram Bot URL")
            return False
            
        # TODO: 实现Telegram Bot API调用
        # payload = {
        #     "chat_id": self.chat_id,
        #     "text": self.format_message(message, title),
        #     "parse_mode": "Markdown"
        # }
        # requests.post(f"https://api.telegram.org/bot{self.bot_token}/sendMessage", json=payload)
        
        logger.info(f"Telegram通知已发送: {message[:50]}...")
        return True


class DingTalkNotifier(NotificationSender):
    """钉钉通知器（预留接口）"""
    
    def __init__(self, config: NotificationConfig):
        super().__init__(config)
        self.secret = config.secret_key
        
    def send(self, message: str, title: str = None, data: Dict = None) -> bool:
        """发送钉钉通知"""
        if not self.enabled:
            return False
            
        webhook_url = self.config.webhook_url
        if not webhook_url:
            logger.error("未配置钉钉Webhook URL")
            return False
            
        # TODO: 实现钉钉自定义机器人API调用
        # 需要使用签名验证
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        secret_enc = bytes(secret_enc)
        import hmac
        import hashlib
        import base64
        import urllib.parse
        
        sign = hmac.new(secret_enc, (timestamp + '\n' + self.secret).encode('utf-8'), 
                       hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(sign))
        
        url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
        
        payload = {
            "msgtype": "text",
            "text": {"content": self.format_message(message, title)}
        }
        
        logger.info(f"钉钉通知已发送: {message[:50]}...")
        return True


class WebhookServer:
    """
    Webhook服务器
    接收外部触发并处理回调
    """
    
    def __init__(self, host: str = '0.0.0.0', port: int = 5000, base_dir: str = None):
        """
        初始化Webhook服务器
        
        Args:
            host: 服务器地址
            port: 服务器端口
            base_dir: 基础目录
        """
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir
        
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        
        # 消息处理器
        self.handlers: Dict[str, Callable] = {}
        
        # 通知器
        self.notifiers: Dict[NotificationType, NotificationSender] = {}
        
        # 消息队列
        self.message_queue: List[WebhookMessage] = []
        
        # 配置
        self.config = self._load_config()
        
        # 注册默认处理器
        self._register_default_handlers()
        
        logger.info(f"Webhook服务器初始化完成 (host={host}, port={port})")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        config_file = os.path.join(self.base_dir, 'config', 'webhook_config.json')
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载Webhook配置失败: {e}")
                
        # 默认配置
        return {
            "enabled": True,
            "secret_key": "",
            "allowed_ips": [],
            "notifications": {
                "wechat": {"enabled": False, "webhook_url": ""},
                "telegram": {"enabled": False, "bot_token": "", "chat_id": ""},
                "dingtalk": {"enabled": False, "webhook_url": "", "secret": ""}
            }
        }

    def _register_default_handlers(self):
        """注册默认处理器"""
        self.register_handler('match_update', self._handle_match_update)
        self.register_handler('odds_change', self._handle_odds_change)
        self.register_handler('bet_placed', self._handle_bet_placed)
        self.register_handler('result_update', self._handle_result_update)
        self.register_handler('analysis_complete', self._handle_analysis_complete)
        self.register_handler('alert', self._handle_alert)

    def register_handler(self, event_type: str, handler: Callable):
        """
        注册事件处理器
        
        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        self.handlers[event_type] = handler
        logger.info(f"已注册处理器: {event_type}")

    def register_notifier(self, notification_type: NotificationType, 
                         notifier: NotificationSender):
        """
        注册通知器
        
        Args:
            notification_type: 通知类型
            notifier: 通知器实例
        """
        self.notifiers[notification_type] = notifier
        logger.info(f"已注册通知器: {notification_type.value}")

    def verify_signature(self, payload: str, signature: str) -> bool:
        """
        验证签名
        
        Args:
            payload: 请求体
            signature: 签名
            
        Returns:
            bool: 验证结果
        """
        if not self.config.get('secret_key'):
            return True
            
        expected = hmac.new(
            self.config['secret_key'].encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)

    def process_webhook(self, event_type: str, data: Dict[str, Any], 
                       signature: str = None) -> Dict[str, Any]:
        """
        处理Webhook请求
        
        Args:
            event_type: 事件类型
            data: 请求数据
            signature: 签名
            
        Returns:
            Dict: 处理结果
        """
        # 创建消息
        message = WebhookMessage(
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            data=data,
            signature=signature
        )
        
        # 添加到队列
        self.message_queue.append(message)
        
        # 调用处理器
        handler = self.handlers.get(event_type)
        if handler:
            try:
                result = handler(data)
                return {'success': True, 'result': result}
            except Exception as e:
                logger.error(f"处理Webhook失败: {e}")
                return {'success': False, 'error': str(e)}
        else:
            logger.warning(f"未找到处理器: {event_type}")
            return {'success': False, 'error': f'Unknown event type: {event_type}'}

    def _handle_match_update(self, data: Dict) -> Dict[str, Any]:
        """处理比赛更新"""
        logger.info(f"收到比赛更新: {data.get('match_id')}")
        return {'processed': True, 'action': 'match_update'}

    def _handle_odds_change(self, data: Dict) -> Dict[str, Any]:
        """处理赔率变化"""
        logger.info(f"收到赔率变化: {data.get('match_id')}")
        return {'processed': True, 'action': 'odds_change'}

    def _handle_bet_placed(self, data: Dict) -> Dict[str, Any]:
        """处理投注下单"""
        logger.info(f"收到投注: {data.get('bet_id')}")
        return {'processed': True, 'action': 'bet_placed'}

    def _handle_result_update(self, data: Dict) -> Dict[str, Any]:
        """处理赛果更新"""
        logger.info(f"收到赛果更新: {data.get('match_id')}")
        return {'processed': True, 'action': 'result_update'}

    def _handle_analysis_complete(self, data: Dict) -> Dict[str, Any]:
        """处理分析完成"""
        logger.info(f"收到分析完成通知: {data.get('analysis_id')}")
        
        # 可以触发通知
        self.notify("analysis_complete", 
                   f"分析完成: {data.get('summary', '任务已完成')}")
        
        return {'processed': True, 'action': 'analysis_complete'}

    def _handle_alert(self, data: Dict) -> Dict[str, Any]:
        """处理告警"""
        logger.warning(f"收到告警: {data.get('message')}")
        
        # 紧急通知
        self.notify("alert",
                   f"⚠️ 告警: {data.get('message')}",
                   urgent=True)
        
        return {'processed': True, 'action': 'alert'}

    def notify(self, notification_type: str, message: str, 
               title: str = None, urgent: bool = False) -> bool:
        """
        发送通知
        
        Args:
            notification_type: 通知类型
            message: 消息内容
            title: 标题
            urgent: 是否紧急
            
        Returns:
            bool: 是否发送成功
        """
        ntype = NotificationType(notification_type)
        notifier = self.notifiers.get(ntype)
        
        if notifier:
            return notifier.send(message, title)
        else:
            logger.debug(f"未配置通知器: {notification_type}")
            return False

    def broadcast(self, message: str, title: str = None):
        """
        广播通知到所有渠道
        
        Args:
            message: 消息内容
            title: 标题
        """
        for ntype, notifier in self.notifiers.items():
            if notifier.enabled:
                try:
                    notifier.send(message, title)
                except Exception as e:
                    logger.error(f"广播通知失败 [{ntype.value}]: {e}")

    def start_server(self):
        """启动服务器（预留接口）"""
        logger.info(f"Webhook服务器配置完成 (host={self.host}, port={self.port})")
        logger.info("注意: 请使用Flask或其他HTTP框架实际启动服务器")
        logger.info("示例: 使用flask run --host=0.0.0.0 --port=5000")
        
        # TODO: 使用Flask实现实际的HTTP服务器
        # from flask import Flask, request, jsonify
        # app = Flask(__name__)
        #
        # @app.route('/webhook', methods=['POST'])
        # def webhook():
        #     data = request.json
        #     event_type = request.headers.get('X-Event-Type', 'unknown')
        #     signature = request.headers.get('X-Signature', '')
        #     return jsonify(self.process_webhook(event_type, data, signature))
        #
        # @app.route('/health', methods=['GET'])
        # def health():
        #     return jsonify({'status': 'ok'})
        #
        # app.run(host=self.host, port=self.port)

    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            'queue_size': len(self.message_queue),
            'handlers': list(self.handlers.keys()),
            'notifiers': [n.value for n in self.notifiers.keys()],
            'server_config': {
                'host': self.host,
                'port': self.port,
                'enabled': self.config.get('enabled', True)
            }
        }

    def clear_queue(self):
        """清空消息队列"""
        count = len(self.message_queue)
        self.message_queue.clear()
        logger.info(f"已清空消息队列 ({count} 条)")


def create_webhook_server(config: Dict[str, Any] = None) -> WebhookServer:
    """
    创建Webhook服务器的工厂函数
    
    Args:
        config: 配置字典
        
    Returns:
        WebhookServer: 配置好的服务器实例
    """
    server = WebhookServer()
    
    # 应用自定义配置
    if config:
        if 'host' in config:
            server.host = config['host']
        if 'port' in config:
            server.port = config['port']
            
        # 配置通知器
        notifications = config.get('notifications', {})
        
        if notifications.get('wechat', {}).get('enabled'):
            wechat_config = NotificationConfig(
                notification_type='wechat',
                enabled=True,
                webhook_url=notifications['wechat'].get('webhook_url')
            )
            server.register_notifier(NotificationType.WECHAT, WechatNotifier(wechat_config))
            
        if notifications.get('telegram', {}).get('enabled'):
            telegram_config = NotificationConfig(
                notification_type='telegram',
                enabled=True,
                api_key=notifications['telegram'].get('bot_token'),
                custom_headers={'chat_id': notifications['telegram'].get('chat_id')}
            )
            server.register_notifier(NotificationType.TELEGRAM, TelegramNotifier(telegram_config))
            
        if notifications.get('dingtalk', {}).get('enabled'):
            dingtalk_config = NotificationConfig(
                notification_type='dingtalk',
                enabled=True,
                webhook_url=notifications['dingtalk'].get('webhook_url'),
                secret_key=notifications['dingtalk'].get('secret')
            )
            server.register_notifier(NotificationType.DINGTALK, DingTalkNotifier(dingtalk_config))
            
    return server


def demo():
    """演示函数"""
    print("=" * 60)
    print("Webhook推送系统演示")
    print("=" * 60)
    
    # 创建服务器
    server = create_webhook_server({
        'host': '0.0.0.0',
        'port': 5000,
        'notifications': {
            'wechat': {'enabled': True, 'webhook_url': 'https://qyapi.weixin.qq.com/...'},
            'telegram': {'enabled': True, 'bot_token': 'xxx', 'chat_id': 'yyy'}
        }
    })
    
    print("\n" + "-" * 60)
    print("Webhook处理测试")
    print("-" * 60)
    
    # 测试各种事件
    test_events = [
        ('match_update', {'match_id': '12345', 'home': '曼联', 'away': '利物浦'}),
        ('odds_change', {'match_id': '12345', 'odds': 1.85, 'change': 0.05}),
        ('analysis_complete', {'analysis_id': 'a001', 'summary': '推荐2串1方案'}),
        ('alert', {'message': '检测到赔率异常'})
    ]
    
    for event_type, data in test_events:
        print(f"\n触发事件: {event_type}")
        result = server.process_webhook(event_type, data)
        print(f"处理结果: {result}")
        
    # 显示状态
    print("\n" + "-" * 60)
    print("服务器状态")
    print("-" * 60)
    status = server.get_queue_status()
    print(f"队列大小: {status['queue_size']}")
    print(f"已注册处理器: {status['handlers']}")
    print(f"已注册通知器: {status['notifiers']}")


if __name__ == "__main__":
    demo()
