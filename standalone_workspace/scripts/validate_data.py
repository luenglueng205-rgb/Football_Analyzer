# -*- coding: utf-8 -*-
"""
P3-2: 数据质量验证 CLI
=======================
用法:
    python -m scripts.validate_data                    # 验证原始数据
    python -m scripts.validate_data --chinese          # 验证中文数据
    python -m scripts.validate_data --league "E0"      # 按联赛过滤
    python -m scripts.validate_data --strict           # 严格模式（打印所有问题）
"""
import sys
import os
import argparse

sys.path.insert(0, ".")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.data_quality_validator import DataQualityValidator
from tools.paths import datasets_dir


def main():
    parser = argparse.ArgumentParser(description="历史数据质量验证")
    parser.add_argument("--chinese", action="store_true",
                        help="验证中文 mapped 数据目录")
    parser.add_argument("--league", type=str, default=None,
                        help="按联赛代码过滤（如 E0 英超）")
    parser.add_argument("--strict", action="store_true",
                        help="严格模式：打印所有问题")
    parser.add_argument("--limit", type=int, default=0,
                        help="限制最大样本数（0=全部）")
    args = parser.parse_args()

    validator = DataQualityValidator(strict_mode=args.strict)

    # 确定数据目录
    if args.chinese:
        data_dir = os.path.join(datasets_dir(), "chinese_mapped")
    else:
        data_dir = os.path.join(datasets_dir(), "raw")

    print(f"\n📂 数据目录: {data_dir}")
    matches = validator.load_matches_from_directory(data_dir)
    print(f"📊 加载样本: {len(matches)} 条")

    if args.limit > 0:
        matches = matches[:args.limit]
        print(f"📊 限制样本: {len(matches)} 条（--limit）")

    if not matches:
        print("⚠️ 未找到任何比赛数据")
        sys.exit(0)

    # 批量验证
    result = validator.validate_batch(matches, league_filter=args.league)

    # 打印报告
    print(result.report())

    # 给出建议
    score = result.avg_health
    if score >= 85:
        print("✅ 数据质量优秀，可直接用于分析。")
    elif score >= 70:
        print("⚠️ 数据质量一般，建议配合外部数据补充。")
    else:
        print("🚨 数据质量较差，建议先清洗再使用。")


if __name__ == "__main__":
    main()
