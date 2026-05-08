"""
数据加载模块
数据源: 管理报表.xlsx（与 backend/ 同目录）
Sheet: 产品（1255行）、创业团队（11863行）
"""
import pandas as pd
import os

EXCEL_PATH = os.path.join(os.path.dirname(__file__), "管理报表.xlsx")

def _clean_cols(df):
    df.columns = [str(c).strip() for c in df.columns]
    return df

def load_product_df():
    """加载产品Sheet — 板块/产品/项目/收入/支出/平台管理费"""
    df = pd.read_excel(EXCEL_PATH, sheet_name="产品", engine="calamine")
    df = _clean_cols(df)
    for col in ["年", "月"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["收入", "支出", "平台管理费", "损益"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    # 对字符串列填充空字符串，避免 groupby 产生 NaN 键（不过滤任何行）
    for col in ["业务板块", "产品", "项目"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
    # 规范化：全角括号 "神经康复（含居家）" → 半角 "神经康复(含居家)"
    if "产品" in df.columns:
        df["产品"] = df["产品"].str.replace("（含居家）", "(含居家)", regex=False)
    print(f"[data_loader] 产品Sheet: {len(df)} 行")
    return df

def load_team_df():
    """加载创业团队Sheet — H团队线性质/上级/核算 + 收支/资金流向/金额g"""
    df = pd.read_excel(EXCEL_PATH, sheet_name="创业团队", engine="calamine")
    df = _clean_cols(df)
    for col in ["年", "月"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "金额g" in df.columns:
        df["金额g"] = pd.to_numeric(df["金额g"], errors="coerce").fillna(0)
    # 统一列名：如果已有"部门收支"则直接用，否则从"收支1"重命名
    if "部门收支" not in df.columns and "收支1" in df.columns:
        df.rename(columns={"收支1": "部门收支"}, inplace=True)
    # 如果两个都存在，删除"收支1"避免重复
    if "部门收支" in df.columns and "收支1" in df.columns:
        df.drop(columns=["收支1"], inplace=True)
    print(f"[data_loader] 创业团队Sheet: {len(df)} 行, 列: {list(df.columns)}")
    return df

def get_meta(product_df):
    """返回元数据：年份、月份、板块列表、产品映射"""
    years = [int(x) for x in sorted(product_df["年"].dropna().astype(int).unique())]
    months = [int(x) for x in sorted(product_df["月"].dropna().astype(int).unique())]
    boards = [str(x) for x in sorted(product_df["业务板块"].dropna().unique())]
    products_by_board = {}
    for b in boards:
        products_by_board[b] = [
            str(x) for x in sorted(
                product_df[product_df["业务板块"] == b]["产品"].dropna().unique()
            )
        ]
    return {
        "years": years,
        "months": months,
        "boards": boards,
        "products_by_board": products_by_board,
    }

def filter_product(product_df, year, months):
    return product_df[
        (product_df["年"] == year) & (product_df["月"].isin(months))
    ].copy()

def filter_team(team_df, year, months):
    return team_df[
        (team_df["年"] == year) & (team_df["月"].isin(months))
    ].copy()

def load_budget_df():
    """加载预算Sheet（销售业绩）"""
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name="预算销售", engine="calamine")
        df = _clean_cols(df)
        if df.empty:
            return None
        # 检查是否包含旧版预算对比列结构
        required = ["月份", "预算收入", "预算支出", "实际收入", "实际支出"]
        if not any(c in df.columns for c in required):
            print(f"[data_loader] 预算Sheet 列结构不匹配: {list(df.columns)[:5]}...")
            return None
        for col in required:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        print(f"[data_loader] 预算Sheet: {len(df)} 行")
        return df
    except Exception as e:
        print(f"[data_loader] 预算Sheet未找到: {e}")
        return None

def get_budget_meta():
    """获取预算Sheet的元数据"""
    try:
        df = load_budget_df()
        if df is None or df.empty:
            return {"has_budget": False}
        return {
            "has_budget": True,
            "teams": [str(x) for x in sorted(df["团队"].dropna().unique())] if "团队" in df.columns else [],
            "months": [int(x) for x in sorted(df["月份"].dropna().astype(int).unique())] if "月份" in df.columns else []
        }
    except:
        return {"has_budget": False}


def get_budget_comparison_data(product_df, team_df, year, months):
    """
    从Excel预算Sheet获取预算数据，并与实际数据进行对比
    返回: list of dict with budget and actual data
    """
    budget_df = load_budget_df()
    if budget_df is None or budget_df.empty:
        return None
    
    result = []
    
    # 遍历预算Sheet中的每一行
    for _, row in budget_df.iterrows():
        month = int(row["月份"])
        team = str(row["团队"]) if pd.notna(row["团队"]) else ""
        
        # 跳过非目标月份的预算
        if month not in months:
            continue
        
        budget_income = float(row["预算收入"]) if pd.notna(row["预算收入"]) else 0
        budget_expense = float(row["预算支出"]) if pd.notna(row["预算支出"]) else 0
        
        # 计算实际数据
        actual_income = 0
        actual_expense = 0
        
        if product_df is not None and not product_df.empty:
            # 从产品数据获取实际收入和支出
            pf = product_df[(product_df["年"] == year) & (product_df["月"] == month)]
            
            # 优先匹配业务板块
            matched = pf[pf["业务板块"] == team]
            if matched.empty:
                # 其次匹配产品
                matched = pf[pf["产品"] == team]
            
            if not matched.empty:
                actual_income = matched["收入"].sum()
                actual_expense = matched["支出"].sum()
        
        if team_df is not None and not team_df.empty and actual_income == 0:
            # 如果产品数据没有匹配，尝试从团队数据获取
            tf = team_df[(team_df["年"] == year) & (team_df["月"] == month)]
            
            # 匹配团队上级
            team_matched = tf[tf["H团队线-上级"] == team]
            if not team_matched.empty:
                # 根据列名获取收入和支出
                if "收入" in team_matched.columns:
                    actual_income = team_matched["收入"].sum()
                if "支出" in team_matched.columns:
                    actual_expense = team_matched["支出"].sum()
        
        # 计算达成率
        inc_ach = round(actual_income / budget_income * 100, 1) if budget_income else None
        exp_ach = round(actual_expense / budget_expense * 100, 1) if budget_expense else None
        
        # 计算差异
        income_diff = actual_income - budget_income
        expense_diff = actual_expense - budget_expense
        
        result.append({
            "月份": month,
            "团队": team,
            "实际收入": actual_income,
            "预算收入": budget_income,
            "收入达成率": inc_ach,
            "收入差异": income_diff,
            "实际支出": actual_expense,
            "预算支出": budget_expense,
            "支出达成率": exp_ach,
            "支出差异": expense_diff,
        })
    
    return result if result else None
