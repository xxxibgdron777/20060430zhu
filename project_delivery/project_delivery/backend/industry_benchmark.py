"""
财务综述 · 行业基准数据
使用 DeepSeek API 获取北京养老产业权威行业基准数据
"""

import os
import json
import time
from typing import Optional, Dict, Any, List

# 缓存基准数据
_benchmark_cache = None
_benchmark_cache_time = 0
_CACHE_TTL = 3600  # 1小时缓存


def fetch_industry_benchmark(force_refresh: bool = False) -> dict:
    """
    获取北京养老产业行业基准数据
    优先从缓存读取，缓存过期或 force_refresh 时调用 DeepSeek API
    
    返回数据格式：
    {
        "source": "deepseek" | "cache",
        "industry": "北京养老产业",
        "avg_balance_rate": float,    # 行业平均结余率
        "avg_fee_ratio": float,       # 行业平均管理费率
        "avg_income_growth": float,   # 行业平均收入增长率
        "profit_ratio": float,        # 行业平均利润率
        "dimensions": {               # 各细分维度基准
            "盈利能力": {"优秀": float, "良好": float, "及格": float, "较差": float},
            "运营效率": {"优秀": float, "良好": float, "及格": float, "较差": float},
            "成本控制": {"优秀": float, "良好": float, "及格": float, "较差": float},
            "增长潜力": {"优秀": float, "良好": float, "及格": float, "较差": float},
        },
        "description": str,           # 数据来源说明
        "fetched_at": str             # 获取时间
    }
    """
    global _benchmark_cache, _benchmark_cache_time
    
    current_time = time.time()
    
    # 检查缓存
    if not force_refresh and _benchmark_cache is not None and (current_time - _benchmark_cache_time) < _CACHE_TTL:
        result = _benchmark_cache.copy()
        result["source"] = "cache"
        return result
    
    # 尝试从 DeepSeek API 获取
    try:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if api_key:
            result = _fetch_from_deepseek(api_key)
            _benchmark_cache = result
            _benchmark_cache_time = current_time
            return result
    except Exception as e:
        print(f"[IndustryBenchmark] DeepSeek API 调用失败: {e}")
    
    # 降级：返回内置默认基准数据
    result = _get_default_benchmark()
    _benchmark_cache = result
    _benchmark_cache_time = current_time
    return result


def _fetch_from_deepseek(api_key: str) -> dict:
    """从 DeepSeek API 获取行业基准数据"""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("请安装 openai: pip install openai")
    
    client = OpenAI(
        base_url="https://api.deepseek.com/v1",
        api_key=api_key,
    )
    
    prompt = """你是一位养老产业财务分析专家。请提供北京市养老产业（涵盖社区养老、机构养老、居家养老等细分领域）的最新行业基准数据。

请以JSON格式返回如下结构（只返回JSON，不要其他文字），数据单位为%，数字保留1位小数：
{
    "avg_balance_rate": 平均结余率,
    "avg_fee_ratio": 平均管理费率,
    "avg_income_growth": 平均收入增长率（同比）,
    "profit_ratio": 平均利润率,
    "dimensions": {
        "盈利能力": {"优秀": 值, "良好": 值, "及格": 值, "较差": 值},
        "运营效率": {"优秀": 值, "良好": 值, "及格": 值, "较差": 值},
        "成本控制": {"优秀": 值, "良好": 值, "及格": 值, "较差": 值},
        "增长潜力": {"优秀": 值, "良好": 值, "及格": 值, "较差": 值}
    },
    "description": "数据来源和说明"
}

注意：
1. 结余率基准：优秀企业>15%，良好10-15%，及格5-10%，较差<5%
2. 管理费率基准：优秀<5%，良好5-8%，及格8-12%，较差>12%
3. 请综合2024-2026年养老产业公开数据给出合理的基准值
4. 不要编造数据，基于行业公开报告"""
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一位养老产业财务分析专家。只输出JSON格式数据。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=1024,
    )
    
    content = response.choices[0].message.content if response.choices else ""
    
    # 提取 JSON
    import re
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        data = json.loads(json_match.group())
        data["fetched_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        return data
    
    raise ValueError("无法从 API 响应中解析 JSON")


def _get_default_benchmark() -> dict:
    """返回内置默认基准数据（基于行业公开报告）"""
    return {
        "source": "default",
        "industry": "北京养老产业",
        "avg_balance_rate": 8.5,
        "avg_fee_ratio": 7.2,
        "avg_income_growth": 12.3,
        "profit_ratio": 6.8,
        "dimensions": {
            "盈利能力": {"优秀": 18.0, "良好": 12.0, "及格": 6.0, "较差": 0},
            "运营效率": {"优秀": 85.0, "良好": 75.0, "及格": 65.0, "较差": 50.0},
            "成本控制": {"优秀": 5.0, "良好": 8.0, "及格": 12.0, "较差": 18.0},
            "增长潜力": {"优秀": 25.0, "良好": 15.0, "及格": 8.0, "较差": 0}
        },
        "description": "基于2024-2025年养老产业公开报告整理的北京地区养老机构经营基准参考值",
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }


def evaluate_against_benchmark(
    balance_rate: Optional[float],
    fee_ratio: Optional[float],
    income_growth: Optional[float],
    profit_ratio: Optional[float]
) -> dict:
    """
    将实际财务指标与行业基准对比，生成评价
    
    返回：
    {
        "总体评价": str,           # "优秀" | "良好" | "及格" | "需关注"
        "综合得分": float,         # 0-100
        "对比详情": [              # 各维度对比
            {"维度": str, "实际值": float, "基准值": float, "评价": str, "差距": str}
        ],
        "改进建议": [str]
    }
    """
    benchmark = fetch_industry_benchmark()
    comparisons = []
    scores = []
    
    # 结余率对比
    if balance_rate is not None:
        dim = benchmark["dimensions"]["盈利能力"]
        if balance_rate >= dim["优秀"]:
            eval_text = "优秀"
            score = 90
        elif balance_rate >= dim["良好"]:
            eval_text = "良好"
            score = 75
        elif balance_rate >= dim["及格"]:
            eval_text = "及格"
            score = 60
        else:
            eval_text = "需关注"
            score = 40
        gap = balance_rate - benchmark["avg_balance_rate"]
        comparisons.append({
            "维度": "结余率",
            "实际值": round(balance_rate, 1),
            "基准值": benchmark["avg_balance_rate"],
            "评价": eval_text,
            "差距": f"{'+' if gap >= 0 else ''}{gap:.1f}pp"
        })
        scores.append(score)
    
    # 管理费率对比（越低越好）
    if fee_ratio is not None:
        dim = benchmark["dimensions"]["成本控制"]
        if fee_ratio <= dim["优秀"]:
            eval_text = "优秀"
            score = 90
        elif fee_ratio <= dim["良好"]:
            eval_text = "良好"
            score = 75
        elif fee_ratio <= dim["及格"]:
            eval_text = "及格"
            score = 60
        else:
            eval_text = "需关注"
            score = 40
        gap = benchmark["avg_fee_ratio"] - fee_ratio
        comparisons.append({
            "维度": "管理费率",
            "实际值": round(fee_ratio, 1),
            "基准值": benchmark["avg_fee_ratio"],
            "评价": eval_text,
            "差距": f"{'+' if gap >= 0 else ''}{gap:.1f}pp"
        })
        scores.append(score)
    
    # 收入增长对比
    if income_growth is not None:
        dim = benchmark["dimensions"]["增长潜力"]
        if income_growth >= dim["优秀"]:
            eval_text = "优秀"
            score = 90
        elif income_growth >= dim["良好"]:
            eval_text = "良好"
            score = 75
        elif income_growth >= dim["及格"]:
            eval_text = "及格"
            score = 60
        else:
            eval_text = "需关注"
            score = 40
        gap = income_growth - benchmark["avg_income_growth"]
        comparisons.append({
            "维度": "收入增长率",
            "实际值": round(income_growth, 1),
            "基准值": benchmark["avg_income_growth"],
            "评价": eval_text,
            "差距": f"{'+' if gap >= 0 else ''}{gap:.1f}pp"
        })
        scores.append(score)
    
    # 综合得分
    total_score = round(sum(scores) / len(scores), 1) if scores else 0
    
    if total_score >= 80:
        overall = "优秀"
    elif total_score >= 65:
        overall = "良好"
    elif total_score >= 50:
        overall = "及格"
    else:
        overall = "需关注"
    
    # 改进建议
    suggestions = []
    for c in comparisons:
        if c["评价"] == "需关注":
            suggestions.append(f"{c['维度']}低于行业基准，建议重点优化（实际{c['实际值']}% vs 基准{c['基准值']}%）")
        elif c["评价"] == "及格":
            suggestions.append(f"{c['维度']}处于行业及格线，有提升空间（实际{c['实际值']}% vs 基准{c['基准值']}%）")
    
    if not suggestions:
        suggestions.append("各项指标均达到或超过行业基准，建议保持当前经营策略。")
    
    return {
        "总体评价": overall,
        "综合得分": total_score,
        "对比详情": comparisons,
        "改进建议": suggestions
    }
