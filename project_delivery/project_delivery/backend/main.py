"""
财务综述 Agent - FastAPI 主程序
三模块: 经营分析 / 智能问答 / 预算对比
数据源: 管理报表.xlsx（产品Sheet + 创业团队Sheet）
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import pandas as pd
import numpy as np
import io
import os
import re
import time
from typing import List, Optional
import datetime

from data_loader import load_product_df, load_team_df, get_meta, filter_product, filter_team, load_budget_df, get_budget_comparison_data
from calculators import (
    to_wan, to_wan_f, calc_pct, format_pct,
    aggregate_board, aggregate_product, aggregate_project,
    aggregate_team_nature, aggregate_team_parent, aggregate_team_account,
    get_support_team_balance, get_kpi, get_monthly_trend, get_pie_data,
    analyze_trends, _team_calc, _team_amt_col,
    get_team_compressed_table,
)
from agent import FinancialAgent
from api_extensions import enhanced_query, get_ai_suggestions, get_team_share_detail
from vip_progress import (
    get_all_vip_records, get_vip_record_by_id, create_vip_record,
    update_vip_record, delete_vip_record, get_vip_summary
)
from admin_api import router as admin_router

# 全局数据 + 缓存时间
product_df = None
team_df = None
_load_time = float('inf')  # 初始化为无穷大，避免启动时重复加载
CACHE_SECONDS = 60  # 1分钟缓存

def parse_months(months: str) -> List[int]:
    """解析月份参数字符串，返回月份列表"""
    if not months or not months.strip():
        return []
    return [int(x) for x in months.split(",") if x.strip()]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时加载数据
    global product_df, team_df, _load_time
    try:
        product_df = load_product_df()
        team_df = load_team_df()
        _load_time = time.time()
        print(f"[startup] 产品 {len(product_df)} 行, 创业团队 {len(team_df)} 行")
    except Exception as e:
        print(f"[startup] 数据加载失败: {e}")
        product_df = pd.DataFrame()
        team_df = pd.DataFrame()
    yield
    # 关闭时清理资源（如果需要）

app = FastAPI(title="财务综述 Agent API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# 注册管理后台 API
app.include_router(admin_router)

# 挂载静态文件目录（frontend目录，自动兼容 Docker 和本地开发）
_this_dir = os.path.dirname(os.path.abspath(__file__))
_frontend_candidates = [
    os.path.join(os.path.dirname(_this_dir), "frontend"),  # 本地开发: 上级目录的frontend
    os.path.join(_this_dir, "frontend"),                    # Docker: 同级目录的frontend
]
frontend_path = next((p for p in _frontend_candidates if os.path.isdir(p)), None)
if frontend_path:
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


def _ensure_native(obj):
    """递归转换 numpy/pandas 类型为 Python 原生类型"""
    if isinstance(obj, dict):
        return {k: _ensure_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_ensure_native(x) for x in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if pd.isna(obj) if isinstance(obj, (float,)) else False:
        return None
    return obj


def _refresh_if_needed():
    global product_df, team_df, _load_time
    if time.time() - _load_time > CACHE_SECONDS:
        try:
            product_df = load_product_df()
            team_df = load_team_df()
            _load_time = time.time()
        except Exception:
            pass


# ==================== 基础接口 ====================

@app.get("/health")
def health():
    return _ensure_native({
        "status": "ok",
        "data_loaded": product_df is not None and not product_df.empty,
        "rows": len(product_df) if product_df is not None else 0,
        "team_rows": len(team_df) if team_df is not None else 0,
    })


@app.get("/api/meta")
def api_meta():
    _refresh_if_needed()
    if product_df is None or product_df.empty:
        return {"years": [2025, 2026], "months": list(range(1, 13))}
    team_natures = []
    if team_df is not None and not team_df.empty:
        team_natures = [str(x) for x in sorted(team_df["H团队线性质"].dropna().unique())]
    meta = get_meta(product_df)
    meta["team_natures"] = team_natures
    return _ensure_native(meta)


@app.get("/api/kpi")
def api_kpi(
    year: int = Query(...),
    months: str = Query(...),  # "3" or "1,2,3"
    mode: str = Query("product"),
):
    _refresh_if_needed()
    ml = parse_months(months)
    if mode == "team" and team_df is not None and not team_df.empty:
        # 创业团队KPI
        tf = filter_team(team_df, year, ml)
        inc, exp, fee = _team_calc(tf)
        curr_bal = inc - exp - fee
        curr_rate = round(curr_bal / inc * 100, 1) if inc else None

        tf_yoy = filter_team(team_df, year - 1, ml)
        yoy_inc, yoy_exp, yoy_fee = _team_calc(tf_yoy)
        yoy_bal = yoy_inc - yoy_exp - yoy_fee
        yoy_rate = round(yoy_bal / yoy_inc * 100, 1) if yoy_inc else None

        is_single = len(ml) == 1
        if is_single:
            m = ml[0]
            if m == 1:
                prev_f = filter_team(team_df, year - 1, [12])
                mom_label = f"{year-1}年12月"
            else:
                prev_f = filter_team(team_df, year, [m - 1])
                mom_label = f"{m - 1}月"
        else:
            max_m = max(ml)
            prev_ml = list(range(1, max_m)) if max_m > 1 else [1]
            prev_f = filter_team(team_df, year, prev_ml)
            mom_label = f"1-{max_m - 1}月" if max_m > 1 else "去年同期"

        prev_inc, prev_exp, prev_fee = _team_calc(prev_f)
        prev_bal = prev_inc - prev_exp - prev_fee
        prev_rate = round(prev_bal / prev_inc * 100, 1) if prev_inc else None

        result = {
            "income": to_wan(inc),
            "expense": to_wan(exp),
            "platform_fee": to_wan(fee),
            "balance": to_wan(curr_bal),
            "balance_rate": curr_rate,
            "yoy": {
                "income_pct": calc_pct(inc, yoy_inc),
                "income_prev": to_wan(yoy_inc),
                "expense_pct": calc_pct(exp, yoy_exp),
                "expense_prev": to_wan(yoy_exp),
                "balance_pct": calc_pct(curr_bal, yoy_bal),
                "balance_prev": to_wan(yoy_bal),
                # 结余率同比变化：展示百分点差值
                "balance_rate_diff": round(curr_rate - yoy_rate, 1) if curr_rate is not None and yoy_rate is not None else None,
                "balance_rate_prev": yoy_rate,
            },
            "mom": {
                "income_pct": calc_pct(inc, prev_inc),
                "income_prev": to_wan(prev_inc),
                "expense_pct": calc_pct(exp, prev_exp),
                "expense_prev": to_wan(prev_exp),
                "balance_pct": calc_pct(curr_bal, prev_bal),
                "balance_prev": to_wan(prev_bal),
                # 结余率环比变化：展示百分点差值
                "balance_rate_diff": round(curr_rate - prev_rate, 1) if curr_rate is not None and prev_rate is not None else None,
                "balance_rate_prev": prev_rate,
            },
            "mom_label": mom_label,
            "is_single": is_single,
        }
        if not is_single:
            max_m = max(ml)
            last_f = filter_team(team_df, year, [max_m])
            li, le, lf = _team_calc(last_f)
            result["month_contribution"] = {
                "month": int(max_m),
                "income": to_wan(li),
                "expense": to_wan(le),
                "balance": to_wan(li - le - lf),
            }
        return _ensure_native(result)

    # 产品模式 - 修改：去掉 team_df 参数
    if product_df is None or product_df.empty:
        raise HTTPException(500, "产品数据未加载")
    return _ensure_native(get_kpi(product_df, year, ml))


@app.get("/api/trend")
def api_trend():
    _refresh_if_needed()
    if product_df is None:
        return {}
    return _ensure_native(get_monthly_trend(product_df))


@app.get("/api/pie")
def api_pie(year: int = Query(...), months: str = Query(...)):
    _refresh_if_needed()
    ml = parse_months(months)
    if product_df is None:
        return []
    return _ensure_native(get_pie_data(product_df, year, ml))


# ==================== 产品线下钻 ====================

@app.post("/api/product/drill")
def product_drill(
    year: int = Body(...),
    months: List[int] = Body(...),
    level: str = Body("board"),
    board: Optional[str] = Body(None),
    product: Optional[str] = Body(None),
):
    _refresh_if_needed()
    if product_df is None or product_df.empty:
        raise HTTPException(500, "产品数据未加载")
    df_f = filter_product(product_df, year, months)
    if level == "board":
        data = aggregate_board(df_f)
    elif level == "product":
        data = aggregate_product(df_f, board)
    elif level == "project":
        data = aggregate_project(df_f, product)
    else:
        raise HTTPException(400, f"未知level: {level}")
    
    # 构建规范化的数据记录
    records = []
    for _, row in data.iterrows():
        r = {}
        for k in data.columns:
            val = row.get(k)
            if k in ["收入", "支出", "平台管理费", "结余", "损益"]:
                r[k] = to_wan(val) if pd.notna(val) else 0
            else:
                r[k] = str(val) if pd.notna(val) else ""
        
        # 添加同比损益（含平台管理费，与显示的结余口径一致）
        if level == "board":
            df_prev = filter_product(product_df, year - 1, months)
            if "业务板块" in r:
                board_name = r["业务板块"]
                # 使用原始数据直接计算，避免万元换算的精度丢失
                curr_b = df_f[df_f["业务板块"] == board_name]
                prev_b = df_prev[df_prev["业务板块"] == board_name]
                curr_bal = curr_b["收入"].sum() - curr_b["支出"].sum() - curr_b["平台管理费"].sum()
                prev_bal = prev_b["收入"].sum() - prev_b["支出"].sum() - prev_b["平台管理费"].sum()
                r["同比损益"] = format_pct(calc_pct(curr_bal, prev_bal))
        # 产品级同比
        elif level == "product":
            df_prev = filter_product(product_df, year - 1, months)
            if board and "产品" in r:
                prod_name = r["产品"]
                curr_b = df_f[(df_f["业务板块"] == board) & (df_f["产品"] == prod_name)]
                prev_b = df_prev[(df_prev["业务板块"] == board) & (df_prev["产品"] == prod_name)]
                if not prev_b.empty:
                    curr_bal = curr_b["收入"].sum() - curr_b["支出"].sum() - curr_b["平台管理费"].sum()
                    prev_bal = prev_b["收入"].sum() - prev_b["支出"].sum() - prev_b["平台管理费"].sum()
                    r["同比损益"] = format_pct(calc_pct(curr_bal, prev_bal))
        records.append(r)
    
    return _ensure_native({"data": records})


@app.get("/api/product/business-card")
def api_product_business_card(
    year: int = Query(2026),
    months: str = Query("1,2,3"),
):
    """
    业务线卡片接口 - 返回固定顺序的板块-产品-项目三级结构
    板块顺序：物业板块、医养板块、餐饮板块、美好生活、支持团队
    每个产品只返回前3个项目
    """
    _refresh_if_needed()
    if product_df is None or product_df.empty:
        raise HTTPException(500, "产品数据未加载")
    
    ml = parse_months(months)
    df_f = filter_product(product_df, year, ml)
    df_prev = filter_product(product_df, year - 1, ml)
    
    # 固定板块顺序
    BOARD_ORDER = ["物业板块", "医养板块", "餐饮板块", "美好生活", "支持团队"]
    
    # 项目显示顺序（按产品分组）
    PROJECT_ORDER = {
        "物业管理": [
            "东环","泛交行","紫金长安","紫金新干线","星颐佳园","机关幼儿园","富卓","新纪元","日报","英特公寓","外经贸","中科","保龄","商报","朗清园托班","万寿路街道","吉源","协和项目"
        ]
    }
    def _sort_projects(product_name: str, projects: list) -> list:
        """按自定义顺序排列项目，不在列表中的排在最后"""
        order = PROJECT_ORDER.get(product_name)
        if not order:
            return projects  # 无自定义顺序则保持原样
        idx = {k: i for i, k in enumerate(order)}
        return sorted(projects, key=lambda p: idx.get(p, 9999))
    
    result = []
    
    for board in BOARD_ORDER:
        board_data = df_f[df_f["业务板块"] == board]
        board_prev = df_prev[df_prev["业务板块"] == board] if not df_prev.empty else pd.DataFrame()
        
        # 板块汇总 - 修改：结余不含管理费
        board_income = board_data["收入"].sum()
        board_expense = board_data["支出"].sum()
        board_balance = board_income - board_expense
        
        board_prev_balance = 0
        if not board_prev.empty:
            board_prev_balance = board_prev["收入"].sum() - board_prev["支出"].sum()
        
        board_yoy_balance = calc_pct(board_balance, board_prev_balance)
        
        # 获取该板块下的所有产品
        products = board_data["产品"].dropna().unique()
        product_list = []
        
        for prod in products:
            prod_data = board_data[board_data["产品"] == prod]
            prod_prev = board_prev[board_prev["产品"] == prod] if not board_prev.empty else pd.DataFrame()
            
            prod_income = prod_data["收入"].sum()
            prod_expense = prod_data["支出"].sum()
            prod_balance = prod_income - prod_expense
            
            prod_prev_balance = 0
            if not prod_prev.empty:
                prod_prev_balance = prod_prev["收入"].sum() - prod_prev["支出"].sum()
            
            prod_yoy_balance = calc_pct(prod_balance, prod_prev_balance)
            
                    # 获取该项目下的所有项目（只取前3个），按自定义顺序排序
            projects = prod_data["项目"].dropna().unique()
            projects = _sort_projects(prod, list(projects))
            project_count = len(projects)
            project_list = []
            
            for proj in projects[:3]:
                proj_data = prod_data[prod_data["项目"] == proj]
                proj_prev = prod_prev[prod_prev["项目"] == proj] if not prod_prev.empty else pd.DataFrame()
                
                proj_income = proj_data["收入"].sum()
                proj_expense = proj_data["支出"].sum()
                proj_balance = proj_income - proj_expense
                
                proj_prev_balance = 0
                if not proj_prev.empty:
                    proj_prev_balance = proj_prev["收入"].sum() - proj_prev["支出"].sum()
                
                proj_yoy_balance = calc_pct(proj_balance, proj_prev_balance)
                
                project_list.append({
                    "name": str(proj),
                    "收入": to_wan(proj_income),
                    "支出": to_wan(proj_expense),
                    "平台管理费": to_wan(proj_data["平台管理费"].sum()),  # 单独展示
                    "结余": to_wan(proj_balance),
                    "同比损益": format_pct(proj_yoy_balance) if proj_yoy_balance is not None else "-",
                    "canDrill": False,
                })
            
            has_no_project = str(prod) == "(无项目)" or project_count == 0
            
            product_list.append({
                "name": str(prod),
                "收入": to_wan(prod_income),
                "支出": to_wan(prod_expense),
                "平台管理费": to_wan(prod_data["平台管理费"].sum()),
                "结余": to_wan(prod_balance),
                "同比损益": format_pct(prod_yoy_balance) if prod_yoy_balance is not None else "-",
                "projectCount": project_count,
                "projects": project_list,
                "canDrill": not has_no_project and project_count > 0,
            })
        
        has_no_product = str(board) == "(无产品)" or len(products) == 0
        
        result.append({
            "name": board,
            "收入": to_wan(board_income),
            "支出": to_wan(board_expense),
            "平台管理费": to_wan(board_data["平台管理费"].sum()),
            "结余": to_wan(board_balance),
            "同比损益": format_pct(board_yoy_balance) if board_yoy_balance is not None else "-",
            "productCount": len(products),
            "products": product_list,
            "canDrill": not has_no_product and len(products) > 0,
        })
    
    return _ensure_native({"data": result})


# ==================== 创业团队下钻 ====================

@app.post("/api/team/drill")
def team_drill(
    year: int = Body(...),
    months: List[int] = Body(...),
    level: str = Body("nature"),
    nature: Optional[str] = Body(None),
    parent: Optional[str] = Body(None),
):
    _refresh_if_needed()
    if team_df is None or team_df.empty:
        raise HTTPException(500, "团队数据未加载")
    df_f = filter_team(team_df, year, months)
    if level == "nature":
        data = aggregate_team_nature(df_f)
    elif level == "parent":
        data = aggregate_team_parent(df_f, nature)
    elif level == "account":
        data = aggregate_team_account(df_f, parent)
    else:
        raise HTTPException(400, f"未知level: {level}")
    
    # 构建规范化的数据记录
    records = []
    for _, row in data.iterrows():
        r = {}
        for k in data.columns:
            val = row.get(k)
            if k in ["收入", "支出", "平台管理费", "损益", "结余"]:
                r[k] = to_wan(val) if pd.notna(val) else 0
            else:
                r[k] = str(val) if pd.notna(val) else ""
        
        # 同比损益
        if level in ("nature", "parent"):
            df_prev = filter_team(team_df, year - 1, months)
            if level == "nature":
                # 按 H团队线性质 匹配上年数据
                prev_g = df_prev[df_prev["H团队线性质"] == r.get("H团队线性质")]
            else:
                prev_g = df_prev[(df_prev["H团队线性质"] == r.get("H团队线性质")) & (df_prev["H团队线-上级"] == r.get("H团队线-上级"))]
            if not prev_g.empty:
                prev_inc, prev_exp, prev_fee = _team_calc(prev_g)
                prev_bal = prev_inc - prev_exp - prev_fee
                curr_bal = r.get("结余") if r.get("结余") is not None else (r.get("收入", 0) - r.get("支出", 0) - r.get("平台管理费", 0))
                r["同比损益"] = format_pct(calc_pct(curr_bal, prev_bal))
        
        records.append(r)
    
    return _ensure_native({"data": records})


@app.get("/api/support/balance")
def api_support_balance(year: int, months: str = Query(...)):
    _refresh_if_needed()
    ml = parse_months(months)
    if product_df is None or team_df is None:
        raise HTTPException(500, "数据未加载")
    bal = get_support_team_balance(product_df, team_df, year, ml)
    return _ensure_native({k: to_wan(v) for k, v in bal.items()})


# ==================== 经营分享 ====================

@app.get("/api/team/share")
def api_team_share(year: int, parent: str):
    _refresh_if_needed()
    if team_df is None or team_df.empty:
        raise HTTPException(500, "团队数据未加载")
    detail = get_team_share_detail(team_df, parent, year)
    if detail is None:
        raise HTTPException(404, f"未找到 {parent} 的数据")
    return _ensure_native(detail)
    

# ==================== 创业团队详情（按收支列分组）====================

@app.post("/api/team/detail")
def team_detail(
    year: int = Body(...),
    months: List[int] = Body(...),
    level: str = Body(...),
    name: str = Body(...),
):
    """
    获取创业团队详情（按收支列分组）
    用于查看详情弹窗中的收入支出科目表格
    根据"收支1"列动态生成收入/支出科目
    """
    _refresh_if_needed()
    if team_df is None or team_df.empty:
        raise HTTPException(500, "团队数据未加载")
    
    # 1. 筛选数据
    df_f = filter_team(team_df, year, months)
    
    # 2. 根据 level 和 name 进一步筛选
    if level == "nature":
        df_f = df_f[df_f["H团队线性质"] == name]
    elif level == "parent":
        df_f = df_f[df_f["H团队线-上级"] == name]
    elif level == "account":
        df_f = df_f[df_f["H团队线-核算"] == name]
    else:
        raise HTTPException(400, f"未知 level: {level}")
    
    if df_f.empty:
        return _ensure_native({"income_items": [], "expense_items": [], "fee": 0})
    
    # 3. 检测金额列
    amt_col = _team_amt_col(df_f)
    
    # 4. 收入科目（收支1 以 "1." 开头）
    income_df = df_f[df_f["收支1"].str.startswith("1.", na=False)]
    income_groups = income_df.groupby("收支1")[amt_col].sum().reset_index()
    income_items = []
    for _, row in income_groups.iterrows():
        income_items.append({
            "科目": str(row["收支1"]),
            "金额": to_wan(row[amt_col]),
        })
    
    # 5. 支出科目（收支1 以 "2." 开头）
    expense_df = df_f[df_f["收支1"].str.startswith("2.", na=False)]
    expense_groups = expense_df.groupby("收支1")[amt_col].sum().reset_index()
    expense_items = []
    for _, row in expense_groups.iterrows():
        expense_items.append({
            "科目": str(row["收支1"]),
            "金额": to_wan(abs(row[amt_col])),  # 支出取绝对值，转换为万元
        })
    
    # 6. 管理费（资金流向 == "管理费"）
    fee_df = df_f[df_f["资金流向"] == "管理费"]
    fee_total = to_wan(abs(fee_df[amt_col].sum())) if not fee_df.empty else 0
    
    return _ensure_native({
        "income_items": income_items,
        "expense_items": expense_items,
        "fee": fee_total,
    })


# ==================== 创业团队分析建议 ====================

@app.get("/api/team/analysis")
def api_team_analysis(year: int, months: str = Query(...)):
    """
    获取创业团队经营分析建议
    按 H团队线-上级 分组，计算各项占比和结余，生成分析建议
    """
    _refresh_if_needed()
    if team_df is None or team_df.empty:
        raise HTTPException(500, "团队数据未加载")
    
    ml = parse_months(months)
    df_f = filter_team(team_df, year, ml)
    
    if df_f.empty:
        return _ensure_native({"teams": [], "suggestions": []})
    
    # 按 H团队线-上级 聚合
    groups = df_f.groupby("H团队线-上级")
    team_records = []
    
    for parent_name, group in groups:
        if pd.isna(parent_name) or str(parent_name).strip() == "":
            continue
        
        inc, exp, fee = _team_calc(group, inc_col="收支1", exp_col="收支1")
        balance = inc - exp - fee
        
        # 计算各项支出占比（如果有部门特殊字段）
        expense_breakdown = {}
        if "部门特殊" in group.columns:
            exp_data = group[
                group["收支1"].str.startswith('2.', na=False) & 
                (group["资金流向"] != "管理费")
            ]
            for special in exp_data["部门特殊"].dropna().unique():
                sp_val = float(exp_data[exp_data["部门特殊"] == special]["金额g" if "金额g" in exp_data.columns else "总计"].sum())
                if exp > 0:
                    expense_breakdown[str(special)] = round(abs(sp_val) / exp * 100, 1)
        
        team_records.append({
            "name": str(parent_name),
            "income": to_wan(inc),
            "expense": to_wan(exp),
            "fee": to_wan(fee),
            "balance": to_wan(balance),
            "expense_breakdown": expense_breakdown,
        })
    
    # 生成分析建议
    suggestions = []
    total_income = sum(r["income"] for r in team_records)
    total_expense = sum(r["expense"] for r in team_records)
    total_balance = sum(r["balance"] for r in team_records)
    
    # 整体分析建议
    if total_balance < 0:
        suggestions.append({
            "type": "warning",
            "title": "整体结余预警",
            "content": f"创业团队整体结余为负（{total_balance:.2f}万元），需重点关注成本管控。"
        })
    
    if total_income > 0 and total_expense / total_income > 0.9:
        suggestions.append({
            "type": "warning",
            "title": "支出占比过高",
            "content": f"支出/收入比达{total_expense/total_income:.0%}，利润空间极小，建议审查成本结构。"
        })
    
    # 各团队分析
    for r in team_records:
        # 支出占比过高
        if r["income"] > 0 and r["expense"] / r["income"] > 0.95:
            suggestions.append({
                "type": "warning",
                "title": f"{r['name']} 支出占比过高",
                "content": f"支出/收入比达{r['expense']/r['income']:.0%}，利润空间极小，建议关注。"
            })
        
        # 结余为负
        if r["balance"] < -50:
            suggestions.append({
                "type": "danger",
                "title": f"{r['name']} 结余为负",
                "content": f"结余为负（{r['balance']:.2f}万元），需重点关注。"
            })
        
        # 支出占比最高的单项
        if r["expense_breakdown"]:
            max_expense = max(r["expense_breakdown"].items(), key=lambda x: x[1], default=(None, 0))
            if max_expense[1] > 30:
                suggestions.append({
                    "type": "info",
                    "title": f"{r['name']} 支出明细提醒",
                    "content": f"\"{max_expense[0]}\" 支出占比达{max_expense[1]}%，建议关注。"
                })
    
    # 按结余排序
    team_records.sort(key=lambda x: x["balance"])
    
    return _ensure_native({
        "teams": team_records,
        "total_income": to_wan(total_income),
        "total_expense": to_wan(total_expense),
        "total_balance": to_wan(total_balance),
        "suggestions": suggestions
    })


# ==================== 创业团队注释 ====================
# 简单使用内存存储，实际生产环境应使用数据库
_team_annotations = {}

@app.get("/api/team/annotations")
def api_get_team_annotations(year: int, months: str = Query(...)):
    """获取团队注释"""
    key = f"{year}_{months}"
    return {"annotations": _team_annotations.get(key, {})}

@app.post("/api/team/annotation")
def api_save_team_annotation(
    year: int = Body(...),
    months: str = Body(...),
    text: str = Body(...),
    team: str = Body(None),
):
    """保存团队注释"""
    import datetime
    key = f"{year}_{months}"
    if key not in _team_annotations:
        _team_annotations[key] = {}
    annotation_key = team or "default"
    _team_annotations[key][annotation_key] = {
        "text": text,
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "team": team
    }
    return {"success": True}


# ==================== 创业团队分析 Tip（可编辑、服务端持久化）====================
import json as _json
import os as _os
from pathlib import Path as _Path

_TIP_FILE = _Path(__file__).resolve().parent / "team_tips.json"

def _load_tips():
    if _TIP_FILE.exists():
        with open(_TIP_FILE, 'r', encoding='utf-8') as f:
            return _json.load(f)
    return {}

def _save_tips(tips: dict):
    _TIP_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_TIP_FILE, 'w', encoding='utf-8') as f:
        _json.dump(tips, f, ensure_ascii=False, indent=2)

@app.get("/api/team/tip")
def api_get_team_tip(team: str = Query(...)):
    """获取某个团队的分析分析 Tip"""
    tips = _load_tips()
    tip = tips.get(team, {})
    return {"team": team, "tip": tip.get("text", ""), "updated_at": tip.get("updated_at", "")}

@app.post("/api/team/tip")
def api_save_team_tip(
    team: str = Body(...),
    text: str = Body(...),
):
    """保存团队分析 Tip（覆盖写入）"""
    import datetime
    tips = _load_tips()
    tips[team] = {
        "text": text,
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    _save_tips(tips)
    return {"success": True, "team": team}


# ==================== AI 智能分析（DeepSeek）====================

@app.post("/api/team/ai_analysis")
def api_team_ai_analysis(
    year: int = Body(...),
    months: List[int] = Body(...),
    team_name: str = Body(...),
):
    """
    AI 智能分析 - 基于 DeepSeek 从企业决策层角度分析团队经营
    分析要点：收入构成、扩大销售、经营建议（不提资金缺口/管理费）
    支出参考"说明/备注"列提供业务背景
    """
    _refresh_if_needed()
    if team_df is None or team_df.empty:
        raise HTTPException(500, "团队数据未加载")

    # 筛选该团队数据（按年月）
    df_f = filter_team(team_df, year, months)

    # 匹配团队（H团队线-核算 > H团队线-上级 > H团队线性质）
    matched = pd.DataFrame()
    match_cols = ["H团队线-核算", "H团队线-上级", "H团队线性质"]
    for col in match_cols:
        if col in df_f.columns:
            m = df_f[df_f[col] == team_name]
            if not m.empty:
                matched = m
                break

    if matched.empty:
        return _ensure_native({"analysis": [], "error": f"未找到 {team_name} 的数据", "fallback": True})

    # 收支列名兼容
    inc_col = next((c for c in ["收支", "部门收支", "收支1"] if c in matched.columns), matched.columns[0])
    amt_col = _team_amt_col(matched)

    # 收入计算（数值为负 => 取绝对值）
    inc_mask = (matched[inc_col] == "一、收入") if inc_col in matched.columns else pd.Series(False, index=matched.index)
    inc = float(abs(matched.loc[inc_mask, amt_col].sum())) if inc_mask.any() else 0.0

    # 支出计算（不含管理费，取绝对值）
    exp_mask = (matched[inc_col] == "二、支出") if inc_col in matched.columns else pd.Series(False, index=matched.index)
    exp = float(abs(matched.loc[exp_mask, amt_col].sum())) if exp_mask.any() else 0.0

    # 管理费
    fee_mask = (matched[inc_col] == "三、管理费") if inc_col in matched.columns else pd.Series(False, index=matched.index)
    fee = float(abs(matched.loc[fee_mask, amt_col].sum())) if fee_mask.any() else 0.0

    balance = inc - exp - fee
    bal_rate = round(balance / inc * 100, 1) if inc else 0

    # 收入构成（用"部门特殊"列分组）
    income_items = []
    inc_data = matched[inc_mask].copy() if inc_mask.any() else pd.DataFrame()
    if not inc_data.empty:
        group_col = "部门特殊" if "部门特殊" in inc_data.columns else inc_col
        for grp_name, grp in inc_data.groupby(group_col):
            val = float(abs(grp[amt_col].sum()))
            if val >= 5:  # 忽略极小项
                income_items.append({"name": str(grp_name), "value": round(to_wan(val), 2)})
    income_items.sort(key=lambda x: x["value"], reverse=True)

    # 支出构成 + 说明/备注
    expense_items = []
    expense_notes = []
    exp_data = matched[exp_mask].copy() if exp_mask.any() else pd.DataFrame()
    if not exp_data.empty:
        group_col = "部门特殊" if "部门特殊" in exp_data.columns else inc_col
        for grp_name, grp in exp_data.groupby(group_col):
            val = float(abs(grp[amt_col].sum()))
            pct = round(val / exp * 100, 1) if exp else 0
            if val >= 5:
                expense_items.append({"name": str(grp_name), "value": round(to_wan(val), 2), "pct": pct})
        # 提取说明/备注
        if "说明/备注" in matched.columns:
            notes_series = matched["说明/备注"].dropna()
            expense_notes = [str(n).strip() for n in notes_series.unique() if str(n).strip() and str(n).strip().lower() != "nan"]
    expense_items.sort(key=lambda x: x["value"], reverse=True)

    # 调用 AI
    try:
        api_key = _os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            return _ensure_native(_fallback_ai_analysis(
                team_name, to_wan(inc), to_wan(exp), to_wan(fee), to_wan(balance),
                income_items, expense_items, expense_notes
            ))

        from openai import OpenAI
        import json as _j

        income_str = _j.dumps(income_items[:5], ensure_ascii=False) if income_items else "暂无明细"
        expense_str = _j.dumps(expense_items[:5], ensure_ascii=False) if expense_items else "暂无明细"
        notes_str = "；".join(expense_notes[:10]) if expense_notes else "无备注信息"

        # 团队专属上下文注入
        team_context_map = {
            "07.上京和园": (
                "背景说明：07.上京和园是公司为未来开展长护险业务布局的前瞻性项目，"
                "不要质疑该团队存在的必要性。当前无收入属业务筹备期正常状态。"
                "支出中的房租/能源类费用主要为房产税、物业费、维修等持有物业的必要支出。"
                "分析时可结合长护险在天津的落地政策和推进进度来评估项目的战略价值和时间窗口。"
            ),
            "上京和园": (
                "背景说明：上京和园是公司为未来开展长护险业务布局的前瞻性项目，"
                "不要质疑该团队存在的必要性。当前无收入属业务筹备期正常状态。"
                "支出中的房租/能源类费用主要为房产税、物业费、维修等持有物业的必要支出。"
                "分析时可结合长护险在天津的落地政策和推进进度来评估项目的战略价值和时间窗口。"
            ),
        }
        team_context = team_context_map.get(team_name, "")
        NL = "\n"

        prompt = f"""你是一位资深企业财务顾问。请从企业决策层角度对团队做简要经营分析。

## 当前团队
{team_name}

## 核心经营数据
- 收入: {to_wan(inc):.2f} 万元
- 支出: {to_wan(exp):.2f} 万元
- 净结余: {to_wan(balance):.2f} 万元
- 结余率: {bal_rate}%

## 收入构成 (TOP)
{income_str}

## 支出构成 (TOP)
{expense_str}

## 支出相关说明/备注
{notes_str}
{f"{NL}## 团队专属背景{NL}{team_context}" if team_context else ""}

## 分析要求
从企业决策者视角给出最多3条简洁分析，严格遵守：
1. 可从收入构成、扩大销售、经营改善等角度分析
2. 可结合"说明/备注"理解支出发生的业务背景
3. 绝对不要出现"资金缺口""管理费""毛利偏低""毛利不足""毛利率低""毛利差"这些词，也不要做毛利相关结论
4. 不要说"是否有必要存在""存在价值""是否合理"这类质疑团队存在性的表述
5. 每条≤80字，精炼直接，直面问题
6. 不带序号编号，每条独立成段落

## 输出格式（纯JSON，不带markdown标记）
{{"items":["分析内容1","分析内容2","分析内容3"]}}"""

        client = OpenAI(
            base_url="https://api.deepseek.com/v1",
            api_key=api_key,
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一位资深企业财务顾问。请严格按JSON格式回复，不要输出任何其他内容。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800,
        )
        content = response.choices[0].message.content.strip()

        # 清理 markdown 包装
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        result = _j.loads(content)
        items = result.get("items", [])

        return _ensure_native({
            "analysis": items[:3],
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fallback": False,
            "income_items": income_items[:5],
            "expense_items": expense_items[:5],
            "expense_notes": expense_notes[:5],
        })

    except Exception as e:
        print(f"[AI Analysis] Error: {e}")
        return _ensure_native(_fallback_ai_analysis(
            team_name, to_wan(inc), to_wan(exp), to_wan(fee), to_wan(balance),
            income_items, expense_items, expense_notes
        ))


def _fallback_ai_analysis(team_name, inc_w, exp_w, fee_w, bal_w, income_items, expense_items, notes):
    """规则引擎兜底分析（AI 不可用时使用）"""
    items = []
    bal_rate = round(bal_w / inc_w * 100, 1) if inc_w else 0

    # 1. 收入构成
    if income_items:
        top = income_items[0]
        items.append(f"收入以{top['name']}为主（{top['value']}万元），建议在稳固核心业务同时拓展高附加值服务，提升收入多元化水平。")
    else:
        items.append(f"当前营收{inc_w:.1f}万元，建议分析各业务线盈利贡献，优化资源配置以扩大营收规模。")

    # 2. 支出优化
    if expense_items:
        top_e = expense_items[0]
        note_hint = ""
        if notes:
            note_hint = "，结合备注信息"
        items.append(f"支出中{top_e['name']}占比较高（{top_e.get('pct', 0)}%）{note_hint}，建议核查该项费用合理性，寻找节支提效空间。")
    else:
        items.append("建议建立支出明细台账，定期审查各项成本合理性，推行节支提效措施。")

    # 3. 经营建议
    if bal_rate > 10:
        items.append(f"结余率{bal_rate}%表现良好，可适当加大市场拓展投入，通过扩大销售规模进一步提升盈利水平。")
    elif bal_rate > 0:
        items.append(f"结余率{bal_rate}%，具备一定盈利基础，建议优化收入结构并适度投入营销资源以加速业绩增长。")
    else:
        items.append("建议聚焦收入增长，通过拓展服务品类、扩大客群覆盖和提升复购率来驱动业务规模增长。")

    return {
        "analysis": items[:3],
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fallback": True,
        "income_items": income_items[:5] if income_items else [],
        "expense_items": expense_items[:5] if expense_items else [],
        "expense_notes": notes[:5] if notes else [],
    }


# ==================== 创业团队经营明细透视（pivot_flat）====================

@app.post("/api/team/pivot_flat")
def api_team_pivot_flat(
    year: int = Body(...),
    months: List[int] = Body(...),
    team_name: str = Body(...),
):
    """
    获取创业团队经营明细透视表（按收支科目分月）
    返回收入、支出、管理费三级结构+结余+同比+占比
    """
    _refresh_if_needed()
    if team_df is None or team_df.empty:
        raise HTTPException(500, "团队数据未加载")

    result = get_team_compressed_table(team_df, team_name, year, months)
    return _ensure_native(result)


# ==================== 智能问答 ====================

@app.post("/api/tool/query")
def tool_query(question: str = Body(...), year: int = Body(2026), months: str = Body("1,2,3")):
    _refresh_if_needed()
    ml = parse_months(months)
    ql = question.lower()

    # 模式1: 结余率低于/不足/小于
    m = re.search(r"结余率.*(低于|不足|小于)\s*(\d+)%", ql)
    if m:
        threshold = int(m.group(2))
        df_f = filter_product(product_df, year, ml)
        boards = aggregate_board(df_f)
        boards["结余率"] = (boards["结余"] / boards["收入"].replace(0, float("nan"))) * 100
        low = boards[boards["结余率"] < threshold]
        
        # 构建规范化的数据记录
        columns = ["板块", "结余率", "结余(万)"]
        records = []
        for _, row in low.iterrows():
            record = {
                "板块": str(row.get("业务板块", "")) if pd.notna(row.get("业务板块")) else "",
                "结余率": round(row.get("结余率", 0), 2) if pd.notna(row.get("结余率")) else 0,
                "结余(万)": round(to_wan(row.get("结余", 0)), 2) if pd.notna(row.get("结余")) else 0,
            }
            records.append(record)
        
        return _ensure_native({
            "type": "table",
            "question": question,
            "columns": columns,
            "data": records,
        })

    # 模式2: 收入/支出最高/最低/增长最快
    m = re.search(r"(收入|支出).*(最高|最低|增长最快)", ql)
    if m:
        metric = m.group(1)
        direction = m.group(2)
        df_f = filter_product(product_df, year, ml)
        agg = aggregate_product(df_f)
        col = "收入" if metric == "收入" else "支出"
        if "增长" in direction:
            df_prev = filter_product(product_df, year - 1, ml)
            prev_agg = aggregate_product(df_prev)
            merged = agg.merge(prev_agg[["产品", col]], on="产品", suffixes=("", "_prev"))
            merged[f"{col}增长"] = merged[col] - merged[f"{col}_prev"]
            merged[f"{col}增长pct"] = merged[f"{col}增长"] / merged[f"{col}_prev"].replace(0, float("nan")) * 100
            top = merged.nlargest(5, f"{col}增长pct")
            
            # 构建规范化的数据记录
            columns = ["产品", f"本期{metric}(万)", f"去年同期(万)", "增长率"]
            records = []
            for _, row in top.iterrows():
                record = {
                    "产品": str(row.get("产品", "")) if pd.notna(row.get("产品")) else "",
                    f"本期{metric}(万)": round(to_wan(row.get(col, 0)), 2) if pd.notna(row.get(col)) else 0,
                    f"去年同期(万)": round(to_wan(row.get(f"{col}_prev", 0)), 2) if pd.notna(row.get(f"{col}_prev")) else 0,
                    "增长率": round(row.get(f"{col}增长pct", 0), 1) if pd.notna(row.get(f"{col}增长pct")) else 0,
                }
                records.append(record)
            
            return _ensure_native({
                "type": "table",
                "question": question,
                "columns": columns,
                "data": records,
            })
        else:
            ascending = direction == "最低"
            top = agg.nlargest(5, col) if not ascending else agg.nsmallest(5, col)
            
            # 构建规范化的数据记录
            columns = ["产品", f"{metric}(万)"]
            records = []
            for _, row in top.iterrows():
                record = {
                    "产品": str(row.get("产品", "")) if pd.notna(row.get("产品")) else "",
                    f"{metric}(万)": round(to_wan(row.get(col, 0)), 2) if pd.notna(row.get(col)) else 0,
                }
                records.append(record)
            
            return _ensure_native({
                "type": "table",
                "question": question,
                "columns": columns,
                "data": records,
            })

    # 模式3: 管理费占比
    m = re.search(r"管理费占比超过\s*(\d+)%", ql)
    if m:
        threshold = int(m.group(2))
        df_f = filter_product(product_df, year, ml)
        boards = aggregate_board(df_f)
        boards["管理费占比"] = (boards["平台管理费"] / boards["收入"].replace(0, float("nan"))) * 100
        high = boards[boards["管理费占比"] > threshold]
        
        # 构建规范化的数据记录
        columns = ["板块", "管理费占比"]
        records = []
        for _, row in high.iterrows():
            record = {
                "板块": str(row.get("业务板块", "")) if pd.notna(row.get("业务板块")) else "",
                "管理费占比": round(row.get("管理费占比", 0), 2) if pd.notna(row.get("管理费占比")) else 0,
            }
            records.append(record)
        
        return _ensure_native({
            "type": "table",
            "question": question,
            "columns": columns,
            "data": records,
        })

    # 模式4: 连续亏损
    m = re.search(r"连续.*亏损.*(\d+).*月", ql)
    if m:
        threshold = int(m.group(1))
        alerts = analyze_trends(product_df, year)
        return _ensure_native({
            "type": "table",
            "question": question,
            "columns": ["预警"],
            "data": [{"预警": a} for a in alerts] if alerts else [],
            "answer": "\n".join(alerts) if alerts else "未发现连续亏损超{}个月的板块".format(threshold),
        })

    # 模式5: 收入波动异常
    m = re.search(r"(收入|损益|结余).*波动", ql)
    if m:
        alerts = analyze_trends(product_df, year)
        return _ensure_native({
            "type": "table",
            "question": question,
            "columns": ["预警"],
            "data": [{"预警": a} for a in alerts] if alerts else [],
            "answer": "\n".join(alerts) if alerts else "未发现异常波动",
        })

    # 模式6: 机构医疗/物业/医养等板块关键词
    for board in product_df["业务板块"].dropna().unique():
        if str(board) in question:
            df_f = filter_product(product_df, year, ml)
            detail = df_f[df_f["业务板块"] == board]
            by_prod = aggregate_product(detail)
            
            # 构建规范化的数据记录
            records = []
            for _, row in by_prod.iterrows():
                r = {
                    "产品": str(row.get("产品", "")) if pd.notna(row.get("产品")) else "",
                    "收入(万)": round(to_wan(row.get("收入", 0)), 2) if pd.notna(row.get("收入")) else 0,
                    "支出(万)": round(to_wan(row.get("支出", 0)), 2) if pd.notna(row.get("支出")) else 0,
                    "管理费(万)": round(to_wan(row.get("平台管理费", 0)), 2) if pd.notna(row.get("平台管理费")) else 0,
                    "结余(万)": round(to_wan(row.get("结余", 0)), 2) if pd.notna(row.get("结余")) else 0,
                }
                records.append(r)
            
            return _ensure_native({
                "type": "table",
                "question": question,
                "columns": ["产品", "收入(万)", "支出(万)", "管理费(万)", "结余(万)"],
                "data": records,
            })

    # 创业团队关键词
    if team_df is not None and not team_df.empty:
        for parent in team_df["H团队线-上级"].dropna().unique():
            if str(parent) in question:
                df_f = filter_team(team_df, year, ml)
                detail = df_f[df_f["H团队线-上级"] == parent]
                by_acc = aggregate_team_account(detail)
                
                # 构建规范化的数据记录
                records = []
                for _, row in by_acc.iterrows():
                    r = {
                        "核算单元": str(row.get("核算单元", "")) if pd.notna(row.get("核算单元")) else "",
                        "收入(万)": round(to_wan(row.get("收入", 0)), 2) if pd.notna(row.get("收入")) else 0,
                        "支出(万)": round(to_wan(row.get("支出", 0)), 2) if pd.notna(row.get("支出")) else 0,
                        "管理费(万)": round(to_wan(row.get("平台管理费", 0)), 2) if pd.notna(row.get("平台管理费")) else 0,
                        "结余(万)": round(to_wan(row.get("结余", 0)), 2) if pd.notna(row.get("结余")) else 0,
                    }
                    records.append(r)
                
                return _ensure_native({
                    "type": "table",
                    "question": question,
                    "columns": ["核算单元", "收入(万)", "支出(万)", "管理费(万)", "结余(万)"],
                    "data": records,
                })

    # 模式7: 产品关键词
    for prod in product_df["产品"].dropna().unique():
        if str(prod) in question and len(str(prod)) > 1:
            df_f = filter_product(product_df, year, ml)
            detail = df_f[df_f["产品"] == prod]
            if detail.empty:
                continue
            by_proj = aggregate_project(detail, prod)
            
            # 构建规范化的数据记录
            records = []
            for _, row in by_proj.iterrows():
                r = {
                    "项目": str(row.get("项目", "")) if pd.notna(row.get("项目")) else "",
                    "收入(万)": round(to_wan(row.get("收入", 0)), 2) if pd.notna(row.get("收入")) else 0,
                    "支出(万)": round(to_wan(row.get("支出", 0)), 2) if pd.notna(row.get("支出")) else 0,
                    "管理费(万)": round(to_wan(row.get("平台管理费", 0)), 2) if pd.notna(row.get("平台管理费")) else 0,
                    "结余(万)": round(to_wan(row.get("结余", 0)), 2) if pd.notna(row.get("结余")) else 0,
                }
                records.append(r)
            
            return _ensure_native({
                "type": "table",
                "question": question,
                "columns": ["项目", "收入(万)", "支出(万)", "管理费(万)", "结余(万)"],
                "data": records,
            })

    return _ensure_native({
        "type": "text",
        "question": question,
        "answer": "暂无法识别，请尝试：'结余率低于5%'、'收入最高'、'支出增长最快'、'物业板块详情'、'机构医疗各产品结余'等",
    })


# ==================== 预算对比 ====================

_budget_data = {}
_budget_admin_token = "admin"


@app.post("/api/budget/upload")
async def budget_upload(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(400, f"解析预算文件失败: {e}")
    required = ["月份", "团队", "预算收入", "预算支出"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise HTTPException(400, f"缺少必要列: {missing}")
    _budget_data["raw"] = df.to_dict(orient="records")
    _budget_data["updated"] = {f"{r['月份']}_{r['团队']}": {"预算收入": r["预算收入"], "预算支出": r["预算支出"]} for r in _budget_data["raw"]}
    return {"status": "ok", "rows": len(_budget_data["raw"])}


@app.get("/api/budget/compare")
def budget_compare(
    year: int = Query(2026),
    months: str = Query(""),
    cumulative: bool = Query(True),
):
    """
    预算对比接口
    - months: 逗号分隔的月份列表，如 "1,2,3" 或留空表示全部
    - cumulative: True=累计模式，False=单月模式
    """
    _refresh_if_needed()
    
    # 解析月份参数
    if months and months.strip():
        month_list = [int(x.strip()) for x in months.split(",") if x.strip()]
    else:
        month_list = list(range(1, 13))
    
    # 累计模式：汇总1到所选最大月的累计数据
    if cumulative and month_list:
        max_month = max(month_list)
        cumulative_months = list(range(1, max_month + 1))
    else:
        cumulative_months = month_list
    
    # 优先方案1: 从Excel的预算Sheet读取数据
    try:
        budget_from_sheet = get_budget_comparison_data(product_df, team_df, year, cumulative_months)
        if budget_from_sheet and len(budget_from_sheet) > 0:
            # 按团队汇总
            team_totals = {}
            for item in budget_from_sheet:
                team = item["团队"]
                if team not in team_totals:
                    team_totals[team] = {
                        "实际收入": 0, "预算收入": 0,
                        "实际支出": 0, "预算支出": 0,
                    }
                team_totals[team]["实际收入"] += item["实际收入"]
                team_totals[team]["预算收入"] += item["预算收入"]
                team_totals[team]["实际支出"] += item["实际支出"]
                team_totals[team]["预算支出"] += item["预算支出"]
            
            # 计算汇总达成率
            result = []
            for team, totals in team_totals.items():
                inc_ach = round(totals["实际收入"] / totals["预算收入"] * 100, 1) if totals["预算收入"] else None
                exp_ach = round(totals["实际支出"] / totals["预算支出"] * 100, 1) if totals["预算支出"] else None
                result.append({
                    "月份": f"1-{max_month}" if cumulative else ",".join(map(str, cumulative_months)),
                    "团队": team,
                    "实际收入": to_wan(totals["实际收入"]),
                    "预算收入": to_wan(totals["预算收入"]),
                    "收入达成率": inc_ach,
                    "实际支出": to_wan(totals["实际支出"]),
                    "预算支出": to_wan(totals["预算支出"]),
                    "支出达成率": exp_ach,
                })
            
            # 按月份分组显示
            monthly_data = {}
            for item in budget_from_sheet:
                month = item["月份"]
                if month not in monthly_data:
                    monthly_data[month] = {}
                team = item["团队"]
                if team not in monthly_data[month]:
                    monthly_data[month][team] = {
                        "实际收入": 0, "预算收入": 0,
                        "实际支出": 0, "预算支出": 0,
                    }
                monthly_data[month][team]["实际收入"] += item["实际收入"]
                monthly_data[month][team]["预算收入"] += item["预算收入"]
                monthly_data[month][team]["实际支出"] += item["实际支出"]
                monthly_data[month][team]["预算支出"] += item["预算支出"]
            
            # 合并月度明细和汇总
            all_rows = []
            for month in sorted(monthly_data.keys()):
                for team, totals in monthly_data[month].items():
                    inc_ach = round(totals["实际收入"] / totals["预算收入"] * 100, 1) if totals["预算收入"] else None
                    exp_ach = round(totals["实际支出"] / totals["预算支出"] * 100, 1) if totals["预算支出"] else None
                    all_rows.append({
                        "月份": month,
                        "团队": team,
                        "实际收入": to_wan(totals["实际收入"]),
                        "预算收入": to_wan(totals["预算收入"]),
                        "收入达成率": inc_ach,
                        "实际支出": to_wan(totals["实际支出"]),
                        "预算支出": to_wan(totals["预算支出"]),
                        "支出达成率": exp_ach,
                    })
            
            # 添加汇总行
            for team, totals in team_totals.items():
                inc_ach = round(totals["实际收入"] / totals["预算收入"] * 100, 1) if totals["预算收入"] else None
                exp_ach = round(totals["实际支出"] / totals["预算支出"] * 100, 1) if totals["预算支出"] else None
                all_rows.append({
                    "月份": f"累计" if cumulative else "合计",
                    "团队": team,
                    "实际收入": to_wan(totals["实际收入"]),
                    "预算收入": to_wan(totals["预算收入"]),
                    "收入达成率": inc_ach,
                    "实际支出": to_wan(totals["实际支出"]),
                    "预算支出": to_wan(totals["预算支出"]),
                    "支出达成率": exp_ach,
                    "isTotal": True,
                })
            
            return _ensure_native({
                "comparison": all_rows,
                "source": "excel_sheet",
                "message": f"从Excel预算Sheet加载了 {len(all_rows)} 条数据（累计模式）"
            })
    except Exception as e:
        print(f"[budget_compare] 从Excel读取预算数据失败: {e}")
    
    # 备选方案2: 使用上传的预算文件数据
    if "raw" not in _budget_data:
        return {"comparison": [], "source": "none", "message": "未找到预算数据，请上传预算Excel或检查Excel中是否有'预算销售'Sheet"}
    
    result = []
    for row in _budget_data["raw"]:
        month = int(row["月份"])
        team = str(row["团队"])
        key = f"{month}_{team}"
        updated = _budget_data.get("updated", {}).get(key, row)

        actual_income = 0
        actual_expense = 0
        if product_df is not None and not product_df.empty:
            pf = product_df[(product_df["年"] == year) & (product_df["月"] == month)]
            matched = pf[pf["业务板块"] == team]
            if matched.empty:
                matched = pf[pf["产品"] == team]
            actual_income = matched["收入"].sum()
            actual_expense = matched["支出"].sum()

        budget_income = updated["预算收入"]
        budget_expense = updated["预算支出"]
        inc_ach = round(actual_income / budget_income * 100, 1) if budget_income else None
        exp_ach = round(actual_expense / budget_expense * 100, 1) if budget_expense else None

        result.append({
            "月份": month, "团队": team,
            "实际收入": to_wan(actual_income), "预算收入": budget_income, "收入达成率": inc_ach,
            "实际支出": to_wan(actual_expense), "预算支出": budget_expense, "支出达成率": exp_ach,
        })
    return _ensure_native({"comparison": result, "source": "uploaded_file", "message": "使用上传的预算文件数据"})


@app.post("/api/budget/update")
def budget_update(token: str, updates: dict):
    if token != _budget_admin_token:
        raise HTTPException(403, "管理员验证失败")
    for key, vals in updates.items():
        if key in _budget_data.get("updated", {}):
            _budget_data["updated"][key].update(vals)
    return {"status": "ok"}


@app.get("/api/budget/info")
def budget_info():
    """
    获取预算数据可用性信息
    """
    # 检查Excel预算Sheet
    has_excel_budget = False
    excel_teams = []
    excel_months = []
    
    try:
        budget_df = load_budget_df()
        if budget_df is not None and not budget_df.empty:
            has_excel_budget = True
            excel_teams = [str(x) for x in sorted(budget_df["团队"].dropna().unique())] if "团队" in budget_df.columns else []
            excel_months = [int(x) for x in sorted(budget_df["月份"].dropna().astype(int).unique())] if "月份" in budget_df.columns else []
    except Exception as e:
        print(f"[budget_info] 检查Excel预算Sheet失败: {e}")
    
    # 检查上传的预算文件
    has_uploaded_budget = "raw" in _budget_data and len(_budget_data["raw"]) > 0
    
    return _ensure_native({
        "has_budget": has_excel_budget or has_uploaded_budget,
        "source": "excel_sheet" if has_excel_budget else ("uploaded_file" if has_uploaded_budget else "none"),
        "excel_sheet": {
            "available": has_excel_budget,
            "teams": excel_teams,
            "months": excel_months
        },
        "uploaded_file": {
            "available": has_uploaded_budget,
            "rows": len(_budget_data.get("raw", []))
        }
    })


@app.get("/api/budget/export")
def budget_export(year: int = 2026):
    """
    导出预算对比数据
    支持从Excel预算Sheet或上传的预算文件导出
    """
    compare = budget_compare(year)
    
    if not compare.get("comparison"):
        raise HTTPException(404, "无预算数据可导出")
    
    output = io.BytesIO()
    df_out = pd.DataFrame(compare["comparison"])
    df_out.to_excel(output, index=False)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=budget_compare_{year}.xlsx"},
    )


# ==================== 增强版智能问答 API ====================

@app.post("/api/ai/query")
def api_ai_query(
    question: str = Body(...),
    year: int = Body(2026),
    months: str = Body("1,2,3"),
):
    """
    增强版智能问答接口（规则匹配 + 数据源直接分析）
    不再调用 AI 大模型
    """
    _refresh_if_needed()
    ml = parse_months(months)
    if not ml:
        ml = [1, 2, 3]
    return enhanced_query(product_df, team_df, question, year, ml)


@app.post("/api/generate_report")
def api_generate_report(
    year: int = Body(2026),
    month: int = Body(3),
):
    """生成延伸阅读简报，返回HTML内容"""
    _refresh_if_needed()
    try:
        from silver_headlines import generate_silver_headlines
        filepath = generate_silver_headlines(year, month)
        with open(filepath, "r", encoding="utf-8") as f:
            html_content = f.read()
        return {"success": True, "html": html_content, "url": f"/reports/{os.path.basename(filepath)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/ai/suggestions")
def api_ai_suggestions(
    year: int = Query(2026),
    months: str = Query("1,2,3"),
):
    """获取 AI 分析建议"""
    _refresh_if_needed()
    ml = parse_months(months)
    return _ensure_native(get_ai_suggestions(product_df, team_df, year, ml))


@app.get("/api/ai/summary")
def api_ai_summary(
    year: int = Query(2026),
    months: str = Query("1,2,3"),
):
    """获取 AI 数据概览"""
    _refresh_if_needed()
    ml = parse_months(months)
    agent = FinancialAgent(product_df, team_df)
    agent.set_context(year, ml)
    return {"summary": agent.get_summary()}


# ==================== 数据导出 API ====================

@app.get("/api/export/board")
def api_export_board(
    year: int = Query(2026),
    months: str = Query("1,2,3"),
):
    """导出板块汇总数据"""
    _refresh_if_needed()
    ml = parse_months(months)
    from api_extensions import export_board_summary
    return _ensure_native(export_board_summary(product_df, year, ml))


@app.get("/api/export/product")
def api_export_product(
    year: int = Query(2026),
    months: str = Query("1,2,3"),
    board: str = Query(None),
):
    """导出产品汇总数据"""
    _refresh_if_needed()
    ml = parse_months(months)
    from api_extensions import export_product_summary
    return _ensure_native(export_product_summary(product_df, year, ml, board))


# ==================== VIP疗程进度管理 API ====================

@app.get("/api/vip/list")
def api_vip_list():
    """获取所有VIP疗程记录"""
    return {"success": True, "data": get_all_vip_records()}

@app.get("/api/vip/summary")
def api_vip_summary():
    """获取VIP疗程汇总信息"""
    return {"success": True, "data": get_vip_summary()}

@app.post("/api/vip/create")
def api_vip_create(
    product: str = Body(...),
    customer_name: str = Body(...),
    start_date: str = Body(...),
    end_date: str = Body(None),
    progress: int = Body(0),
    notes: str = Body(""),
):
    """创建VIP疗程记录"""
    record = create_vip_record(product, customer_name, start_date, end_date, progress, notes)
    return {"success": True, "data": record}

@app.put("/api/vip/update/{record_id}")
def api_vip_update(record_id: int, **kwargs):
    """更新VIP疗程记录"""
    record = update_vip_record(record_id, **kwargs)
    return {"success": True, "data": record}

@app.delete("/api/vip/delete/{record_id}")
def api_vip_delete(record_id: int):
    """删除VIP疗程记录"""
    delete_vip_record(record_id)
    return {"success": True, "message": "删除成功"}

@app.get("/api/vip/products")
def api_vip_products():
    """获取可用的健康管理产品列表（从数据源提取）"""
    _refresh_if_needed()
    if product_df is None or product_df.empty:
        return {"success": True, "data": ["居家照护", "社区养老", "医疗机构", "教育培训", "机构养老"]}
    # 从医养板块提取产品
    yi_product = product_df[product_df["业务板块"] == "医养板块"]["产品"].dropna().unique()
    return {"success": True, "data": sorted([str(p) for p in yi_product])}


# ==================== 前端 ====================

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    html_path = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>前端文件未找到</h1>", status_code=404)


@app.get("/admins", response_class=HTMLResponse)
def serve_admin():
    """管理后台页面"""
    html_path = os.path.join(os.path.dirname(__file__), "frontend", "admins.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>管理后台文件未找到</h1>", status_code=404)
        