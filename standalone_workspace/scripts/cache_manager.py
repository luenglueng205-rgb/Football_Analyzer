# -*- coding: utf-8 -*-
"""
P3-3: 缓存管理 CLI
===================
用法:
    python -m scripts.cache_manager stats    # 查看命中率统计
    python -m scripts.cache_manager warm      # 从 Redis 预热内存兜底
    python -m scripts.cache_manager clear     # 清空当前前缀所有缓存
    python -m scripts.cache_manager get <key> # 读取指定 key
    python -m scripts.cache_manager set <key> <json> # 写入（测试用）
"""
import sys
import json
import argparse

sys.path.insert(0, ".")

from core.redis_cache import RedisCache, get_cache


def main():
    parser = argparse.ArgumentParser(description="Redis 缓存管理工具")
    parser.add_argument("action", choices=["stats", "warm", "clear", "get", "set"],
                        help="操作类型")
    parser.add_argument("key", nargs="?", help="缓存 key（get/set 时使用）")
    parser.add_argument("value", nargs="?", help="缓存值 JSON（set 时使用）")
    args = parser.parse_args()

    cache: RedisCache = get_cache()

    if args.action == "stats":
        s = cache.stats()
        print("=" * 40)
        print("  Redis 缓存统计")
        print("=" * 40)
        print(f"  命中次数   : {s['hit']}")
        print(f"  未命中次数 : {s['miss']}")
        print(f"  命中率     : {s['hit_rate']:.2%}")
        print(f"  内存回退   : {s['mem_fallback']}")
        print(f"  Redis 异常 : {s['redis_err']}")
        print(f"  内存大小   : {s['mem_size']} 条")
        print("=" * 40)

    elif args.action == "warm":
        n = cache.warm_memory()
        print(f"预热完成，共 {n} 条写入内存兜底")

    elif args.action == "clear":
        n = cache.clear_prefix()
        print(f"清空完成，共删除 {n} 条")

    elif args.action == "get":
        if not args.key:
            print("错误: get 需要指定 key")
            sys.exit(1)
        val = cache.get(args.key)
        if val is None:
            print("(nil)")
        else:
            print(json.dumps(val, ensure_ascii=False, indent=2))

    elif args.action == "set":
        if not args.key:
            print("错误: set 需要指定 key 和 value")
            sys.exit(1)
        try:
            value = json.loads(args.value) if args.value else None
        except json.JSONDecodeError:
            value = args.value
        cache.set(args.key, value)
        print(f"已写入: {args.key}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
