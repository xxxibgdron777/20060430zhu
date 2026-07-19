"""
管理简报 API 路由
- GET  /api/briefing         获取简报（优先读缓存）
- POST /api/briefing/refresh  强制重新生成
- GET  /api/briefing/export   导出 Markdown
"""
import datetime
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import List
import io

from briefing_rules import generate_briefing
from briefing_cache import get_cached, save_cache, invalidate_all, get_cache_info

router = APIRouter()

BJT = datetime.timezone(datetime.timedelta(hours=8))


def _parse_months(months: str) -> List[int]:
    if not months or not months.strip():
        return []
    return [int(x) for x in months.split(",") if x.strip()]


@router.get("/api/briefing")
def get_briefing(
    year: int = Query(2026),
    months: str = Query("1,2,3,4,5"),
):
    """获取管理简报（优先缓存）"""
    import main as m
    m._refresh_if_needed()

    ml = _parse_months(months)
    if not ml:
        raise HTTPException(400, "月份参数无效")

    cached = get_cached(year, ml)
    if cached:
        return {**cached, "source": "cache"}

    if m.product_df is None or m.product_df.empty:
        raise HTTPException(500, "数据未加载")

    briefing = generate_briefing(m.product_df, m.team_df, year, ml, ai_polish=True)
    save_cache(year, ml, briefing)

    return {
        "briefing": briefing,
        "generated_at": datetime.datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S"),
        "year": year, "months": ml, "source": "computed",
    }


@router.post("/api/briefing/refresh")
def refresh_briefing(
    year: int = Query(2026),
    months: str = Query("1,2,3,4,5"),
):
    """强制重新生成简报"""
    import main as m
    m._refresh_if_needed()

    ml = _parse_months(months)
    if not ml:
        raise HTTPException(400, "月份参数无效")
    if m.product_df is None or m.product_df.empty:
        raise HTTPException(500, "数据未加载")

    briefing = generate_briefing(m.product_df, m.team_df, year, ml, ai_polish=True)
    save_cache(year, ml, briefing)

    return {
        "briefing": briefing,
        "generated_at": datetime.datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S"),
        "year": year, "months": ml, "source": "refreshed",
    }


@router.get("/api/briefing/export")
def export_briefing(
    year: int = Query(2026),
    months: str = Query("1,2,3,4,5"),
):
    """导出 Markdown"""
    ml = _parse_months(months)
    cached = get_cached(year, ml)
    if not cached:
        raise HTTPException(404, "请先生成简报")

    md = _to_markdown(cached.get("briefing", {}), cached.get("generated_at", ""))
    buf = io.BytesIO(md.encode("utf-8"))
    return StreamingResponse(buf, media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=briefing_{year}_{ml[0]}-{ml[-1]}.md"})


@router.get("/api/briefing/cache_info")
def briefing_cache_info():
    return get_cache_info()


def _to_markdown(b: dict, generated_at: str) -> str:
    lines = [f"# 管理简报\n\n> 生成时间：{generated_at}\n"]
    snap = b.get("snapshot", {})
    lines.append(f"## 一、经营快照\n\n{snap.get('summary', '')}\n")
    lines.append(f"| 指标 | 数值 |\n|------|------|\n| 总收入 | {snap.get('income', 0)}万 |\n| 总支出 | {snap.get('expense', 0)}万 |\n| 总结余 | {snap.get('balance', 0)}万 |\n| 结余率 | {snap.get('rate', 0)}% |\n")

    rz = b.get("red_zone", {})
    lines.append("## 二、红灯区（需立即关注）\n")
    if rz.get("boards"):
        lines.append("### 低结余率板块\n\n| 板块 | 结余率 | 结余(万) |\n|------|--------|----------|")
        for x in rz["boards"]:
            lines.append(f"| {x['name']} | {x['rate']}% | {x['balance']} |")
        lines.append("")
    if rz.get("loss_projects"):
        lines.append("### 亏损项目\n\n| 板块 | 产品 | 项目 | 结余(万) |\n|------|------|------|----------|")
        for x in rz["loss_projects"]:
            lines.append(f"| {x['board']} | {x['product']} | {x['project']} | {x['balance']} |")
        lines.append("")
    if not rz.get("boards") and not rz.get("loss_projects"):
        lines.append("无重大风险项。\n")

    lines.append("## 三、趋势预警\n")
    for w in b.get("trends", []):
        icon = "⚠️" if "decline" in w.get("type", "") else "✅"
        lines.append(f"- {icon} {w.get('message', '')}")
    lines.append("")

    lines.append("## 四、专项洞察\n")
    for ins in b.get("insights", []):
        lines.append(f"### {ins.get('topic', '')}\n\n{ins.get('detail', '')}\n")
        if ins.get("observation"):
            lines.append(f"> {ins['observation']}\n")

    lines.append("## 五、管理行动建议\n")
    for s in b.get("suggestions", []):
        tag = f"【{s.get('priority', '')}】"
        lines.append(f"- {tag} {s.get('suggestion', '')}")
    lines.append("")
    return "\n".join(lines)
