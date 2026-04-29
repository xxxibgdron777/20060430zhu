"""
管理后台 API - 支持对 Excel 三个 Sheet 的增删改查
"""
import pandas as pd
import os
import time
from fastapi import APIRouter, HTTPException, Body, UploadFile, File, Query
from typing import List, Dict, Any, Optional
import json
import tempfile

router = APIRouter(prefix="/api/admin", tags=["admin"])

EXCEL_PATH = os.path.join(os.path.dirname(__file__), "管理报表.xlsx")

# ---------- Excel 内存缓存（避免每次请求重复读文件）----------
_excel_cache: Dict[str, pd.DataFrame] = {}
_cache_mtime: float = 0.0
_CACHE_TTL = 60  # 缓存有效期（秒）

def _get_file_mtime() -> float:
    try:
        return os.path.getmtime(EXCEL_PATH)
    except:
        return 0.0

def load_excel(sheet_name: str, use_cache: bool = True) -> pd.DataFrame:
    """加载指定 Sheet，带内存缓存，只在文件变化时重新读取"""
    global _excel_cache, _cache_mtime

    now = time.time()
    current_mtime = _get_file_mtime()

    # 文件变了 或 缓存过期 → 重新读取
    if (
        not use_cache
        or sheet_name not in _excel_cache
        or _cache_mtime != current_mtime
        or (now - _cache_mtime) > _CACHE_TTL
    ):
        try:
            df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name)
            df = df.reset_index(drop=True)
            _excel_cache[sheet_name] = df
            _cache_mtime = current_mtime
        except Exception as e:
            raise HTTPException(500, f"加载 {sheet_name} 失败: {e}")

    return _excel_cache[sheet_name]

def save_excel(df: pd.DataFrame, sheet_name: str):
    """保存指定 Sheet，保留其他 Sheet 不变"""
    try:
        # 读取所有 sheet
        with pd.ExcelFile(EXCEL_PATH) as xls:
            all_sheets = {}
            for name in xls.sheet_names:
                if name == sheet_name:
                    all_sheets[name] = df
                else:
                    all_sheets[name] = pd.read_excel(xls, sheet_name=name)
        
        # 写回所有 sheet
        with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl') as writer:
            for name, sheet_df in all_sheets.items():
                sheet_df.to_excel(writer, sheet_name=name, index=False)
        
        return True
    except Exception as e:
        raise HTTPException(500, f"保存失败: {e}")

def df_to_dict_list(df: pd.DataFrame, with_index: bool = False) -> List[Dict]:
    """
    DataFrame 转换为字典列表，处理 NaN 值
    with_index=True 时在每条记录中加入 _idx 字段（对应 Excel 真实行号）
    """
    records = []
    for idx, row in df.iterrows():
        record = {}
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                record[col] = None
            elif isinstance(val, (int, float)):
                record[col] = val
            else:
                record[col] = str(val)
        if with_index:
            record["_idx"] = int(idx)
        records.append(record)
    return records

# ==================== 产品 Sheet API ====================

@router.get("/product")
def get_products(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
):
    """
    分页获取产品数据，支持关键词搜索（向后兼容：不传分页参数时返回全部）
    """
    df = load_excel("产品")

    # 关键词搜索过滤
    if keyword:
        kw = keyword.lower()
        mask = pd.Series(False, index=df.index)
        for col in df.columns:
            mask |= df[col].astype(str).str.lower().str.contains(kw, na=False)
        df = df[mask]

    total = len(df)

    # 有分页参数 → 分页返回；无参数 → 返回全部（兼容旧逻辑）
    if page and page_size:
        start = (page - 1) * page_size
        end = start + page_size
        df = df.iloc[start:end]

    return {
        "success": True,
        "data": df_to_dict_list(df, with_index=True),
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@router.post("/product")
def create_product(data: Dict[str, Any] = Body(...)):
    """新增产品数据"""
    df = load_excel("产品")
    
    # 添加新行
    new_row = pd.DataFrame([data])
    df = pd.concat([df, new_row], ignore_index=True)
    
    save_excel(df, "产品")
    return {"success": True, "message": "新增成功"}

@router.put("/product/{index}")
def update_product(index: int, data: Dict[str, Any] = Body(...)):
    """更新产品数据"""
    df = load_excel("产品")
    
    if index < 0 or index >= len(df):
        raise HTTPException(404, "记录不存在")
    
    # 更新数据
    for key, val in data.items():
        if key in df.columns:
            df.at[index, key] = val
    
    save_excel(df, "产品")
    return {"success": True, "message": "更新成功"}

@router.delete("/product/{index}")
def delete_product(index: int):
    """删除产品数据"""
    df = load_excel("产品")
    
    if index < 0 or index >= len(df):
        raise HTTPException(404, "记录不存在")
    
    df = df.drop(index).reset_index(drop=True)
    save_excel(df, "产品")
    return {"success": True, "message": "删除成功"}


# ==================== 创业团队 Sheet API ====================

@router.get("/team")
def get_teams(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
):
    """
    分页获取创业团队数据，支持关键词搜索
    """
    df = load_excel("创业团队")

    if keyword:
        kw = keyword.lower()
        mask = pd.Series(False, index=df.index)
        for col in df.columns:
            mask |= df[col].astype(str).str.lower().str.contains(kw, na=False)
        df = df[mask]

    total = len(df)

    if page and page_size:
        start = (page - 1) * page_size
        end = start + page_size
        df = df.iloc[start:end]

    return {
        "success": True,
        "data": df_to_dict_list(df, with_index=True),
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@router.post("/team")
def create_team(data: Dict[str, Any] = Body(...)):
    """新增创业团队数据"""
    df = load_excel("创业团队")
    
    new_row = pd.DataFrame([data])
    df = pd.concat([df, new_row], ignore_index=True)
    
    save_excel(df, "创业团队")
    return {"success": True, "message": "新增成功"}

@router.put("/team/{index}")
def update_team(index: int, data: Dict[str, Any] = Body(...)):
    """更新创业团队数据"""
    df = load_excel("创业团队")
    
    if index < 0 or index >= len(df):
        raise HTTPException(404, "记录不存在")
    
    for key, val in data.items():
        if key in df.columns:
            df.at[index, key] = val
    
    save_excel(df, "创业团队")
    return {"success": True, "message": "更新成功"}

@router.delete("/team/{index}")
def delete_team(index: int):
    """删除创业团队数据"""
    df = load_excel("创业团队")
    
    if index < 0 or index >= len(df):
        raise HTTPException(404, "记录不存在")
    
    df = df.drop(index).reset_index(drop=True)
    save_excel(df, "创业团队")
    return {"success": True, "message": "删除成功"}


# ==================== 预算对比 Sheet API ====================

@router.get("/budget")
def get_budgets(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
):
    """
    分页获取预算对比数据
    """
    try:
        df = load_excel("预算对比（销售业绩）")
    except:
        return {"success": True, "data": [], "total": 0, "page": 1, "page_size": page_size}

    total = len(df)

    if page and page_size:
        start = (page - 1) * page_size
        end = start + page_size
        df = df.iloc[start:end]

    return {
        "success": True,
        "data": df_to_dict_list(df, with_index=True),
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@router.post("/budget")
def create_budget(data: Dict[str, Any] = Body(...)):
    """新增预算对比数据"""
    try:
        df = load_excel("预算对比（销售业绩）")
    except:
        # 如果 sheet 不存在，创建新的
        df = pd.DataFrame()
    
    new_row = pd.DataFrame([data])
    if df.empty:
        df = new_row
    else:
        df = pd.concat([df, new_row], ignore_index=True)
    
    save_excel(df, "预算对比（销售业绩）")
    return {"success": True, "message": "新增成功"}

@router.put("/budget/{index}")
def update_budget(index: int, data: Dict[str, Any] = Body(...)):
    """更新预算对比数据"""
    df = load_excel("预算对比（销售业绩）")
    
    if index < 0 or index >= len(df):
        raise HTTPException(404, "记录不存在")
    
    for key, val in data.items():
        if key in df.columns:
            df.at[index, key] = val
    
    save_excel(df, "预算对比（销售业绩）")
    return {"success": True, "message": "更新成功"}

@router.delete("/budget/{index}")
def delete_budget(index: int):
    """删除预算对比数据"""
    df = load_excel("预算对比（销售业绩）")
    
    if index < 0 or index >= len(df):
        raise HTTPException(404, "记录不存在")
    
    df = df.drop(index).reset_index(drop=True)
    save_excel(df, "预算对比（销售业绩）")
    return {"success": True, "message": "删除成功"}

@router.post("/import/{sheet_type}")
async def import_data(sheet_type: str, file: UploadFile = File(...)):
    """
    批量导入数据
    从上传的 Excel 文件中读取数据并追加到指定 Sheet
    """
    # 验证文件类型
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "只支持 Excel 文件 (.xlsx, .xls)")
    
    # 根据 sheet_type 确定 Sheet 名称
    sheet_map = {
        'product': '产品',
        'team': '创业团队',
        'budget': '预算对比（销售业绩）'
    }
    
    if sheet_type not in sheet_map:
        raise HTTPException(400, f"不支持的 Sheet 类型: {sheet_type}")
    
    sheet_name = sheet_map[sheet_type]
    
    # 保存上传的文件到临时位置
    tmp_path = None
    try:
        # 读取上传的文件内容
        content = await file.read()
        
        # 使用临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx', mode='wb') as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        # 读取上传的 Excel 文件
        new_df = pd.read_excel(tmp_path)
        
        # 读取现有的 Sheet
        existing_df = load_excel(sheet_name)
        
        # 追加新数据
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        
        # 保存
        save_excel(combined_df, sheet_name)
        
        # 清理临时文件
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        
        return {"success": True, "count": len(new_df), "message": f"成功导入 {len(new_df)} 条数据"}
        
    except Exception as e:
        # 清理临时文件
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(500, f"导入失败: {str(e)}")
