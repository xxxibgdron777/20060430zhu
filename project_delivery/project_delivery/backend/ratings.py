"""
评分数据库模块 - SQLite
记录用户对 AI 分析建议的评分，用于后续优化建议质量
"""
import sqlite3
import os
import hashlib
from datetime import datetime
from typing import Optional, Dict, List

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ratings.db")


def _get_conn():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL,
            suggestion_id TEXT NOT NULL,
            score INTEGER NOT NULL CHECK(score >= 1 AND score <= 5),
            month TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_rating
        ON ratings(ip_address, suggestion_id, month)
    """)
    conn.commit()
    conn.close()


def submit_rating(ip_address: str, suggestion_id: str, score: int, month: str) -> Dict:
    """
    提交评分
    - ip_address: 用户 IP
    - suggestion_id: 建议内容hash作为唯一ID
    - score: 1-5 分
    - month: YYYYMM 格式
    返回: {"success": bool, "message": str, "already_rated": bool}
    """
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO ratings (ip_address, suggestion_id, score, month) VALUES (?, ?, ?, ?)",
            (ip_address, suggestion_id, score, month)
        )
        conn.commit()
        return {"success": True, "message": "评分提交成功", "already_rated": False}
    except sqlite3.IntegrityError:
        return {"success": False, "message": "您本月已对此建议评过分，无法重复评分", "already_rated": True}
    finally:
        conn.close()


def check_rating(ip_address: str, suggestion_id: str, month: str) -> Optional[int]:
    """
    检查用户是否已对某建议评分
    返回: score (1-5) 或 None（未评分）
    """
    conn = _get_conn()
    row = conn.execute(
        "SELECT score FROM ratings WHERE ip_address = ? AND suggestion_id = ? AND month = ?",
        (ip_address, suggestion_id, month)
    ).fetchone()
    conn.close()
    return row["score"] if row else None


def get_user_ratings(ip_address: str, month: str) -> Dict[str, int]:
    """
    获取用户在指定月份的所有评分
    返回: {suggestion_id: score}
    """
    conn = _get_conn()
    rows = conn.execute(
        "SELECT suggestion_id, score FROM ratings WHERE ip_address = ? AND month = ?",
        (ip_address, month)
    ).fetchall()
    conn.close()
    return {r["suggestion_id"]: r["score"] for r in rows}


def get_suggestion_stats(suggestion_id: str) -> Dict:
    """
    获取某建议的评分统计
    返回: {"count": int, "avg": float, "distribution": {1: n, 2: n, ...}}
    """
    conn = _get_conn()
    rows = conn.execute(
        "SELECT score FROM ratings WHERE suggestion_id = ?",
        (suggestion_id,)
    ).fetchall()
    conn.close()
    if not rows:
        return {"count": 0, "avg": 0, "distribution": {}}
    scores = [r["score"] for r in rows]
    dist = {}
    for s in scores:
        dist[s] = dist.get(s, 0) + 1
    return {
        "count": len(scores),
        "avg": round(sum(scores) / len(scores), 2),
        "distribution": dist
    }


def suggestion_hash(content: str) -> str:
    """生成建议内容的短hash作为ID"""
    return hashlib.md5(content.encode("utf-8")).hexdigest()[:12]


# 启动时初始化
init_db()
