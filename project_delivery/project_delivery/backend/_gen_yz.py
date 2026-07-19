# -*- coding: utf-8 -*-
"""驿站 BP分析报告 v14 — 气泡标签去加粗+字号加大2"""
import pandas as pd, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.ticker as mt
from io import BytesIO; import base64, datetime, os, re

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei','SimHei','WenQuanYi Micro Hei','DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
EXCEL='/app/管理报表.xlsx'; OUTPUT='/app/frontend/驿站_分析报告.html'

# === 96%饱和度色板 ===
BLUE='#2090f5'; RED='#f03038'; GREEN='#5bb821'; ORANGE='#fa8c16'
GOLD='#faad14'; PURPLE='#7a30d8'; CYAN='#13b4c2'; GRAY='#b0b0b0'
PIECOLORS=['#f05050','#fa8c16','#5bb821','#2090f5','#7a30d8','#eb3a9a','#b0b0b0']
BLUE_BAR=['#2090f5','#40a5ff','#69c0ff','#91d5ff','#bae7ff','#d6e4ff']
# 4大类颜色：基础人工/服务人工/物料/场地相关
COST4_COLORS=['#2090f5','#f05050','#fa8c16','#5bb821']
COST4_LABELS=['基础人工','服务人工','物料','场地相关']
BG_CANVAS='#fafafa'
# quadrant bg colors (alpha 0.10)
QB_GREEN='#b7eb8f'; QB_BLUE='#bae0ff'; QB_RED='#ffbbb8'; QB_ORANGE='#ffd591'

def merge_cost(k):
    """将原始细项归入4大类"""
    k=k.strip()
    if '团队基础人工' in k: return 0  # 基础人工
    if any(w in k for w in ['服务提成','人工-清洁','人工-专业组','渠道费']): return 1  # 服务人工
    if any(w in k for w in ['物料/','助餐点']): return 2  # 物料
    if any(w in k for w in ['房租/','物业','车位','电梯','能源','公区清洁','维修','网络']): return 3  # 场地相关
    s=re.sub(r'^[\d]+）','',k)
    if s.startswith('人工-'): return 1
    return 2  # 兜底归物料

def to_img(fig):
    b=BytesIO(); fig.savefig(b,format='png',dpi=130,bbox_inches='tight',facecolor=BG_CANVAS)
    plt.close(fig); b.seek(0); return base64.b64encode(b.read()).decode()

def load():
    df=pd.read_excel(EXCEL,sheet_name='驿站',engine='calamine',header=None)
    # 从表头行（第6行，索引5）动态读取驿站名称和列位置
    hdr=df.iloc[5]
    stations={}
    for i in range(2,len(hdr)):
        v=hdr.iloc[i]
        if pd.isna(v): continue
        s=str(v).strip()
        if s in ('总计','汇总','合计') or not s: break
        stations[s]=i
    if not stations:  # 兜底：使用旧硬编码
        stations={'08.东直门&交道口':2,'09.体育馆路':3,'10.德外街道':4,'11.北下关南二':5,'12.海淀镇':6,'13.万寿路紫金':7,'14.田村路&中关村':8}
    rows=[]
    for i in range(2,len(df)):
        r=df.iloc[i]
        cat=str(r[0]).strip() if pd.notna(r[0]) else ''
        sub=str(r[1]).strip() if pd.notna(r[1]) and str(r[1])!='(全部)' else ''
        if not cat or '汇总' in cat: continue
        vals={}
        for s,col in stations.items():
            v=r[col]
            if pd.notna(v):
                try: vals[s]=float(v)
                except: pass
        if vals: rows.append({'cat':cat,'sub':sub,'vals':vals})
    return rows,stations

def compute():
    rows,stations=load()
    pl={s:{'收入':0,'支出':0,'管理费':0}for s in stations}
    for r in rows:
        for s,v in r['vals'].items():
            if '收入' in r['cat']: pl[s]['收入']+=v
            elif '支出' in r['cat']: pl[s]['支出']+=abs(v)
            elif '管理费' in r['cat']: pl[s]['管理费']+=abs(v)
    costs={}
    st_costs={s:{} for s in stations}
    for r in rows:
        if '支出' in r['cat']:
            k=r['sub'][:35] if r['sub'] else '其他'
            costs[k]=costs.get(k,0)+sum(abs(v) for v in r['vals'].values())
            for s,v in r['vals'].items():
                if v: st_costs[s][k]=st_costs[s].get(k,0)+abs(v)
    revs={}
    for r in rows:
        if '收入' in r['cat']:
            k=r['sub'][:30] if r['sub'] else '其他'
            revs[k]=revs.get(k,0)+sum(v for v in r['vals'].values())
    return pl,costs,revs,stations,rows,st_costs

def generate():
    now=datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    pl,costs,revs,stations,rows,st_costs=compute()
    snames=list(stations.keys()); tot_inc=sum(pl[s]['收入']for s in snames)
    short_names={'14.田村路&中关村':'永达&黄庄'}
    def short(s): return short_names.get(s, s[:6])
    tot_exp=sum(pl[s]['支出']for s in snames); tot_fee=sum(pl[s]['管理费']for s in snames)
    tot_bal=tot_inc-tot_exp-tot_fee; profit=sum(1 for s in snames if pl[s]['收入']-pl[s]['支出']-pl[s]['管理费']>=0)

    # ===== Chart 1: P&L by station =====
    fig,ax=plt.subplots(figsize=(9,4.5))
    x=range(len(snames)); w=0.22
    incs=[pl[s]['收入']/10000 for s in snames]
    exps=[pl[s]['支出']/10000 for s in snames]
    fees=[pl[s]['管理费']/10000 for s in snames]
    bals=[pl[s]['收入']/10000-pl[s]['支出']/10000-pl[s]['管理费']/10000 for s in snames]
    ax.bar([i-w*1.2 for i in x],incs,w,color=BLUE,label='收入',edgecolor='white')
    ax.bar([i for i in x],exps,w,color=RED,label='支出',edgecolor='white')
    ax.bar([i+w*1.2 for i in x],fees,w,color=GOLD,label='管理费',edgecolor='white')
    for i,b in enumerate(bals):
        ax.text(i,b+2 if b>=0 else b-4,f'{b:+.0f}万',ha='center',fontsize=7,fontweight='bold',color=GREEN if b>=0 else RED)
    ax.set_xticks(x); ax.set_xticklabels([short(s) for s in snames],fontsize=8,color='#666')
    ax.set_ylabel('万元',fontsize=9,color='#666'); ax.set_title('各驿站损益对比',fontweight='bold',fontsize=11,color='#444')
    ax.legend(fontsize=8,ncol=3); ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.tick_params(colors='#999')
    plt.tight_layout(); c1=to_img(fig)

    # ===== Chart 2: Revenue concentration =====
    fig,ax=plt.subplots(figsize=(8,3.5))
    rtop=sorted(revs.items(),key=lambda x:x[1],reverse=True)
    rns=[k[:15] for k,_ in rtop]; rvs=[v/10000 for _,v in rtop]
    ax.barh(range(len(rns)-1,-1,-1),rvs,color=BLUE_BAR[:len(rns)])
    ax.set_yticks(range(len(rns))); ax.set_yticklabels(rns[::-1],fontsize=9,color='#555')
    ax.set_xlabel('万元',fontsize=9,color='#666'); ax.set_title('全站点收入构成',fontweight='bold',fontsize=11,color='#444')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False); ax.tick_params(colors='#999')
    for i,v in enumerate(rvs): ax.text(v+2,len(rns)-1-i,f'{v:.0f}万',va='center',fontsize=8,color='#666')
    plt.tight_layout(); c3=to_img(fig)

    # ===== Chart 3: 成本率堆积柱状图（4大类） =====
    fig,ax=plt.subplots(figsize=(9,4.5))
    x=range(len(snames)); w=0.18
    # 按4大类汇总每个驿站成本
    cat4_sum={s:[0,0,0,0] for s in snames}  # [基础人工,服务人工,物料,场地相关]
    for s in snames:
        for k,v in st_costs[s].items():
            ci=merge_cost(k); cat4_sum[s][ci]+=v
    # 转为收入占比
    cat4_pct={s:[cat4_sum[s][j]/pl[s]['收入']*100 if pl[s]['收入']>0 else 0 for j in range(4)] for s in snames}
    # 绘制堆积条
    bottoms=[0]*len(snames)
    for j in range(4):
        vals=[cat4_pct[s][j] for s in snames]
        ax.bar([i-w*1.5 for i in x],vals,w,bottom=bottoms,color=COST4_COLORS[j],
               label=COST4_LABELS[j],edgecolor='white',linewidth=0.5)
        bottoms=[bottoms[i]+vals[i] for i in range(len(snames))]
    # 总成本率标注在柱顶
    for i,s in enumerate(snames):
        total=(pl[s]['支出']+pl[s]['管理费'])/pl[s]['收入']*100 if pl[s]['收入']>0 else 0
        ax.text(i-w*1.5,total+1.5,f'{total:.0f}%',ha='center',fontsize=9,fontweight='bold',color='#1a1a1a')
    ax.set_xlim(-0.6,len(snames)-0.6)
    ax.set_xticks([i-w*1.5 for i in x])
    ax.set_xticklabels([short(s) for s in snames],fontsize=12,color='#000000')
    ax.axhline(y=90,color=RED,linestyle='--',linewidth=1,alpha=0.4)
    ax.axhline(y=80,color=GREEN,linestyle='--',linewidth=1,alpha=0.4)
    ax.set_ylabel('成本率(%)',fontsize=10,color='#1a1a1a')
    ax.set_title('各驿站成本率构成',fontweight='bold',fontsize=12,color='#1a1a1a')
    ax.legend(fontsize=9,ncol=1,loc='lower right',framealpha=0.8)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.tick_params(colors='#aaa',labelsize=9)
    plt.tight_layout(); c4=to_img(fig)

    # ===== Chart 4: 盈亏象限（纯象限，无饼图） =====
    xs=[pl[s]['收入']/10000 for s in snames]
    ys=[(pl[s]['收入']-pl[s]['支出']-pl[s]['管理费'])/pl[s]['收入']*100 for s in snames]
    zs_all=[(pl[s]['支出']+pl[s]['管理费'])/10000 for s in snames]
    colors_q=[GREEN if y>=0 else RED for y in ys]
    z_norm=[(z-min(zs_all))/(max(zs_all)-min(zs_all))*3600+840 for z in zs_all]
    med_inc=np.median(xs)

    fig=plt.figure(figsize=(14,9),facecolor=BG_CANVAS)
    ax=fig.add_subplot(1,1,1)

    # 先 autoscale
    ax.scatter(xs,ys,s=[5]*len(snames),alpha=0)
    xpad=(max(xs)-min(xs))*0.15+15; ypad=10
    ax.set_xlim(min(xs)-xpad,max(xs)+xpad)
    ax.set_ylim(min(ys)-ypad,max(ys)+ypad)
    xlim=ax.get_xlim(); ylim=ax.get_ylim()

    # 四象限背景
    ax.fill_between([med_inc,xlim[1]],0,ylim[1],alpha=0.10,color=QB_GREEN,zorder=0)
    ax.fill_between([xlim[0],med_inc],0,ylim[1],alpha=0.10,color=QB_BLUE,zorder=0)
    ax.fill_between([med_inc,xlim[1]],ylim[0],0,alpha=0.10,color=QB_RED,zorder=0)
    ax.fill_between([xlim[0],med_inc],ylim[0],0,alpha=0.10,color=QB_ORANGE,zorder=0)

    # 十字分割线
    ax.axhline(y=0,color='#bbb',linestyle='-',linewidth=0.8,alpha=0.5)
    ax.axvline(x=med_inc,color='#bbb',linestyle='-',linewidth=0.8,alpha=0.5)

    # 散点气泡
    for i in range(len(snames)):
        ax.scatter(xs[i],ys[i],s=z_norm[i],c=colors_q[i],alpha=0.5,
                   edgecolors='white',linewidth=2,zorder=5)

    # 站点标签：全名 + 营收（气泡内白字 or 偏移黑字）
    def quadrant_offset(x_i,y_i):
        if x_i>=med_inc and y_i>=0: return (32,22)   # 右上
        elif x_i<med_inc and y_i>=0: return (-32,22)  # 左上
        elif x_i>=med_inc and y_i<0: return (32,-22)  # 右下
        else: return (-32,-22)                        # 左下

    for i,s in enumerate(snames):
        # 简化全名（去"08."等编号前缀）
        full=s.split('.',1)[-1] if '.' in s else s
        txt=f'{full} ¥{pl[s]["收入"]/10000:.0f}万'
        ox,oy=quadrant_offset(xs[i],ys[i])
        if z_norm[i]>1200:
            ax.annotate(txt,(xs[i],ys[i]),ha='center',va='center',
                        fontsize=17,color='#1a1a1a',zorder=6)
        else:
            ax.annotate(txt,(xs[i],ys[i]),textcoords='offset points',
                        xytext=(ox*1.8,oy*1.5),fontsize=17,color='#1a1a1a',
                        arrowprops=dict(arrowstyle='->',color='#aaa',lw=0.9))

    # 象限名
    ax.text(xlim[1]*0.91,ylim[1]*0.94,'● 明星站点',fontsize=20,color=GREEN,ha='right',fontweight='bold',alpha=0.7)
    ax.text(xlim[0]+xpad*0.3,ylim[1]*0.94,'● 高效小站',fontsize=20,color=BLUE,ha='left',fontweight='bold',alpha=0.7)
    ax.text(xlim[1]*0.91,ylim[0]+ypad*0.2,'● 规模陷阱',fontsize=20,color=RED,ha='right',fontweight='bold',alpha=0.7)
    ax.text(xlim[0]+xpad*0.3,ylim[0]+ypad*0.2,'● 危机站点',fontsize=20,color=ORANGE,ha='left',fontweight='bold',alpha=0.7)

    ax.set_xlabel('总收入（万元）',fontsize=16,color='#1a1a1a')
    ax.set_ylabel('结余率（%）',fontsize=16,color='#1a1a1a')
    ax.set_title('盈亏象限',fontweight='bold',fontsize=18,color='#1a1a1a')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.tick_params(colors='#aaa',labelsize=9)
    ax.grid(True,alpha=0.12,linestyle='-')
    plt.subplots_adjust(left=0.08,right=0.95,top=0.93,bottom=0.08); c5=to_img(fig)

    # ===== HTML =====
    css='''
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#f0f2f5;color:#262626;line-height:1.5}
.wrap{max-width:1100px;margin:0 auto;padding:20px}
.hd{background:linear-gradient(135deg,#141414,#2d2d2d);color:#fff;padding:20px 28px;border-radius:10px 10px 0 0}
.hd h1{font-size:22px;font-weight:600}.hd .sub{font-size:14px;color:#bfbfbf;margin-top:2px}
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;padding:18px 28px;background:#fff}
.kpi{text-align:center;padding:14px 8px;border-radius:8px;background:#fafafa;border:1px solid #f0f0f0}
.kpi .v{font-size:24px;font-weight:700;color:#2090f5}.kpi .v.red{color:#f03038}.kpi .v.green{color:#5bb821}
.kpi .l{font-size:13px;color:#8c8c8c;margin-top:3px}
.sec{background:#fff;margin:12px 0;border-radius:10px;overflow:hidden;border:1px solid #f0f0f0}
.sec h2{font-size:16px;font-weight:600;padding:14px 24px;border-bottom:1px solid #f0f0f0;display:flex;align-items:center;gap:8px;color:#434343}
.sec h2 .dot{width:8px;height:8px;border-radius:50%;background:#2090f5;display:inline-block}
.bd{padding:18px 22px}.chart{text-align:center;margin:8px 0}.chart img{max-width:100%;border-radius:4px}
.fact{padding:8px 14px;margin:6px 0;border-left:3px solid #2090f5;background:#f0f5ff;font-size:14px;border-radius:0 4px 4px 0;line-height:1.5;color:#595959}
.fact.warn{border-left-color:#fa8c16;background:#fff7e6}
.fact.alarm{border-left-color:#f03038;background:#fff1f0}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
table{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0}
th{background:#fafafa;padding:7px 10px;text-align:left;font-weight:600;border-bottom:2px solid #e8e8e8;font-size:12px;color:#595959}
td{padding:6px 10px;border-bottom:1px solid #f0f0f0;color:#595959}
/* 驿站损益对比表 */
.yz-table{border-radius:8px;overflow:hidden;border:1px solid #e8e8e8;font-size:13px;margin:10px 0}
.yz-table th{background:linear-gradient(180deg,#f8f9fb,#f0f2f5);padding:10px 12px;font-size:12px;color:#434343;border-bottom:2px solid #dce0e6;text-align:center;font-weight:600;letter-spacing:.5px}
.yz-table th:first-child{text-align:left;border-radius:8px 0 0 0}
.yz-table th:last-child{border-radius:0 8px 0 0}
.yz-table td{padding:10px 12px;border-bottom:1px solid #f2f3f5;text-align:center;color:#434343;font-variant-numeric:tabular-nums;font-size:13px}
.yz-table td:first-child{text-align:left;font-weight:500;color:#262626}
.yz-table tr:last-child td{border-bottom:none}
.yz-table tr:nth-child(odd) td{background:#fafbfc}
.yz-table tr:nth-child(even) td{background:#fff}
.yz-table tr:hover td{background:#f0f4ff}
.yz-table .num-up{color:#5bb821;font-weight:600}
.yz-table .num-down{color:#f03038;font-weight:600}
.yz-table .status-ok{color:#5bb821;font-size:16px}
.yz-table .status-warn{color:#fa8c16;font-size:16px}
tr:hover td{background:#fafafa}
.ft{text-align:center;padding:18px;color:#bfbfbf;font-size:13px}
.concise{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}
.concise-item{border:1px solid #f0f0f0;border-radius:8px;padding:12px 14px;background:#fafafa}
.concise-item .c-num{display:inline-block;width:22px;height:22px;line-height:22px;text-align:center;border-radius:50%;color:#fff;font-size:11px;font-weight:700;margin-right:8px}
.num-red{background:#f03038}.num-orange{background:#fa8c16}.num-blue{background:#2090f5}
.concise-item .c-title{font-size:15px;font-weight:600;display:inline;color:#434343}
.concise-item .c-body{font-size:13px;color:#595959;margin-top:6px;line-height:1.5}
.concise-item details{margin-top:6px;font-size:13px}
.concise-item details summary{color:#2090f5;cursor:pointer;font-size:13px}
.concise-item details div{margin-top:4px;padding:8px 10px;background:#fff;border-radius:4px;line-height:1.5;color:#595959}
@media(max-width:768px){.kpis{grid-template-columns:repeat(2,1fr)}.grid2{grid-template-columns:1fr}.concise{grid-template-columns:1fr}}
'''
    h=f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>驿站业务 BP分析报告</title><style>{css}</style></head><body><div class="wrap">
<div class="hd"><h1>驿站业务 · BP分析报告</h1><div class="sub">取数: 管理报表/驿站 Sheet · 2026年1-6月 · {now}</div></div>

<div class="kpis">
<div class="kpi"><div class="v">{tot_inc/10000:.0f}万</div><div class="l">总收入</div></div>
<div class="kpi"><div class="v red">{tot_exp/10000:.0f}万</div><div class="l">总支出</div></div>
<div class="kpi"><div class="v {"green" if tot_bal>=0 else "red"}">{tot_bal/10000:+.0f}万</div><div class="l">净结余</div></div>
<div class="kpi"><div class="v">{profit}/{len(snames)}</div><div class="l">盈利驿站/总数</div></div>
<div class="kpi"><div class="v red">{(tot_exp+tot_fee)/tot_inc*100:.0f}%</div><div class="l">综合成本率</div></div>
</div>'''

    # Section 1: P&L（仅表格，无柱状图）
    h+=f'''<div class="sec"><h2><span class="dot"></span>各驿站损益对比</h2><div class="bd">
<table class="yz-table"><tr><th>驿站</th><th>收入(万)</th><th>支出(万)</th><th>管理费(万)</th><th>结余(万)</th><th>结余率</th><th>成本率</th><th>状态</th></tr>'''
    for s in snames:
        d=pl[s]; bal=d['收入']-d['支出']-d['管理费']
        rate=bal/d['收入']*100 if d['收入']>0 else 0
        crate=(d['支出']+d['管理费'])/d['收入']*100 if d['收入']>0 else 0
        st='<span class="status-ok">●</span>' if bal>=0 else '<span class="status-warn">●</span>'
        cls='num-up' if bal>=0 else 'num-down'
        h+=f'<tr><td>{s}</td><td>{d["收入"]/10000:.1f}</td><td>{d["支出"]/10000:.1f}</td><td>{d["管理费"]/10000:.1f}</td><td class="{cls}">{bal/10000:+.1f}</td><td>{rate:+.1f}%</td><td>{crate:.0f}%</td><td>{st}</td></tr>'
    h+='</table>'
    h+=f'<div class="fact"><b>4家驿站亏损</b>（北下关-5.2%、海淀-4.1%、万寿路-3.1%、田村路-3.3%），3家盈利。</div>'
    h+=f'<div class="fact">体育馆路结余率29.7%为全站点最高，成本率仅67%。</div>'
    h+='</div></div>'

    # Section 2: Revenue
    h+=f'''<div class="sec"><h2><span class="dot"></span>收入结构：过度依赖单一来源</h2><div class="bd"><div class="chart"><img src="data:image/png;base64,{c3}"/></div>
<div class="fact alarm"><b>家庭养老床位收入占比83%</b>。6个驿站该收入占比超72%，一旦政策调整影响巨大。</div>
<div class="fact warn">德外街道是例外：基本养老对象占46%、老年餐桌32%。收入多元化≠更高盈利，核心是<b>每种收入的边际贡献率</b>。</div></div></div>'''

    # Section 3: 成本·盈亏全景
    labor=sum(v for k,v in costs.items() if any(x in k for x in ['人工','照护','提成','清洁','外包']))
    h+=f'''<div class="sec"><h2><span class="dot" style="background:#7a30d8"></span>成本·盈亏全景</h2><div class="bd">
<div class="chart"><img src="data:image/png;base64,{c4}"/></div>
<div class="fact alarm">人工成本占支出{int(labor/sum(costs.values())*100)}%（{labor/10000:.0f}万），家庭照护者{sum(v for k,v in costs.items() if "家庭照护" in k)/10000:.0f}万。可控成本仅占5%。</div>
<div class="chart" style="margin-top:8px"><img src="data:image/png;base64,{c5}"/></div>
<div class="fact" style="margin-top:4px">象限四区：气泡大小=成本规模，绿=盈/红=亏。成本率堆积图见上方。</div>
</div></div>'''

    # Section 4: BP核心结论
    h+=f'''<div class="sec"><h2><span class="dot" style="background:#f03038"></span>BP核心结论</h2><div class="bd"><div class="concise">
<div class="concise-item">
<span class="c-num num-red">1</span><span class="c-title">转包模式是亏损根源</span>
<div class="c-body">北下关、海淀镇、田村路三站照护者人工占比47-81%。盈利的东直门、体育馆路均为自营。</div>
<details><summary>展开详情</summary><div>三站共亏损20万，照护者人工合计292万。若将50%转包转为自营（按体育馆路团队人工占比35%估算），可节省人工成本约100万，实现整体扭亏。</div></details>
</div>
<div class="concise-item">
<span class="c-num num-red">2</span><span class="c-title">收入单一化风险极高</span>
<div class="c-body">83%收入依赖家庭养老床位。政策调整将带来系统性冲击。</div>
<details><summary>展开详情</summary><div>6个驿站家庭床位收入占比超72%。德外街道的多元化结构（基本养老46%/老年餐桌32%）可作范本，但其助餐毛利率需先达标。</div></details>
</div>
<div class="concise-item">
<span class="c-num num-blue">3</span><span class="c-title">体育馆路是标杆</span>
<div class="c-body">29.7%结余率证明小规模+自营+严控成本可行。</div>
<details><summary>展开详情</summary><div>建议将其团队配置、供应商管理、排班制度标准化并推广至北下关（最近似，收入规模接近）。</div></details>
</div>
<div class="concise-item">
<span class="c-num num-orange">4</span><span class="c-title">助餐业务普遍亏损</span>
<div class="c-body">德外8.5万+万寿路15.2万助餐支出，对应收入不足。</div>
<details><summary>展开详情</summary><div>需逐站点核算助餐毛利率。亏损站点考虑调整定价（提价10-15%）、缩减规模，或评估是否有政府补贴可争取。</div></details>
</div>
<div class="concise-item">
<span class="c-num num-blue">5</span><span class="c-title">出路在收入质量而非节支</span>
<div class="c-body">人工外可控成本仅5%。核心路径：拓展非床位收入、优化转包定价、外包转自营。</div>
<details><summary>展开详情</summary><div>物料+房租仅40万（5%），再怎么省也省不出扭转亏损的20万缺口。田村路市场化收入仅8.7万，万寿路残联10万——非床位收入有200万+空间待挖掘。</div></details>
</div>
</div></div></div>'''

    h+=f'<div class="ft">财务BP出品 &nbsp;|&nbsp; 7个驿站完整分析 &nbsp;|&nbsp; {now}</div></div></body></html>'

    os.makedirs(os.path.dirname(OUTPUT),exist_ok=True)
    with open(OUTPUT,'w',encoding='utf-8') as f: f.write(h)
    print(f'[yizhan v12] {len(h):,} bytes')

if __name__=='__main__': generate()
