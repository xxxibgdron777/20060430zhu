"""
管理简报缓存管理
- 内存缓存 + 文件持久化
- 缓存失效：管理报表上传新文件 / 用户手动刷新
"""
import json
import os
import datetime
from typing import Optional, Dict

CACHE_DIR = os.path.join(os.path.dirname(__file__), "briefing_cache")
_memory_cache: Dict[str, dict] = {}

BJT = datetime.timezone(datetime.timedelta(hours=8))


def _cache_key(year: int, months: list) -> str:
    return f"{year}_{','.join(map(str, sorted(months)))}"


def _file_path(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = key.replace(",", "_")
    return os.path.join(CACHE_DIR, f"briefing_{safe}.json")


def get_cached(year: int, months: list) -> Optional[dict]:
    key = _cache_key(year, months)
    if key in _memory_cache:
        return _memory_cache[key]
    fp = _file_path(key)
    if os.path.exists(fp):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            _memory_cache[key] = data
            return data
        except Exception:
            pass
    return None


def save_cache(year: int, months: list, briefing: dict):
    key = _cache_key(year, months)
    now = datetime.datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")
    entry = {"briefing": briefing, "generated_at": now, "year": year, "months": months}
    _memory_cache[key] = entry
    try:
        fp = _file_path(key)
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        print(f"[briefing_cache] 文件缓存写入失败: {e}")


def invalidate_all():
    """清除所有缓存（管理报表更新时调用）"""
    global _memory_cache
    _memory_cache = {}
    if os.path.exists(CACHE_DIR):
        for f in os.listdir(CACHE_DIR):
            if f.startswith("briefing_") and f.endswith(".json"):
                try:
                    os.remove(os.path.join(CACHE_DIR, f))
                except Exception:
                    pass
    print("[briefing_cache] 缓存已清除")


def get_cache_info() -> dict:
    return {
        "memory_count": len(_memory_cache),
        "keys": list(_memory_cache.keys()),
    }
