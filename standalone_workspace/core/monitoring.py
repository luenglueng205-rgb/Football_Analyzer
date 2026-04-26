"""
Sentry 异常追踪模块

使用方式：在任意入口文件中 import 即可
    from core.monitoring import init_sentry  # noqa: F401

Sentry 采用单例模式，重复调用 init_sentry() 不会重复初始化。
DSN 未配置时静默跳过，不影响正常运行。
"""

import os
from dotenv import load_dotenv

load_dotenv()

SENTRY_DSN = os.getenv("SENTRY_DSN", "")


def init_sentry():
    """Sentry 异常追踪初始化。DSN 未配置或 sentry_sdk 未安装时静默跳过。"""
    if not SENTRY_DSN:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            environment=os.getenv("ENV", "development"),
            release=os.getenv("APP_VERSION", "football_analyzer@unknown"),
        )
    except ImportError:
        pass


init_sentry()
