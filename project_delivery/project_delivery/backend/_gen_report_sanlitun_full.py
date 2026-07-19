#!/usr/bin/env python3
"""三里屯医疗诊所 完整版报告生成器（KPI卡片+万后缀+分组行）"""
import os, sys, pandas as pd

EXCEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '管理报表.xlsx')
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '三里屯_分析报告.html')

def generate():
    raw=pd.read_excel(EXCEL, sheet_name='创业团队', engine='calamine')
    raw.columns=[str(c).strip() for c in raw.columns]
    yf=raw[(raw["年"]==2026)&(raw["月"].isin([1,2,3,4,5,6]))]
    st=yf[yf["H团队线-上级"].astype(str).str.contains("健康管理|神经康复|运动康复",na=False)]
    sub_col="收支1" if "收支1" in st.columns else "部门收支"
    def tw(v): return round(v/10000) if v else 0
    pv=st.pivot_table(values="金额g",index=["收支",sub_col],columns="H团队线-上级",aggfunc="sum",fill_value=0)
    cols=list(pv.columns); rows=[]
    for (ie,sub), row in pv.iterrows():
        cells={c:tw(row[c]) for c in cols}
        cells["_type"]=str(ie); cells["_sub"]=str(sub) if pd.notna(sub) else ""
        cells["_total"]=tw(row.sum())
        s=str(sub) if pd.notna(sub) else ""
        cells["_hard"]=("2.7" in s and "房屋" in s) or ("2.8" in s and "折旧" in s)
        rows.append(cells)
    tr={c:tw(st[st["H团队线-上级"]==c]["金额g"].sum()) for c in cols}; tr["_total"]=tw(st["金额g"].sum())
    hmsk=st[sub_col].astype(str).str.contains("2.7.*房屋|2.8.*折旧",na=False,regex=True)
    hard={c:abs(tw(st[(st["H团队线-上级"]==c)&hmsk]["金额g"].sum())) for c in cols}
    hard_total=sum(hard.values())
    adj={c:tw(st[(st["H团队线-上级"]==c)]["金额g"].sum())+hard[c] for c in cols}
    inc_rows=[r for r in rows if "收入" in r.get("_type","")]
    exp_rows=[r for r in rows if "支出" in r.get("_type","")]
    mgr_rows=[r for r in rows if "管理费" in r.get("_type","")]
    inc_total=sum(r.get("_total",0) for r in inc_rows)
    exp_total=-sum(r.get("_total",0) for r in exp_rows)
    mgr_total=-sum(r.get("_total",0) for r in mgr_rows)
    all_exp=exp_total+mgr_total; balance=inc_total-all_exp; net_total=balance+hard_total
    inc_col={c:sum(r.get(c,0) for r in inc_rows) for c in cols}
    exp_col={c:sum(r.get(c,0) for r in exp_rows) for c in cols}
    mgr_col={c:sum(r.get(c,0) for r in mgr_rows) for c in cols}
    all_exp_col={c:exp_col[c]+mgr_col[c] for c in cols}
    bal_col={c:inc_col[c]+all_exp_col[c] for c in cols}
    def w(v): return f"{v}万" if v is not None else "—"
    def fmt_row(r,hm=False):
        hmark=' 🔧' if hm else ''; hcls=' hard' if hm else ''
        s=f'<tr class="sub{hcls}"><td>- {r["_sub"]}{hmark}</td>'
        for c in cols: s+=f'<td class="r">{w(r.get(c,0))}</td>'
        return s+f'<td class="r">{w(r["_total"])}</td></tr>'
    now=pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
    html=f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>三里屯医疗诊所 分析报告</title><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#f0f2f5;color:#1d1d1f;line-height:1.6}}
.wrap{{max-width:900px;margin:0 auto;padding:24px 20px}}
.hd{{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:24px 28px;border-radius:10px 10px 0 0}}
.hd h1{{font-size:20px;font-weight:600}}.hd p{{font-size:12px;color:#a0a0b0;margin-top:3px}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;padding:16px 28px;background:#fff;border-bottom:1px solid #f0f0f0}}
.kpi{{text-align:center;padding:12px 6px;border-radius:8px;background:#fafafa}}
.kpi .v{{font-size:20px;font-weight:700;color:#1890ff}}.kpi .v.red{{color:#f5222d}}.kpi .v.green{{color:#52c41a}}
.kpi .l{{font-size:10px;color:#8c8c8c;margin-top:2px}}
.sec{{background:#fff;margin:12px 0;border-radius:10px;overflow:hidden;border:1px solid #f0f0f0}}
.sec h2{{font-size:14px;font-weight:600;padding:14px 24px;border-bottom:1px solid #f0f0f0;display:flex;align-items:center;gap:8px}}
.sec h2 .dot{{width:8px;height:8px;border-radius:50%;background:#1890ff;display:inline-block}}
.bd{{padding:18px 24px}}table{{width:100%;border-collapse:collapse;font-size:12px;margin:8px 0}}
th{{background:#fafafa;padding:8px 10px;text-align:left;font-weight:600;border-bottom:2px solid #e8e8e8;font-size:11px;color:#595959}}
td{{padding:7px 10px;border-bottom:1px solid #f0f0f0}}tr:hover td{{background:#fafafa}}
.r{{text-align:right}}.r1{{font-weight:600;background:#fafafa}}.r1 td{{border-top:1px solid #e8e8e8}}
.sub td:first-child{{padding-left:28px;color:#595959;font-size:11px}}
.hard td{{background:#fffbf0}}.total td{{font-weight:700;border-top:2px solid #d9d9d9;background:#f5f5f7}}
.adj td{{font-weight:600;color:#0071e3;background:#e6f7ff}}
.note{{font-size:12px;color:#8c8c8c;background:#fafafa;padding:12px 16px;border-radius:8px;margin:10px 0;line-height:1.8}}
.ft{{text-align:center;padding:16px;color:#bfbfbf;font-size:11px}}
@media(max-width:768px){{.kpis{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><div class="wrap">
<div class="hd"><h1>三里屯医疗诊所 分析报告</h1><p>取数期间：2026年1-6月 &nbsp;|&nbsp; 数据源：创业团队 Sheet</p></div>
<div class="kpis">
<div class="kpi"><div class="v">{w(inc_total)}</div><div class="l">收入合计</div></div>
<div class="kpi"><div class="v red">{w(all_exp)}</div><div class="l">支出合计</div></div>
<div class="kpi"><div class="v {"red" if balance<0 else "green"}">{balance:+d}万</div><div class="l">结余</div></div>
<div class="kpi"><div class="v">{w(hard_total)}</div><div class="l">硬性固定成本</div></div></div>
<div class="sec"><h2><span class="dot"></span>科室经营透视表（万元）</h2><div class="bd">
<table><thead><tr><th>行标签</th>'''
    for c in cols: html+=f'<th class="r">{c}</th>'
    html+='<th class="r">总计</th></tr></thead><tbody>'
    html+='<tr class="r1"><td><b>一、收入</b></td>'
    for c in cols: html+=f'<td class="r"><b>{w(inc_col.get(c,0))}</b></td>'
    html+=f'<td class="r"><b>{w(inc_total)}</b></td></tr>'
    for r in inc_rows: html+=fmt_row(r)
    html+='<tr class="r1"><td><b>二、支出</b></td>'
    for c in cols: html+=f'<td class="r"><b>{w(-exp_col.get(c,0))}</b></td>'
    html+=f'<td class="r"><b>{w(exp_total)}</b></td></tr>'
    for r in exp_rows: html+=fmt_row(r,r.get("_hard",False))
    if mgr_rows:
        html+='<tr class="r1"><td><b>三、管理费</b></td>'
        for c in cols: html+=f'<td class="r"><b>{w(-mgr_col.get(c,0))}</b></td>'
        html+=f'<td class="r"><b>{w(mgr_total)}</b></td></tr>'
        for r in mgr_rows: html+=fmt_row(r)
    html+='<tr class="total"><td><b>合计（结余）</b></td>'
    for c in cols: html+=f'<td class="r"><b>{bal_col.get(c,0):+d}万</b></td>'
    html+=f'<td class="r"><b>{balance:+d}万</b></td></tr>'
    html+='<tr class="adj"><td><b>不扣除硬性固定成本结余</b></td>'
    for c in cols: html+=f'<td class="r"><b>{adj.get(c,0):+d}万</b></td>'
    html+=f'<td class="r"><b>{net_total:+d}万</b></td></tr></tbody></table>'
    parts=[f"{c} {adj[c]}万" for c in cols]
    html+=f'<div class="note"><b>硬性固定成本合计：{hard_total}万</b>（2.7 房屋/物业/能源/网络 + 2.8 折旧），属装修分摊和资产折旧，非日常运营成本。扣除后各科室可考核结余：{"、".join(parts)}，建议以此评估各科室实际经营表现。</div>'
    if cols:
        top=max(cols,key=lambda c:adj.get(c,0)); hpct=int(hard_total/max(all_exp,1)*100)
        html+=f'<div class="note">• 扣除硬性固定成本后，<b>{top}</b>可考核结余最高（{adj[top]}万）。硬性固定成本占比支出{hpct}%，属结构性费用，不影响对科室经营效率的判断。</div>'
    html+=f'</div></div><div class="ft">三里屯医疗诊所 分析报告 &nbsp;|&nbsp; 数据均为动态读取 &nbsp;|&nbsp; 生成时间：{now}</div></div></body></html>'
    with open(OUTPUT,'w',encoding='utf-8') as f: f.write(html)
    print(f'[sanlitun-full] {os.path.getsize(OUTPUT):,} bytes')

if __name__=='__main__':
    generate()
