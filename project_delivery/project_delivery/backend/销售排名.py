""" 销售排名报告 — 双时段 · 杂志编辑风 """
import pandas as pd

# ════════ 数据层 ════════
df = pd.read_excel('/app/管理报表.xlsx', sheet_name='销售排名', engine='calamine', header=0)
MAX_MONTH = int(df['月份'].max())  # 6
W = lambda v: v/10000

# 全时段 1-MAX_MONTH月
all_months = df.groupby(['销售网点', '销售人员'])['金额'].sum().reset_index()
all_months['金额万'] = all_months['金额'].apply(lambda v: round(W(v), 1))

# 重点时段 3-MAX_MONTH月
q2 = df[df['月份'] >= 3]
q2_months = q2.groupby(['销售网点', '销售人员'])['金额'].sum().reset_index()
q2_months['金额万3'] = q2_months['金额'].apply(lambda v: round(W(v), 1))

# 合并双时段
person = all_months.merge(q2_months[['销售网点', '销售人员', '金额万3']],
                           on=['销售网点', '销售人员'], how='left')
person['金额万3'] = person['金额万3'].fillna(0)

# 全平台个人排名（按全时段金额）
person = person.sort_values('金额', ascending=False).reset_index(drop=True)
person['个人排名'] = range(1, len(person)+1)

# 网点聚合
outlet = person.groupby('销售网点').agg(网点总金额=('金额', 'sum'), 人数=('销售人员', 'count')).reset_index()
outlet = outlet.sort_values('网点总金额', ascending=False).reset_index(drop=True)

# ════════ HTML 构建 ════════
def build_outlet_html(rank, row):
    name = row['销售网点']
    total = round(W(row['网点总金额']), 1)
    cnt = int(row['人数'])
    people = person[person['销售网点'] == name].sort_values('金额', ascending=False)

    person_rows = ''
    for _, p in people.iterrows():
        amt1 = p['金额万']
        amt3 = p['金额万3']
        prank = p['个人排名']
        top_cls = ' top' if prank <= 10 else ''
        pers_name = p['销售人员']
        person_rows += f'<div class="person{top_cls}"><div class="name">{pers_name}</div><div class="n1">{amt1:,.1f}万</div><div class="n3">{amt3:,.1f}万</div><div class="rank">No. {prank}</div></div>'

    return f"""<div class="shop">
  <div class="shop-bar">
    <div class="shop-no">{rank}</div>
    <div class="shop-info">
      <div class="shop-name">{name}</div>

    </div>
    <div class="shop-total"><b>Σ {total:,.1f}万</b></div>
  </div>
  <div class="tbl-hdr"><div>姓名</div><div>1-{MAX_MONTH}月合计</div><div>3-{MAX_MONTH}月合计</div><div>个人排名</div></div>
  <div class="person-list">{person_rows}</div>
</div>"""

outlet_html = '\n'.join(build_outlet_html(i+1, row) for i, row in outlet.iterrows())

# ════════ CSS ════════
CSS = """\
:root{--ink:#1d1d1f;--ink2:#6e6e73;--paper:#f5f5f7;--card:#fff;--accent:#0071e3;--line:#e8e8ed;--gold:#e8a800}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","PingFang SC","Microsoft YaHei",sans-serif;
  background:var(--paper);color:var(--ink);-webkit-font-smoothing:antialiased;line-height:1.5}

.wrap{max-width:860px;margin:0 auto;padding:56px 20px 80px}

.hero{margin-bottom:40px}
.hero h1{font-size:32px;font-weight:700;letter-spacing:-.02em;margin-bottom:12px}
.hero .sub{font-size:13px;color:var(--ink2);line-height:1.7;margin-bottom:8px}
.hero .sub b{color:var(--ink);font-weight:600}

.shop{background:var(--card);border-radius:16px;margin-bottom:8px;overflow:hidden;
  box-shadow:0 1px 3px rgba(0,0,0,.04)}
.shop-bar{display:flex;align-items:center;padding:16px 22px;gap:12px;
  background:linear-gradient(135deg,#00B0F0,#0098d4);color:#fff}
.shop-bar .shop-name{color:#fff}
.shop-bar .shop-meta{color:rgba(255,255,255,.75)}
.shop-bar .shop-total b{color:#fff}
.shop-no{width:34px;height:34px;border-radius:10px;display:flex;align-items:center;justify-content:center;
  font-size:15px;font-weight:700;background:#FFC000;color:#fff;flex-shrink:0}
.shop-info{flex:1;min-width:0}
.shop-name{font-size:17px;font-weight:600;letter-spacing:-.01em}
.shop-total{text-align:right;flex-shrink:0}
.shop-total b{font-size:22px;font-weight:700;color:var(--accent)}

.tbl-hdr{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:10px 22px 6px;
  background:#00B0F0;color:#fff;font-size:10px;font-weight:600;text-align:center}

.person-list{padding:0 22px 10px}
.person{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:8px 0;font-size:13px;text-align:center}
.person:nth-child(even){background:#f5f5f7}
.person .name{font-weight:500}
.person .n1,.person .n3{font-variant-numeric:tabular-nums}
.person .n1{font-weight:600}
.person .n3{color:var(--ink2)}
.person .rank{font-weight:700;font-size:13px}

.person.top .name{font-weight:700}
.person.top .n1{color:var(--accent);font-weight:700}
.person.top .rank{color:var(--gold);font-weight:800}
.person.top .rank::before{content:'\u2605';margin-right:3px}

.footer{margin-top:40px;text-align:center;font-size:11px;color:var(--ink2)}
"""

# ════════ HTML ════════
html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>销售排行榜</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

<div class="hero">
  <h1>销售排行榜</h1>
  <p class="sub">数据来源：以所有<b>自费客户</b>为对象，销售额取自<b>美丽花</b>与<b>ABC</b>。统计已完成<b>居家服务</b>及<b>在站医疗</b>，仅含已关联至销售人员的订单。</p>
</div>

{outlet_html}

<p class="footer">数据来源：管理报表 · 销售排名 sheet · 1-{MAX_MONTH}月全量 / 3-{MAX_MONTH}月重点区间</p>

</div>
</body>
</html>"""

output = '/app/销售排行榜.html'
with open(output, 'w', encoding='utf-8') as f:
    f.write(html)
print('报告:', output)
print('网点数:', len(outlet), '| 人数:', len(person), '| 最大月份:', MAX_MONTH)
