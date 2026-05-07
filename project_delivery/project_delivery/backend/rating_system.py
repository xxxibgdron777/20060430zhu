"""
财务综述 · 经营分析评级系统
SQLite 存储 + AI 自学习分析
"""

import sqlite3
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "ratings.db")


# ==================== 数据库初始化 ====================

def _get_conn():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化评级数据库表"""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT NOT NULL,
                dimension TEXT NOT NULL DEFAULT '综合',
                rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
                comment TEXT DEFAULT '',
                year INTEGER NOT NULL DEFAULT 2026,
                month INTEGER NOT NULL DEFAULT 3,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rating_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT NOT NULL,
                insight_type TEXT NOT NULL,
                content TEXT NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()


# ==================== 评级 CRUD ====================

def submit_rating(
    team_name: str,
    rating: int,
    dimension: str = "综合",
    comment: str = "",
    year: int = 2026,
    month: int = 3
) -> dict:
    """提交评级"""
    conn = _get_conn()
    try:
        # 检查是否已存在同一团队同一维度的评级
        existing = conn.execute(
            "SELECT id FROM ratings WHERE team_name=? AND dimension=? AND year=? AND month=?",
            (team_name, dimension, year, month)
        ).fetchone()
        
        if existing:
            conn.execute(
                "UPDATE ratings SET rating=?, comment=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (rating, comment, existing["id"])
            )
        else:
            conn.execute(
                "INSERT INTO ratings (team_name, dimension, rating, comment, year, month) VALUES (?, ?, ?, ?, ?, ?)",
                (team_name, dimension, rating, comment, year, month)
            )
        conn.commit()
        
        return {"success": True, "team_name": team_name, "rating": rating, "dimension": dimension}
    finally:
        conn.close()


def get_ratings(
    team_name: Optional[str] = None,
    year: int = 2026,
    month: Optional[int] = None
) -> List[dict]:
    """获取评级列表"""
    conn = _get_conn()
    try:
        query = "SELECT * FROM ratings WHERE year=?"
        params = [year]
        
        if team_name:
            query += " AND team_name=?"
            params.append(team_name)
        if month is not None:
            query += " AND month=?"
            params.append(month)
        
        query += " ORDER BY created_at DESC"
        
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_rating_stats(
    year: int = 2026,
    month: Optional[int] = None,
    team_name: Optional[str] = None
) -> dict:
    """获取评级统计"""
    conn = _get_conn()
    try:
        query = "SELECT * FROM ratings WHERE year=?"
        params = [year]
        if month is not None:
            query += " AND month=?"
            params.append(month)
        if team_name:
            query += " AND team_name=?"
            params.append(team_name)
        
        rows = conn.execute(query, params).fetchall()
        
        if not rows:
            return {
                "total": 0,
                "avg_rating": 0,
                "by_team": {},
                "by_dimension": {},
                "distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        
        ratings_data = [dict(r) for r in rows]
        
        by_team = {}
        for r in ratings_data:
            tn = r["team_name"]
            if tn not in by_team:
                by_team[tn] = {"ratings": [], "avg": 0, "count": 0}
            by_team[tn]["ratings"].append(r["rating"])
            by_team[tn]["count"] += 1
        
        for tn in by_team:
            by_team[tn]["avg"] = round(sum(by_team[tn]["ratings"]) / len(by_team[tn]["ratings"]), 2)
        
        by_dim = {}
        for r in ratings_data:
            d = r["dimension"]
            if d not in by_dim:
                by_dim[d] = {"ratings": [], "avg": 0, "count": 0}
            by_dim[d]["ratings"].append(r["rating"])
            by_dim[d]["count"] += 1
        
        for d in by_dim:
            by_dim[d]["avg"] = round(sum(by_dim[d]["ratings"]) / len(by_dim[d]["ratings"]), 2)
        
        dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in ratings_data:
            dist[r["rating"]] = dist.get(r["rating"], 0) + 1
        
        all_ratings = [r["rating"] for r in ratings_data]
        
        return {
            "total": len(ratings_data),
            "avg_rating": round(sum(all_ratings) / len(all_ratings), 2) if all_ratings else 0,
            "by_team": by_team,
            "by_dimension": by_dim,
            "distribution": dist
        }
    finally:
        conn.close()


# ==================== AI 自学习分析 ====================

def generate_ai_rating_insights(
    ratings_data: List[dict],
    team_df: Optional[pd.DataFrame] = None,
    year: int = 2026,
    months: List[int] = None
) -> List[dict]:
    """
    基于评级数据和财务数据，自动生成分析洞察
    
    规则驱动的自学习分析：
    1. 低分团队（<3分）→ 分析结余率/支出结构
    2. 高分团队（>=4分）→ 识别成功因素
    3. 评分波动 → 检测异常
    4. 结合财务数据 → 验证评级合理性
    """
    insights = []
    
    if not ratings_data:
        return insights
    
    if months is None:
        months = [1, 2, 3]
    
    by_team = {}
    for r in ratings_data:
        tn = r.get("team_name", "")
        if tn not in by_team:
            by_team[tn] = []
        by_team[tn].append(r)
    
    for team_name, team_ratings in by_team.items():
        ratings_list = [r["rating"] for r in team_ratings]
        avg_rating = sum(ratings_list) / len(ratings_list)
        
        if avg_rating < 3:
            if team_df is not None and not team_df.empty:
                tf = team_df[(team_df["年"] == year) & (team_df["月"].isin(months))]
                team_data = tf[tf["H团队线-上级"] == team_name]
                
                if not team_data.empty:
                    from calculators import _team_calc
                    inc, exp, fee = _team_calc(team_data)
                    balance = inc - exp - fee
                    
                    if balance < 0:
                        insights.append({
                            "team_name": team_name,
                            "type": "warning",
                            "content": f"团队评级偏低（{avg_rating:.1f}分），且结余为负（{round(balance/10000):.0f}万），建议重点审查成本结构。"
                        })
                    elif inc > 0 and (exp + fee) / inc > 0.95:
                        insights.append({
                            "team_name": team_name,
                            "type": "warning",
                            "content": f"团队评级偏低（{avg_rating:.1f}分），支出/收入比偏高，利润空间有限。"
                        })
                    else:
                        insights.append({
                            "team_name": team_name,
                            "type": "info",
                            "content": f"团队评级偏低（{avg_rating:.1f}分），建议关注经营效率提升。"
                        })
                else:
                    insights.append({
                        "team_name": team_name,
                        "type": "info",
                        "content": f"团队评级偏低（{avg_rating:.1f}分），建议加强经营管理。"
                    })
        
        elif avg_rating >= 4:
            insights.append({
                "team_name": team_name,
                "type": "success",
                "content": f"团队评级优秀（{avg_rating:.1f}分），经营状况良好，可总结最佳实践推广。"
            })
        
        if len(ratings_list) >= 2:
            variance = np.var(ratings_list) if len(ratings_list) > 1 else 0
            if variance > 1.5:
                insights.append({
                    "team_name": team_name,
                    "type": "alert",
                    "content": f"团队评级存在较大波动（方差{variance:.2f}），建议了解近期经营变化。"
                })
        
        comments = [r.get("comment", "") for r in team_ratings if r.get("comment")]
        if comments:
            concern_keywords = ["成本", "支出", "亏损", "风险", "问题", "下降"]
            positive_keywords = ["增长", "盈利", "优秀", "稳定", "提升"]
            
            concerns = [c for c in comments if any(kw in c for kw in concern_keywords)]
            positives = [c for c in comments if any(kw in c for kw in positive_keywords)]
            
            if concerns and avg_rating < 3.5:
                insights.append({
                    "team_name": team_name,
                    "type": "warning",
                    "content": f"评级评论中提及经营问题，建议关注：{'；'.join(concerns[:2])}"
                })
            if positives and avg_rating >= 3.5:
                insights.append({
                    "team_name": team_name,
                    "type": "success",
                    "content": f"评级评论中提及正面表现：{'；'.join(positives[:2])}"
                })
    
    total_avg = sum(
        sum(r["rating"] for r in team_ratings) / len(team_ratings)
        for team_ratings in by_team.values()
    ) / len(by_team) if by_team else 0
    
    insights.append({
        "team_name": "总体",
        "type": "summary",
        "content": f"本期共评级 {len(ratings_data)} 条，涉及 {len(by_team)} 个团队，综合均分 {total_avg:.2f}"
    })
    
    return insights


def get_ai_rating_analysis(
    year: int = 2026,
    month: Optional[int] = None,
    team_df: Optional[pd.DataFrame] = None
) -> dict:
    """获取 AI 评级分析报告"""
    ratings = get_ratings(year=year, month=month)
    
    if not ratings:
        return {
            "has_data": False,
            "message": "暂无评级数据，请先为团队打分",
            "insights": [],
            "stats": get_rating_stats(year=year, month=month)
        }
    
    stats = get_rating_stats(year=year, month=month)
    months_list = [month] if month else list(range(1, 13))
    insights = generate_ai_rating_insights(ratings, team_df, year, months_list)
    
    conn = _get_conn()
    try:
        for insight in insights:
            conn.execute(
                "INSERT INTO rating_insights (team_name, insight_type, content) VALUES (?, ?, ?)",
                (insight["team_name"], insight["type"], insight["content"])
            )
        conn.commit()
    finally:
        conn.close()
    
    return {
        "has_data": True,
        "total_ratings": len(ratings),
        "stats": stats,
        "insights": insights
    }


# ==================== 初始化 ====================

init_db()
