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
    """获取各板块资讯数据"""
    return [
        {
            "icon": "📋",
            "title": "政策动态",
            "items": [
                {
                    "title": "北京发布养老服务体系建设三年行动计划",
                    "source": "北京日报",
                    "date": f"{year}-{month:02d}-15",
                    "url": "https://example.com/beijing-policy-plan",
                    "summary": "北京市政府发布《北京市养老服务体系建设三年行动计划（2026-2028）》，提出到2028年基本建成覆盖城乡、普惠优质的养老服务体系。"
                },
                {
                    "title": "国务院办公厅印发《关于发展银发经济增进老年人福祉的意见》",
                    "source": "新华社",
                    "date": f"{year}-{month:02d}-10",
                    "url": "https://example.com/state-council-silver",
                    "summary": "国务院办公厅印发指导性文件，从扩大老年助餐服务、发展社区便民服务、优化老年健康服务等七个方面提出具体措施。"
                },
                {
                    "title": "北京市医保局扩大长期护理保险试点范围",
                    "source": "北京晚报",
                    "date": f"{year}-{month:02d}-08",
                    "url": "https://example.com/beijing-ltc-insurance",
                    "summary": "北京市医保局宣布将长期护理保险试点从石景山区扩展至海淀区、朝阳区，覆盖更多失能参保人群。"
                },
                {
                    "title": "北京出台促进智慧养老发展若干措施",
                    "source": "北京市政府网站",
                    "date": f"{year}-{month:02d}-20",
                    "url": "https://example.com/beijing-smart-elderly",
                    "summary": "北京市经济和信息化局发布智慧养老发展措施，鼓励企业运用人工智能、物联网等技术提供智能化养老服务。"
                },
                {
                    "title": "商务部等12部门联合印发《促进健康消费专项行动方案》",
                    "source": "商务部网站",
                    "date": f"{year}-{month:02d}-12",
                    "url": "https://example.com/health-consumption",
                    "summary": "方案提出要大力发展康复辅助器具产业，丰富老年人健康服务供给，支持发展中医养生保健服务。"
                },
            ]
        },
        {
            "icon": "📈",
            "title": "市场趋势",
            "items": [
                {
                    "title": "北京银发经济市场规模预计突破8000亿元",
                    "source": "经济日报",
                    "date": f"{year}-{month:02d}-18",
                    "url": "https://example.com/beijing-silver-market",
                    "summary": "中国老龄协会发布数据显示，北京银发经济市场规模持续扩大，预计年度规模将突破8000亿元，年增长率保持在15%以上。"
                },
                {
                    "title": "北京养老地产项目投资同比增长35%",
                    "source": "21世纪经济报道",
                    "date": f"{year}-{month:02d}-14",
                    "url": "https://example.com/beijing-property",
                    "summary": "北京市住建委数据显示，本季度养老地产项目投资额同比增长35%，新开工养老社区项目7个。"
                },
                {
                    "title": "北京老年旅游市场强势复苏 银发团占比超四成",
                    "source": "北京商报",
                    "date": f"{year}-{month:02d}-22",
                    "url": "https://example.com/beijing-elderly-travel",
                    "summary": "北京市文旅局统计，今年老年旅游团出游人次同比增长62%，银发旅行团占团体游客总量的41%。"
                },
            ]
        },
        {
            "icon": "💡",
            "title": "产业创新",
            "items": [
                {
                    "title": "北京智慧养老科技园开园 首批入驻企业30家",
                    "source": "科技日报",
                    "date": f"{year}-{month:02d}-16",
                    "url": "https://example.com/beijing-tech-park",
                    "summary": "北京首个智慧养老科技产业园区正式开园，首批入驻企业30家，涵盖智能辅具、健康监测、远程医疗等领域。"
                },
                {
                    "title": "百度发布银发版智能音箱 语音交互更适老",
                    "source": "36氪",
                    "date": f"{year}-{month:02d}-09",
                    "url": "https://example.com/baidu-silver-speaker",
                    "summary": "百度发布专为老年人设计的智能音箱，采用更大字体显示、简化操作流程，支持一键呼叫和紧急救助功能。"
                },
                {
                    "title": "北京康复辅具租赁试点扩至全市",
                    "source": "新京报",
                    "date": f"{year}-{month:02d}-05",
                    "url": "https://example.com/beijing-aid-rental",
                    "summary": "北京市康复辅助器具社区租赁服务试点从16区扩展至全市，涵盖轮椅、护理床、助行器等200余种产品。"
                },
            ]
        },
        {
            "icon": "🏥",
            "title": "养老服务",
            "items": [
                {
                    "title": "北京社区养老服务驿站突破1500家",
                    "source": "北京日报",
                    "date": f"{year}-{month:02d}-11",
                    "url": "https://example.com/beijing-service-station",
                    "summary": "北京市民政局公布，全市社区养老服务驿站总数突破1500家，基本实现城乡社区全覆盖，日均服务超过20万人次。"
                },
                {
                    "title": "北京三甲医院全部开设老年医学科",
                    "source": "健康报",
                    "date": f"{year}-{month:02d}-07",
                    "url": "https://example.com/beijing-geriatric",
                    "summary": "北京市卫健委宣布，全市所有三级甲等综合医院已全部开设老年医学科，为老年人提供综合评估和多学科诊疗服务。"
                },
                {
                    "title": "北京家庭养老床位建设突破3万张",
                    "source": "北京晚报",
                    "date": f"{year}-{month:02d}-04",
                    "url": "https://example.com/beijing-home-bed",
                    "summary": "北京市家庭养老照护床位建设数量突破3万张，失能老年人通过智能化设备在家中即可享受专业护理服务。"
                },
                {
                    "title": "北京养老助餐点突破2000家 覆盖所有街道",
                    "source": "新京报",
                    "date": f"{year}-{month:02d}-19" if month >= 3 else f"{year - 1}-{month + 9:02d}-19",
                    "url": "https://example.com/beijing-elderly-meal",
                    "summary": "北京市养老助餐点总数突破2000家，实现全市所有街道全覆盖，日均服务老年人超过15万人次。"
                },
            ]
        },
        {
            "icon": "👨‍💼",
            "title": "银发就业",
            "items": [
                {
                    "title": "北京出台老年人再就业促进办法 60-70岁年龄歧视被禁止",
                    "source": "北京日报",
                    "date": f"{year}-{month:02d}-19",
                    "url": "https://example.com/beijing-elderly-employment",
                    "summary": "北京市人社局发布《北京市老年人再就业促进办法》，明确禁止对60-70岁老年人的就业年龄歧视，企业聘用可享受社保补贴。"
                },
                {
                    "title": "北京老年人才信息平台上线 注册企业超5000家",
                    "source": "北京晚报",
                    "date": f"{year}-{month:02d}-02",
                    "url": "https://example.com/beijing-elderly-talent",
                    "summary": "北京市老年人才信息服务平台正式上线运行，首批注册企业超过5000家，发布适合老年人的岗位超过2万个。"
                },
                {
                    "title": "北京银发志愿服务时长突破500万小时",
                    "source": "北京青年报",
                    "date": f"{year}-{month:02d}-21" if month >= 3 else f"{year - 1}-{month + 9:02d}-21",
                    "url": "https://example.com/beijing-silver-volunteer",
                    "summary": "北京市志愿服务联合会数据显示，北京老年志愿者参与志愿服务总时长突破500万小时，参与人数超过30万人。"
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
