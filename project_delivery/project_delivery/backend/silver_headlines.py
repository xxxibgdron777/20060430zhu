"""
延伸阅读 — 银发经济简报 v2.1
聚焦：官方政策（养老/物业/餐饮/医疗）、税收政策、行业动态
数据来源：政府官网(.gov.cn)、央媒 — 全部真实可查
数据文件：silver_headlines_data.json — 独立维护，每月1号更新
"""
import os
import json
import datetime
import time

# AI API Key fallback（容器无环境变量时使用硬编码）
_DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "") or "sk-28f9f7bc51144cefaf3c570cbb5295b4"
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "silver_headlines_data.json")
VALIDATE_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".link_cache.json")
VALIDATE_CACHE_HOURS = 24  # 链接校验结果缓存24小时

# 需要排除的分类ID（不在页面展示）——当前无排除项，所有分类均展示
EXCLUDED_CATEGORIES = set()


def _validate_links(data):
    """并发校验所有政策链接有效性，返回失效链接集合"""
    # 读取缓存
    cache = {}
    if os.path.exists(VALIDATE_CACHE_FILE):
        try:
            with open(VALIDATE_CACHE_FILE, "r") as f:
                raw = json.load(f)
                ts = raw.get("_ts", 0)
                if time.time() - ts < VALIDATE_CACHE_HOURS * 3600:
                    cache = raw.get("results", {})
        except:
            pass

    # 收集所有需要检查的URL
    urls_to_check = {}
    for cat in data.get("categories", []):
        if cat.get("id") in EXCLUDED_CATEGORIES:
            continue
        items = cat.get("items", [])
        if "sub_categories" in cat:
            for sub in cat["sub_categories"]:
                items.extend(sub.get("items", []))
        for item in items:
            url = item.get("url", "")
            if url and url not in cache:
                urls_to_check[url] = url

    if not urls_to_check:
        return set(url for url, ok in cache.items() if not ok)

    # 并发检查（超时3秒）
    broken = set()
    def _check(url):
        try:
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "Mozilla/5.0")
            resp = urllib.request.urlopen(req, timeout=3)
            return url, resp.status < 400
        except:
            return url, False

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_check, u): u for u in urls_to_check}
        for f in as_completed(futures):
            try:
                url, ok = f.result()
                cache[url] = ok
                if not ok:
                    broken.add(url)
            except:
                pass

    # 更新缓存
    try:
        with open(VALIDATE_CACHE_FILE, "w") as f:
            json.dump({"_ts": time.time(), "results": cache}, f)
    except:
        pass

    # 合并历史失效链接
    broken.update(url for url, ok in cache.items() if not ok)
    return broken


def _load_data(validate=True):
    """加载数据文件，标记失效链接（不删除内容）"""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 校验链接有效性（只标记，不过滤）
    broken_urls = _validate_links(data) if validate else set()

    today = datetime.date.today()
    for cat in data.get("categories", []):
        # 排除指定分类（不展示）
        if cat.get("id") in EXCLUDED_CATEGORIES:
            cat["items"] = []
            continue
        # 标记子分类中的失效链接
        if "sub_categories" in cat:
            for sub in cat["sub_categories"]:
                for item in sub.get("items", []):
                    if item.get("url", "") in broken_urls:
                        item["link_broken"] = True
        # 标记主分类中的失效链接
        for item in cat.get("items", []):
            if item.get("url", "") in broken_urls:
                item["link_broken"] = True

    return data


def generate_silver_headlines(year=None, month=None, output_dir=None):
    """生成延伸阅读简报（供 main.py /api/generate_report 调用）"""
    now = datetime.datetime.now()
    if year is None: year = now.year
    if month is None: month = now.month
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    os.makedirs(output_dir, exist_ok=True)
    gen_time = now.strftime("%Y年%m月%d日 %H:%M")
    data = _load_data(validate=True)
    html = _build_html(data, gen_time)
    filename = f"extended_reading_{year}_{month:02d}.html"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return filepath


def _build_html(data, gen_time):
    """构建简报 HTML（兼容旧版 main.py generate_report 调用）"""
    cats = data.get("categories", [])
    html = _render_categories(cats)
    return html


def policy_chat(user_message, history=None):
    """
    政策咨询 AI — 基于 DeepSeek API
    环境变量: DEEPSEEK_API_KEY
    """
    if history is None:
        history = []
    data = _load_data(validate=False)
    summary = _build_policy_summary(data)
    # 只注入与用户问题相关的政策摘要（关键词匹配，限800字）
    q_lower = user_message.lower()
    relevant_lines = []
    for line in summary.split("\n"):
        if any(kw in line for kw in q_lower.split() if len(kw) >= 2) or line.startswith("【"):
            relevant_lines.append(line)
    filtered_summary = "\n".join(relevant_lines)[:800] if relevant_lines else summary[:500]

    prompt = f"""你是北京养老/物业/餐饮/医疗行业政策专家。根据以下已收录政策内容回答用户问题。
要求：只引用收录内容，不编造。无相关内容时如实告知。回答简洁专业，每条回答不超过200字。

已收录政策摘要：
{filtered_summary}

用户问题：{user_message[:300]}"""
    try:
        api_key = _DEEPSEEK_API_KEY
        if not api_key:
            return {"error": "DEEPSEEK_API_KEY 未配置", "answer": "AI 服务暂不可用，请检查 API Key 配置"}
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        messages = [{"role": "system", "content": prompt[:1500]}]
        for h in history[-6:]:
            role = h.get("role", "user")
            content = h.get("content", "")[:200]
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message[:300]})
        resp = client.chat.completions.create(
            model="deepseek-chat", messages=messages,
            temperature=0.5, max_tokens=500
        )
        answer = resp.choices[0].message.content.strip()
        return {"answer": answer}
    except Exception as e:
        return {"error": str(e), "answer": f"AI 服务调用失败：{str(e)[:100]}"}


def _build_policy_summary(data):
    """构建已收录政策的文本摘要，供 AI 参考"""
    lines = []
    for cat in data.get("categories", []):
        lines.append(f"【{cat['title']}】")
        if "sub_categories" in cat:
            for sub in cat["sub_categories"]:
                lines.append(f"  {sub['title']}:")
                for item in sub["items"][:3]:
                    lines.append(f"    - {item['title']} ({item.get('source','')})")
        else:
            for item in cat.get("items", [])[:3]:
                lines.append(f"  - {item['title']} ({item.get('source','')})")
    return "\n".join(lines)


def _render_categories(cats):
    """渲染所有分类为HTML"""
    sections = []
    for cat in cats:
        if "sub_categories" in cat:
            sections.append(_render_official(cat))
        else:
            items = cat.get("items", [])
            if not items:
                continue
            deadline_class = "bidding" if cat.get("is_bidding") else ""
            items_html = "".join([
                f"""<div class="sl-item {deadline_class}">
                  <a href="{item['url']}" target="_blank" rel="noopener noreferrer" class="sl-title">{item['title']}</a>
                  {f'<span class="sl-broken" title="链接可能已失效">⚠</span>' if item.get('link_broken') else ''}
                  <div class="sl-meta">
                    <span>{item.get('source','')}</span>
                    <span>{item.get('date','')}</span>
                    {f'<span class="sl-deadline">截止：{item["deadline"]}</span>' if item.get('deadline') else ''}
                  </div>
                  {f'<div class="sl-summary">{item["summary"]}</div>' if item.get('summary') else ''}
                </div>""" for item in items
            ])
            sections.append(f"""<div class="sl-card">
              <div class="sl-card-header"><i class="fa-solid fa-{cat.get('icon','circle-info')}"></i> {cat['title']}</div>
              {f'<div class="sl-card-desc">{cat["description"]}</div>' if cat.get('description') else ''}
              <div class="sl-items">{items_html}</div>
            </div>""")
    style = """<style>
.sl-card{background:#fff;border-radius:16px;padding:20px 24px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,0.06);border:1px solid rgba(0,0,0,0.04)}
.sl-card-header{font-size:15px;font-weight:600;color:#1D1D1F;margin-bottom:6px;display:flex;align-items:center;gap:8px}
.sl-card-header i{color:#007AFF;font-size:16px}
.sl-card-desc{font-size:12px;color:#86868B;margin-bottom:12px}
.sl-item{padding:10px 0;border-bottom:1px solid #F2F2F7}
.sl-item:last-child{border-bottom:none}
.sl-title{font-size:14px;color:#0066CC;text-decoration:none;font-weight:500;line-height:1.5}
.sl-title:hover{text-decoration:underline}
.sl-meta{font-size:11px;color:#86868B;margin-top:4px;display:flex;gap:12px;flex-wrap:wrap}
.sl-deadline{color:#FF9500;font-weight:600}
.sl-summary{font-size:12px;color:#6E6E73;margin-top:4px;line-height:1.5}
.sl-subcat{margin-bottom:16px}
.sl-subcat-title{font-size:13px;font-weight:600;color:#1D1D1F;padding:6px 10px;background:#F5F5F7;border-radius:6px;margin-bottom:8px}
.sl-broken{font-size:11px;color:#FF9500;margin-left:4px;cursor:help}
</style>"""
    return style + "".join(sections)


def _render_official(cat):
    """渲染含子分类的官方政策"""
    subs = []
    for sub in cat.get("sub_categories", []):
        items_html = "".join([
            f"""<div class="sl-item">
              <a href="{item['url']}" target="_blank" rel="noopener noreferrer" class="sl-title">{item['title']}</a>
              {f'<span class="sl-broken" title="链接可能已失效">⚠</span>' if item.get('link_broken') else ''}
              <div class="sl-meta"><span>{item.get('source','')}</span><span>{item.get('date','')}</span></div>
              {f'<div class="sl-summary">{item["summary"]}</div>' if item.get('summary') else ''}
            </div>""" for item in sub.get("items", [])
        ])
        subs.append(f"""<div class="sl-subcat">
          <div class="sl-subcat-title">{sub['title']}</div>
          <div class="sl-items">{items_html}</div>
        </div>""")
    desc = cat.get('description', '')
    return f"""<div class="sl-card">
      <div class="sl-card-header"><i class="fa-solid fa-{cat.get('icon','landmark')}"></i> {cat['title']}</div>
      {f'<div class="sl-card-desc">{desc}</div>' if desc else ''}
      {"".join(subs)}
    </div>"""
