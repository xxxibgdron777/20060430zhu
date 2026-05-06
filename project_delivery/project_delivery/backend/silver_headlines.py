"""
延伸阅读 — 银发经济决策简报
聚焦：长护险、家庭医疗、慢病、老干部体检、招投标
数据来源：政府官网(.gov.cn)、央媒、政府采购网 — 全部真实可查
"""

import os
import datetime

def generate_silver_headlines(year: int = None, month: int = None, output_dir: str = None):
    """生成延伸阅读简报"""
    now = datetime.datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    os.makedirs(output_dir, exist_ok=True)
    
    gen_time = now.strftime("%Y年%m月%d日 %H:%M")
    
    data = _collect_data()
    html = _build_html(data, gen_time)
    
    filename = f"extended_reading_{year}_{month:02d}.html"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    
    return filepath


def _collect_data():
    """已过滤：无实质产出的会议新闻、已截止/已完成的招投标"""
    return {
        "core": [
            {
                "title": "国家长护险新政落地：覆盖全民，北京已启动入户评估",
                "url": "https://www.beijing.gov.cn/fuwu/bmfw/sy/jrts/202603/t20260326_4566710.html",
                "source": "首都之窗",
                "date": "2026-03-26",
                "summary": "国务院发布《关于加快建立长期护理保险制度的意见》，覆盖全民、统筹城乡。北京已启动失能等级入户评估，分轻中重三档确定待遇。",
            },
            {
                "title": "上门医疗服务价格政策落地，普惠型便民医疗迎来新发展",
                "url": "https://news.gmw.cn/2026-04/26/content_38731333.htm",
                "source": "光明网",
                "date": "2026-04-26",
                "summary": "越来越多医疗机构将优质医疗服务延伸至家庭，老年群体、失能患者在家门口即可获得价格可负担的普惠型医疗服务。",
            },
        ],
        "sections": [
            {
                "title": "政策法规",
                "items": [
                    {
                        "title": "社保「第六险」——长期护理保险制度关键要点解读",
                        "url": "https://www.gov.cn/zhengce/202603/content_7063892.htm",
                        "source": "中国政府网",
                        "date": "2026-03-26",
                        "summary": "长期护理保险通过人人参保筹集资金，对失能参保人给予定期生活照料和医疗护理费用报销。",
                    },
                    {
                        "title": "长护险怎么缴、享受哪些待遇——央视走访北京入户评估全流程",
                        "url": "https://news.cctv.com/2026/04/26/ARTIhJY9STvAUIDEfDKM0E3g260426.shtml",
                        "source": "央视新闻",
                        "date": "2026-04-26",
                        "summary": "失能评估分轻中重三级，两名评估员同时入户，不同等级享受不同保险待遇。",
                    },
                    {
                        "title": "石景山探索失能老人「家庭病床」：不用老人跑，医护上门到",
                        "url": "https://www.beijing.gov.cn/fuwu/bmfw/sy/jrts/202603/t20260314_4557268.html",
                        "source": "北京市人民政府",
                        "date": "2026-03-14",
                        "summary": "设立家庭病床后，医护人员定期上门定制照护方案，高龄、失能、长期卧床老人无需奔波，上门医疗+家庭病床模式在全市推广。",
                    },
                ]
            },
            {
                "title": "政府采购与招投标",
                "items": [
                    {
                        "title": "丰台区养老家庭照护床位建设（适老化改造）公开征集",
                        "url": "https://www.bjft.gov.cn/xxfb/zfgg/202603/t20260327_208673.shtml",
                        "source": "丰台区人民政府",
                        "date": "2026-03-27",
                        "summary": "预算40万元，标准2000元/人，预计服务200人，含评估、改造方案制定及施工验收。",
                    },
                    {
                        "title": "智慧养老服务信息系统升级改造项目招标",
                        "url": "https://project.21csp.com.cn/c171/202604/11429469.html",
                        "source": "中国政府采购网",
                        "date": "2026-04-24",
                        "summary": "智慧养老服务信息系统升级改造，在北京市政府采购电子交易平台获取招标文件。",
                    },
                    {
                        "title": "昌平区1791名离休及处级以上退休干部健康体检成交公告",
                        "url": "https://ggzyfw.beijing.gov.cn/jyxxzbjggg/20260430/5516174.html",
                        "source": "北京市公共资源交易平台",
                        "date": "2026-04-30",
                        "summary": "中标方：昌平区中医医院、北京小汤山医院。",
                    },
                    {
                        "title": "市委老干部局2026年（5月至8月）政府采购意向",
                        "url": "https://www.bjlgbj.gov.cn/lgbjsy/tzgg/202604/t20260427_57772.html",
                        "source": "北京市老干部局",
                        "date": "2026-04-27",
                        "summary": "北京市老干部活动中心发布5-8月采购意向，便于供应商提前了解。",
                    },
                ]
            },
            {
                "title": "银发医养市场动态",
                "items": [
                    {
                        "title": "北京日报：上门医疗+家庭病床，破解高龄老人照护困境",
                        "url": "https://news.bjd.com.cn/2026/03/10/11622818.shtml",
                        "source": "北京日报",
                        "date": "2026-03-10",
                        "summary": "双井第二社区卫生服务中心9个家医团队，签约后可申请肌肉注射、更换胃管尿管、采血等上门医疗服务。",
                    },
                    {
                        "title": "36氪发布《2026年中国银发经济产业研究报告》",
                        "url": "https://m.36kr.com/p/3777435336807172",
                        "source": "36氪研究院",
                        "date": "2026-04-22",
                        "summary": "2025年末我国60岁以上人口达3.23亿（占比23%），银发经济正从传统养老延伸为覆盖「为老」与「备老」的综合性产业体系。",
                    },
                    {
                        "title": "北京市卫健委：2026年慢性病防治项目遴选公告",
                        "url": "https://wjw.beijing.gov.cn/zwgk_20040/tzgg/202604/t20260420_4596687.html",
                        "source": "北京市卫生健康委员会",
                        "date": "2026-04-20",
                        "summary": "围绕全国高血压日、世界卒中日、联合国糖尿病日等开展健康宣传活动，普及慢病防控知识。",
                    },
                ]
            },
        ],
        "notes": [
            "国管局养老服务类投标项目：本轮未检索到相关项目",
            "抗衰老相关政策：本轮未检索到北京市2026年专项政策文件",
            "数据来源：北京市人民政府、中国政府采购网、北京市公共资源交易平台、北京市卫健委、退役军人事务局、央视新闻、光明网、北京日报、36氪研究院",
        ]
    }


def _build_html(data: dict, gen_time: str):
    # Apple-style palette & typography
    color_bg = "#FBFBFD"
    color_card = "#FFFFFF"
    color_text = "#1D1D1F"
    color_text2 = "#6E6E73"
    color_text3 = "#86868B"
    color_accent = "#007AFF"
    color_link = "#0066CC"
    color_divider = "#E5E5EA"
    color_highlight_bg = "#F5F5F7"
    color_highlight_border = "#D2D2D7"
    
    def card_open(margin=16):
        return f'<div style="background:{color_card};border-radius:10px;padding:16px 14px;margin-bottom:{margin}px;box-shadow:0 1px 3px rgba(0,0,0,0.04);border:1px solid {color_divider}">'
    
    def card_close():
        return '</div>'
    
    html = []
    
    # === 主容器 ===
    html.append(f'''
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","PingFang SC","Helvetica Neue",sans-serif;background:{color_bg};color:{color_text};-webkit-font-smoothing:antialiased}}
a{{color:{color_link};text-decoration:none}}
a:hover{{text-decoration:underline}}
</style>
<div style="max-width:720px;margin:0 auto;padding:14px 10px 28px">
''')
    
    # === 头部 ===
    html.append(f'''
<div style="padding:24px 0 18px;border-bottom:1px solid {color_divider};margin-bottom:20px">
    <div style="font-size:11px;font-weight:500;color:{color_text3};letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">Extended Reading</div>
    <h1 style="font-size:24px;font-weight:700;letter-spacing:-0.5px;color:{color_text};margin:0">延伸阅读</h1>
    <div style="font-size:13px;font-weight:400;color:{color_text2};margin-top:6px;line-height:1.5">银发经济决策简报 · 聚焦长护险、家庭医疗、慢病、老干部体检、招投标</div>
    <div style="font-size:11px;color:{color_text3};margin-top:10px">{gen_time}</div>
</div>
''')
    
    # === 核心关注 ===
    core = data.get("core", [])
    if core:
        html.append(f'''
<div style="background:{color_highlight_bg};border:1px solid {color_highlight_border};border-radius:10px;padding:14px 14px;margin-bottom:18px">
    <div style="font-size:10px;font-weight:600;color:{color_accent};letter-spacing:1.5px;text-transform:uppercase;margin-bottom:12px">核心关注</div>
''')
        for i, item in enumerate(core):
            sep = f'border-top:1px solid {color_divider};padding-top:14px;margin-top:14px' if i > 0 else ''
            html.append(f'''
    <div style="{sep}">
        <a href="{item["url"]}" target="_blank" rel="noopener" style="font-size:15px;font-weight:600;color:{color_text};display:block;line-height:1.4;margin-bottom:4px">{item["title"]}</a>
        <div style="font-size:11px;color:{color_text3};margin-bottom:4px">{item["source"]} · {item["date"]}</div>
        <div style="font-size:13px;color:{color_text2};line-height:1.5">{item["summary"]}</div>
    </div>''')
        html.append(card_close())
    
    # === 各板块 ===
    for sec in data.get("sections", []):
        html.append(card_open())
        html.append(f'<div style="font-size:11px;font-weight:600;color:{color_accent};letter-spacing:1.5px;text-transform:uppercase;margin-bottom:14px">{sec["title"]}</div>')
        for i, item in enumerate(sec["items"]):
            sep = f'border-top:1px solid {color_divider};padding-top:14px;margin-top:14px' if i > 0 else ''
            html.append(f'''
        <div style="{sep}">
            <a href="{item["url"]}" target="_blank" rel="noopener" style="font-size:14px;font-weight:600;color:{color_text};display:block;line-height:1.4;margin-bottom:3px">{item["title"]}</a>
            <div style="font-size:11px;color:{color_text3};margin-bottom:3px">{item["source"]} · {item["date"]}</div>
            <div style="font-size:13px;color:{color_text2};line-height:1.5">{item["summary"]}</div>
        </div>''')
        html.append(card_close())
    
    # === 备注 ===
    notes = data.get("notes", [])
    if notes:
        html.append(f'<div style="font-size:12px;color:{color_text3};line-height:1.8;padding:0 4px;margin-top:-8px;margin-bottom:20px">')
        for note in notes:
            html.append(f'<div style="margin-bottom:2px">{note}</div>')
        html.append('</div>')
    
    # === 底部 ===
    html.append(f'''
<div style="text-align:center;padding:24px 0 8px;font-size:11px;color:{color_text3};border-top:1px solid {color_divider};margin-top:8px">
    <div>延伸阅读 · 财务综述 Agent 自动生成</div>
    <div style="margin-top:4px">数据来源：政府公开信息、央媒报道、政府采购平台 · 仅供内部决策参考</div>
    <div style="margin-top:8px"><a href="/" style="color:{color_text3}">返回首页</a></div>
</div>
</div>
''')
    
    return "".join(html)
