"""
AI 智能问答路由 — /api/ai/chat + /api/ai/report
优化: 3轮历史+token截断+相似问题缓存+规则匹配优先
"""
import json, datetime, os, hashlib
from fastapi import APIRouter, Body, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from qwen_client import chat as qwen_chat
from rag_service import retrieve as rag_retrieve

_product_df, _team_df = None, None
_filter_product, _filter_team = None, None
_to_wan, _refresh = None, None

# 缓存: {hash(question+months+year): "answer"}
_answer_cache = {}
_report_cache = {}
MAX_CACHE_SIZE = 50

def _init_refs():
    global _product_df, _team_df, _filter_product, _filter_team, _to_wan, _refresh
    if _product_df is None:
        import main as m
        from calculators import to_wan as _tw
        _product_df, _team_df = m.product_df, m.team_df
        _filter_product, _filter_team = m.filter_product, m.filter_team
        _to_wan = _tw
        _refresh = m._refresh_if_needed

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []
    year: int = 2026
    months: List[int] = [1, 2, 3, 4]
    mode: str = "product"

class ReportRequest(BaseModel):
    year: int = 2026
    months: List[int] = [1, 2, 3, 4]


def _rule_answer(question, year, months, mode):
    """规则匹配优先，命中直接返回，不调用大模型"""
    _init_refs()
    df = _product_df if mode == "product" else _team_df
    if df is None:
        return None
    q = question.strip().lower()
    filtered = _filter_product(df, year, months) if mode == "product" else _filter_team(df, year, months)
    inc_col = "收入" if mode == "product" else "金额g"
    grp_col = "业务板块" if mode == "product" else "H团队线性质"

    if any(w in q for w in ["收入最高", "收入最多"]):
        if grp_col in filtered.columns:
            grp = filtered.groupby(grp_col)[inc_col].sum().sort_values(ascending=False)
            return "当前{0}年{1}-{2}月，**{3}**收入最高，为{4}万元。".format(year, months[0], months[-1], str(grp.index[0]), _to_wan(int(grp.iloc[0])))

    if "结余率" in q and ("低于" in q or "小于" in q):
        if grp_col not in filtered.columns:
            return None
        results = []
        for name, grp in filtered.groupby(grp_col):
            inc = grp[inc_col].sum()
            exp = _get_expense(grp, mode)
            if inc > 0 and (inc - exp) / inc * 100 < 5:
                results.append("{0}（结余率 {1:.1f}%）".format(name, (inc-exp)/inc*100))
        return "结余率低于5%：" + "、".join(results) if results else "所有板块结余率≥5%。"

    if any(w in q for w in ["亏损", "亏", "负结余"]):
        if grp_col not in filtered.columns:
            return None
        results = []
        for name, grp in filtered.groupby(grp_col):
            inc = grp[inc_col].sum()
            exp = _get_expense(grp, mode)
            if inc - exp < 0:
                results.append("{0}（{1}万元）".format(name, _to_wan(int(inc-exp))))
        return "亏损项目：" + "、".join(results) if results else "无亏损项目。"

    return None


def _get_expense(df, mode):
    if mode == "product":
        cols = [c for c in df.columns if c.strip() == "支出" or "支出" in str(c)]
        return int(df[cols[0]].sum()) if cols else 0
    return 0


def _build_fin_summary(mode, year, months):
    """板块级摘要，<250字符"""
    _init_refs()
    if mode == "product" and _product_df is not None:
        df = _filter_product(_product_df, year, months)
        inc = int(df["收入"].sum())
        exp = _get_expense(df, "product")
        bal = inc - exp
        s = "{0}年{1}-{2}月:收入{3}万支出{4}万结余{5}万。".format(year, months[0], months[-1], _to_wan(inc), _to_wan(exp), _to_wan(bal))
        if "业务板块" in df.columns:
            bds = []
            for b, g in df.groupby("业务板块"):
                bi = int(g["收入"].sum())
                be = _get_expense(g, "product")
                bds.append(b + str(_to_wan(bi)) + "/" + str(_to_wan(bi-be)))
            s += ";".join(bds[:5])
        return s[:250]
    return ""


def _cache_key(question, year, months):
    h = hashlib.md5(question.encode() + str(year).encode() + str(months).encode()).hexdigest()
    return h


@router.post("/ai/chat")
def ai_chat(req: ChatRequest):
    """智能问答：缓存→规则→千问"""
    # 0. 缓存命中
    ck = _cache_key(req.message, req.year, req.months)
    if ck in _answer_cache:
        print(f"[缓存命中] {req.message[:30]}")
        return {"answer": _answer_cache[ck], "source": "cache"}

    # 1. 规则匹配
    ans = _rule_answer(req.message, req.year, req.months, req.mode)
    if ans:
        _answer_cache[ck] = ans
        if len(_answer_cache) > MAX_CACHE_SIZE:
            _answer_cache.pop(next(iter(_answer_cache)))
        return {"answer": ans, "source": "rule"}

    # 2. RAG检索（仅保留标题+来源）
    policy_items = rag_retrieve(req.message, k=3)
    policy_ctx = ""
    if policy_items:
        for p in policy_items:
            policy_ctx += p["title"][:80] + "|" + p["source"] + "|" + p["url"] + "\n"

    # 3. 财务摘要（<250字）
    fin_ctx = _build_fin_summary(req.mode, req.year, req.months)

    # 4. 构建精简提示
    system_prompt = "基于数据回答（引用政策标来源）。\n数据:" + fin_ctx + "\n政策:" + policy_ctx
    system_prompt = system_prompt[:1500]

    msgs = [{"role": "system", "content": system_prompt}]
    total_chars = len(system_prompt)

    # 最近3轮，每轮截断200字
    for h in req.history[-6:][-6:]:  # 取最近6条=3轮
        role = h.get("role", "user")
        content = h.get("content", "")[:200]
        msgs.append({"role": role, "content": content})
        total_chars += len(content)

    # 当前问题截断300字
    user_msg = req.message[:300]
    msgs.append({"role": "user", "content": user_msg})
    total_chars += len(user_msg)

    # 成本日志
    est_tokens = total_chars // 4
    print(f"[API成本] /ai/chat ≈{est_tokens}tok 缓存:{len(_answer_cache)}条 政策:{len(policy_items)}条")

    answer, token_info = qwen_chat(msgs, max_tokens=400)

    _answer_cache[ck] = answer
    if len(_answer_cache) > MAX_CACHE_SIZE:
        _answer_cache.pop(next(iter(_answer_cache)))

    return {"answer": answer + "\n\n" + token_info, "source": "qwen", "policy_refs": len(policy_items)}


@router.post("/ai/report")
def ai_report(req: ReportRequest):
    """生成管理层行动报告"""
    _init_refs()
    if _product_df is None:
        raise HTTPException(500, "数据未加载")

    # 缓存命中（同year+months直接返回）
    rpt_key = str(req.year) + "_" + ",".join(map(str, req.months))
    if rpt_key in _report_cache:
        print(f"[缓存命中] /ai/report {rpt_key}")
        return _report_cache[rpt_key]

    df = _filter_product(_product_df, req.year, req.months)
    inc = int(df["收入"].sum())
    exp = _get_expense(df, "product")
    fee = int(df["平台管理费"].sum()) if "平台管理费" in df.columns else 0
    bal = inc - exp - fee
    bal_rate = round(bal / inc * 100, 1) if inc > 0 else 0

    boards = []
    for b, g in df.groupby("业务板块"):
        bi = int(g["收入"].sum())
        be = _get_expense(g, "product")
        bb = bi - be
        br = round(bb / bi * 100, 1) if bi > 0 else 0
        boards.append({"name": str(b), "income": bi, "expense": be, "balance": bb, "rate": br})
    boards.sort(key=lambda x: x["rate"])

    worst = [b for b in boards if b["balance"] < 0][:3]
    worst_str = "；".join([b["name"] + "(" + str(_to_wan(b["balance"])) + "万)" for b in worst]) if worst else "无"

    # 精简数据
    data_text = str(req.year) + "年" + str(req.months[0]) + "-" + str(req.months[-1]) + "月 "
    data_text += "收入" + str(_to_wan(inc)) + "万支出" + str(_to_wan(exp)) + "万结余" + str(_to_wan(bal)) + "万"
    data_text += "率" + str(bal_rate) + "%亏损:" + worst_str
    data_text = data_text[:400]

    # 政策引用（仅标题）
    policy_items = rag_retrieve("养老 物业 餐饮 医疗 经营 管理", k=3)
    policy_ctx = ""
    for p in policy_items:
        policy_ctx += p["title"][:60] + "|" + p["source"] + "|" + p["url"] + "\n"

    prompt = "生成精简行动报告(markdown,##一财务概览##二重点关注##三专项分析(驿站/物业+养老/长护险/居家康复/老干部体检/老年餐桌)##四行动建议(3条+优先级)##五风险预警)。每段≤3句。\n数据:" + data_text + "\n政策:" + policy_ctx

    print(f"[API成本] /ai/report ≈{len(prompt)//4}tok")
    report, token_info = qwen_chat([{"role": "user", "content": prompt[:1500]}], max_tokens=800)

    result = {
        "report": report + "\n\n" + token_info,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_range": str(req.year) + "年" + str(req.months[0]) + "-" + str(req.months[-1]) + "月"
    }
    _report_cache[rpt_key] = result
    return result
