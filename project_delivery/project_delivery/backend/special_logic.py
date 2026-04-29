"""
特殊逻辑模块 - 基于产品线数据的板块详情和分析
- 物业板块详情
- 医养板块详情
- 关键词搜索（结余率/收入/支出/管理费）
- 趋势预警分析
"""

import re
import pandas as pd
from calculators import to_wan, to_wan_f, calc_pct, aggregate_board, aggregate_product, aggregate_project


def get_property_detail(df: pd.DataFrame, year: int, months: list) -> dict:
    """物业板块各产品收支明细"""
    filtered = df[(df["年"] == year) & (df["月"].isin(months))]
    prop_data = filtered[filtered["业务板块"] == "物业板块"]
    if prop_data.empty:
        return {"products": [], "projects": [], "total": {}}

    by_product = prop_data.groupby("产品").agg(
        收入=("收入", "sum"), 支出=("支出", "sum"), 平台管理费=("平台管理费", "sum"),
    ).reset_index()
    by_product["结余"] = by_product["收入"] - by_product["支出"] - by_product["平台管理费"]

    wuye = prop_data[prop_data["产品"] == "物业管理"]
    by_project = wuye.groupby("项目").agg(
        收入=("收入", "sum"), 支出=("支出", "sum"), 平台管理费=("平台管理费", "sum"),
    ).reset_index()
    by_project["结余"] = by_project["收入"] - by_project["支出"] - by_project["平台管理费"]

    ti = prop_data["收入"].sum()
    te = prop_data["支出"].sum()
    tp = prop_data["平台管理费"].sum()
    
    # 构建规范化的数据记录
    products = []
    for _, row in by_product.iterrows():
        products.append({
            "产品": str(row.get("产品", "")) if pd.notna(row.get("产品")) else "",
            "收入": round(to_wan(row.get("收入", 0)), 2) if pd.notna(row.get("收入")) else 0,
            "支出": round(to_wan(row.get("支出", 0)), 2) if pd.notna(row.get("支出")) else 0,
            "平台管理费": round(to_wan(row.get("平台管理费", 0)), 2) if pd.notna(row.get("平台管理费")) else 0,
            "结余": round(to_wan(row.get("结余", 0)), 2) if pd.notna(row.get("结余")) else 0,
        })
    
    projects = []
    for _, row in by_project.iterrows():
        projects.append({
            "项目": str(row.get("项目", "")) if pd.notna(row.get("项目")) else "",
            "产品": str(row.get("产品", "")) if pd.notna(row.get("产品")) else "",
            "收入": round(to_wan(row.get("收入", 0)), 2) if pd.notna(row.get("收入")) else 0,
            "支出": round(to_wan(row.get("支出", 0)), 2) if pd.notna(row.get("支出")) else 0,
            "平台管理费": round(to_wan(row.get("平台管理费", 0)), 2) if pd.notna(row.get("平台管理费")) else 0,
            "结余": round(to_wan(row.get("结余", 0)), 2) if pd.notna(row.get("结余")) else 0,
        })
    
    return {
        "products": products,
        "projects": projects,
        "total": {"收入": to_wan(ti), "支出": to_wan(te), "平台管理费": to_wan(tp), "结余": to_wan(ti - te - tp)},
    }


def get_yiyang_detail(df: pd.DataFrame, year: int, months: list) -> dict:
    """医养板块各产品明细"""
    filtered = df[(df["年"] == year) & (df["月"].isin(months))]
    yy_data = filtered[filtered["业务板块"] == "医养板块"]
    if yy_data.empty:
        return {"products": [], "total": {}}

    by_product = yy_data.groupby("产品").agg(
        收入=("收入", "sum"), 支出=("支出", "sum"), 平台管理费=("平台管理费", "sum"),
    ).reset_index()
    by_product["结余"] = by_product["收入"] - by_product["支出"] - by_product["平台管理费"]

    ti = yy_data["收入"].sum()
    te = yy_data["支出"].sum()
    tp = yy_data["平台管理费"].sum()
    
    # 构建规范化的数据记录
    products = []
    for _, row in by_product.iterrows():
        products.append({
            "产品": str(row.get("产品", "")) if pd.notna(row.get("产品")) else "",
            "收入": round(to_wan(row.get("收入", 0)), 2) if pd.notna(row.get("收入")) else 0,
            "支出": round(to_wan(row.get("支出", 0)), 2) if pd.notna(row.get("支出")) else 0,
            "平台管理费": round(to_wan(row.get("平台管理费", 0)), 2) if pd.notna(row.get("平台管理费")) else 0,
            "结余": round(to_wan(row.get("结余", 0)), 2) if pd.notna(row.get("结余")) else 0,
        })
    
    return {
        "products": products,
        "total": {"收入": to_wan(ti), "支出": to_wan(te), "平台管理费": to_wan(tp), "结余": to_wan(ti - te - tp)},
    }


def search_by_keyword(df: pd.DataFrame, year: int, months: list, question: str) -> dict:
    """基于关键词的自然语言查询"""
    ql = question.lower()

    # 模式1: 结余率低于
    m = re.search(r"结余率.*(低于|不足|小于)\s*(\d+)%", ql)
    if m:
        threshold = int(m.group(2))
        filtered = df[(df["年"] == year) & (df["月"].isin(months))]
        boards = filtered.groupby("业务板块").agg(
            收入=("收入", "sum"), 支出=("支出", "sum"), 平台管理费=("平台管理费", "sum"),
        ).reset_index()
        boards["结余"] = boards["收入"] - boards["支出"] - boards["平台管理费"]
        boards["结余率"] = (boards["结余"] / boards["收入"].replace(0, float("nan"))) * 100
        low = boards[boards["结余率"] < threshold]
        
        # 构建规范化的数据记录
        data = []
        for _, row in low.iterrows():
            data.append({
                "板块": str(row.get("业务板块", "")) if pd.notna(row.get("业务板块")) else "",
                "结余率": round(row.get("结余率", 0), 2) if pd.notna(row.get("结余率")) else 0,
                "结余(万)": round(to_wan(row.get("结余", 0)), 2) if pd.notna(row.get("结余")) else 0,
            })
        
        return {
            "type": "table", "question": question,
            "columns": ["板块", "结余率", "结余(万)"],
            "data": data,
        }

    # 模式2: 收入/支出最高
    m = re.search(r"(收入|支出)(最[高低])", ql)
    if m:
        metric = m.group(1)
        direction = "最高" if "高" in m.group(2) else "最低"
        filtered = df[(df["年"] == year) & (df["月"].isin(months))]
        agg = filtered.groupby("产品").agg(收入=("收入", "sum"), 支出=("支出", "sum")).reset_index()
        col = "收入" if metric == "收入" else "支出"
        top = agg.nlargest(5, col) if direction == "最高" else agg.nsmallest(5, col)
        
        # 构建规范化的数据记录
        data = []
        for _, row in top.iterrows():
            data.append({
                "产品": str(row.get("产品", "")) if pd.notna(row.get("产品")) else "",
                f"{metric}(万)": round(to_wan(row.get(col, 0)), 2) if pd.notna(row.get(col)) else 0,
            })
        
        return {
            "type": "table", "question": question,
            "columns": ["产品", f"{metric}(万)"],
            "data": data,
        }

    # 模式3: 管理费占比
    m = re.search(r"管理费占比超过\s*(\d+)%", ql)
    if m:
        threshold = int(m.group(1))
        filtered = df[(df["年"] == year) & (df["月"].isin(months))]
        boards = filtered.groupby("业务板块").agg(收入=("收入", "sum"), 平台管理费=("平台管理费", "sum")).reset_index()
        boards["管理费占比"] = (boards["平台管理费"] / boards["收入"].replace(0, float("nan"))) * 100
        high = boards[boards["管理费占比"] > threshold]
        
        # 构建规范化的数据记录
        data = []
        for _, row in high.iterrows():
            data.append({
                "板块": str(row.get("业务板块", "")) if pd.notna(row.get("业务板块")) else "",
                "管理费占比": round(row.get("管理费占比", 0), 2) if pd.notna(row.get("管理费占比")) else 0,
            })
        
        return {
            "type": "table", "question": question,
            "columns": ["板块", "管理费占比"],
            "data": data,
        }

    # 模式4: 板块/产品关键词
    for board in df["业务板块"].dropna().unique():
        if board in question:
            filtered = df[(df["年"] == year) & (df["月"].isin(months))]
            detail = filtered[filtered["业务板块"] == board]
            by_prod = detail.groupby("产品").agg(
                收入=("收入", "sum"), 支出=("支出", "sum"), 平台管理费=("平台管理费", "sum"),
            ).reset_index()
            by_prod["结余"] = by_prod["收入"] - by_prod["支出"] - by_prod["平台管理费"]
            
            # 构建规范化的数据记录
            data = []
            for _, row in by_prod.iterrows():
                data.append({
                    "产品": str(row.get("产品", "")) if pd.notna(row.get("产品")) else "",
                    "收入(万)": round(to_wan(row.get("收入", 0)), 2) if pd.notna(row.get("收入")) else 0,
                    "支出(万)": round(to_wan(row.get("支出", 0)), 2) if pd.notna(row.get("支出")) else 0,
                    "管理费(万)": round(to_wan(row.get("平台管理费", 0)), 2) if pd.notna(row.get("平台管理费")) else 0,
                    "结余(万)": round(to_wan(row.get("结余", 0)), 2) if pd.notna(row.get("结余")) else 0,
                })
            
            return {"type": "table", "question": question, "columns": ["产品", "收入(万)", "支出(万)", "管理费(万)", "结余(万)"], "data": data}

    return {"type": "text", "question": question, "answer": "暂无法识别，请尝试：'结余率低于5%'、'收入最高'、'物业板块详情'等"}
