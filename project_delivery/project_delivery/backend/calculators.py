"""
财务综述 Agent · 核心计算模块 v2.0
遵循 财务综述 Agent 取数原则 v1.0
- 金额：万元，整数，千分位
- 百分比：整数带符号
- 同比/环比：分母取绝对值，除零保护
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple


# ==================== 格式化工具 ====================

def to_wan(yuan_value):
    """
    元 → 万元，四舍五入取整
    用于所有金额显示
    """
    if pd.isna(yuan_value):
        return 0
    return int(round(float(yuan_value) / 10000))


def abs_to_wan(yuan_value):
    """
    元 → 万元，绝对值，四舍五入取整
    用于环形图等需要绝对值的场景
    """
    if pd.isna(yuan_value):
        return 0
    return int(round(abs(float(yuan_value)) / 10000))


def to_wan_f(yuan_value):
    """
    元 → 万元，取整
    用于精确计算场景
    """
    if pd.isna(yuan_value):
        return 0
    return round(float(yuan_value) / 10000)


def format_pct(pct: Optional[float]) -> str:
    """
    格式化百分比：整数带符号（正数带+号，负数带-号）
    返回：'+5%', '-12%', 或 '-' (当 pct 为 None 时)
    """
    if pct is None:
        return '-'
    sign = '+' if pct >= 0 else ''
    return f'{sign}{int(round(pct))}%'


def format_pct_raw(pct: Optional[float]) -> Optional[str]:
    """
    格式化百分比（原始值，可能带小数）
    返回：'+5.2%', '-12.0%', 或 None (当 pct 为 None 时)
    """
    if pct is None:
        return None
    sign = '+' if pct >= 0 else ''
    return f'{sign}{round(pct, 1)}%'


def format_wan_with_sign(value: int) -> str:
    """
    格式化金额（万元），带正负符号
    返回：'+8,045', '-3,200', '0'
    """
    if value > 0:
        return f'+{value:,}'
    elif value < 0:
        return f'{value:,}'
    return '0'


def pct_cls(pct: Optional[float]) -> str:
    """
    返回百分比对应的颜色类名
    正数：绿色 'up', 负数：红色 'down', 无效值：空字符串
    """
    if pct is None:
        return ''
    return 'up' if pct >= 0 else 'down'


def num_cls(value: Optional[float]) -> str:
    """
    返回数值对应的颜色类名
    正数/零：绿色 'positive', 负数：红色 'negative'
    """
    if value is None:
        return ''
    return 'positive' if value >= 0 else 'negative'


# ==================== 核心计算 ====================

def calc_pct(current, previous) -> Optional[float]:
    """
    同比/环比百分比
    公式: (当期 - 去年同期) / |去年同期| × 100
    除零保护:
      - 分母=0 且 分子=0 → 返回 0
      - 分母=0 且 分子≠0 → 返回 None
    """
    if pd.isna(previous) or previous == 0:
        if pd.isna(current) or current == 0:
            return 0
        return None
    if pd.isna(current):
        return None
    return (float(current) - float(previous)) / abs(float(previous)) * 100


def calc_yoy(current: float, previous: float) -> dict:
    """
    计算同比变化
    返回: { pct, abs_change }
    """
    pct = calc_pct(current, previous)
    abs_change = current - previous
    return {
        'pct': pct,
        'pct_formatted': format_pct(pct),
        'abs_change': abs_change,
        'abs_change_wan': to_wan(abs_change),
        'abs_change_formatted': f'{previous / 10000:.0f}万',  # 去年同期值
    }


def calc_mom(current: float, previous: float) -> dict:
    """
    计算环比变化（仅用于单月模式）
    返回: { pct, abs_change }
    """
    pct = calc_pct(current, previous)
    abs_change = current - previous
    return {
        'pct': pct,
        'pct_formatted': format_pct(pct),
        'abs_change': abs_change,
        'abs_change_wan': to_wan(abs_change),
        'abs_change_formatted': f'{previous / 10000:.0f}万',  # 上期值
    }


def calc_cumulative_growth(curr_cumulative: float, prev_cumulative: float, 
                           latest_month_value: float) -> dict:
    """
    计算累计模式增长
    - 较上期累计增长%
    - 最新月份贡献值
    
    返回格式符合用户要求的卡片布局
    """
    # 上期累计区间 = 当期累计去掉最后一个月份
    # 简化处理：上期累计 = 当期累计 - 最新月份值
    prev_range_value = curr_cumulative - latest_month_value
    
    pct = calc_pct(curr_cumulative, prev_range_value)
    growth = curr_cumulative - prev_range_value
    growth_wan = to_wan(growth)
    latest_wan = to_wan(latest_month_value)
    
    return {
        'pct': pct,
        'pct_formatted': format_pct(pct),
        'growth_sign': '+' if growth_wan >= 0 else '',
        'growth_formatted': f'{growth_wan:+}万',  # 如 +382万
        'latest_month_sign': '+' if latest_wan >= 0 else '',
        'latest_month_formatted': f'{latest_wan:+}万',  # 如 +382万
        'latest_month_wan': latest_wan,
        'pct_cls': pct_cls(pct),
    }


# ==================== 产品线聚合 ====================

def aggregate_board(df_filtered: pd.DataFrame) -> pd.DataFrame:
    """按业务板块聚合"""
    if df_filtered.empty:
        return pd.DataFrame()
    
    g = df_filtered.groupby("业务板块").agg(
        收入=("收入", "sum"),
        支出=("支出", "sum"),
        平台管理费=("平台管理费", "sum"),
    ).reset_index()
    g["结余"] = g["收入"] - g["支出"]  # 结余不含管理费
    return g


def aggregate_product(df_filtered: pd.DataFrame, board: Optional[str] = None) -> pd.DataFrame:
    """按产品聚合"""
    if df_filtered.empty:
        return pd.DataFrame()
    if board:
        df_filtered = df_filtered[df_filtered["业务板块"] == board]
    g = df_filtered.groupby(["业务板块", "产品"]).agg(
        收入=("收入", "sum"),
        支出=("支出", "sum"),
        平台管理费=("平台管理费", "sum"),
    ).reset_index()
    g["结余"] = g["收入"] - g["支出"]  # 结余不含管理费
    return g


def aggregate_project(df_filtered: pd.DataFrame, product: Optional[str] = None) -> pd.DataFrame:
    """按项目聚合"""
    if df_filtered.empty:
        return pd.DataFrame()
    if product:
        df_filtered = df_filtered[df_filtered["产品"] == product]
    g = df_filtered.groupby(["业务板块", "产品", "项目"]).agg(
        收入=("收入", "sum"),
        支出=("支出", "sum"),
        平台管理费=("平台管理费", "sum"),
    ).reset_index()
    g["结余"] = g["收入"] - g["支出"]  # 结余不含管理费
    return g


# ==================== 创业团队聚合 ====================


def _team_amt_col(df: pd.DataFrame) -> str:
    """获取团队数据的金额列名，优先用'总计'（创业团队），否则用'金额g'（产品线）"""
    col = getattr(df, "_team_amt_col", None) or ("总计" if "总计" in df.columns else "金额g")
    return col


def _team_calc(sub_df: pd.DataFrame, inc_col: str = "收支", exp_col: str = "收支") -> Tuple[float, float, float]:
    """
    从数据计算 收入/支出/平台管理费
    inc_col/exp_col: 分类列（产品用"收支"，创业团队用"收支1"）
    金额列：自动检测"总计"或"金额g"
    """
    if sub_df.empty:
        return 0.0, 0.0, 0.0

    amt_col = _team_amt_col(sub_df)
    
    # 创业团队用"收支1"列，值为"1.x"开头（收入）或"2.x"开头（支出）
    # 产品线用字符串匹配"一、收入"/"二、支出"
    if inc_col == "收支1":
        # 创业团队：1.x 开头是收入（排除管理费），2.x 开头是支出
        income_cond = (sub_df[inc_col].str.startswith('1.', na=False)) & (sub_df["资金流向"] != "管理费")
        expense_cond = (sub_df[exp_col].str.startswith('2.', na=False)) & (sub_df["资金流向"] != "管理费")
        fee_cond = (sub_df["资金流向"] == "管理费") & (sub_df[inc_col].str.startswith('2.', na=False))
    elif "一、收入" in sub_df.columns:
        # 二进制列判断
        income_cond = (sub_df["一、收入"].fillna(0) != 0) & (sub_df["资金流向"] != "管理费")
        expense_cond = (sub_df["二、支出"].fillna(0) != 0) & (sub_df["资金流向"] != "管理费")
        fee_cond = sub_df["资金流向"] == "管理费"
    else:
        # 产品线字符串匹配
        income_cond = (sub_df[inc_col] == "一、收入") & (sub_df["资金流向"] != "管理费")
        expense_cond = (sub_df[exp_col] == "二、支出") & (sub_df["资金流向"] != "管理费")
        fee_cond = sub_df["资金流向"] == "管理费"

    income = float(sub_df.loc[income_cond, amt_col].sum())
    expense = float(-sub_df.loc[expense_cond, amt_col].sum())  # 负→正
    fee = float(-sub_df.loc[fee_cond, amt_col].sum())  # 红字支出取负→正

    return income, expense, fee


def aggregate_team_nature(df_filtered: pd.DataFrame) -> pd.DataFrame:
    """按 H团队线性质 聚合"""
    if df_filtered.empty:
        return pd.DataFrame()
    
    groups = df_filtered.groupby("H团队线性质")
    records = []
    for name, group in groups:
        inc, exp, fee = _team_calc(group, inc_col="收支1", exp_col="收支1")
        records.append({
            "H团队线性质": str(name),
            "H团队线-上级": "",  # 一级不需要这个字段，由前端展开时填充
            "收入": inc, "支出": exp, "平台管理费": fee,
            "结余": inc - exp - fee,
        })
    return pd.DataFrame(records)


def aggregate_team_parent(df_filtered: pd.DataFrame, nature: Optional[str] = None) -> pd.DataFrame:
    """按 H团队线性质 + H团队线-上级 聚合"""
    if df_filtered.empty:
        return pd.DataFrame()
    if nature:
        df_filtered = df_filtered[df_filtered["H团队线性质"] == nature]
    
    groups = df_filtered.groupby(["H团队线性质", "H团队线-上级"])
    records = []
    for (nat, parent), group in groups:
        inc, exp, fee = _team_calc(group, inc_col="收支1", exp_col="收支1")
        records.append({
            "H团队线性质": str(nat),
            "H团队线-上级": str(parent),
            "收入": inc, "支出": exp, "平台管理费": fee,
            "结余": inc - exp - fee,
        })
    return pd.DataFrame(records)


def aggregate_team_account(df_filtered: pd.DataFrame, parent: Optional[str] = None) -> pd.DataFrame:
    """按 H团队线性质 + H团队线-上级 + H团队线-核算 聚合"""
    if df_filtered.empty:
        return pd.DataFrame()
    if parent:
        df_filtered = df_filtered[df_filtered["H团队线-上级"] == parent]
    
    groups = df_filtered.groupby(["H团队线性质", "H团队线-上级", "H团队线-核算"])
    records = []
    for (nat, par, acc), group in groups:
        inc, exp, fee = _team_calc(group, inc_col="收支1", exp_col="收支1")
        records.append({
            "H团队线性质": str(nat),
            "H团队线-上级": str(par),
            "H团队线-核算": str(acc),
            "收入": inc, "支出": exp, "平台管理费": fee,
            "结余": inc - exp - fee,
        })
    return pd.DataFrame(records)


# ==================== 支持团队计算 ====================

def get_support_team_balance(product_df: pd.DataFrame, team_df: pd.DataFrame, 
                             year: int, months: list) -> dict:
    """
    支持团队结余（特殊公式）
    注意：如果不需要特殊处理，可以忽略此函数。
    """
    # 从团队表获取支持团队自身支出
    team_filtered = team_df[(team_df["年"] == year) & (team_df["月"].isin(months))]
    support_expense = 0.0
    if not team_filtered.empty and "A产品线" in team_filtered.columns:
        amt_col = _team_amt_col(team_df)
        cond = (team_filtered["二、支出"].fillna(0) != 0) & (team_filtered["A产品线"] == "支持团队")
        support_expense = float(-team_filtered.loc[cond, amt_col].sum())
    
    # 从产品表获取其他板块的管理费合计（作为支持团队的红字收入）
    prod_filtered = product_df[(product_df["年"] == year) & (product_df["月"].isin(months))]
    other_mgmt = prod_filtered[prod_filtered["业务板块"] != "支持团队"]["平台管理费"].sum()
    support_income = 0.0
    support_fee = -float(other_mgmt)
    
    balance = support_income - support_expense - support_fee
    
    return {
        "收入": support_income,
        "支出": support_expense,
        "平台管理费": support_fee,
        "结余": balance,
        "其他板块管理费合计": float(other_mgmt),
    }


# ==================== KPI 计算（产品线） ====================

def get_kpi(product_df: pd.DataFrame, year: int, months: list) -> dict:
    """
    产品线 KPI（高层关注）
    只使用产品 sheet 中的“收入”和“支出”两列，不涉及管理费。
    """
    is_single = len(months) == 1
    max_month = max(months)
    
    curr = product_df[(product_df["年"] == year) & (product_df["月"].isin(months))]
    curr_income = curr["收入"].sum()
    curr_expense = curr["支出"].sum()
    curr_balance = curr_income - curr_expense
    curr_rate = (curr_balance / curr_income * 100) if curr_income else None
    
    yoy = product_df[(product_df["年"] == year - 1) & (product_df["月"].isin(months))]
    yoy_income = yoy["收入"].sum()
    yoy_expense = yoy["支出"].sum()
    yoy_balance = yoy_income - yoy_expense
    yoy_rate = (yoy_balance / yoy_income * 100) if yoy_income else None
    
    if is_single:
        m = months[0]
        if m == 1:
            prev = product_df[(product_df["年"] == year - 1) & (product_df["月"] == 12)]
            mom_label = f"{year-1}年12月"
        else:
            prev = product_df[(product_df["年"] == year) & (product_df["月"] == m - 1)]
            mom_label = f"{m-1}月"
    else:
        if max_month <= 1:
            prev = product_df[(product_df["年"] == year - 1) & (product_df["月"] == 1)]
            mom_label = "去年同期"
        else:
            prev_months_list = list(range(1, max_month))
            prev = product_df[(product_df["年"] == year) & (product_df["月"].isin(prev_months_list))]
            mom_label = f"1-{max_month-1}月"
    
    prev_income = prev["收入"].sum()
    prev_expense = prev["支出"].sum()
    prev_balance = prev_income - prev_expense
    prev_rate = (prev_balance / prev_income * 100) if prev_income else None
    
    latest_month = None
    if not is_single and max_month >= 1:
        latest = product_df[(product_df["年"] == year) & (product_df["月"] == max_month)]
        latest_income = latest["收入"].sum()
        latest_expense = latest["支出"].sum()
        latest_balance = latest_income - latest_expense
        latest_month = {
            'income': latest_income,
            'expense': latest_expense,
            'balance': latest_balance,
        }
    
    result = {
        "income": to_wan(curr_income),
        "expense": to_wan(curr_expense),
        "balance": to_wan(curr_balance),
        "balance_rate": round(curr_rate, 1) if curr_rate is not None else None,
        "yoy": {
            "income_pct": calc_pct(curr_income, yoy_income),
            "income_pct_formatted": format_pct(calc_pct(curr_income, yoy_income)),
            "income_prev": to_wan(yoy_income),
            "income_prev_formatted": f"{yoy_income / 10000:.0f}万",
            "expense_pct": calc_pct(curr_expense, yoy_expense),
            "expense_pct_formatted": format_pct(calc_pct(curr_expense, yoy_expense)),
            "expense_prev": to_wan(yoy_expense),
            "balance_pct": calc_pct(curr_balance, yoy_balance),
            "balance_pct_formatted": format_pct(calc_pct(curr_balance, yoy_balance)),
            "balance_prev": to_wan(yoy_balance),
            "balance_rate_pct": calc_pct(curr_rate, yoy_rate),
            "balance_rate_pct_formatted": format_pct(calc_pct(curr_rate, yoy_rate)),
            "balance_rate_prev": round(yoy_rate, 1) if yoy_rate is not None else None,
        },
        "mom": {
            "income_pct": calc_pct(curr_income, prev_income),
            "income_pct_formatted": format_pct(calc_pct(curr_income, prev_income)),
            "income_prev": to_wan(prev_income),
            "income_prev_formatted": f"{prev_income / 10000:.0f}万",
            "expense_pct": calc_pct(curr_expense, prev_expense),
            "expense_pct_formatted": format_pct(calc_pct(curr_expense, prev_expense)),
            "expense_prev": to_wan(prev_expense),
            "balance_pct": calc_pct(curr_balance, prev_balance),
            "balance_pct_formatted": format_pct(calc_pct(curr_balance, prev_balance)),
            "balance_prev": to_wan(prev_balance),
            "balance_prev_formatted": f"{prev_balance / 10000:.0f}万",
            "balance_rate_pct": calc_pct(curr_rate, prev_rate),
            "balance_rate_pct_formatted": format_pct(calc_pct(curr_rate, prev_rate)),
            "balance_rate_prev": round(prev_rate, 1) if prev_rate is not None else None,
        },
        "mom_label": mom_label,
        "is_single": is_single,
        "prev_year": year - 1,
    }
    
    if not is_single and latest_month:
        prev_range_income = curr_income - latest_month['income']
        prev_range_balance = curr_balance - latest_month['balance']
        income_growth_pct = calc_pct(curr_income, prev_range_income)
        balance_growth_pct = calc_pct(curr_balance, prev_range_balance)
        result["cumulative"] = {
            "income_growth_pct": income_growth_pct,
            "income_growth_pct_formatted": format_pct(income_growth_pct),
            "income_growth_sign": '+' if to_wan(curr_income - prev_range_income) >= 0 else '',
            "balance_growth_pct": balance_growth_pct,
            "balance_growth_pct_formatted": format_pct(balance_growth_pct),
            "balance_growth_sign": '+' if to_wan(curr_balance - prev_range_balance) >= 0 else '',
            "latest_month_income": to_wan(latest_month['income']),
            "latest_month_balance": to_wan(latest_month['balance']),
            "latest_month_label": f"{max_month}月",
            "prev_range_label": f"1-{max_month-1}月" if max_month > 1 else "去年同期",
        }
        result["month_contribution"] = {
            "month": int(max_month),
            "income": to_wan(latest_month['income']),
            "expense": to_wan(latest_month['expense']),
            "balance": to_wan(latest_month['balance']),
            "income_sign": '+' if to_wan(latest_month['income']) >= 0 else '',
            "balance_sign": '+' if to_wan(latest_month['balance']) >= 0 else '',
        }
    
    return result


# ==================== 创业团队经营分析压缩表（增强版：含同比） ====================

def _classify_subj(subj: str) -> str:
    """根据收支1名称判断类型：income / expense / fee / balance"""
    if pd.isna(subj):
        return "unknown"
    s = str(subj).strip()
    if s.startswith("1.") or s == "一、收入" or "收入" in s:
        return "income"
    if s.startswith("2.") or s == "二、支出" or "支出" in s:
        return "expense"
    if "管理费" in s or s == "三、管理费":
        return "fee"
    return "unknown"


def _apply_pct_sign(val) -> str:
    """将数值转为带正负符号的万元字符串"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "0"
    wan = to_wan(float(val))
    if wan > 0:
        return f"+{wan:,}"
    return f"{wan:,}"


def get_team_compressed_table(team_df: pd.DataFrame, parent_name: str, year: int, months: list = None) -> dict:
    """
    创业团队经营分析压缩表（增强版：含同比线上线下数据）

    参数:
        team_df: 创业团队原始数据
        parent_name: 要分析的 H团队线-上级 名称
        year: 年份
        months: 月份列表，默认 1-12

    返回:
        {
            "parent": str,          # 上级名称
            "year": int,            # 年份
            "months": list,         # 月份列表
            "cols": list,           # 表头月份列
            "rows": [               # 表格行（带同比数据）
                {
                    "name": str,           # 科目名称
                    "level": str,          # "total" | "sub" | "balance"
                    "type": str,           # "income" | "expense" | "fee" | "balance"
                    "values": {},          # {month: amount_in_wan}
                    "total": int,          # 全年合计（万元）
                    "yoy_pct": float|None, # 同比%
                    "yoy_prev": int|None,  # 去年同期（万元）
                    "ratio": str|None,     # 占比字符串，如 "35.2%"
                    "indent": bool,        # 是否缩进（子科目缩进）
                }
            ],
            "summary": {
                "income": int,           # 收入（万元）
                "expense": int,          # 支出（万元）
                "fee": int,             # 管理费（万元）
                "balance": int,         # 结余（万元）
                "fee_ratio": str,       # 管理费占比
                "income_yoy": float|None,
                "expense_yoy": float|None,
                "balance_yoy": float|None,
                "income_prev": int,
                "expense_prev": int,
                "balance_prev": int,
            },
            "analysis": [str]
        }
    """
    if months is None:
        months = list(range(1, 13))
    months_3_12 = [m for m in months if m >= 3]

    # ---- 今年数据 ----
    # 支持通过 H团队线-上级 / H团队线性质 / H团队线-核算 三种方式匹配
    def _filter_team(df, yr):
        cols_to_try = ["H团队线-上级", "H团队线性质", "H团队线-核算"]
        filtered = pd.DataFrame()
        for col in cols_to_try:
            if col in df.columns:
                subset = df[
                    (df["年"] == yr) &
                    (df["月"].isin(months)) &
                    (df[col] == parent_name)
                ]
                if not subset.empty:
                    filtered = subset.copy()
                    break
        return filtered

    filtered = _filter_team(team_df, year)

    # ---- 去年同期 ----
    prev_year = year - 1
    prev_filtered = _filter_team(team_df, prev_year)

    if filtered.empty:
        return {
            "parent": parent_name, "year": year, "months": months, "cols": [],
            "rows": [], "summary": {}, "analysis": [f"未找到 '{parent_name}' 的数据"]
        }

    # ---- 按 (收支1, 月) 分组计算（汇总行） ----
    def _build_pivot(df_subset):
        if df_subset.empty:
            empty_df = pd.DataFrame(index=pd.Index([], name="收支1"), columns=list(months) + ["全年"])
            return empty_df, empty_df.copy(), empty_df.copy()
        records = []
        grouped = df_subset.groupby(["收支1", "月"])
        for (subj, month), group in grouped:
            inc, exp, fee = _team_calc(group, inc_col="收支1", exp_col="收支1")
            records.append({"收支1": subj, "月": month, "收入": inc, "支出": exp, "管理费": fee})
        if not records:
            empty_df = pd.DataFrame(index=pd.Index([], name="收支1"), columns=list(months) + ["全年"])
            return empty_df, empty_df.copy(), empty_df.copy()
        dg = pd.DataFrame(records)
        piv_i = dg.pivot_table(index="收支1", columns="月", values="收入", fill_value=0)
        piv_e = dg.pivot_table(index="收支1", columns="月", values="支出", fill_value=0)
        piv_f = dg.pivot_table(index="收支1", columns="月", values="管理费", fill_value=0)
        for m in months:
            for p in [piv_i, piv_e, piv_f]:
                if m not in p.columns:
                    p[m] = 0
        piv_i = piv_i.reindex(columns=months, fill_value=0)
        piv_e = piv_e.reindex(columns=months, fill_value=0)
        piv_f = piv_f.reindex(columns=months, fill_value=0)
        piv_i["全年"] = piv_i[months].sum(axis=1)
        piv_e["全年"] = piv_e[months].sum(axis=1)
        piv_f["全年"] = piv_f[months].sum(axis=1)
        return piv_i, piv_e, piv_f

    piv_i, piv_e, piv_f = _build_pivot(filtered)
    prev_piv_i, prev_piv_e, prev_piv_f = _build_pivot(prev_filtered)

    # ---- 分类汇总 ----
    def _classify(name):
        if pd.isna(name): return "unknown"
        s = str(name).strip()
        if s.startswith("1.") or s == "一、收入" or ("收" in s and "支" not in s):
            return "income"
        if s.startswith("2.") or s == "二、支出":
            return "expense"
        if "管理费" in s or s == "三、管理费":
            return "fee"
        return "unknown"

    all_subjects = set(list(piv_i.index) + list(piv_e.index) + list(piv_f.index))
    income_subjects = sorted([s for s in all_subjects if _classify(s) == "income"])
    # 费用科目：在piv_f中有非零值的项（不论收支1名称）
    fee_subjects = sorted([s for s in piv_f.index if piv_f.loc[s, "全年"] != 0]) if not piv_f.empty else []
    expense_subjects = sorted([s for s in all_subjects if _classify(s) == "expense" and s not in fee_subjects])

    # ---- 按类型聚合部门特殊明细 ----
    # 一次性构建：按收支类型（income/expense/fee）聚合部门特殊
    def _build_type_pivot(df, type_subjects, piv_type):
        """按类型聚合部门特殊明细，跨多个收支1科目"""
        if df.empty or "部门特殊" not in df.columns or not type_subjects:
            return None  # 空DataFrame
        sub_df = df[df["收支1"].isin(type_subjects)]
        if sub_df.empty:
            return None
        records = []
        grouped = sub_df.groupby(["部门特殊", "月"])
        for (dept, month), group in grouped:
            inc, exp, fee_amt = _team_calc(group, inc_col="收支1", exp_col="收支1")
            if piv_type == "i":
                val = inc
            elif piv_type == "e":
                val = exp
            else:
                val = fee_amt
            records.append({"部门特殊": dept, "月": month, "金额": val})
        if not records:
            return None
        dg = pd.DataFrame(records)
        piv = dg.pivot_table(index="部门特殊", columns="月", values="金额", fill_value=0, aggfunc="sum")
        for m in months:
            if m not in piv.columns:
                piv[m] = 0
        piv = piv.reindex(columns=months, fill_value=0)
        piv["全年"] = piv[months].sum(axis=1)
        # 只保留非零行
        piv = piv[piv["全年"] != 0]
        return piv

    # 构建三种类型的聚合透视
    dept_inc_piv = _build_type_pivot(filtered, income_subjects, "i")
    dept_exp_piv = _build_type_pivot(filtered, expense_subjects + fee_subjects, "e")
    dept_fee_piv = _build_type_pivot(filtered, fee_subjects, "f")

    def _get_subject_total(piv, subj, col="全年"):
        if subj in piv.index and col in piv.columns:
            return float(piv.loc[subj, col])
        return 0.0

    def _get_yoy(curr_val, prev_val):
        if prev_val == 0 or prev_val is None:
            return None
        return round((curr_val - prev_val) / abs(prev_val) * 100, 1)

    # 全年合计
    total_income = float(sum(_get_subject_total(piv_i, s) for s in income_subjects))
    total_expense = float(sum(_get_subject_total(piv_e, s) for s in expense_subjects))
    total_fee = float(sum(_get_subject_total(piv_f, s) for s in fee_subjects))
    total_balance = total_income - total_expense - total_fee

    # 去年同期全年
    prev_total_income = float(sum(_get_subject_total(prev_piv_i, s) for s in income_subjects))
    prev_total_expense = float(sum(_get_subject_total(prev_piv_e, s) for s in expense_subjects))
    prev_total_fee = float(sum(_get_subject_total(prev_piv_f, s) for s in fee_subjects))
    prev_total_balance = prev_total_income - prev_total_expense - prev_total_fee

    # ---- 构建行数据 ----
    rows = []

    def _make_row(name, level, rtype, subj_list, piv, prev_piv, ratio_base, indent=False):
        # subj_list: for summary rows (e.g. all income subjects), or empty for total row
        if subj_list:
            vals = {m: sum(_get_subject_total(piv, s, m) for s in subj_list) for m in months}
            total = float(sum(_get_subject_total(piv, s) for s in subj_list))
            prev_total = float(sum(_get_subject_total(prev_piv, s) for s in subj_list))
        else:
            vals = {m: 0.0 for m in months}
            total = 0.0
            prev_total = 0.0

        ratio = f"{(total / ratio_base * 100):.1f}%" if (ratio_base and ratio_base != 0) else None
        yoy = _get_yoy(total, prev_total)

        return {
            "name": name,
            "level": level,
            "type": rtype,
            "values": {m: to_wan(vals[m]) for m in months},
            "total": to_wan(total),
            "yoy_pct": yoy,
            "yoy_prev": to_wan(prev_total),
            "ratio": ratio,
            "indent": indent,
        }

    # 辅助函数：渲染按类型聚合的部门特殊子行
    def _render_type_dept_rows(dept_piv, rtype, ratio_base):
        """从按类型聚合的dept_piv读取部门特殊行，相同字段已聚合"""
        if dept_piv is None or dept_piv.empty:
            return
        for dept_name in dept_piv.index:
            dept_name_str = str(dept_name).strip()
            if not dept_name_str:
                continue
            total_val = float(dept_piv.loc[dept_name, "全年"]) if "全年" in dept_piv.columns else 0.0
            if total_val == 0:
                continue
            vals = {}
            for m in months:
                try:
                    vals[m] = float(dept_piv.loc[dept_name, m])
                except (KeyError, ValueError):
                    vals[m] = 0.0
            ratio = f"{(total_val / ratio_base * 100):.1f}%" if (ratio_base and ratio_base != 0) else None
            rows.append({
                "name": dept_name_str,
                "level": "sub",
                "type": rtype,
                "values": {m: to_wan(vals[m]) for m in months},
                "total": to_wan(total_val),
                "yoy_pct": None,
                "yoy_prev": 0,
                "ratio": ratio,
                "indent": True,
            })

    # 收入：总行 + 聚合的部门特殊明细
    if income_subjects:
        rows.append(_make_row("一、收入", "total", "income", income_subjects, piv_i, prev_piv_i, total_income))
        _render_type_dept_rows(dept_inc_piv, "income", total_income)

    # 支出：总行（含fee科目的支出部分）
    all_expense_subs = list(dict.fromkeys(expense_subjects + fee_subjects))
    if all_expense_subs:
        total_expense = float(sum(_get_subject_total(piv_e, s) for s in all_expense_subs if s in piv_e.index))
        rows.append(_make_row("二、支出", "total", "expense", all_expense_subs, piv_e, prev_piv_e, total_expense))
        _render_type_dept_rows(dept_exp_piv, "expense", total_expense)

    # 管理费：总行 + 聚合的部门特殊明细
    if fee_subjects and dept_fee_piv is not None and not dept_fee_piv.empty:
        total_fee = float(sum(_get_subject_total(piv_f, s) for s in fee_subjects))
        rows.append(_make_row("三、管理费", "total", "fee", fee_subjects, piv_f, prev_piv_f, total_income))
        _render_type_dept_rows(dept_fee_piv, "fee", total_income)

    # 结余行
    balance_yoy = _get_yoy(total_balance, prev_total_balance)
    rows.append({
        "name": "结余",
        "level": "balance",
        "type": "balance",
        "values": {m: to_wan(
            sum(_get_subject_total(piv_i, s, m) for s in income_subjects) -
            sum(_get_subject_total(piv_e, s, m) for s in expense_subjects) -
            sum(_get_subject_total(piv_f, s, m) for s in fee_subjects)
        ) for m in months},
        "total": to_wan(total_balance),
        "yoy_pct": balance_yoy,
        "yoy_prev": to_wan(prev_total_balance),
        "ratio": None,
        "indent": False,
    })

    # ---- 分析建议 ----
    analysis = []
    if total_balance < 0:
        analysis.append(f"❌ 结余为负（{to_wan(total_balance)}万），需重点关注资金缺口。")
    elif to_wan(total_balance) > 0:
        analysis.append(f"✅ 结余为正（{to_wan(total_balance)}万），经营状况良好。")

    if total_income > 0 and prev_total_income > 0:
        inc_yoy = _get_yoy(total_income, prev_total_income)
        if inc_yoy is not None:
            if inc_yoy > 10:
                analysis.append(f"📈 收入同比大幅增长 {inc_yoy}%，去年同期 {to_wan(prev_total_income)}万。")
            elif inc_yoy < -10:
                analysis.append(f"📉 收入同比下降 {inc_yoy}%，需分析原因。")

    if total_balance < 0 and prev_total_balance > 0:
        analysis.append(f"⚠️ 结余由盈转亏，去年同期 {to_wan(prev_total_balance)}万，今年 {to_wan(total_balance)}万。")
    elif total_balance > 0 and prev_total_balance < 0:
        analysis.append(f"🎉 结余由亏转盈，扭亏 {to_wan(total_balance - prev_total_balance)}万。")

    if total_income > 0:
        fee_ratio = total_fee / total_income * 100
        if fee_ratio > 15:
            analysis.append(f"⚙️ 管理费占收入 {fee_ratio:.0f}%，比例偏高，建议关注管理效率。")
        elif fee_ratio > 10:
            analysis.append(f"ℹ️ 管理费占收入 {fee_ratio:.0f}%，处于合理区间。")

    if income_subjects and total_income > 0:
        max_sub = max(income_subjects, key=lambda s: _get_subject_total(piv_i, s))
        max_val = _get_subject_total(piv_i, max_sub)
        ratio = max_val / total_income * 100
        if ratio > 50 and len(income_subjects) > 1:
            analysis.append(f"📊 收入集中度过高：{max_sub} 占 {ratio:.0f}%，存在单一依赖风险。")

    if expense_subjects and total_expense > 0:
        high = [s for s in expense_subjects if _get_subject_total(piv_e, s) / total_expense > 0.4]
        if high:
            analysis.append(f"💰 重点支出项：{'、'.join(high)} 合计占 {sum(_get_subject_total(piv_e, s) for s in high)/total_expense*100:.0f}%。")

    return {
        "parent": parent_name,
        "year": year,
        "months": months,
        "cols": [f"{m}月" for m in months],
        "rows": rows,
        "summary": {
            "income": to_wan(total_income),
            "expense": to_wan(total_expense),
            "fee": to_wan(total_fee),
            "balance": to_wan(total_balance),
            "fee_ratio": f"{total_fee/total_income*100:.1f}%" if total_income else "0%",
            "income_yoy": _get_yoy(total_income, prev_total_income),
            "expense_yoy": _get_yoy(total_expense, prev_total_expense),
            "balance_yoy": _get_yoy(total_balance, prev_total_balance),
            "income_prev": to_wan(prev_total_income),
            "expense_prev": to_wan(prev_total_expense),
            "balance_prev": to_wan(prev_total_balance),
        },
        "analysis": analysis,
    }

# ==================== KPI 计算 ====================

def get_kpi(product_df: pd.DataFrame, year: int, months: list) -> dict:
    """
    产品线 KPI（高层关注）
    - 只使用产品 sheet 中的"收入"和"支出"两列
    - 总收入 = 收入列求和
    - 总支出 = 支出列求和
    - 总结余 = 总收入 - 总支出
    - 结余率 = 结余 / 收入 * 100
    - 不考虑管理费，也不单独处理支持团队
    """
    is_single = len(months) == 1
    max_month = max(months)
    
    # 当期数据
    curr = product_df[(product_df["年"] == year) & (product_df["月"].isin(months))]
    curr_income = curr["收入"].sum()
    curr_expense = curr["支出"].sum()
    curr_balance = curr_income - curr_expense
    curr_rate = (curr_balance / curr_income * 100) if curr_income else None
    
    # 去年同期数据
    yoy = product_df[(product_df["年"] == year - 1) & (product_df["月"].isin(months))]
    yoy_income = yoy["收入"].sum()
    yoy_expense = yoy["支出"].sum()
    yoy_balance = yoy_income - yoy_expense
    yoy_rate = (yoy_balance / yoy_income * 100) if yoy_income else None
    
    # 环比/上期数据
    if is_single:
        m = months[0]
        if m == 1:
            prev = product_df[(product_df["年"] == year - 1) & (product_df["月"] == 12)]
            mom_label = f"{year-1}年12月"
        else:
            prev = product_df[(product_df["年"] == year) & (product_df["月"] == m - 1)]
            mom_label = f"{m-1}月"
    else:
        if max_month <= 1:
            prev = product_df[(product_df["年"] == year - 1) & (product_df["月"] == 1)]
            mom_label = "去年同期"
        else:
            prev_months_list = list(range(1, max_month))
            prev = product_df[(product_df["年"] == year) & (product_df["月"].isin(prev_months_list))]
            mom_label = f"1-{max_month-1}月"
    
    prev_income = prev["收入"].sum()
    prev_expense = prev["支出"].sum()
    prev_balance = prev_income - prev_expense
    prev_rate = (prev_balance / prev_income * 100) if prev_income else None
    
    # 最新月份数据（用于累计模式的贡献值）
    latest_month = None
    if not is_single and max_month >= 1:
        latest = product_df[(product_df["年"] == year) & (product_df["月"] == max_month)]
        latest_income = latest["收入"].sum()
        latest_expense = latest["支出"].sum()
        latest_balance = latest_income - latest_expense
        latest_month = {
            'income': latest_income,
            'expense': latest_expense,
            'balance': latest_balance,
        }
    
    result = {
        "income": to_wan(curr_income),
        "expense": to_wan(curr_expense),
        "balance": to_wan(curr_balance),
        "balance_rate": round(curr_rate, 1) if curr_rate is not None else None,
        
        "yoy": {
            "income_pct": calc_pct(curr_income, yoy_income),
            "income_pct_formatted": format_pct(calc_pct(curr_income, yoy_income)),
            "income_prev": to_wan(yoy_income),
            "income_prev_formatted": f"{to_wan(yoy_income):,}",  # 纯数字，前端加"万"
            
            "expense_pct": calc_pct(curr_expense, yoy_expense),
            "expense_pct_formatted": format_pct(calc_pct(curr_expense, yoy_expense)),
            "expense_prev": to_wan(yoy_expense),
            
            "balance_pct": calc_pct(curr_balance, yoy_balance),
            "balance_pct_formatted": format_pct(calc_pct(curr_balance, yoy_balance)),
            "balance_prev": to_wan(yoy_balance),
            
            "balance_rate_pct": calc_pct(curr_rate, yoy_rate),
            "balance_rate_pct_formatted": format_pct(calc_pct(curr_rate, yoy_rate)),
            "balance_rate_prev": round(yoy_rate, 1) if yoy_rate is not None else None,
        },
        
        "mom": {
            "income_pct": calc_pct(curr_income, prev_income),
            "income_pct_formatted": format_pct(calc_pct(curr_income, prev_income)),
            "income_prev": to_wan(prev_income),
            "income_prev_formatted": f"{to_wan(prev_income):,}",  # 纯数字，前端加"万"
            
            "expense_pct": calc_pct(curr_expense, prev_expense),
            "expense_pct_formatted": format_pct(calc_pct(curr_expense, prev_expense)),
            "expense_prev": to_wan(prev_expense),
            
            "balance_pct": calc_pct(curr_balance, prev_balance),
            "balance_pct_formatted": format_pct(calc_pct(curr_balance, prev_balance)),
            "balance_prev": to_wan(prev_balance),
            "balance_prev_formatted": f"{to_wan(prev_balance):,}",  # 纯数字，前端加"万"
            
            "balance_rate_pct": calc_pct(curr_rate, prev_rate),
            "balance_rate_pct_formatted": format_pct(calc_pct(curr_rate, prev_rate)),
            "balance_rate_prev": round(prev_rate, 1) if prev_rate is not None else None,
        },
        
        "mom_label": mom_label,
        "is_single": is_single,
        "prev_year": year - 1,
    }
    
    # 累计模式：添加增长和贡献值
    if not is_single and latest_month:
        prev_range_income = curr_income - latest_month['income']
        prev_range_balance = curr_balance - latest_month['balance']
        
        income_growth_pct = calc_pct(curr_income, prev_range_income)
        balance_growth_pct = calc_pct(curr_balance, prev_range_balance)
        
        result["cumulative"] = {
            "income_growth_pct": income_growth_pct,
            "income_growth_pct_formatted": format_pct(income_growth_pct),
            "income_growth_sign": '+' if to_wan(curr_income - prev_range_income) >= 0 else '',
            
            "balance_growth_pct": balance_growth_pct,
            "balance_growth_pct_formatted": format_pct(balance_growth_pct),
            "balance_growth_sign": '+' if to_wan(curr_balance - prev_range_balance) >= 0 else '',
            
            "latest_month_income": to_wan(latest_month['income']),
            "latest_month_balance": to_wan(latest_month['balance']),
            "latest_month_label": f"{max_month}月",
            "prev_range_label": f"1-{max_month-1}月" if max_month > 1 else "去年同期",
        }
        
        result["month_contribution"] = {
            "month": int(max_month),
            "income": to_wan(latest_month['income']),
            "expense": to_wan(latest_month['expense']),
            "balance": to_wan(latest_month['balance']),
            "income_sign": '+' if to_wan(latest_month['income']) >= 0 else '',
            "balance_sign": '+' if to_wan(latest_month['balance']) >= 0 else '',
        }
    
    return result

# ==================== 趋势 & 图表 ====================

def get_monthly_trend(product_df: pd.DataFrame) -> dict:
    """月度趋势（按板块，2025-2026，含同比环比）"""
    boards = ["物业板块", "医养板块", "餐饮板块", "美好生活"]
    result = {}
    
    # 先收集所有年份的数据
    all_years_data = {}
    for yr in sorted(product_df["年"].dropna().unique()):
        yd = product_df[product_df["年"] == yr]
        year_months = {}
        for month in sorted(yd["月"].dropna().unique()):
            md = yd[yd["月"] == month]
            entry = {"month": int(month)}
            for board in boards:
                bd = md[md["业务板块"] == board]
                entry[board] = to_wan(bd["收入"].sum())
            year_months[int(month)] = entry
        all_years_data[int(yr)] = year_months
    
    # 按年份组织数据，计算同比和环比
    for yr in sorted(all_years_data.keys()):
        year_months = []
        prev_year = all_years_data.get(yr - 1, {})
        curr_year = all_years_data.get(yr, {})
        
        for month in sorted(curr_year.keys()):
            entry = {"month": month}
            for board in boards:
                curr_val = curr_year[month].get(board, 0) or 0
                prev_month_val = prev_year.get(month, {}).get(board, 0) or 0
                
                # 同比（与去年同月相比）
                if prev_month_val and prev_month_val != 0:
                    yoy = ((curr_val - prev_month_val) / abs(prev_month_val)) * 100
                else:
                    yoy = None
                
                # 环比（与上月相比）
                prev_mom_val = curr_year.get(month - 1, {}).get(board, 0) if month > 1 else 0
                if prev_mom_val and prev_mom_val != 0:
                    mom = ((curr_val - prev_mom_val) / abs(prev_mom_val)) * 100
                else:
                    mom = None
                
                entry[board] = curr_val
                entry[f'{board}_yoy'] = round(yoy, 1) if yoy is not None else None
                entry[f'{board}_mom'] = round(mom, 1) if mom is not None else None
            
            year_months.append(entry)
        result[str(int(yr))] = year_months
    
    return result
def get_pie_data(product_df: pd.DataFrame, year: int, months: list) -> list:
    """
    环形图数据：各业务板块 |结余| 绝对值占比
    不含支持团队
    """
    filtered = product_df[(product_df["年"] == year) & (product_df["月"].isin(months))]
    boards = ["物业板块", "医养板块", "餐饮板块", "美好生活"]
    
    data = []
    for board in boards:
        bd = filtered[filtered["业务板块"] == board]
        balance = bd["收入"].sum() - bd["支出"].sum() - bd["平台管理费"].sum()
        data.append({
            "name": board.replace("板块", ""),
            "value": abs_to_wan(balance)  # 使用绝对值
        })
    
    return data


# ==================== 趋势预警 ====================

def analyze_trends(product_df: pd.DataFrame, year: int) -> list:
    """
    趋势预警：检测损益同比下滑超30%的板块
    """
    alerts = []
    curr = product_df[product_df["年"] == year]
    prev = product_df[product_df["年"] == year - 1]
    
    if curr.empty or prev.empty:
        return alerts
    
    for board in curr["业务板块"].dropna().unique():
        bc = curr[curr["业务板块"] == board]
        bp = prev[prev["业务板块"] == board]
        
        for m in range(1, 13):
            mc = bc[bc["月"] == m]
            mp = bp[bp["月"] == m]
            
            if mc.empty or mp.empty:
                continue
            
            cb = mc["收入"].sum() - mc["支出"].sum() - mc["平台管理费"].sum()
            pb = mp["收入"].sum() - mp["支出"].sum() - mp["平台管理费"].sum()
            
            pct = calc_pct(cb, pb)
            if pct is not None and pct < -30:
                alerts.append(f"{board}{m}月损益同比下滑{abs(int(round(pct)))}%（本期{to_wan(cb)}万 vs 去年{to_wan(pb)}万）")
    
    return alerts







# ==================== 创业团队经营分析压缩表（简化版：table + analysis） ====================

def get_team_pivot(team_df: pd.DataFrame, parent_name: str, year: int,
                   months: list = None) -> dict:
    """
    创业团队经营分析压缩表（简化版）

    参数:
        team_df: DataFrame，必须包含列：年、月、H团队线-上级、收支1、金额g（或 总计）、收支、资金流向
        parent_name: 字符串，要分析的 H团队线-上级 名称
        year: 整数，年份
        months: 列表，月份，默认 list(range(1,13))

    返回:
        {"table": pd.DataFrame, "analysis": list}
        - table.收支科目：行名称，子科目以两个空格开头
        - table.1月~12月：各月金额（万元，整数）
        - table.全年合计：1-12月求和
        - table.3-12月合计：3-12月求和（如月份含3月及之后）
        - table.收入结构/成本结构/管理费占比：百分比字符串或 None
    """
    if months is None:
        months = list(range(1, 13))
    months = sorted(set(int(m) for m in months))
    has_m3 = any(m >= 3 for m in months)

    # ---- 1. 筛选数据 ----
    df = team_df[
        (team_df["年"] == year) &
        (team_df["月"].isin(months)) &
        (team_df["H团队线-上级"] == parent_name)
    ].copy()

    if df.empty:
        return {"table": pd.DataFrame(), "analysis": [f"未找到 '{parent_name}' 的数据"]}

    # ---- 2. 按 (收支1, 月) 分组，调用 _team_calc ----
    records = []
    for (subj, m), group in df.groupby(["收支1", "月"]):
        inc, exp, fee = _team_calc(group, inc_col="收支1", exp_col="收支1")
        records.append({"收支1": subj, "月": m, "收入": inc, "支出": exp, "管理费": fee})

    if not records:
        return {"table": pd.DataFrame(), "analysis": [f"'{parent_name}' 无可用数据"]}

    dg = pd.DataFrame(records)

    piv_i = dg.pivot_table(index="收支1", columns="月", values="收入", fill_value=0)
    piv_e = dg.pivot_table(index="收支1", columns="月", values="支出", fill_value=0)
    piv_f = dg.pivot_table(index="收支1", columns="月", values="管理费", fill_value=0)
    for m in months:
        for p in [piv_i, piv_e, piv_f]:
            if m not in p.columns:
                p[m] = 0
    piv_i = piv_i.reindex(columns=sorted(piv_i.columns), fill_value=0)
    piv_e = piv_e.reindex(columns=sorted(piv_e.columns), fill_value=0)
    piv_f = piv_f.reindex(columns=sorted(piv_f.columns), fill_value=0)

    # ---- 3. 区分科目类型 ----
    def _classify(s):
        if pd.isna(s):
            return "unknown"
        s = str(s).strip()
        if s.startswith("1.") or s == "一、收入":
            return "income"
        if s.startswith("2.") or s == "二、支出":
            return "expense"
        if "管理费" in s or s == "三、管理费":
            return "fee"
        return "unknown"

    all_subjects = set(piv_i.index) | set(piv_e.index) | set(piv_f.index)
    income_subs = sorted([s for s in all_subjects if _classify(s) == "income"])
    expense_subs = sorted([s for s in all_subjects if _classify(s) == "expense"])
    fee_subs = sorted([s for s in all_subjects if _classify(s) == "fee"])

    def _total(piv, subj, col="全年"):
        if subj in piv.index and col in piv.columns:
            return float(piv.loc[subj, col])
        return 0.0

    # 全年列
    piv_i["全年"] = piv_i[months].sum(axis=1)
    piv_e["全年"] = piv_e[months].sum(axis=1)
    piv_f["全年"] = piv_f[months].sum(axis=1)
    # 3-12月合计列
    m3_12 = [m for m in months if m >= 3]
    if has_m3 and m3_12:
        piv_i["3-12月合计"] = piv_i[m3_12].sum(axis=1)
        piv_e["3-12月合计"] = piv_e[m3_12].sum(axis=1)
        piv_f["3-12月合计"] = piv_f[m3_12].sum(axis=1)

    # ---- 4. 汇总值 ----
    total_income = sum(_total(piv_i, s) for s in income_subs)
    total_expense = sum(_total(piv_e, s) for s in expense_subs)
    total_fee = sum(_total(piv_f, s) for s in fee_subs)
    total_balance = total_income - total_expense - total_fee

    # ---- 5. 构建层级表格行 ----
    table_rows = []
    month_cols = [f"{m}月" for m in months]
    extra_cols = ["全年合计"]
    if has_m3:
        extra_cols.append("3-12月合计")

    def _make_row(name, vals_dict, ratio_str):
        """构造一行：name + 月值 + 合计列 + 占比"""
        row = {"收支科目": name}
        for m in months:
            row[f"{m}月"] = to_wan(vals_dict.get(m, 0.0))
        row["全年合计"] = to_wan(vals_dict.get("全年", 0.0))
        if has_m3:
            row["3-12月合计"] = to_wan(vals_dict.get("3-12月合计", 0.0))
        row["收入结构"] = ratio_str if ratio_str is not None else None
        return row

    # --- 一、收入 ---
    inc_total_vals = {m: sum(_total(piv_i, s, m) for s in income_subs) for m in months}
    inc_total_vals["全年"] = total_income
    if has_m3:
        inc_total_vals["3-12月合计"] = sum(inc_total_vals.get(m, 0) for m in m3_12)
    table_rows.append(_make_row("一、收入", inc_total_vals, "100%"))

    for subj in income_subs:
        sub_vals = {m: float(piv_i.loc[subj, m]) if subj in piv_i.index else 0.0 for m in months}
        sub_vals["全年"] = float(piv_i.loc[subj, "全年"]) if subj in piv_i.index else 0.0
        if has_m3 and subj in piv_i.index:
            sub_vals["3-12月合计"] = float(piv_i.loc[subj, "3-12月合计"])
        ratio = f"{(sub_vals['全年'] / total_income * 100):.1f}%" if total_income else None
        table_rows.append(_make_row(f"  {subj}", sub_vals, ratio))

    # --- 二、支出 ---
    exp_total_vals = {m: sum(_total(piv_e, s, m) for s in expense_subs) for m in months}
    exp_total_vals["全年"] = total_expense
    if has_m3:
        exp_total_vals["3-12月合计"] = sum(exp_total_vals.get(m, 0) for m in m3_12)
    table_rows.append(_make_row("二、支出", exp_total_vals, "100%"))

    for subj in expense_subs:
        sub_vals = {m: float(piv_e.loc[subj, m]) if subj in piv_e.index else 0.0 for m in months}
        sub_vals["全年"] = float(piv_e.loc[subj, "全年"]) if subj in piv_e.index else 0.0
        if has_m3 and subj in piv_e.index:
            sub_vals["3-12月合计"] = float(piv_e.loc[subj, "3-12月合计"])
        ratio = f"{(sub_vals['全年'] / total_expense * 100):.1f}%" if total_expense else None
        table_rows.append(_make_row(f"  {subj}", sub_vals, ratio))

    # --- 三、管理费 ---
    fee_total_vals = {m: sum(_total(piv_f, s, m) for s in fee_subs) for m in months}
    fee_total_vals["全年"] = total_fee
    if has_m3:
        fee_total_vals["3-12月合计"] = sum(fee_total_vals.get(m, 0) for m in m3_12)
    fee_ratio = f"{(total_fee / total_income * 100):.1f}%" if total_income else None
    table_rows.append(_make_row("三、管理费", fee_total_vals, fee_ratio))

    # --- 结余 ---
    bal_vals = {
        **{m: (
            sum(_total(piv_i, s, m) for s in income_subs) -
            sum(_total(piv_e, s, m) for s in expense_subs) -
            sum(_total(piv_f, s, m) for s in fee_subs)
        ) for m in months},
        "全年": total_balance,
    }
    if has_m3:
        bal_vals["3-12月合计"] = sum(bal_vals.get(m, 0) for m in m3_12)
    table_rows.append(_make_row("结余", bal_vals, None))

    df_table = pd.DataFrame(table_rows)
    # 移除内部 None 值，用 0 填充
    fill_dict = {c: 0 for c in df_table.columns if c != "收支科目"}
    if fill_dict:
        df_table = df_table.fillna(value=fill_dict)

    # ---- 6. 自动生成分析建议 ----
    analysis = []

    if total_balance < 0:
        analysis.append(f"❌ 该团队整体结余为负（{to_wan(total_balance)}万），需重点关注。")

    if income_subs and total_income > 0:
        concentrated = [
            (s, _total(piv_i, s) / total_income * 100)
            for s in income_subs
            if s not in ("一、收入",)
            and _total(piv_i, s) / total_income * 100 > 50
        ]
        for subj, ratio in concentrated:
            analysis.append(f"📈 收入高度集中于「{subj}」，占比 {ratio:.1f}%，存在依赖风险。")

    if expense_subs and total_expense > 0:
        high_exp = [
            s for s in expense_subs
            if s not in ("二、支出",)
            and _total(piv_e, s) / total_expense * 100 > 40
        ]
        if high_exp:
            high_ratio = sum(_total(piv_e, s) for s in high_exp) / total_expense * 100
            analysis.append(
                f"💰 支出占比过高：{'、'.join(high_exp)} 合计占总支出的 {high_ratio:.1f}%，建议优化。"
            )

    if total_income > 0:
        fee_pct = total_fee / total_income * 100
        if fee_pct > 15:
            analysis.append(f"⚙️ 管理费占收入比例较高（{fee_pct:.1f}%），需关注管理效率。")

    return {"table": df_table, "analysis": analysis}

