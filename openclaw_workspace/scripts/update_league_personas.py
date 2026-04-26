# -*- coding: utf-8 -*-
"""
P3-1: 联赛画像定时更新脚本
===========================
功能：
- 从历史数据批量重新计算所有联赛画像
- 保存到 league_persona_v2.json
- 建议通过 cron 定期执行（如每周一凌晨）

用法：
    python -m scripts.update_league_personas        # 立即运行
    python -m scripts.update_league_personas --dry  # 预览（不写入磁盘）
"""
import sys
import os
import argparse

sys.path.insert(0, ".")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.league_profiler_v2 import DynamicLeagueProfiler


def main():
    parser = argparse.ArgumentParser(description="联赛画像批量更新")
    parser.add_argument("--dry", action="store_true",
                        help="只计算不保存（预览模式）")
    parser.add_argument("--force", action="store_true",
                        help="强制重新计算（忽略磁盘缓存）")
    args = parser.parse_args()

    print("=" * 50)
    print("  联赛画像批量更新")
    print("=" * 50)

    profiler = DynamicLeagueProfiler()

    if args.force:
        print("⚡ 强制模式：跳过磁盘缓存")
        profiler._memory_cache.clear()

    if args.dry:
        print("🔍 预览模式：不写入磁盘\n")
    else:
        print("📝 写入模式：结果将保存到 league_persona_v2.json\n")

    count = profiler.recompute_all_leagues()

    print(f"\n✅ 完成，共计算 {count} 个联赛画像")

    if profiler._memory_cache:
        print("\n📊 计算结果摘要：")
        for code, persona in list(profiler._memory_cache.items())[:10]:
            p = persona.get("profile", {})
            print(f"   {code:<20} 方差={p.get('variance','?'):<15} "
                  f"场均={p.get('avg_total_goals','?')} 球  "
                  f"样本={p.get('sample_size', 0)} 场")

    if not args.dry:
        print(f"\n💾 已保存到: {profiler._cache_dir}")


if __name__ == "__main__":
    main()
