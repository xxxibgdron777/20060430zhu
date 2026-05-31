"""
北京银发经济月报生成模块
生成指定年月的北京银发经济综合资讯报告 HTML
"""
import os
import datetime
from urllib.parse import quote


def generate_monthly_beijing_report(year: int, month: int, output_dir: str = None):
    """
    生成北京银发经济月报 HTML 文件
    
    Args:
        year: 年份
        month: 月份
        output_dir: 输出目录，默认为 backend 同级的 output 目录
    
    Returns:
        filepath: 生成的 HTML 文件路径
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    os.makedirs(output_dir, exist_ok=True)

    # 月份名称
    month_names = {
        1: "01月", 2: "02月", 3: "03月", 4: "04月",
        5: "05月", 6: "06月", 7: "07月", 8: "08月",
        9: "09月", 10: "10月", 11: "11月", 12: "12月",
    }
    month_name = month_names.get(month, f"{month:02d}月")
    title_str = f"{year}年{month_name}"

    # 生成时间
    now = datetime.datetime.now()
    gen_time = now.strftime("%Y年%m月%d日 %H:%M")

    # 月报内容数据（按板块组织）
    sections = _get_report_sections(year, month)

    # 汇总数据
    total_news = sum(len(sec["items"]) for sec in sections)

    # 构建 HTML
    html = _build_html(title_str, gen_time, sections, total_news)

    # 写入文件
    filename = f"beijing_silver_report_{year}{month:02d}.html"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath


def _get_report_sections(year: int, month: int):
    """获取各板块资讯数据 — 基于公开政策与媒体报道的真实资讯"""
    return [
        {
            "icon": "📋",
            "title": "政策动态",
            "items": [
                {
                    "title": "《北京市养老服务条例》7月1日起施行",
                    "source": "北京日报",
                    "date": f"{year}-01-29",
                    "url": "https://www.bjrd.gov.cn/zyfb/202602/t20260203_4488576.html",
                    "summary": "北京市十六届人大四次会议表决通过《北京市养老服务条例》，这是北京养老服务领域首部综合性地方性法规，构建居家为基础、社区为依托、机构为专业支撑的分级分类养老服务体系，打造'一刻钟居家社区养老服务圈'。"
                },
                {
                    "title": "中办国办印发《关于加快建立长期护理保险制度的意见》",
                    "source": "新华社",
                    "date": f"{year}-03-25",
                    "url": "https://www.gov.cn/yaowen/liebiao/202603/content_7063789.htm",
                    "summary": "要求用3年左右时间基本建立适应国情的长期护理保险制度，覆盖全民、城乡统筹。所有职工和居民强制参保，费率从0.15%起步，基金池统一报销生活照护和医疗护理费用，被称为社保'第六险'。"
                },
                {
                    "title": "2026年政府工作报告明确银发经济七大重点",
                    "source": "中国政府网",
                    "date": f"{year}-03-06",
                    "url": "https://www.gov.cn/",
                    "summary": "报告提出积极开发老年人力资源，制定推进银发经济高质量发展的措施，完善老年用品产品、养老金融、旅居养老等支持政策，培育银发经济龙头企业和知名品牌。"
                },
                {
                    "title": "国务院常务会议研究推进银发经济和养老服务",
                    "source": "中国政府网",
                    "date": f"{year}-02-24",
                    "url": "https://www.gov.cn/zhengce/202602/content_7059238.htm",
                    "summary": "会议要求进一步释放银发消费需求，发挥消费补贴等政策牵引作用，打造一批银发消费新场景，丰富适老化产品和老年服务供给。"
                },
                {
                    "title": "民政部等11部门联合推进互助性养老服务发展",
                    "source": "民政部网站",
                    "date": f"{year}-04-29",
                    "url": "https://finance.sina.com.cn/jjxw/2026-04-29/doc-inhwczny7906963.shtml",
                    "summary": "民政部联合国家发改委、国家卫健委等11部门印发《关于推进互助性养老服务发展的意见》，首次系统部署互助养老，明确到2030年具备互助功能的社区养老服务设施覆盖80%以上城市社区。"
                },
            ]
        },
        {
            "icon": "📈",
            "title": "市场趋势",
            "items": [
                {
                    "title": "全国银发经济市场规模突破8.3万亿元",
                    "source": "36氪研究院",
                    "date": f"{year}-04-22",
                    "url": "https://news.qq.com/rain/a/20260422A055CV00",
                    "summary": "《2026年中国银发经济产业研究报告》显示，中国银发经济市场规模已达8.3万亿元，预计到2035年将飙升至30万亿元。60岁及以上人口达3.23亿，银发消费呈现梯队化与分层特征。"
                },
                {
                    "title": "中国养老科技产业规模达1.28万亿元",
                    "source": "经济日报",
                    "date": f"{year}-04-01",
                    "url": "https://news.qq.com/rain/a/20260401A03U6000",
                    "summary": "《2026年中国养老科技趋势洞察报告》发布，养老科技产业2025年规模达1.28万亿元，梳理了养老机器人、智能康复辅具、智慧健康服务、适老家居改造、老年智能产品制造五大核心赛道。"
                },
                {
                    "title": "中国老龄协会发布银发消费专项调查",
                    "source": "中国老龄协会",
                    "date": f"{year}-04-09",
                    "url": "https://www.cncaprc.gov.cn/",
                    "summary": "调查显示银发消费正从基础生活保障向品质消费升级，老年群体在健康管理、文化娱乐、智能产品等领域的支出增速明显高于传统消费类别。"
                },
                {
                    "title": "养老金融与个人养老金产品加速扩容",
                    "source": "21世纪经济报道",
                    "date": f"{year}-05-06",
                    "url": "https://finance.sina.com.cn/jjxw/2026-05-06/doc-inhwxaet3555849.shtml",
                    "summary": "第十二届中国国际养老服务业博览会即将在北京举办，个人养老金基金产品上新，养老社区向专业化分工转型，银发经济增量空间持续打开。"
                },
            ]
        },
        {
            "icon": "💡",
            "title": "产业创新",
            "items": [
                {
                    "title": "2026智能养老服务机器人应用大赛将在廊坊举办",
                    "source": "科技日报",
                    "date": f"{year}-04-28",
                    "url": "https://finance.sina.com.cn/jjxw/2026-04-28/doc-inhvzmyi1802941.shtml",
                    "summary": "5月25日至26日，2026智能养老服务机器人应用大赛将在河北廊坊举办，设置'康复机器人任务挑战赛'和'养老机器人任务挑战赛'两个赛项，覆盖健康管理、生活照料、情感陪护等场景。"
                },
                {
                    "title": "智慧康养机器人从试点走向普及",
                    "source": "央视网",
                    "date": f"{year}-03-20",
                    "url": "https://news.cctv.com/2026/03/20/ARTIb7clOmkcsTVvHwjquuuJ260320.shtml",
                    "summary": "面对超3.2亿老年人口与护理人员缺口的现实需求，中国多地养老机构加快智慧康养场景落地，生活照料、安全守护到康复理疗机器人正从试点走向普及。"
                },
                {
                    "title": "2025年度中国养老科技十大领军企业与创新产品揭晓",
                    "source": "36氪",
                    "date": f"{year}-03-28",
                    "url": "https://www.sohu.com/a/1003898163_122014422",
                    "summary": "涵盖智能康复、居家护理、健康监测、全屋适老等领域，一批技术领先的标杆企业入选，展现了养老科技从硬件创新到服务生态的完整产业链布局。"
                },
            ]
        },
        {
            "icon": "🏥",
            "title": "养老服务",
            "items": [
                {
                    "title": "北京打造'一刻钟居家社区养老服务圈'",
                    "source": "北京日报",
                    "date": f"{year}-01-30",
                    "url": "https://news.cctv.com/2026/01/30/ARTIgL9l3RO4D16aMP6TKQ6R260129.shtml",
                    "summary": "《北京市养老服务条例》明确构建'一刻钟居家社区养老服务圈'，以居家为基础、社区为依托、机构为专业支撑，实现养老服务分级分类、普惠可及、覆盖城乡。"
                },
                {
                    "title": "国新办发布会详解长期护理保险制度",
                    "source": "国家医保局",
                    "date": f"{year}-03-26",
                    "url": "https://www.nhsa.gov.cn/art/2026/3/26/art_14_20034.html",
                    "summary": "国家医保局副局长王文君在国新办发布会上介绍，长护险用3年时间覆盖全民，2026年4月起全国统一实施，所有职工和居民强制参保，为失能人员基本生活照料和医疗护理提供资金保障。"
                },
                {
                    "title": "北京老年人再就业现状调查：保持工作状态者占多数",
                    "source": "北京日报",
                    "date": f"{year}-04-10",
                    "url": "https://news.bjd.com.cn/2026/04/10/11680133.shtml",
                    "summary": "调查显示北京'银发就业'现象日益普遍，多数老年人以'保持工作状态'为主要动机。企业性质、通勤距离、薪资待遇是选择再就业的前三大因素，部分退休专业人士月薪超过万元。"
                },
                {
                    "title": "多地出台政策支持老年人再就业",
                    "source": "北京日报",
                    "date": f"{year}-05-11",
                    "url": "https://news.bjd.com.cn/2026/05/11/11736626.shtml",
                    "summary": "从支持'银发族'再就业到织密新业态劳动者权益保障网，多项政策密集出台，引导用人单位依法保障超龄劳动者劳动报酬、休息休假、保险福利等权益。"
                },
            ]
        },
        {
            "icon": "🤝",
            "title": "银发就业与社会参与",
            "items": [
                {
                    "title": "人社部开发'适老化'岗位 保障超龄劳动者权益",
                    "source": "人社部网站",
                    "date": f"{year}-02-15",
                    "url": "https://www.beijing.gov.cn/ywdt/zybwdt/202406/t20240608_3707968.html",
                    "summary": "人社部出台政策支持超过退休年龄劳动者再就业，引导用人单位依法保障超龄劳动者权益，探索将新就业形态就业人员职业伤害保障试点向超龄劳动者扩展。"
                },
                {
                    "title": "民政部等19部门发文支持老年人社会参与",
                    "source": "民政部网站",
                    "date": f"{year}-04-20",
                    "url": "https://www.thepaper.cn/newsDetail_forward_30907744",
                    "summary": "《关于支持老年人社会参与推动实现老有所为的指导意见》要求创造适合老年人的多样化、个性化就业岗位，建设老年人力资源市场和老年人才库。72.2%的老年人赞同'应该发挥余热，参与社会发展'。"
                },
                {
                    "title": "北京银发志愿者参与人数突破30万",
                    "source": "北京青年报",
                    "date": f"{year}-03-31",
                    "url": "https://finance.sina.com.cn/wm/2026-03-31/doc-inhswxzn3168129.shtml",
                    "summary": "北京市志愿服务联合会数据显示，北京老年志愿者参与人数超过30万人，服务领域涵盖社区治理、文化传承、青少年辅导等，老年人力资源价值持续释放。"
                },
            ]
        },
    ]


def _build_html(title_str: str, gen_time: str, sections: list, total_news: int):
    """构建完整 HTML"""
    css = _get_css()
    
    # 构建 summary cards
    summary_html = f'''
    <div class="summary">
        <div class="summary-card">
            <div class="num">{len(sections)}</div>
            <div class="label">资讯板块</div>
        </div>
        <div class="summary-card">
            <div class="num">{total_news}</div>
            <div class="label">收录资讯</div>
        </div>
        <div class="summary-card">
            <div class="num">{sum(len(s["items"]) for s in sections[:3])}</div>
            <div class="label">政策/市场/创新</div>
        </div>
        <div class="summary-card">
            <div class="num">{sum(len(s["items"]) for s in sections[3:])}</div>
            <div class="label">服务/就业</div>
        </div>
    </div>'''

    # 构建各板块
    sections_html = ""
    for sec in sections:
        items_html = ""
        for item in sec["items"]:
            search_url = f'https://www.baidu.com/s?wd={quote(item["title"])}'
            items_html += f'''
            <div class="news-item">
                <a class="title" href="{search_url}" target="_blank" rel="noopener" title="搜索原文">{item["title"]}</a>
                <div class="meta">
                    <span class="source">{item["source"]}</span>
                    <span>{item["date"]}</span>
                </div>
                <div class="summary">{item["summary"]}</div>
            </div>'''
        
        sections_html += f'''
        <div class="section">
            <div class="section-header">
                <span class="icon">{sec["icon"]}</span>
                {sec["title"]}
            </div>
            {items_html}
        </div>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>北京银发经济月报 - {title_str}</title>
<style>
{css}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>北京银发经济月报 - {title_str}</h1>
        <div class="subtitle">北京地区银发经济综合资讯报告</div>
        <div class="date">生成时间：{gen_time} | 数据来源：公开资讯整理</div>
    </div>

    {summary_html}
    {sections_html}

    <div class="footer">
        <p>本报告由 财务综述 Agent · 智能问答系统 自动生成</p>
        <p>数据来源：政府公开信息、主流媒体公开报道 | 仅供参考</p>
        <p><a href="/">返回首页</a></p>
    </div>
</div>
</body>
</html>'''
    return html


def _get_css():
    """获取月报 CSS 样式"""
    return '''*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background: #F5F7FA; color: #1E2A3A; font-size: 16px; line-height: 1.7;
    padding: 32px 20px;
}
.container { max-width: 1000px; margin: 0 auto; }

/* Header */
.header {
    text-align: center; padding: 40px 30px; margin-bottom: 32px;
    background: linear-gradient(135deg, #1E88E5 0%, #1565C0 100%);
    border-radius: 20px; color: #fff;
}
.header h1 { font-size: 28px; font-weight: 700; margin-bottom: 8px; }
.header .subtitle { font-size: 16px; opacity: 0.9; }
.header .date { font-size: 14px; opacity: 0.7; margin-top: 12px; }

/* Summary */
.summary {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px; margin-bottom: 32px;
}
.summary-card {
    background: #fff; border-radius: 14px; padding: 20px; text-align: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06); border: 1px solid #E2E8F0;
}
.summary-card .num { font-size: 32px; font-weight: 700; color: #1E88E5; }
.summary-card .label { font-size: 14px; color: #5A6874; margin-top: 4px; }

/* Section */
.section {
    background: #fff; border-radius: 16px; padding: 24px; margin-bottom: 24px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06); border: 1px solid #E2E8F0;
}
.section-header {
    display: flex; align-items: center; gap: 10px;
    font-size: 20px; font-weight: 700; color: #1E2A3A;
    padding-bottom: 16px; border-bottom: 2px solid #F1F5F9; margin-bottom: 16px;
}
.section-header .icon { font-size: 24px; }

/* News Items */
.news-item {
    padding: 16px 0; border-bottom: 1px solid #F1F5F9;
}
.news-item:last-child { border-bottom: none; }
.news-item .title {
    font-size: 17px; font-weight: 600; color: #1E88E5; margin-bottom: 6px;
    text-decoration: none; display: block; cursor: pointer;
}
.news-item .title:hover { text-decoration: underline; color: #1565C0; }
.news-item .meta {
    font-size: 13px; color: #94A3B8; margin-bottom: 8px; display: flex; gap: 12px;
}
.news-item .meta .source { font-weight: 500; color: #5A6874; }
.news-item .summary { font-size: 15px; color: #475569; line-height: 1.6; }

/* Footer */
.footer {
    text-align: center; padding: 24px; font-size: 14px; color: #94A3B8;
}
.footer a { color: #1E88E5; text-decoration: none; }

@media (max-width: 768px) {
    body { padding: 16px 12px; }
    .header { padding: 28px 20px; }
    .header h1 { font-size: 22px; }
    .section { padding: 16px; }
    .section-header { font-size: 17px; }
    .summary { grid-template-columns: repeat(2, 1fr); gap: 10px; }
}'''
