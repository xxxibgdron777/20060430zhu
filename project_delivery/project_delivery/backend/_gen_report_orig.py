# -*- coding: utf-8 -*-
"""国管局1 报告生成器 —— 读服务器Excel，输出与原始报告完全一致的HTML"""
import pandas as pd, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.ticker as mt
from io import BytesIO
import base64, datetime, os

plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

EXCEL = '/app/管理报表.xlsx'
OUTPUT = '/app/frontend/国管局1_分析报告.html'
MTIME_FILE = '/tmp/.report_mtime'

def fmt(n):
    if pd.isna(n) or abs(n) < 0.5: return '0'
    return f'{n:,.0f}'

def to_img(fig):
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=130, bbox_inches='tight', facecolor='#f8f9fa')
    plt.close(fig); buf.seek(0)
    return base64.b64encode(buf.read()).decode()

def load():
    df = pd.read_excel(EXCEL, sheet_name='国管局1', engine='calamine')
    df['y'] = pd.to_numeric(df['年份'], errors='coerce')
    df['m'] = pd.to_numeric(df['月份'], errors='coerce')
    df['amt'] = pd.to_numeric(df['金额'], errors='coerce')
    df = df.dropna(subset=['y','m','amt']).copy()
    df['y'] = df['y'].astype(int); df['m'] = df['m'].astype(int); df['amt'] = df['amt']
    cc = '所项目1' if '所项目1' in df.columns else 'B项目1'
    kc = '科目A' if '科目A' in df.columns else 'A产品线2'
    df[cc] = df[cc].astype(str).str.strip()
    df[kc] = df[kc].astype(str).str.strip()
    return df, cc, kc

def generate():
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    df_all, cc, kc = load()
    year = 2026; months = sorted(df_all[df_all.y==2026].m.unique()); max_m = max(months) if months else 5
    df_now = df_all[(df_all['y']==year)&(df_all['m'].isin(months))]
    total = df_now['amt'].sum()
    years = sorted(df_all['y'].unique())
    fy = [y for y in years if len(df_all[df_all['y']==y]['m'].unique())==12]
    FY, LY = min(fy) if fy else years[0], max(fy) if fy else years[-1]
    cats = sorted(df_all[kc].unique())
    clients = sorted(df_all[cc].unique())
    yr = df_all.groupby('y')['amt'].sum()
    py_same = df_all[(df_all['y']==year-1)&(df_all['m'].isin(months))]['amt'].sum()
    yoy_val = (total - py_same)/py_same if py_same else 0
    cr3_v = df_now.groupby(cc)['amt'].sum().nlargest(3).sum() if cc else 0
    cr3 = cr3_v/total if total>0 else 0

    # ===== Chart 1: 逐月走势 2025 vs 2026 =====
    fig, ax = plt.subplots(figsize=(8.5,3.8))
    m26 = df_all[df_all['y']==2026].groupby('m')['amt'].sum()
    m25 = df_all[df_all['y']==2025].groupby('m')['amt'].sum()
    x = range(1,13)
    v25 = [m25.get(m,0)/10000 for m in x]
    v26 = [m26.get(m,0)/10000 if m <= max_m else None for m in x]
    ax.plot(x, v25, 'o-', color='#8c8c8c', linewidth=1.8, markersize=5, label='2025年', zorder=2)
    ax.plot(x[:max_m], [v for v in v26[:max_m] if v], 's-', color='#1890ff', linewidth=3, markersize=8, label='2026年(已发生)', zorder=4)
    ax.plot(x[max_m:], v25[max_m:], 's--', color='#91d5ff', linewidth=1.5, markersize=5, alpha=0.6, label='2026年(待发生=去年参照)', zorder=1)
    for i in range(max_m):
        if v26[i] and v25[i]>0:
            chg = (v26[i]-v25[i])/v25[i]*100
            ax.annotate(f'{"↑" if chg>0 else "↓"}{abs(chg):.0f}%', (i+1,v26[i]), textcoords="offset points", xytext=(0,12), fontsize=7, ha='center', color='#f5222d' if chg>0 else '#52c41a', fontweight='bold')
    ax.axvline(x=5.5, color='#ff4d4f', linestyle=':', linewidth=1.5, alpha=0.5)
    ax.text(5.7, ax.get_ylim()[1]*0.95, '←已发生 | 待观察→', fontsize=8, color='#ff4d4f')
    ax.set_xticks(x); ax.set_xlabel('月份',fontsize=11); ax.set_ylabel('营收(万元)',fontsize=11)
    ax.set_title('2026年逐月走势 vs 2025同期', fontweight='bold', fontsize=13)
    ax.legend(fontsize=9, loc='upper left'); ax.spines['top'].set_visible(False)
    c1 = to_img(fig)

    # ===== Chart 2: 业务结构（左:2026vs2025柱状 右:2023-2026折线）=====
    colors = ['#5B8FF9','#5AD8A6','#FF9845','#F46649','#9270CA','#269A99']
    fig,(ax2a,ax2b)=plt.subplots(1,2,figsize=(11,4.2))

    # Left: 2026 vs 2025 同期科目对比柱状图
    cat_now = df_now.groupby(kc)['amt'].sum()
    cat_prev2 = df_all[(df_all['y']==year-2)&(df_all['m'].isin(months))].groupby(kc)['amt'].sum() if year-2 in years else pd.Series()
    cat_prev = df_all[(df_all['y']==year-1)&(df_all['m'].isin(months))].groupby(kc)['amt'].sum()
    x = range(len(cats)); w = 0.3
    v26 = [cat_now.get(c,0)/10000 for c in cats]
    v25 = [cat_prev.get(c,0)/10000 for c in cats]
    ax2a.bar([i-w/2 for i in x], v25, w, color='#d9d9d9', label=f'{year-1}年1-{max_m}月', edgecolor='white')
    ax2a.bar([i+w/2 for i in x], v26, w, color='#1890ff', label=f'{year}年1-{max_m}月', edgecolor='white')
    for i in range(len(cats)):
        if v25[i]>0:
            chg = (v26[i]-v25[i])/v25[i]*100
            ax2a.annotate(f'{chg:+.0f}%', (i, max(v26[i],v25[i])), textcoords="offset points", xytext=(0,5), fontsize=8, ha='center', color='#f5222d' if chg>0 else '#52c41a', fontweight='bold')
    ax2a.set_xticks(x); ax2a.set_xticklabels(cats, fontsize=9)
    ax2a.set_ylabel('营收(万元)',fontsize=9); ax2a.set_title(f'{year}vs{year-1}同期·科目对比',fontweight='bold',fontsize=10)
    ax2a.legend(fontsize=8); ax2a.spines['top'].set_visible(False)

    # Right: 2023-2026 同期科目增长轨迹折线图
    compare_years = [y for y in [year-3,year-2,year-1,year] if y in years]
    for i,cat in enumerate(cats):
        vs = []
        for y2 in compare_years:
            v = df_all[(df_all['y']==y2)&(df_all['m'].isin(months))].groupby(kc)['amt'].sum().get(cat,0)/10000
            vs.append(v)
        ax2b.plot(compare_years, vs, 'o-', color=colors[i%6], label=cat, linewidth=2, markersize=5)
    ax2b.set_xticks(compare_years); ax2b.set_ylabel('营收(万元)',fontsize=9)
    ax2b.set_title(f'{compare_years[0]}-{year}同期增长轨迹',fontweight='bold',fontsize=10)
    ax2b.legend(fontsize=7,ncol=3); ax2b.spines['top'].set_visible(False)
    plt.tight_layout(); c2 = to_img(fig)

    # ===== Chart 3: 客户动向 =====
    cl26 = df_now.groupby(cc)['amt'].sum().sort_values(ascending=False)
    cl25 = df_all[(df_all['y']==2025)&(df_all['m'].isin(months))].groupby(cc)['amt'].sum()
    comp = []
    for cl in clients:
        v26 = cl26.get(cl,0); v25 = cl25.get(cl,0)
        if v26>5000 or v25>10000: comp.append((cl,v26,v25,(v26-v25)/v25*100 if v25>0 else 0, v26-v25))
    comp.sort(key=lambda x:x[4], reverse=True)
    top20 = comp[:20]
    fig,ax3=plt.subplots(figsize=(9,4.5))
    names = [c.replace('国管局-','') for c,_,_,_,_ in top20]
    vals = [v26/10000 for _,v26,_,_,_ in top20]
    diffs = [d/10000 for _,_,_,_,d in top20]
    colors_bar = ['#1890ff' if d>0 else '#f5222d' for d in diffs]
    ax3.barh(range(len(names)), vals, color=colors_bar, edgecolor='white', height=0.7)
    for i,(_,v26,v25,chg,diff) in enumerate(top20):
        ax3.text(v26/10000+1, i, f'{v26/10000:.1f}万 ({"+" if diff>0 else ""}{diff/10000:.1f}万)', va='center', fontsize=8, fontweight='bold', color='#1890ff' if diff>0 else '#f5222d')
    ax3.set_yticks(range(len(names))); ax3.set_yticklabels(names,fontsize=7); ax3.invert_yaxis()
    ax3.set_xlabel(f'2026年1-{max_m}月营收(万元)',fontsize=10)
    ax3.set_title('客户同比变化 TOP20',fontweight='bold',fontsize=12)
    ax3.spines['top'].set_visible(False)
    plt.tight_layout(); c3 = to_img(fig)

    # ===== Chart 4: 季度热力 =====
    sz = df_all[df_all['y'].isin(fy)].copy()
    sz['Q'] = sz['m'].apply(lambda m: 'Q1' if m<=3 else ('Q2' if m<=6 else ('Q3' if m<=9 else 'Q4')))
    qy = sz.groupby(['y','Q'])['amt'].sum().reset_index()
    qp = qy.pivot_table(index='y',columns='Q',values='amt',fill_value=0)
    qpct = qp.div(qp.sum(axis=1),axis=0)*100
    fig,ax4=plt.subplots(figsize=(8,3.5))
    ax4.imshow(qpct.values.T, cmap='YlOrRd', aspect='auto')
    for i in range(len(qpct.columns)):
        for j in range(len(qpct.index)):
            v=qpct.iloc[j,i]; cl='white' if v>55 else 'black'
            ax4.text(j,i,f'{v:.1f}%',ha='center',va='center',fontsize=10,fontweight='bold',color=cl)
    ax4.set_xticks(range(len(qpct.index))); ax4.set_xticklabels([str(y) for y in qpct.index],fontsize=10)
    ax4.set_yticks(range(len(qpct.columns))); ax4.set_yticklabels(qpct.columns.tolist(),fontsize=10)
    ax4.set_title('历年季度营收占比热力图(%)',fontweight='bold',fontsize=12)
    plt.tight_layout(); c4 = to_img(fig)

    # ===== Chart 5: 月度轨迹 =====
    mo = sz.groupby(['y','m'])['amt'].sum().reset_index()
    mp = mo.pivot_table(index='y',columns='m',values='amt',fill_value=0)
    fig,ax5=plt.subplots(figsize=(8.5,3))
    for yl,cl,al,st,lw in [(2024,'#d9d9d9',0.4,'-',1),(2025,'#8c8c8c',0.7,'-',2),(2026,'#1890ff',1,'o-',3)]:
        d = df_all[df_all['y']==yl].groupby('m')['amt'].sum()
        xs = sorted(d.index.tolist()); ys = d.values/10000
        ax5.plot(xs,ys,st,color=cl,alpha=al,linewidth=lw,markersize=6 if yl==2026 else 4,label=f'{yl}年')
        if yl==2026:
            for mx,my in zip(xs,ys): ax5.annotate(f'{my:.0f}万',(mx,my),textcoords="offset points",xytext=(0,12),fontsize=8,ha='center',fontweight='bold',color='#1890ff')
    ax5.set_xticks(range(1,13)); ax5.set_xlabel('月份',fontsize=9); ax5.set_ylabel('营收(万元)',fontsize=9)
    ax5.set_title('月度营收——聚焦2026',fontweight='bold',fontsize=12)
    ax5.legend(fontsize=9,ncol=3); ax5.spines['top'].set_visible(False)
    plt.tight_layout(); c5 = to_img(fig)

    # ===== Build HTML =====
    h = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>国管局1 · 2026经营看板</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#f0f2f5;color:#262626;line-height:1.5}}
.wrap{{max-width:1100px;margin:0 auto;padding:20px}}
.hd{{background:linear-gradient(135deg,#141414,#2d2d2d);color:#fff;padding:20px 28px;border-radius:10px 10px 0 0}}
.hd h1{{font-size:20px;font-weight:600}} .hd .sub{{font-size:12px;color:#bfbfbf;margin-top:2px}}
.strip{{background:#e6f7ff;border:1px solid #91d5ff;padding:8px 28px;font-size:12px;color:#0050b3}}
.kpis{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;padding:18px 28px;background:#fff}}
.kpi{{text-align:center;padding:14px 8px;border-radius:8px;background:#fafafa;border:1px solid #f0f0f0}}
.kpi .v{{font-size:22px;font-weight:700;color:#1890ff}}
.kpi .v.red{{color:#f5222d}} .kpi .v.green{{color:#52c41a}} .kpi .v.gray{{color:#8c8c8c}}
.kpi .l{{font-size:11px;color:#8c8c8c;margin-top:3px}}
.sec{{background:#fff;margin:12px 0;border-radius:10px;overflow:hidden}}
.sec h2{{font-size:14px;font-weight:600;padding:14px 24px;border-bottom:1px solid #f0f0f0;display:flex;align-items:center;gap:8px}}
.sec h2 i{{display:inline-block;width:8px;height:8px;border-radius:50%}}
.sec h2 i.blue{{background:#1890ff}} .sec h2 i.orange{{background:#fa8c16}} .sec h2 i.red{{background:#f5222d}}
.bd{{padding:18px 22px}}
.chart img{{max-width:100%;border-radius:4px}}
.fact{{padding:6px 14px;margin:5px 0;border-left:3px solid #1890ff;background:#f0f5ff;font-size:12px;border-radius:0 4px 4px 0;line-height:1.6}}
.fact.warn{{border-left-color:#fa8c16;background:#fff7e6}}
.fact.alarm{{border-left-color:#f5222d;background:#fff1f0}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
table{{width:100%;border-collapse:collapse;font-size:11px}}
th{{background:#fafafa;padding:7px 10px;text-align:left;font-weight:600;border-bottom:2px solid #e8e8e8;font-size:11px;color:#595959}}
td{{padding:6px 10px;border-bottom:1px solid #f0f0f0}}
tr:hover td{{background:#fafafa}}
.tag{{display:inline-block;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600}}
.tag-up{{background:#fff1f0;color:#cf1322}}
.tag-down{{background:#f6ffed;color:#389e0d}}
.ft{{text-align:center;padding:18px;color:#bfbfbf;font-size:11px}}
small{{color:#8c8c8c}}
@media(max-width:768px){{.kpis{{grid-template-columns:repeat(2,1fr)}}.grid2{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="wrap">

<div class="hd">
<h1>国管局1 · 2026年经营看板</h1>
<div class="sub">数据截至2026年{max_m}月 · 报告日 {now}</div>
</div>
<div class="strip">
📌 本看板聚焦<strong>2026年当期表现</strong>及<strong>趋势方向</strong>，历史数据作为参照。2026年仅有1-{max_m}月数据（非完整年），所有对比均为同期口径。
</div>

<div class="kpis">
<div class="kpi"><div class="v">{total/10000:.0f}万</div><div class="l">2026年1-{max_m}月营收</div></div>
<div class="kpi"><div class="v {"green" if yoy_val>0 else "red"}">{yoy_val*100:+.1f}%</div><div class="l">vs 2025年同期</div></div>
<div class="kpi"><div class="v gray">{total/max_m*12/10000:.0f}万</div><div class="l">年化推算（线性）</div></div>
<div class="kpi"><div class="v">{cr3*100:.1f}%</div><div class="l">CR3集中度(2026) <span class="tip">ⓘ<span class="tt">前三名客户营收占总营收比例</span></span></div></div>
<div class="kpi"><div class="v">{len(clients)}家</div><div class="l">活跃客户数</div></div>
</div>

<div class="sec">
<h2><i class="blue"></i>2026逐月走势 vs 2025同期</h2>
<div class="bd"><div class="chart"><img src="data:image/png;base64,{c1}"/></div>
<div class="fact">{max_m}个月中，{sum(1 for m in range(1,max_m+1) if m26.get(m,0)>m25.get(m,0))}个月超过去年同期，{sum(1 for m in range(1,max_m+1) if m26.get(m,0)<=m25.get(m,0))}个月低于同期。5月后为预估区间（虚线=去年实际作为参考）。</div>
</div>
</div>

<div class="sec">
<h2><i class="blue"></i>业务结构：什么在涨、什么在缩</h2>
<div class="bd"><div class="chart"><img src="data:image/png;base64,{c2}"/></div>
<div class="grid2"><div>'''

    # Category same-period comparison
    cat_now = df_now.groupby(kc)['amt'].sum()
    cat_prev = df_all[(df_all['y']==year-1)&(df_all['m'].isin(months))].groupby(kc)['amt'].sum()
    for c in cats:
        v26 = cat_now.get(c,0); v25 = cat_prev.get(c,0)
        if v26>0 or v25>0:
            chg = (v26-v25)/v25*100 if v25>0 else 0
            cls = 'warn' if abs(chg)>50 else ''
            arrow = '↑' if chg>0 else '↓'
            h += f'<div class="fact {cls}"><b>{c}</b>：2026年1-{max_m}月 {fmt(v26)}，同期 {arrow} {abs(chg):.0f}%（2025同期 {fmt(v25)}）</div>'

    # 2024-2026同期对比表（替代CAGR）
    prev2 = df_all[(df_all['y']==year-2)&(df_all['m'].isin(months))].groupby(kc)['amt'].sum()
    h += f'</div><div><table><tr><th>科目</th><th>2024年1-{max_m}月</th><th>2025年1-{max_m}月</th><th>2026年1-{max_m}月</th><th>2025→2026变化</th></tr>'
    for c in cats:
        v24 = prev2.get(c,0); v25 = cat_prev.get(c,0); v26 = cat_now.get(c,0)
        chg = (v26-v25)/v25*100 if v25>0 else 0
        arrow = '↑' if chg>0 else ('↓' if chg<0 else '→')
        h += f'<tr><td>{c}</td><td>{v24/10000:.0f}万</td><td>{v25/10000:.0f}万</td><td><b>{v26/10000:.0f}万</b></td><td style="color:{"#f5222d" if chg>0 else "#52c41a"}">{arrow}{abs(chg):.0f}%</td></tr>'
    h += '</table></div></div></div></div>'

    # Client movement
    big_drops = sum(1 for cl in clients if (cl26.get(cl,0)-cl25.get(cl,0))<-10000 and cl25.get(cl,0)>20000)
    h += f'''
<div class="sec">
<h2><i class="orange"></i>客户动向：2026年谁在增、谁在减</h2>
<div class="bd"><div class="chart"><img src="data:image/png;base64,{c3}"/></div>
<div class="fact alarm">⚠ 2026年1-{max_m}月，<b>{big_drops}家</b>大客户（2025年营收>2万）较同期下降超1万元。<small>注意：2026年仅{max_m}个月数据，部分下降可能因业务尚未发生。</small></div>
<div class="fact"><b>CR3={cr3*100:.1f}%</b>，客户集中度{"较高" if cr3>0.5 else "适中"}。</div>
</div>
</div>
'''

    # Seasonal
    q3q4_avg = np.mean([qpct.loc[y,'Q3']+qpct.loc[y,'Q4'] for y in fy])
    h2_2025 = df_all[(df_all['y']==2025)&(df_all['m'].between(7,12))]['amt'].sum()
    h += f'''
<div class="sec">
<h2><i class="blue"></i>季节节奏 → 下半年预判</h2>
<div class="bd"><div class="chart"><img src="data:image/png;base64,{c4}"/></div>
<div class="grid2">
<div>
<div class="fact" style="font-size:14px">2021-2025年Q3+Q4平均占比<b>{q3q4_avg:.0f}%</b>，下半年是主战场。</div>
<div class="fact warn" style="font-size:14px">若2026年H2维持2025年H2的营收水平（{fmt(h2_2025)}），全年预计可达<b>{fmt(total+h2_2025)}</b>。</div>
</div>
<div style="font-size:14px;color:#8c8c8c"><p style="margin-bottom:6px"><b>Q4占比趋势：</b></p>'''
    for y in fy:
        q4 = qpct.loc[y,'Q4']
        h += f'<div>· {y}年Q4占比 <b>{q4:.0f}%</b>{" ⚠年底效应" if q4>30 else ""}</div>'
    h += '</div></div></div></div>'

    # Monthly focus
    h += f'''
<div class="sec">
<h2><i class="blue"></i>月度营收轨迹——聚焦当前</h2>
<div class="bd"><div class="chart"><img src="data:image/png;base64,{c5}"/></div></div>
</div>
'''

    # Signals
    signals = []
    for c in cats:
        v26 = cat_now.get(c,0); v25 = cat_prev.get(c,0)
        if v25>0 and abs((v26-v25)/v25)>0.3:
            signals.append(f'科目<b>{c}</b>：2026年1-{max_m}月较同期变动 <b>{(v26-v25)/v25*100:+.0f}%</b>（{fmt(v25)}→{fmt(v26)}）')
    for cl in cl26.head(5).index:
        v26 = cl26.get(cl,0); v25 = cl25.get(cl,0)
        if v25>10000 and abs((v26-v25)/v25)>0.3:
            cls_sign = 'alarm' if (v26-v25)/v25<-0.3 else 'warn'
            signals.append(f'大客户<b>{cl}</b>：2026年1-{max_m}月较同期变动 <b>{(v26-v25)/v25*100:+.0f}%</b>（{fmt(v25)}→{fmt(v26)}）')

    h += f'''
<div class="sec">
<h2><i class="red"></i>2026年需关注的信号（{len(signals)}条）</h2>
<div class="bd">'''
    for s in signals[:15]:
        h += f'<div class="fact alarm">{s}</div>'
    h += f'''
<div class="fact" style="margin-top:8px;border-left-color:#bfbfbf;background:#fafafa">
📎 <b>数据说明</b>：上述比较均为2026年1-{max_m}月 vs 2025年1-{max_m}月同期口径。2026年全年数据尚未完整，变动幅度可能随下半年业务开展而变化。
</div></div></div>

<div class="ft">财务BP出品 · {len(clients)}个客户完整保留 · 聚焦当前与趋势</div>
</div></body></html>'''

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(h)
    with open(MTIME_FILE, 'w') as f:
        f.write(str(os.path.getmtime(EXCEL)))
    print(f'[{datetime.datetime.now().strftime("%H:%M:%S")}] Report generated: {len(h):,} bytes')

if __name__ == '__main__':
    generate()
