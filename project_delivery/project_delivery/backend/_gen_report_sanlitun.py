"""三里屯医疗诊所 专项分析报告 生成模块
用法：
  from _gen_report_sanlitun import compute_pivot, generate_html
  data = compute_pivot(year=2026, months=[1,2,3,4,5])
  generate_html(data, output_path="frontend/三里屯_分析报告.html")
"""
import os, json
import pandas as pd

def _resolve_excel():
    """多路径查找管理报表.xlsx（优先项目根目录）"""
    for p in [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "管理报表.xlsx"),  # project_delivery/
        "/app/管理报表.xlsx",
        os.path.join(os.path.dirname(__file__), "管理报表.xlsx"),  # backend/
    ]:
        if os.path.exists(p):
            return p
    return "/app/管理报表.xlsx"

def compute_pivot(year: int, months: list):
    """读 Excel → 筛选三里屯 → 透视表 → 返回 data dict"""
    try:
        raw = pd.read_excel(_resolve_excel(), sheet_name="创业团队", engine="calamine")
    except (ValueError, ImportError):
        raw = pd.read_excel(_resolve_excel(), sheet_name="创业团队")
    raw.columns = [str(c).strip() for c in raw.columns]
    yf = raw[(raw["年"] == year) & (raw["月"].isin(months))]
    st = yf[yf["H团队线-上级"].astype(str).str.contains("健康管理|神经康复|运动康复", na=False)]
    sub_col = "收支1" if "收支1" in st.columns else "部门收支"
    if st.empty:
        return None

    def tw(v):
        return round(v / 10000) if v else 0

    pv = st.pivot_table(values="金额g", index=["收支", sub_col],
                        columns="H团队线-上级", aggfunc="sum", fill_value=0)
    cols = list(pv.columns)
    rows = []
    for (ie, sub), row in pv.iterrows():
        cells = {c: tw(row[c]) for c in cols}
        cells["_type"] = str(ie)
        cells["_sub"] = str(sub) if pd.notna(sub) else ""
        cells["_total"] = tw(row.sum())
        s = str(sub) if pd.notna(sub) else ""
        cells["_hard"] = ("2.7" in s and "房屋" in s) or ("2.8" in s and "折旧" in s)
        rows.append(cells)

    tr = {c: tw(st[st["H团队线-上级"] == c]["金额g"].sum()) for c in cols}
    tr["_total"] = tw(st["金额g"].sum())

    hmsk = st[sub_col].astype(str).str.contains("2.7.*房屋|2.8.*折旧", na=False, regex=True)
    hard = {c: abs(tw(st[(st["H团队线-上级"] == c) & hmsk]["金额g"].sum())) for c in cols}
    adj = {c: tw(st[(st["H团队线-上级"] == c)]["金额g"].sum()) + hard[c] for c in cols}

    return {
        "columns": cols, "rows": rows, "total_row": tr,
        "hard_costs": hard, "hard_total": sum(hard.values()), "adj_balance": adj
    }


def generate_html(year: int, months: list, output_path: str = None):
    """生成独立 HTML 报告文件"""
    data = compute_pivot(year, months)
    if data is None:
        print("[sanlitun] 无数据")
        return

    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "三里屯_分析报告.html")

    cols = data["columns"]
    rows = data["rows"]
    tr = data["total_row"]
    hard = data["hard_costs"]
    adj = data["adj_balance"]

    period = f"{year}年" + (f"{months[0]}-{months[-1]}月" if len(months) > 1 else f"{months[0]}月")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>三里屯医疗诊所 分析报告</title>
<style>
body{{font-family:-apple-system,'PingFang SC',sans-serif;max-width:800px;margin:40px auto;padding:0 20px;color:#1d1d1f}}
h1{{font-size:20px;border-bottom:2px solid #0071e3;padding-bottom:8px}}
table{{width:100%;border-collapse:collapse;font-size:12px;margin:12px 0}}
th{{background:#f5f6f8;padding:6px 10px;text-align:left;border-bottom:2px solid #e4e6ea;font-size:10px;text-transform:uppercase}}
td{{padding:6px 10px;border-bottom:1px solid #f0f0f2}}td.r{{text-align:right}}
tr:nth-child(even) td{{background:#fafbfd}}
.note{{font-size:12px;color:#6e6e73;background:#f8f9fb;padding:12px 16px;border-radius:8px;margin:16px 0}}
</style></head><body>
<h1>三里屯医疗诊所 分析报告</h1>
<p style="color:#6e6e73;font-size:13px">取数期间：{period}</p>
<table><thead><tr><th>行标签</th>"""
    for c in cols:
        html += f"<th class='r'>{c}</th>"
    html += "<th class='r'>总计</th></tr></thead><tbody>"

    for r in rows:
        bg = ' style="background:#fffbf0"' if r.get("_hard") else ""
        html += f"<tr{bg}><td>{('&nbsp;&nbsp;- '+r['_sub']) if r['_sub'] else '<strong>'+r['_type']+'</strong>'}</td>"
        for c in cols:
            html += f"<td class='r'>{r.get(c,0)}</td>"
        html += f"<td class='r'>{r.get('_total',0)}</td></tr>"

    html += '<tr style="font-weight:600;border-top:2px solid #d2d2d7"><td><strong>合计</strong></td>'
    for c in cols:
        html += f"<td class='r'>{tr.get(c,0)}</td>"
    html += f"<td class='r'>{tr.get('_total',0)}</td></tr>"

    html += '<tr style="font-weight:600;color:#0071e3"><td><strong>不扣除硬性成本结余</strong></td>'
    for c in cols:
        html += f"<td class='r'>{adj.get(c,0)}</td>"
    html += "<td class='r'>—</td></tr></tbody></table>"

    html += f'<div class="note"><strong>硬性固定成本合计：{data["hard_total"]}万</strong>（2.7 房屋/物业/能源/网络 + 2.8 折旧），属装修分摊和资产折旧，非日常运营成本。扣除后各科室可考核结余：'
    parts = [f"{c} {adj[c]}万" for c in cols]
    html += '、'.join(parts)
    html += "，建议以此评估各科室实际经营表现。</div>"
    html += f"<p style='font-size:11px;color:#aeaeb2'>生成时间：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}</p>"
    html += "</body></html>"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[sanlitun] 报告已写入 {output_path}")


if __name__ == "__main__":
    generate_html(year=2026, months=[1, 2, 3, 4, 5, 6])
