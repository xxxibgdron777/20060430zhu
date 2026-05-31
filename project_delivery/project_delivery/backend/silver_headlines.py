"""
延伸阅读 — 银发经济决策简报
聚焦：官方政策、行业动态、招投标、适老化改造、行业会议
数据来源：政府官网(.gov.cn)、央媒、政府采购网 — 全部真实可查
数据文件：silver_headlines_data.json — 独立维护，每周日8:00更新
"""

import os
import json
import datetime

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "silver_headlines_data.json")


def _load_data():
    """加载数据文件，过滤过期招投标"""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    today = datetime.date.today()

    # 过滤招投标：移除已过截止日期的项目
    for cat in data.get("categories", []):
        if cat.get("is_bidding"):
            valid_items = []
            for item in cat["items"]:
                dl = item.get("deadline", "")
                if dl:
                    try:
                        dl_date = datetime.date.fromisoformat(dl)
                        if dl_date >= today:
                            valid_items.append(item)
                    except ValueError:
                        valid_items.append(item)  # 日期格式异常保留
                else:
                    valid_items.append(item)
            cat["items"] = valid_items

    return data


def generate_silver_headlines(year: int = None, month: int = None, output_dir: str = None):
    """生成延伸阅读简报（供 main.py /api/generate_report 调用）"""
    now = datetime.datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    os.makedirs(output_dir, exist_ok=True)

    gen_time = now.strftime("%Y年%m月%d日 %H:%M")
    data = _load_data()
    html = _build_html(data, gen_time)

    filename = f"extended_reading_{year}_{month:02d}.html"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath


def _build_html(data: dict, gen_time: str):
    """构建 Apple 风格简报 HTML"""

    # === 配色 ===
    color_bg = "#FBFBFD"
    color_card = "#FFFFFF"
    color_text = "#1D1D1F"
    color_text2 = "#6E6E73"
    color_text3 = "#86868B"
    color_accent = "#007AFF"
    color_link = "#0066CC"
    color_divider = "#E5E5EA"
    color_tag_bg = "#F2F2F7"
    color_deadline_warn = "#FF9500"
    color_icon_bg = "#E8F0FE"

    def card_open(margin=12):
        return f'<div style="background:{color_card};border-radius:12px;padding:16px;margin-bottom:{margin}px;box-shadow:0 1px 3px rgba(0,0,0,0.04);border:1px solid {color_divider}">'

    def card_close():
        return '</div>'

    # 分类图标映射
    icon_map = {
        "policies": "fa-gavel",
        "industry": "fa-chart-line",
        "bidding": "fa-file-contract",
        "elderly_renovation": "fa-house-chimney",
        "events": "fa-calendar-check",
    }

    html = []

    # === 样式 ===
    html.append('''<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","PingFang SC","Helvetica Neue",sans-serif;background:''' + color_bg + ''';color:''' + color_text + ''';-webkit-font-smoothing:antialiased}
a{color:''' + color_link + ''';text-decoration:none}
a:hover{text-decoration:underline}
.deadline-tag{display:inline-block;font-size:10px;padding:2px 8px;border-radius:10px;font-weight:500}
.deadline-active{background:#FFF3E0;color:#E65100}
.category-icon{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:8px;margin-right:8px;font-size:12px}
.policy-item{padding:12px 0;border-bottom:1px solid ''' + color_divider + '''}
.policy-item:last-child{border-bottom:none}
</style>''')

    # === 主容器 ===
    html.append(f'<div style="max-width:720px;margin:0 auto;padding:14px 10px 28px">')

    # === 头部 ===
    last_updated = data.get("last_updated", gen_time)
    html.append(f'''
<div style="padding:20px 0 16px;border-bottom:1px solid {color_divider};margin-bottom:16px">
    <div style="font-size:11px;font-weight:500;color:{color_text3};letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">Extended Reading</div>
    <h1 style="font-size:24px;font-weight:700;letter-spacing:-0.5px;color:{color_text};margin:0">银发经济决策简报</h1>
    <div style="font-size:13px;font-weight:400;color:{color_text2};margin-top:6px;line-height:1.5">聚焦长期政策 · 行业动态 · 招投标 · 适老化改造 · 行业会议</div>
    <div style="font-size:11px;color:{color_text3};margin-top:8px">生成时间：{gen_time} &nbsp;|&nbsp; 数据更新：{last_updated}</div>
</div>''')

    # === 五大分类 ===
    for cat in data.get("categories", []):
        cat_title = cat.get("title", "")
        cat_desc = cat.get("description", "")
        cat_id = cat.get("id", "")
        is_bidding = cat.get("is_bidding", False)
        items = cat.get("items", [])

        if not items:
            continue

        html.append(card_open())
        # 分类标题
        icon = icon_map.get(cat_id, "fa-circle")
        html.append(f'''
    <div style="display:flex;align-items:center;margin-bottom:12px">
        <div style="width:28px;height:28px;border-radius:8px;background:{color_icon_bg};display:flex;align-items:center;justify-content:center;margin-right:10px;font-size:12px;color:{color_accent}">
            <i class="fa-solid {icon}"></i>
        </div>
        <div>
            <div style="font-size:15px;font-weight:700;color:{color_text};line-height:1.3">{cat_title}</div>
            <div style="font-size:11px;color:{color_text3};margin-top:2px">{cat_desc}</div>
        </div>
    </div>''')

        for i, item in enumerate(items):
            title = item.get("title", "")
            url = item.get("url", "")
            source = item.get("source", "")
            date = item.get("date", "")
            summary = item.get("summary", "")
            deadline = item.get("deadline", "")

            html.append(f'<div class="policy-item">')

            # 标题（有链接用 a 标签，否则纯文本）
            if url:
                html.append(f'<a href="{url}" target="_blank" rel="noopener noreferrer" style="font-size:14px;font-weight:600;color:{color_text};display:block;line-height:1.5;margin-bottom:6px">{title}</a>')
            else:
                html.append(f'<span style="font-size:14px;font-weight:600;color:{color_text};display:block;line-height:1.5;margin-bottom:6px">{title}</span>')

            # 来源 + 日期 + 截止日期（招投标类）
            html.append(f'<div style="font-size:11px;color:{color_text3};margin-bottom:6px">')
            html.append(f'<span style="font-weight:500">{source}</span>')
            html.append(f' · {date}')
            if is_bidding and deadline:
                html.append(f' · <span style="color:{color_deadline_warn};font-weight:600">截止：{deadline}</span>')
            html.append('</div>')

            # 摘要
            html.append(f'<div style="font-size:13px;color:{color_text2};line-height:1.6">{summary}</div>')

            html.append('</div>')

        html.append(card_close())

    # === 备注 ===
    notes = data.get("notes", [])
    if notes:
        html.append(f'<div style="font-size:12px;color:{color_text3};line-height:1.8;padding:0 4px;margin-bottom:20px">')
        for note in notes:
            html.append(f'<div style="margin-bottom:2px">· {note}</div>')
        html.append('</div>')

    # === 底部 ===
    html.append(f'''
<div style="text-align:center;padding:24px 0 8px;font-size:11px;color:{color_text3};border-top:1px solid {color_divider};margin-top:8px">
    <div>银发经济决策简报 · 财务综述 Agent 自动生成</div>
    <div style="margin-top:4px">数据来源：政府公开信息、央媒报道、政府采购平台 · 仅供内部决策参考</div>
    <div style="margin-top:8px"><a href="/" style="color:{color_text3}">返回首页</a></div>
</div>
</div>''')

    return "".join(html)


def auto_check_and_clean():
    """自动检查：打印过期招投标和失效数据统计（供 cron 调用）"""
    data = _load_data()
    today = datetime.date.today()
    total_items = 0
    all_tenders = 0
    active_tenders = 0

    for cat in data.get("categories", []):
        total_items += len(cat.get("items", []))
        if cat.get("is_bidding"):
            all_tenders = len(cat.get("items", []))
            active_tenders = len(cat.get("items", []))  # already filtered by _load_data

    # 重新计算（未过滤）
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    raw_tenders = 0
    expired_tenders = 0
    for cat in raw_data.get("categories", []):
        if cat.get("is_bidding"):
            for item in cat.get("items", []):
                raw_tenders += 1
                dl = item.get("deadline", "")
                if dl:
                    try:
                        if datetime.date.fromisoformat(dl) < today:
                            expired_tenders += 1
                    except ValueError:
                        pass

    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] 简报数据检查:")
    print(f"  总条目: {total_items}")
    print(f"  招投标: {raw_tenders} (有效: {raw_tenders - expired_tenders}, 已过期: {expired_tenders})")

    return expired_tenders == 0


if __name__ == "__main__":
    # 直接运行：生成最新简报 + 检查数据状态
    filepath = generate_silver_headlines()
    print(f"简报已生成: {filepath}")
    auto_check_and_clean()
