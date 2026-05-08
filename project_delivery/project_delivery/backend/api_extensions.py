"""
财务综述 Agent · API 扩展模块
包含增强的 API 端点和工具函数
"""

import re
import pandas as pd
import numpy as np
from typing import List, Optional
from calculators import (
    to_wan, to_wan_f, calc_pct, format_pct,
    aggregate_board, aggregate_product, aggregate_project,
    aggregate_team_nature, aggregate_team_parent, aggregate_team_account,
    get_support_team_balance, get_kpi, get_monthly_trend, get_pie_data,
    analyze_trends, _team_calc,
)
from agent import FinancialAgent, VolcEngineAgent


def ensure_native(obj):
    """递归转换 numpy/pandas 类型为 Python 原生类型"""
    if isinstance(obj, dict):
        return {k: ensure_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [ensure_native(x) for x in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if pd.isna(obj) if isinstance(obj, (float,)) else False:
        return None
    return obj


def filter_product(product_df, year, months):
    return product_df[
        (product_df["年"] == year) & (product_df["月"].isin(months))
    ].copy()


def filter_team(team_df, year, months):
    return team_df[
        (team_df["年"] == year) & (team_df["月"].isin(months))
    ].copy()


# ==================== 增强版智能问答 API ====================

def enhanced_query(product_df, team_df, question: str, year: int, months: List[int]) -> dict:
    """
    增强版智能问答接口（规则匹配优先 + DeepSeek AI 补充）
    - 优先使用 FinancialAgent（规则匹配）
    - 规则未命中时，使用 DeepSeek V3.2 进行数据分析和回答
    """
    # 关键词别名映射（将非标准名称映射为数据中实际名称）
    alias_map = {
        "机构医疗": "医养板块",
        "银发经济": "",
    }
    for alias, target in alias_map.items():
        if alias in question and target:
            question = question.replace(alias, target)
    
    # 1. 规则匹配优先
    rule_agent = FinancialAgent(product_df, team_df)
    rule_agent.set_context(year, months)
    rule_result = rule_agent.query(question)
    
    # 默认回复含 suggestions 字段，表示未命中规则
    is_default = "suggestions" in rule_result
    if is_default:
        # 规则未命中，使用 DeepSeek AI 补充
        try:
            ai_agent = VolcEngineAgent(product_df, team_df)
            ai_agent.set_context(year, months)
            ai_result = ai_agent.query(question)
            if ai_result and ai_result.get("answer") and "抱歉" not in ai_result.get("answer", ""):
                ai_result["source"] = "rule+ai"
                return ensure_native(ai_result)
        except Exception:
            import traceback
            traceback.print_exc()
    
    rule_result["source"] = "rule"
    return ensure_native(rule_result)


def get_ai_suggestions(product_df, team_df, year: int, months: List[int]) -> List[dict]:
    """
    获取 AI 分析建议
    基于当前数据状态，生成潜在的分析关注点
    """
    df_f = filter_product(product_df, year, months)
    
    suggestions = []
    
    # 1. 检测低结余率板块
    boards = aggregate_board(df_f)
    if boards.empty:
        return suggestions
    boards["结余率"] = (boards["结余"] / boards["收入"].replace(0, float("nan"))) * 100
    boards["管理费占比"] = (boards["平台管理费"] / boards["收入"].replace(0, float("nan"))) * 100
    low_rate = boards[boards["结余率"] < 10]
    if not low_rate.empty:
        # 构建规范化的数据记录
        data1 = []
        for _, row in low_rate.iterrows():
            data1.append({
                "业务板块": str(row.get("业务板块", "")) if pd.notna(row.get("业务板块")) else "",
                "结余率": round(row.get("结余率", 0), 2) if pd.notna(row.get("结余率")) else 0,
            })
        suggestions.append({
            "type": "warning",
            "title": "低结余率预警",
            "message": f"{len(low_rate)} 个板块结余率低于10%，建议关注成本管控",
            "action": f"哪些板块结余率低于10%？",
            "data": data1
        })
    
    # 2. 检测亏损板块
    loss_boards = boards[boards["结余"] < 0]
    if not loss_boards.empty:
        data2 = []
        for _, row in loss_boards.iterrows():
            data2.append({
                "业务板块": str(row.get("业务板块", "")) if pd.notna(row.get("业务板块")) else "",
                "结余": round(to_wan(row.get("结余", 0)), 2) if pd.notna(row.get("结余")) else 0,
            })
        suggestions.append({
            "type": "danger",
            "title": "亏损板块",
            "message": f"{len(loss_boards)} 个板块当前处于亏损状态",
            "action": "查看亏损板块详情",
            "data": data2
        })
    
    # 3. 同比下滑检测
    alerts = analyze_trends(product_df, year)
    if alerts:
        suggestions.append({
            "type": "alert",
            "title": "同比异常波动",
            "message": f"发现 {len(alerts)} 项同比下滑超30%的情况",
            "action": "查看详细预警",
            "data": [{"预警": a} for a in alerts[:5]]
        })
    
    # 4. 高管理费占比
    high_fee = boards[boards["管理费占比"] > 10]
    if not high_fee.empty:
        data4 = []
        for _, row in high_fee.iterrows():
            data4.append({
                "业务板块": str(row.get("业务板块", "")) if pd.notna(row.get("业务板块")) else "",
                "管理费占比": round(row.get("管理费占比", 0), 2) if pd.notna(row.get("管理费占比")) else 0,
            })
        suggestions.append({
            "type": "info",
            "title": "管理费占比偏高",
            "message": f"{len(high_fee)} 个板块管理费占比超过10%",
            "action": "管理费占比超过10%的板块？",
            "data": data4
        })
    
    return ensure_native(suggestions)


# ==================== 经营分享 API ====================

def _get_amt_col(df: pd.DataFrame) -> str:
    """获取团队数据的金额列名，优先用'总计'（创业团队），否则用'金额g'"""
    return "总计" if "总计" in df.columns else ("金额g" if "金额g" in df.columns else "金额g")


def get_team_share_detail(team_df, parent_name: str, year: int) -> Optional[dict]:
    """
    创业团队经营分享详情
    按收支+部门特殊科目，生成12月+合计列
    """
    filtered = team_df[(team_df["年"] == year) & (team_df["H团队线-上级"] == parent_name)]
    if filtered.empty:
        return None
    
    total_income, total_expense, _ = _team_calc(filtered)
    amt_col = _get_amt_col(filtered)
    
    rows = []
    
    for sz_type in ["一、收入", "二、支出"]:
        sz_data = filtered[filtered["收支"] == sz_type]
        if sz_data.empty:
            continue
        
        mgmt = sz_data[sz_data["资金流向"] == "管理费"]
        non_mgmt = sz_data[sz_data["资金流向"] != "管理费"]
        
        # 大类合计行
        row = {"科目": sz_type, "level": "major"}
        row_total = 0
        row_total_3_12 = 0
        for m in range(1, 13):
            md = non_mgmt[non_mgmt["月"] == m]
            val = float(md[amt_col].sum())
            row[f"{m}月"] = to_wan(val)
            row_total += val
            if m >= 3:
                row_total_3_12 += val
        row["1-12月"] = to_wan(row_total)
        row["3-12月"] = to_wan(row_total_3_12)
        if sz_type == "一、收入":
            row["收入占比"] = round(row_total / total_income * 100, 1) if total_income else None
            row["支出占比"] = None
        else:
            row["支出占比"] = round(abs(row_total) / total_expense * 100, 1) if total_expense else None
            row["收入占比"] = None
        rows.append(row)
        
        # 部门特殊明细
        if "部门特殊" in filtered.columns:
            specials = non_mgmt["部门特殊"].dropna().unique()
            for sp in sorted(specials):
                sp_data = non_mgmt[non_mgmt["部门特殊"] == sp]
                row = {"科目": sp, "level": "detail"}
                row_total = 0
                row_total_3_12 = 0
                for m in range(1, 13):
                    md = sp_data[sp_data["月"] == m]
                    val = float(md[amt_col].sum())
                    row[f"{m}月"] = to_wan(val)
                    row_total += val
                    if m >= 3:
                        row_total_3_12 += val
                row["1-12月"] = to_wan(row_total)
                row["3-12月"] = to_wan(row_total_3_12)
                if sz_type == "一、收入":
                    row["收入占比"] = round(row_total / total_income * 100, 1) if total_income else None
                    row["支出占比"] = None
                else:
                    row["支出占比"] = round(abs(row_total) / total_expense * 100, 1) if total_expense else None
                    row["收入占比"] = None
                rows.append(row)
        
        # 管理费行
        if not mgmt.empty:
            row = {"科目": "平台管理费", "level": "mgmt"}
            row_total = 0
            row_total_3_12 = 0
            for m in range(1, 13):
                md = mgmt[mgmt["月"] == m]
                val = float(md[amt_col].sum())
                row[f"{m}月"] = to_wan(val)
                row_total += val
                if m >= 3:
                    row_total_3_12 += val
            row["1-12月"] = to_wan(row_total)
            row["3-12月"] = to_wan(row_total_3_12)
            row["收入占比"] = None
            row["支出占比"] = None
            rows.append(row)
    
    # 结余行
    row = {"科目": "结余", "level": "balance"}
    row_total = 0
    row_total_3_12 = 0
    for m in range(1, 13):
        md = filtered[filtered["月"] == m]
        inc_m, exp_m, fee_m = _team_calc(md)
        bal_m = inc_m - exp_m - fee_m
        row[f"{m}月"] = to_wan(bal_m)
        row_total += bal_m
        if m >= 3:
            row_total_3_12 += bal_m
    row["1-12月"] = to_wan(row_total)
    row["3-12月"] = to_wan(row_total_3_12)
    row["收入占比"] = None
    row["支出占比"] = None
    rows.append(row)
    
    # 生成分析建议
    suggestions = []
    if row_total < 0:
        suggestions.append(f"该团队年度结余为负（{to_wan(row_total)}万），需关注成本管控。")
    if total_expense > 0 and total_income > 0:
        ratio = total_expense / total_income
        if ratio > 0.95:
            suggestions.append(f"支出/收入比达{ratio:.0%}，利润空间极小，建议审查成本结构。")
    
    # 月度结余连续为负检测
    neg_count = 0
    for m in range(1, 13):
        md = filtered[filtered["月"] == m]
        if not md.empty:
            inc_m, exp_m, fee_m = _team_calc(md)
            if inc_m - exp_m - fee_m < 0:
                neg_count += 1
            else:
                neg_count = 0
        if neg_count >= 3:
            suggestions.append(f"结余连续{neg_count}个月为负，需预警关注。")
            break
    
    return ensure_native({
        "parent": parent_name,
        "total_income": to_wan(total_income),
        "total_expense": to_wan(total_expense),
        "rows": rows,
        "suggestions": suggestions,
    })


# ==================== 数据导出 API ====================

def export_board_summary(product_df, year: int, months: List[int]) -> List[dict]:
    """导出板块汇总数据"""
    df_f = filter_product(product_df, year, months)
    boards = aggregate_board(df_f)
    boards["结余率"] = (boards["结余"] / boards["收入"].replace(0, float("nan"))) * 100
    
    records = []
    for _, row in boards.iterrows():
        r = {
            "业务板块": str(row.get("业务板块", "")) if pd.notna(row.get("业务板块")) else "",
            "收入": round(to_wan(row.get("收入", 0)), 2) if pd.notna(row.get("收入")) else 0,
            "支出": round(to_wan(row.get("支出", 0)), 2) if pd.notna(row.get("支出")) else 0,
            "平台管理费": round(to_wan(row.get("平台管理费", 0)), 2) if pd.notna(row.get("平台管理费")) else 0,
            "结余": round(to_wan(row.get("结余", 0)), 2) if pd.notna(row.get("结余")) else 0,
            "结余率": f"{row.get('结余率', 0):.1f}%" if pd.notna(row.get("结余率")) else "0.0%",
        }
        records.append(r)
    
    return ensure_native(records)


def export_product_summary(product_df, year: int, months: List[int], board: str = None) -> List[dict]:
    """导出产品汇总数据"""
    df_f = filter_product(product_df, year, months)
    prods = aggregate_product(df_f, board)
    
    records = []
    for _, row in prods.iterrows():
        r = {
            "业务板块": str(row.get("业务板块", "")) if pd.notna(row.get("业务板块")) else "",
            "产品": str(row.get("产品", "")) if pd.notna(row.get("产品")) else "",
            "收入": round(to_wan(row.get("收入", 0)), 2) if pd.notna(row.get("收入")) else 0,
            "支出": round(to_wan(row.get("支出", 0)), 2) if pd.notna(row.get("支出")) else 0,
            "平台管理费": round(to_wan(row.get("平台管理费", 0)), 2) if pd.notna(row.get("平台管理费")) else 0,
            "结余": round(to_wan(row.get("结余", 0)), 2) if pd.notna(row.get("结余")) else 0,
        }
        records.append(r)
    
    return ensure_native(records)
