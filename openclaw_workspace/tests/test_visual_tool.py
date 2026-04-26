from tools.atomic_skills import generate_visual_chart
import json

# 模拟大模型想要生成一张雷达图对比两队实力
radar_data = [
    {"name": "预期进球", "value": 1.54, "group": "阿森纳"},
    {"name": "预期失球", "value": 0.8, "group": "阿森纳"},
    {"name": "控球率指数", "value": 60, "group": "阿森纳"},
    {"name": "近期状态", "value": 85, "group": "阿森纳"},
    
    {"name": "预期进球", "value": 1.19, "group": "利物浦"},
    {"name": "预期失球", "value": 1.1, "group": "利物浦"},
    {"name": "控球率指数", "value": 55, "group": "利物浦"},
    {"name": "近期状态", "value": 75, "group": "利物浦"}
]

res = generate_visual_chart(
    chart_type="radar_chart",
    chart_data=radar_data,
    title="阿森纳 vs 利物浦 赛前多维数据对比"
)

print(json.dumps(json.loads(res), indent=2, ensure_ascii=False))

# 模拟大模型想要生成一张比分概率柱状图
column_data = [
    {"category": "1-0", "value": 0.12},
    {"category": "2-0", "value": 0.08},
    {"category": "1-1", "value": 0.15},
    {"category": "0-1", "value": 0.10}
]

res2 = generate_visual_chart(
    chart_type="column_chart",
    chart_data=column_data,
    title="泊松模型预测高概率比分",
    axis_x_title="比分",
    axis_y_title="概率"
)

print("\n" + json.dumps(json.loads(res2), indent=2, ensure_ascii=False))
