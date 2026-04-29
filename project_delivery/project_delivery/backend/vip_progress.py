"""
VIP疗程进度管理模块
支持管理员在线编辑保存，数据存储在本地JSON文件
"""
import json
import os
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel
from fastapi import HTTPException

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
VIP_DATA_FILE = os.path.join(DATA_DIR, "vip_progress.json")

class VIPRecord(BaseModel):
    """VIP疗程记录模型"""
    id: Optional[int] = None
    product: str  # 健康管理产品
    customer_name: str  # 客户姓名
    start_date: str  # 疗程开始日 (YYYY-MM-DD)
    end_date: Optional[str] = None  # 疗程结束日
    progress: int  # 服务进度 (0-100)
    notes: Optional[str] = ""  # 备注
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

def _ensure_data_dir():
    """确保数据目录存在"""
    os.makedirs(DATA_DIR, exist_ok=True)

def _load_data() -> List[Dict]:
    """加载VIP数据"""
    _ensure_data_dir()
    if not os.path.exists(VIP_DATA_FILE):
        return []
    try:
        with open(VIP_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def _save_data(records: List[Dict]):
    """保存VIP数据"""
    _ensure_data_dir()
    with open(VIP_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

def get_all_vip_records() -> List[Dict]:
    """获取所有VIP疗程记录"""
    return _load_data()

def get_vip_record_by_id(record_id: int) -> Optional[Dict]:
    """根据ID获取VIP记录"""
    records = _load_data()
    for r in records:
        if r.get('id') == record_id:
            return r
    return None

def create_vip_record(product: str, customer_name: str, start_date: str, 
                      end_date: Optional[str] = None, progress: int = 0, 
                      notes: str = "") -> Dict:
    """创建新的VIP疗程记录"""
    records = _load_data()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 生成新ID
    max_id = 0
    for r in records:
        if r.get('id', 0) > max_id:
            max_id = r.get('id', 0)
    new_id = max_id + 1
    
    new_record = {
        "id": new_id,
        "product": product,
        "customer_name": customer_name,
        "start_date": start_date,
        "end_date": end_date,
        "progress": progress,
        "notes": notes,
        "created_at": now,
        "updated_at": now
    }
    records.append(new_record)
    _save_data(records)
    return new_record

def update_vip_record(record_id: int, **kwargs) -> Dict:
    """更新VIP疗程记录"""
    records = _load_data()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for i, r in enumerate(records):
        if r.get('id') == record_id:
            # 更新字段
            for key in ['product', 'customer_name', 'start_date', 'end_date', 'progress', 'notes']:
                if key in kwargs and kwargs[key] is not None:
                    records[i][key] = kwargs[key]
            records[i]['updated_at'] = now
            _save_data(records)
            return records[i]
    
    raise HTTPException(status_code=404, detail=f"未找到ID为{record_id}的记录")

def delete_vip_record(record_id: int) -> bool:
    """删除VIP疗程记录"""
    records = _load_data()
    original_len = len(records)
    records = [r for r in records if r.get('id') != record_id]
    
    if len(records) == original_len:
        raise HTTPException(status_code=404, detail=f"未找到ID为{record_id}的记录")
    
    _save_data(records)
    return True

def get_vip_summary() -> Dict:
    """获取VIP疗程汇总信息"""
    records = _load_data()
    total = len(records)
    completed = len([r for r in records if r.get('progress', 0) >= 100])
    in_progress = len([r for r in records if 0 < r.get('progress', 0) < 100])
    not_started = len([r for r in records if r.get('progress', 0) == 0])
    
    # 按产品分组统计
    by_product = {}
    for r in records:
        product = r.get('product', '未知')
        if product not in by_product:
            by_product[product] = {"total": 0, "completed": 0, "in_progress": 0}
        by_product[product]["total"] += 1
        prog = r.get('progress', 0)
        if prog >= 100:
            by_product[product]["completed"] += 1
        elif prog > 0:
            by_product[product]["in_progress"] += 1
    
    return {
        "total": total,
        "completed": completed,
        "in_progress": in_progress,
        "not_started": not_started,
        "by_product": by_product
    }
