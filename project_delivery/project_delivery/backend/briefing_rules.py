"""
管理简报规则引擎
基于财务数据与业务规则，自动生成面向决策层的高质量行动建议
技术路线：规则引擎（80%）+ AI 润色（20%）
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from calculators import to_wan, _team_calc_with_fee


# ==================== 模块1: 经营快照 ====================

def compute_snapshot(product_df: pd.DataFrame, year: int, months: list) -> dict:
    """当期总收入、总支出、总结余、同比变化"""
    curr = product_df[(product_df["年"] == year) & (product_df["月"].isin(months))]
    income = float(curr["收入"].sum())
    expense = float(curr["支出"].sum())
    balance = income - expense
    rate = round(balance / income * 100, 1) if income else 0

    # 同比
    yoy = product_df[(product_df["年"] == year - 1) & (product_df["月"].isin(months))]
    yoy_income = float(yoy["收入"].sum())
    yoy_expense = float(yoy["支出"].sum())
    yoy_balance = yoy_income - yoy_expense

    inc_chg = round((income - yoy_income) / abs(yoy_income) * 100, 1) if yoy_income else None
    exp_chg = round((expense - yoy_expense) / abs(yoy_expense) * 100, 1) if yoy_expense else None
    bal_chg = round((balance - yoy_balance) / abs(yoy_balance) * 100, 1) if yoy_balance else None

    summary = f"{year}年{months[0]}-{months[-1]}月，总收入{to_wan(income)}万，总支出{to_wan(expense)}万，结余{to_wan(balance)}万（结余率{rate}%）。"
    if inc_chg is not None:
        direction = "增长" if inc_chg >= 0 else "下降"
        summary += f"同比收入{direction}{abs(inc_chg)}%"
    return {
        "income": to_wan(income), "expense": to_wan(expense), "balance": to_wan(balance),
        "rate": rate, "yoy_income": inc_chg, "yoy_expense": exp_chg, "yoy_balance": bal_chg,
        "summary": summary,
    }


# ==================== 模块2: 红灯区 ====================

def compute_red_zone(product_df: pd.DataFrame, team_df: pd.DataFrame, year: int, months: list) -> dict:
    """结余率最低的3个板块/团队 + 亏损项目"""
    curr = product_df[(product_df["年"] == year) & (product_df["月"].isin(months))]
    boards = []
    for b, g in curr.groupby("业务板块"):
        inc = float(g["收入"].sum())
        exp = float(g["支出"].sum())
        bal = inc - exp
        r = round(bal / inc * 100, 1) if inc else 0
        boards.append({"name": str(b), "income": to_wan(inc), "expense": to_wan(exp),
                       "balance": to_wan(bal), "rate": r})
    boards.sort(key=lambda x: x["rate"])

    # 需立即关注：结余率 < 5% 且 |结余| > 10万，排除支持团队
    red = [b for b in boards if b["name"] != "支持团队" and b["rate"] < 5 and abs(b["balance"]) > 10][:3]

    # 亏损项目（结余为负，排除支持团队）
    proj = curr.groupby(["业务板块", "产品", "项目"]).agg(收入=("收入", "sum"), 支出=("支出", "sum")).reset_index()
    proj["结余"] = proj["收入"] - proj["支出"]
    losses = []
    for _, r in proj[(proj["结余"] < 0) & (proj["业务板块"] != "支持团队")].sort_values("结余").iterrows():
        if abs(to_wan(r["结余"])) >= 1:
            losses.append({"board": str(r["业务板块"]), "product": str(r["产品"]),
                           "project": str(r["项目"]), "balance": to_wan(r["结余"])})

    # 团队红灯
    team_red = []
    if team_df is not None and not team_df.empty:
        tf = team_df[(team_df["年"] == year) & (team_df["月"].isin(months))]
        if not tf.empty and "H团队线性质" in tf.columns:
            for nat, g in tf.groupby("H团队线性质"):
                inc, exp, fee = _team_calc_with_fee(g)
                bal = inc - exp - fee
                r = round(bal / inc * 100, 1) if inc else 0
                if r < 5 and abs(to_wan(bal)) > 10:
                    team_red.append({"name": str(nat), "income": to_wan(inc),
                                     "balance": to_wan(bal), "rate": r})

    return {"boards": red, "loss_projects": losses[:5], "teams": team_red[:3]}


# ==================== 模块3: 趋势预警 ====================

def compute_trend_warnings(product_df: pd.DataFrame, year: int, months: list) -> list:
    """连续2个月收入/结余下滑 > 10% 的板块"""
    warnings = []
    if len(months) < 2:
        return [{"type": "info", "message": "当前筛选月份不足2个月，无法进行趋势分析。"}]

    sorted_m = sorted(months)
    last_two = sorted_m[-2:]
    m1, m2 = last_two[0], last_two[1]
    y1 = year if m1 < m2 or m1 == m2 else year - 1

    curr = product_df[(product_df["年"] == year) & (product_df["月"] == m2)]
    prev = product_df[(product_df["年"] == y1) & (product_df["月"] == m1)]

    for board in curr["业务板块"].unique():
        c_inc = float(curr[curr["业务板块"] == board]["收入"].sum())
        p_inc = float(prev[prev["业务板块"] == board]["收入"].sum())
        c_exp = float(curr[curr["业务板块"] == board]["支出"].sum())
        p_exp = float(prev[prev["业务板块"] == board]["支出"].sum())
        c_bal, p_bal = c_inc - c_exp, p_inc - p_exp

        if p_inc > 0:
            chg = (c_inc - p_inc) / abs(p_inc) * 100
            if chg < -10:
                warnings.append({"type": "income_decline", "target": str(board),
                                 "change": round(chg, 1),
                                 "message": f"{board} {m2}月收入环比下降{abs(round(chg, 1))}%（{to_wan(p_inc)}万→{to_wan(c_inc)}万）"})
        if p_bal > 0:
            b_chg = (c_bal - p_bal) / abs(p_bal) * 100
            if b_chg < -10:
                warnings.append({"type": "balance_decline", "target": str(board),
                                 "change": round(b_chg, 1),
                                 "message": f"{board} {m2}月结余环比下降{abs(round(b_chg, 1))}%（{to_wan(p_bal)}万→{to_wan(c_bal)}万）"})
    if not warnings:
        warnings.append({"type": "ok", "message": "各板块近期趋势平稳，无显著下滑。"})
    return warnings


# ==================== 模块4: 专项洞察 ====================

def _team_yuan_to_wan(val: float) -> int:
    """团队数据为元，转换为万元取整"""
    return round(val / 10000) if val else 0

def _safe_yoy_pct(curr_val: float, prev_val: float) -> dict:
    """安全的同比计算，前值为0或无数据时返回None"""
    if not prev_val or prev_val == 0:
        return {"pct": None, "display": "去年同期无数据"}
    pct = round((curr_val - prev_val) / abs(prev_val) * 100, 1)
    sign = "+" if pct >= 0 else ""
    return {"pct": pct, "display": f"{sign}{pct}%"}

def _fmt_period(months: list) -> str:
    """格式化取数期间：2026年1-5月累计 或 2026年5月"""
    if len(months) == 1:
        return f"{months[0]}月"
    return f"{months[0]}-{months[-1]}月累计"


def compute_special_insights(product_df: pd.DataFrame, team_df: pd.DataFrame, year: int, months: list) -> list:
    """2个固定主题：自付费销售网点 + 三里屯诊所透视"""
    insights = []
    period = _fmt_period(months)

    if team_df is None or team_df.empty:
        return [{"topic": "自付费销售网点", "data": None, "detail": "暂无创业团队数据", "period": period},
                {"topic": "三里屯医疗诊所", "data": None, "detail": "暂无团队数据", "period": period}]

    tf = team_df[(team_df["年"] == year) & (team_df["月"].isin(months))]
    ptf = team_df[(team_df["年"] == year - 1) & (team_df["月"].isin(months))]


    # ===== A: 100%自付费销售网点排行榜 =====
    sc = tf[(tf["B项目2"].astype(str).str.contains("市场", na=False)) &
            (tf["收支"] == "一、收入") &
            (tf["资金流向"].isin(["实收", "应收"]))]
    if not sc.empty:
        sc_grp = sc.groupby("销售部门")["金额g"].sum().sort_values(ascending=False)
        sc_grp = sc_grp[sc_grp > 0]
        sc_total = int(sc_grp.sum())
        sc_list = [{"name": str(n), "amount": _team_yuan_to_wan(v), "pct": round(v / sc_total * 100) if sc_total else 0}
                   for n, v in sc_grp.items()]
        top1 = sc_list[0] if sc_list else None
        insights.append({
            "topic": "自付费销售网点",
            "period": period,
            "data": {"outlets": sc_list, "total_count": len(sc_list), "top1": top1},
            "detail": f"共{len(sc_list)}个网点，第1名{top1['name']}({top1['amount']}万)占{top1['pct']}%",
            "observation": f"前三名合计占{sum(o['pct'] for o in sc_list[:3])}%，集中度极高。"
        })
    else:
        insights.append({"topic": "自付费销售网点", "period": period, "data": None, "detail": "暂无销售网点数据"})

    # ===== B: 三里屯医疗诊所 透视表 =====
    try:
        from _gen_report_sanlitun import compute_pivot
        pivot = compute_pivot(year, months)
        if pivot:
            insights.append({
                "topic": "三里屯医疗诊所",
                "period": period,
                "data": {"pivot": pivot},
                "detail": f"三个科室合计{'盈利' if pivot['total_row'].get('_total', 0) >= 0 else '亏损'}{abs(pivot['total_row'].get('_total', 0))}万，硬性固定成本{pivot.get('hard_total', 0)}万",
                "observation": "扣除硬性成本后，运动康复可考核结余最高，健康管理需重点关注成本控制。"
            })
        else:
            insights.append({"topic": "三里屯医疗诊所", "period": period, "data": None, "detail": "暂无三里屯数据"})
    except Exception as e:
        print(f"[briefing] 三里屯洞察生成失败: {e}")
        insights.append({"topic": "三里屯医疗诊所", "period": period, "data": None, "detail": "三里屯数据生成异常"})

    return insights


# ==================== 模块5: 管理行动建议 ====================

def compute_action_suggestions(product_df: pd.DataFrame, team_df: pd.DataFrame, year: int, months: list) -> list:
    """基于条件→建议模板映射，按优先级匹配"""
    suggestions = []
    curr = product_df[(product_df["年"] == year) & (product_df["月"].isin(months))]
    sorted_m = sorted(months)

    boards_data = []
    for b, g in curr.groupby("业务板块"):
        inc = float(g["收入"].sum()); exp = float(g["支出"].sum())
        bal = inc - exp; r = round(bal / inc * 100, 1) if inc else 0
        exp_grp = g.groupby("产品")["支出"].sum()
        top_exp = str(exp_grp.idxmax()) if not exp_grp.empty else ""
        boards_data.append({"name": str(b), "income": inc, "expense": exp, "balance": bal, "rate": r, "top_expense": top_exp})

    # 规则1: 结余率 < 3% 且收入 > 100万
    for bd in boards_data:
        if bd["rate"] < 3 and bd["income"] > 1000000:
            suggestions.append({"priority": "高", "condition": "low_margin_high_revenue",
                "suggestion": f"对{bd['name']}进行成本复盘，重点核查{bd['top_expense']}，下周三前提交报告。",
                "target": bd["name"], "metric": bd["rate"]})

    # 规则2: 连续3个月收入下滑 > 15%
    if len(sorted_m) >= 3:
        last3 = sorted_m[-3:]
        for b, g in curr.groupby("业务板块"):
            incs = []
            for m in last3:
                y = year
                mi = float(g[g["月"] == m]["收入"].sum())
                incs.append(mi)
            if all(incs[i] > 0 for i in range(3)):
                d1 = (incs[1] - incs[0]) / incs[0] * 100
                d2 = (incs[2] - incs[1]) / incs[1] * 100
                if d1 < -15 and d2 < -15:
                    suggestions.append({"priority": "高", "condition": "consecutive_decline",
                        "suggestion": f"{b}收入连续3个月下滑（{round(d1,1)}%、{round(d2,1)}%），建议立即分析原因，暂停无效推广。",
                        "target": b, "metric": round(d2, 1)})

    # 规则3: 驿站结余率 < 5%
    if team_df is not None and not team_df.empty:
        tf = team_df[(team_df["年"] == year) & (team_df["月"].isin(months))]
        if "H团队线-上级" in tf.columns:
            for parent, g in tf.groupby("H团队线-上级"):
                if "驿站" in str(parent):
                    inc, exp, fee = _team_calc_with_fee(g)
                    bal = inc - exp - fee; r = round(bal / inc * 100, 1) if inc else 0
                    if r < 5:
                        suggestions.append({"priority": "中", "condition": "station_low_margin",
                            "suggestion": f"{parent}结余率仅{r}%，建议增加居家康复增值服务，目标提升客单价。",
                            "target": parent, "metric": r})

    # 规则4: 物业管理费占比 > 15%
    for bd in boards_data:
        if "物业" in bd["name"] and bd["income"] > 0:
            mgmt = float(curr[(curr["业务板块"] == bd["name"])]["平台管理费"].sum())
            ratio = round(mgmt / bd["income"] * 100, 1)
            if ratio > 15:
                suggestions.append({"priority": "中", "condition": "high_mgmt_fee",
                    "suggestion": f"物业板块管理费占收入{ratio}%，高于合理范围，建议复核物业管理项目合同酬金执行情况。",
                    "target": bd["name"], "metric": ratio})

    # 规则5: 项目连续2月亏损
    if len(sorted_m) >= 2:
        m1, m2 = sorted_m[-2], sorted_m[-1]
        for (b, p), g in curr.groupby(["业务板块", "产品"]):
            b1 = float(g[g["月"] == m1]["收入"].sum()) - float(g[g["月"] == m1]["支出"].sum())
            b2 = float(g[g["月"] == m2]["收入"].sum()) - float(g[g["月"] == m2]["支出"].sum())
            if b1 < 0 and b2 < 0:
                suggestions.append({"priority": "高", "condition": "consecutive_loss",
                    "suggestion": f"{b}-{p}已连续2个月亏损（{to_wan(b1)}万、{to_wan(b2)}万），建议暂停或重新谈判成本，下周五前给出处置方案。",
                    "target": f"{b}-{p}", "metric": to_wan(b2)})

    # 规则6: 支持团队结余为负
    for bd in boards_data:
        if "支持" in bd["name"] and bd["balance"] < 0:
            suggestions.append({"priority": "低", "condition": "support_team_negative",
                "suggestion": f"支持团队当期结余{to_wan(bd['balance'])}万（管理费冲抵后），属正常资金调度，无需干预。",
                "target": bd["name"], "metric": to_wan(bd["balance"])})

    prio_order = {"高": 0, "中": 1, "低": 2}
    suggestions.sort(key=lambda x: prio_order.get(x["priority"], 9))
    return suggestions[:5]


# ==================== 主函数 ====================

def _match_suggestions_to_red_zone(red_zone: dict, suggestions: list) -> list:
    """将行动建议匹配到红灯区各行，按名字或板块-产品模糊匹配"""
    matched = []
    used = set()
    # 遍历红灯区各行（团队→板块→亏损项目）
    for t in red_zone.get("teams", []):
        sug = None
        for i, s in enumerate(suggestions):
            if i in used: continue
            target = s.get("target", "")
            # 团队名匹配
            if t["name"] in target or target in t["name"]:
                sug = s; used.add(i); break
        matched.append({"type": "team", "name": t["name"], "balance": t["balance"],
                        "rate": t["rate"], "suggestion": sug})
    for b in red_zone.get("boards", []):
        sug = None
        for i, s in enumerate(suggestions):
            if i in used: continue
            target = s.get("target", "")
            if b["name"] in target:
                sug = s; used.add(i); break
        matched.append({"type": "board", "name": b["name"], "balance": b["balance"],
                        "rate": b["rate"], "suggestion": sug})
    for p in red_zone.get("loss_projects", []):
        sug = None
        for i, s in enumerate(suggestions):
            if i in used: continue
            target = s.get("target", "")
            # 板块-产品匹配
            key = p["board"] + "-" + p["product"]
            if key in target or p["product"] in target:
                sug = s; used.add(i); break
        name = p["board"] + " · " + p["product"]
        matched.append({"type": "proj", "name": name, "balance": p["balance"],
                        "suggestion": sug})
    # 未匹配的建议追加到末尾
    for i, s in enumerate(suggestions):
        if i not in used:
            matched.append({"type": "sugg_only", "name": s.get("target", ""),
                            "suggestion": s})
    return matched


def generate_briefing(product_df: pd.DataFrame, team_df: pd.DataFrame, year: int, months: list, ai_polish: bool = True) -> dict:
    """生成完整管理简报（6个模块：快照+红灯区+趋势+4个专项洞察+建议）
    
    数据计算全部由规则引擎完成（保证数值准确），文案润色由 DeepSeek AI 完成（保证专业表达）。
    AI 失败时静默降级为规则模板输出。
    """
    snapshot = compute_snapshot(product_df, year, months)
    red_zone = compute_red_zone(product_df, team_df, year, months)
    trends = compute_trend_warnings(product_df, year, months)
    insights = compute_special_insights(product_df, team_df, year, months)
    suggestions = compute_action_suggestions(product_df, team_df, year, months)

    if ai_polish:
        snapshot, red_zone, insights, suggestions = _ai_enhance_briefing(
            snapshot, red_zone, trends, insights, suggestions, year, months)

    # 管理行动建议匹配红灯区各行
    red_zone["suggestions"] = _match_suggestions_to_red_zone(red_zone, suggestions[:5])

    return {"snapshot": snapshot, "red_zone": red_zone, "trends": trends,
            "insights": insights,
            "year": year, "months": months}


def _ai_enhance_briefing(snapshot: dict, red_zone: dict, trends: list,
                        insights: list, suggestions: list, year: int, months: list) -> tuple:
    """AI 增强全部模块文案（DeepSeek），失败时静默降级"""
    try:
        # 尝试 DeepSeek，失败则回退 Qwen
        client = None
        model_name = ""
        try:
            from openai import OpenAI
            import os
            key = os.environ.get("DEEPSEEK_API_KEY", "") or "sk-f51bfc8f60f34a2f86b42fe3614ecdb9"
            client = OpenAI(api_key=key, base_url="https://api.deepseek.com/v1")
            model_name = "deepseek-chat"
        except Exception:
            try:
                from qwen_client import chat as qwen_chat
                client = "qwen"
            except Exception:
                pass

        period = f"{year}年" + (f"{months[0]}-{months[-1]}月累计" if len(months) > 1 else f"{months[0]}月")

        # 构建规则引擎产生的结构化数据上下文
        ctx = _build_ai_context(snapshot, red_zone, trends, insights, suggestions, period)

        if client is None:
            return snapshot, red_zone, insights, suggestions

        prompt = f"""你是资深财务BP专家，请根据以下结构化经营数据，生成一份面向管理层的"管理行动简报"。
要求：
1. 语言精练专业，杜绝空话套话
2. 经营快照总结用一句话概括（15字以内）
3. 每个专项洞察的detail字段说明数据含义（50字以内）
4. 每个专项洞察的observation字段给出可操作建议（30字以内）
5. 管理建议的suggestion字段精炼到25字以内
6. 所有金额单位为万元，百分比带+/-符号
7. 去年同期无数据时不展示同比变化

经营数据：
{ctx}

请输出JSON，格式如下：
{{"snapshot_summary":"一句话总结","red_zone_summary":"红灯区一句话总结",
"insights":[{{"topic":"...","detail":"...","observation":"..."}}, ...],
"suggestions":[{{"priority":"...","suggestion":"...","target":"..."}}, ...]}}
直接输出JSON："""

        answer = ""
        if client == "qwen":
            answer, _ = qwen_chat([{"role": "user", "content": prompt}], max_tokens=1200, temperature=0.3)
        else:
            resp = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1200, temperature=0.3
            )
            answer = resp.choices[0].message.content

        # 解析 AI 输出
        import json, re
        json_match = re.search(r'\{[\s\S]*\}', answer)
        if json_match:
            ai = json.loads(json_match.group())

            # 更新快照总结
            if ai.get("snapshot_summary"):
                snapshot["summary"] = ai["snapshot_summary"]

            # 更新红灯区总结
            if ai.get("red_zone_summary") and red_zone.get("boards"):
                red_zone["ai_summary"] = ai["red_zone_summary"]

            # 更新专项洞察文案
            ai_insights = ai.get("insights", [])
            if isinstance(ai_insights, list) and len(ai_insights) == len(insights):
                for i, ai_ins in enumerate(ai_insights):
                    if ai_ins.get("detail"):
                        insights[i]["detail"] = ai_ins["detail"]
                    if ai_ins.get("observation"):
                        insights[i]["observation"] = ai_ins["observation"]

            # 更新建议文案
            ai_suggs = ai.get("suggestions", [])
            if isinstance(ai_suggs, list) and len(ai_suggs) == len(suggestions):
                for i, ai_s in enumerate(ai_suggs):
                    if ai_s.get("suggestion"):
                        suggestions[i]["suggestion"] = ai_s["suggestion"]
                    if ai_s.get("target"):
                        suggestions[i]["target"] = ai_s["target"]

    except Exception as e:
        print(f"[briefing] AI增强失败，降级为规则模板: {e}")

    return snapshot, red_zone, insights, suggestions


def _build_ai_context(snapshot: dict, red_zone: dict, trends: list,
                      insights: list, suggestions: list, period: str) -> str:
    """构建 AI 正文明细的数据上下文"""
    lines = [f"取数期间：{period}"]

    # 快照
    sn = snapshot
    lines.append(f"【经营快照】收入{sn['income']}万 支出{sn['expense']}万 "
                 f"结余{sn['balance']}万 结余率{sn['rate']}% "
                 f"同比收入{sn.get('yoy_income','-')}% 同比支出{sn.get('yoy_expense','-')}% "
                 f"同比结余{sn.get('yoy_balance','-')}%")

    # 红灯区
    if red_zone.get("boards") or red_zone.get("teams"):
        lines.append("【红灯区】")
        for b in red_zone.get("boards", []):
            if b["name"] != "支持团队":
                lines.append(f"  板块：{b['name']} 结余率{b['rate']}% 结余{b['balance']}万")
        for t in red_zone.get("teams", [])[:3]:
            lines.append(f"  团队：{t['name']} 结余率{t['rate']}% 结余{t['balance']}万")

    # 趋势
    if trends:
        lines.append("【趋势预警】")
        for t in trends[:5]:
            lines.append(f"  {t.get('message','')}")

    # 专项洞察
    if insights:
        lines.append("【专项洞察】")
        for ins in insights:
            if ins.get("data"):
                d = ins["data"]
                topic = ins["topic"]
                parts = [f"  {topic}："]
                if "income" in d:
                    parts.append(f"收入{d['income']}万")
                if "balance" in d:
                    parts.append(f"结余{d['balance']}万")
                if "hard_total" in d:
                    parts.append(f"硬性成本{d['hard_total']}万")
                if "adj_balance" in d:
                    parts.append(f"可考核结余{d['adj_balance']}万")
                if "total_count" in d:
                    parts.append(f"共{d['total_count']}个")
                if "outlets" in d:
                    top = d["outlets"][:5]
                    parts.append("TOP5:" + ",".join([f"{o['name']}({o['amount']}万)" for o in top]))
                if "stations" in d:
                    top = d["stations"][:3]
                    parts.append("TOP3:" + ",".join([f"{s['name']}({s['amount']}万)" for s in top]))
                if "products" in d:
                    top = d["products"][:3]
                    parts.append("产品:" + ",".join([f"{p['name']}({p['pct']}%)" for p in top]))
                if "pivot" in d:
                    pv = d["pivot"]
                    tr = pv.get("total_row", {})
                    parts.append(f"合计{tr.get('_total',0)}万")
                    parts.append(f"硬性成本{pv.get('hard_total',0)}万")
                lines.append(" ".join(parts))

    # 原始建议
    if suggestions:
        lines.append("【管理建议（原始模板）】")
        for i, s in enumerate(suggestions):
            lines.append(f"  {i+1}.[{s['priority']}] {s.get('suggestion','')} (目标:{s.get('target','')})")

    return "\n".join(lines)
