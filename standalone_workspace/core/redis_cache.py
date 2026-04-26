# -*- coding: utf-8 -*-
"""
P3-3: Redis 分布式缓存层 + 内存兜底
============================================
功能：
- Redis 主缓存（跨进程持久化，支持 TTL）
- 自动降级到内存缓存（Redis 不可用时）
- 完整数据类型序列化/反序列化
- 缓存统计（命中率、大小监控）

依赖：redis>=5.0.0
配置：.env 中 REDIS_HOST / REDIS_PORT / REDIS_DB / REDIS_PASSWORD
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

try:
    import redis as _redis
    _REDIS_AVAILABLE = True
except ImportError:
    _redis = None  # type: ignore[assignment]
    _REDIS_AVAILABLE = False

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── 配置常量 ──────────────────────────────────────────────────────────────────
_DEFAULT_TTL = int(os.getenv("REDIS_CACHE_TTL", 86400))   # 默认 24 小时
_PREFIX = os.getenv("REDIS_CACHE_PREFIX", "fb")
_REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
_REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
_REDIS_DB = int(os.getenv("REDIS_DB", "0"))
_REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None) or None


class RedisCache:
    """
    Redis 分布式缓存 + 内存兜底

    设计原则：
    1. Redis 可用时作为主缓存（跨进程共享）
    2. Redis 不可用时自动降级到内存字典
    3. 所有操作幂等，不抛异常
    4. 支持任意 JSON 可序列化对象
    """

    _instance: Optional["RedisCache"] = None

    def __init__(
        self,
        prefix: str = _PREFIX,
        default_ttl: int = _DEFAULT_TTL,
        host: str = _REDIS_HOST,
        port: int = _REDIS_PORT,
        db: int = _REDIS_DB,
        password: Optional[str] = _REDIS_PASSWORD,
    ):
        self.prefix = prefix
        self.default_ttl = default_ttl

        # ── 内存兜底（Redis 不可用时）──────────────────────────────────────────
        self._memory: Dict[str, tuple[Any, Optional[datetime]]] = {}

        # ── Redis 连接（延迟初始化）────────────────────────────────────────────
        self._redis: Optional[Any] = None
        self._redis_config = dict(host=host, port=port, db=db, password=password,
                                  decode_responses=False, socket_timeout=3,
                                  socket_connect_timeout=3, retry_on_timeout=False)

        # ── 统计计数器 ─────────────────────────────────────────────────────────
        self._stats = {"hit": 0, "miss": 0, "mem_fallback": 0, "redis_err": 0}

    # ── 单例 ───────────────────────────────────────────────────────────────────
    @classmethod
    def get_instance(cls) -> "RedisCache":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Redis 连接管理 ─────────────────────────────────────────────────────────
    def _get_redis(self) -> Optional[Any]:
        if not _REDIS_AVAILABLE:
            return None
        if self._redis is None:
            try:
                self._redis = _redis.Redis(**self._redis_config)  # type: ignore[operator]
                self._redis.ping()
                logger.info(f"[Redis] 连接成功 {self._redis_config['host']}:{self._redis_config['port']}")
            except Exception as e:
                logger.warning(f"[Redis] 连接失败，降级到内存缓存: {e}")
                self._redis = None
        return self._redis

    # ── Key 工具 ───────────────────────────────────────────────────────────────
    def _make_key(self, key: str) -> str:
        """生成带前缀的哈希 key，避免撞库"""
        h = hashlib.md5(key.encode("utf-8")).hexdigest()[:16]
        return f"{self.prefix}:{h}:{key}"

    # ── 公开 API ───────────────────────────────────────────────────────────────
    def get(self, key: str) -> Optional[Any]:
        """
        读取缓存。
        优先 Redis → 回退内存。
        """
        # Redis 路径
        client = self._get_redis()
        if client:
            try:
                full_key = self._make_key(key)
                raw = client.get(full_key)
                if raw is not None:
                    self._stats["hit"] += 1
                    return json.loads(raw.decode("utf-8"))
            except Exception as e:
                self._stats["redis_err"] += 1
                logger.warning(f"[Redis] get 失败，降级内存: {e}")

        # 内存兜底
        if key in self._memory:
            value, expiry = self._memory[key]
            if expiry is None or expiry > datetime.now():
                self._stats["hit"] += 1
                self._stats["mem_fallback"] += 1
                return value
            else:
                del self._memory[key]

        self._stats["miss"] += 1
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        写入缓存。
        优先写入 Redis → 同步写入内存（作为兜底快照）。
        """
        ttl = ttl if ttl is not None else self.default_ttl
        expiry = (datetime.now() + timedelta(seconds=ttl)) if ttl > 0 else None

        # 同步写入内存（即使 Redis 不可用，内存也始终可用）
        self._memory[key] = (value, expiry)

        # Redis 路径
        client = self._get_redis()
        if client:
            try:
                full_key = self._make_key(key)
                payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
                client.setex(full_key, ttl, payload)
                return True
            except Exception as e:
                self._stats["redis_err"] += 1
                logger.warning(f"[Redis] set 失败，仅保留内存缓存: {e}")

        return True   # 内存已写入，视为成功

    def delete(self, key: str) -> bool:
        """删除指定缓存项"""
        self._memory.pop(key, None)
        client = self._get_redis()
        if client:
            try:
                client.delete(self._make_key(key))
            except Exception:
                pass
        return True

    def clear_prefix(self) -> int:
        """清除所有带当前前缀的键（Redis + 内存）"""
        count = 0
        # 内存
        keys_to_del = [k for k in self._memory if k.startswith(self.prefix)]
        for k in keys_to_del:
            del self._memory[k]
            count += 1
        # Redis
        client = self._get_redis()
        if client:
            try:
                pattern = f"{self.prefix}:*"
                cursor = 0
                while True:
                    cursor, keys = client.scan(cursor, match=pattern, count=200)
                    if keys:
                        client.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"[Redis] clear_prefix 失败: {e}")
        return count

    def stats(self) -> Dict[str, Any]:
        """返回缓存命中率统计"""
        total = self._stats["hit"] + self._stats["miss"]
        hit_rate = self._stats["hit"] / total if total > 0 else 0.0
        return {
            "hit": self._stats["hit"],
            "miss": self._stats["miss"],
            "hit_rate": round(hit_rate, 4),
            "mem_fallback": self._stats["mem_fallback"],
            "redis_err": self._stats["redis_err"],
            "mem_size": len(self._memory),
        }

    def warm_memory(self) -> int:
        """
        从 Redis 预热内存兜底（Redis 重启后内存为空，调用此方法可重建兜底）。
        返回预热条目数。
        """
        count = 0
        client = self._get_redis()
        if client:
            try:
                pattern = f"{self.prefix}:*"
                cursor = 0
                while True:
                    cursor, keys = client.scan(cursor, match=pattern, count=200)
                    for full_key in keys:
                        raw = client.get(full_key)
                        if raw:
                            try:
                                # 从 full_key 逆推原始 key（不完美但够用）
                                value = json.loads(raw.decode("utf-8"))
                                # 尝试提取原始 key 部分
                                parts = full_key.split(":", 2)
                                if len(parts) >= 3:
                                    original_key = parts[2]
                                    self._memory[original_key] = (value, None)
                                    count += 1
                            except Exception:
                                pass
                    if cursor == 0:
                        break
                logger.info(f"[RedisCache] 预热完成，共 {count} 条")
            except Exception as e:
                logger.warning(f"[RedisCache] 预热失败: {e}")
        return count

    def __repr__(self) -> str:
        client = self._get_redis()
        status = "Redis OK" if client else "MEMORY-ONLY"
        return f"<RedisCache [{status}] {self.stats()}>"


# ── 快捷函数（兼容旧 API）─────────────────────────────────────────────────────
_cache: Optional[RedisCache] = None

def get_cache() -> RedisCache:
    global _cache
    if _cache is None:
        _cache = RedisCache.get_instance()
    return _cache

def cache_get(key: str) -> Optional[Any]:
    return get_cache().get(key)

def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    return get_cache().set(key, value, ttl)

def cache_delete(key: str) -> bool:
    return get_cache().delete(key)

def cache_stats() -> Dict[str, Any]:
    return get_cache().stats()


if __name__ == "__main__":
    # 快速测试
    c = RedisCache(prefix="test")
    c.set("hello", {"msg": "world"}, ttl=60)
    print("get:", c.get("hello"))
    print("stats:", c.stats())
    print(c)
