"""
AI 经营分析建议代理
基于 OpenAI/DeepSeek 模型，结合行业知识生成深度分析建议
"""
import os
import json
from typing import List, Dict, Optional
from openai import OpenAI


def _build_analysis_prompt(team_name: str, data: Dict) -> str:
    """
    构建分析提示词，包含多维经营数据
    """
    summary = data.get("summary", {})
    months = data.get("months", [])
    monthly_balance = data.get("monthly_balance", [])
    income_items = data.get("income_items", [])
    expense_items = data.get("expense_items", [])
    fee = data.get("fee", 0)
    total_income = summary.get("income", 0)
    total_expense = summary.get("expense", 0)
    total_balance = total_income - total_expense - fee
    bal_rate = round(total_balance / total_income * 100, 1) if total_income else 0
    fee_ratio = round(fee / total_income * 100, 1) if total_income else 0

    prompt = f"""你是一位资深财务咨询顾问，专精于养老服务行业。请根据以下经营数据，为"{team_name}"团队提供深度经营分析。

## 经营数据
- 收入合计: {total_income:.2f} 万元
- 支出合计: {total_expense:.2f} 万元
- 管理费: {fee:.2f} 万元
- 净结余: {total_balance:.2f} 万元
- 结余率: {bal_rate}%
- 管理费占比: {fee_ratio}%

### 月度结余趋势
{(json.dumps([{'month': m, 'balance': round(b, 2)} for m, b in zip(months[-6:], monthly_balance[-6:])], ensure_ascii=False) if len(monthly_balance) >= 6 else json.dumps(list(zip(months, monthly_balance)), ensure_ascii=False))}

### 收入科目 TOP5
{(json.dumps(income_items[:5], ensure_ascii=False) if income_items else '暂无明细')}

### 支出科目 TOP5
{(json.dumps(expense_items[:5], ensure_ascii=False) if expense_items else '暂无明细')}

## 北京市养老服务行业参考基准
- 养老机构平均结余率: 8%-15%
- 社区养老服务结余率: 3%-10%
- 居家照护结余率: 10%-20%
- 人力成本占总成本比: 55%-70%
- 管理费占收入比: 3%-8%

## 分析要求
请严格按以下5个维度生成分析，每条分析用简洁专业的语言（≤80字），并给出对应的严重程度（info/warning/danger）：

1. **行业对比**：结合北京养老行业基准，对比结余率、费用结构，给出相对行业的优劣评价
2. **趋势预测**：基于近6个月结余趋势做时间序列预判，预测下季度结余变化，给出资金预警
3. **改进建议**：针对该团队类型的 1-2 条具体可操作的改进措施
4. **异常现象**：指出最需要关注的 1 个异常（如无则写"暂未发现明显异常"）
5. **管理动作**：下季度可执行的 1-2 条管理行动

## ⚠️ 重要约束（必须严格遵守）
- 市场/业务收入占比高是好事，绝对不要分析为"单一依赖风险"或"收入集中风险"
- 不要将管理费金额或占比描述为"过高"、"偏高"等负面评价
- 管理费是正常的平台费用支出，不要建议"降低管理费"或"更换服务平台"
- 收入结构单一说明该业务线市场竞争力强，应从优势角度解读

## 输出格式（必须是纯JSON，不要markdown标记）
{{
  "suggestions": [
    {{"category": "行业对比", "type": "info|warning|danger", "content": "建议内容"}},
    {{"category": "趋势预测", "type": "info|warning|danger", "content": "建议内容"}},
    {{"category": "改进建议", "type": "info|warning|danger", "content": "建议内容"}},
    {{"category": "异常现象", "type": "info|warning|danger", "content": "建议内容"}},
    {{"category": "管理动作", "type": "info|warning|danger", "content": "建议内容"}}
  ]
}}"""
    return prompt


def generate_analysis(team_name: str, data: Dict) -> List[Dict]:
    """
    调用 AI 模型生成经营分析建议
    返回: [{"id": "hash", "category": "...", "type": "...", "content": "..."}, ...]
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return _fallback_analysis(team_name, data)

    client = OpenAI(
        base_url="https://api.deepseek.com/v1",
        api_key=api_key,
    )

    prompt = _build_analysis_prompt(team_name, data)

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一位资深的养老服务行业财务顾问。请严格按JSON格式回复，不要输出任何其他内容。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        content = response.choices[0].message.content.strip()

        # 清理可能的 markdown 标记
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        result = json.loads(content)
        suggestions = result.get("suggestions", [])

        # 为每条建议生成唯一ID
        from ratings import suggestion_hash
        for s in suggestions:
            s["id"] = suggestion_hash(s.get("content", ""))

        return suggestions

    except Exception as e:
        print(f"[AnalysisAgent] AI 调用失败: {e}")
        return _fallback_analysis(team_name, data)


def _fallback_analysis(team_name: str, data: Dict) -> List[Dict]:
    """
    规则引擎兜底分析（AI不可用时使用）
    """
    from ratings import suggestion_hash
    summary = data.get("summary", {})
    total_income = summary.get("income", 0)
    total_expense = summary.get("expense", 0)
    fee = data.get("fee", 0)
    total_balance = total_income - total_expense - fee
    bal_rate = round(total_balance / total_income * 100, 1) if total_income else 0

    suggestions = []

    # 1. 行业对比
    if bal_rate > 15:
        s = {"category": "行业对比", "type": "info", "content": f"结余率{bal_rate}%高于北京养老行业平均（8%-15%），盈利能力优于行业基准。"}
    elif bal_rate > 8:
        s = {"category": "行业对比", "type": "info", "content": f"结余率{bal_rate}%处于北京养老行业中等水平（8%-15%），仍有优化空间。"}
    elif bal_rate > 0:
        s = {"category": "行业对比", "type": "warning", "content": f"结余率{bal_rate}%低于北京养老行业基准（8%-15%），需关注成本结构优化。"}
    else:
        s = {"category": "行业对比", "type": "danger", "content": f"结余率为负（{bal_rate}%），远低于行业基准，面临经营风险。"}
    s["id"] = suggestion_hash(s["content"])
    suggestions.append(s)

    # 2. 趋势预测
    monthly_balance = data.get("monthly_balance", [])
    if len(monthly_balance) >= 3:
        recent = monthly_balance[-3:]
        trend = sum(recent) / len(recent) if recent else 0
        if trend < 0:
            s = {"category": "趋势预测", "type": "danger", "content": f"近3月平均结余{trend:.1f}万为负，按当前趋势下季度可能继续亏损，建议立即启动降本增效措施。"}
        elif len(monthly_balance) >= 5 and monthly_balance[-1] < monthly_balance[-3]:
            s = {"category": "趋势预测", "type": "warning", "content": f"结余呈下降趋势（{monthly_balance[-3]:.1f}→{monthly_balance[-1]:.1f}万），预计下季度可能收窄至{max(0, monthly_balance[-1]*0.9):.1f}万。"}
        else:
            s = {"category": "趋势预测", "type": "info", "content": f"近3月结余稳定在{trend:.1f}万左右，预计下季度可维持该水平，建议关注季节性波动。"}
    else:
        s = {"category": "趋势预测", "type": "info", "content": "数据不足，尚无法进行趋势预测，建议积累至少3个月数据后重新评估。"}
    s["id"] = suggestion_hash(s["content"])
    suggestions.append(s)

    # 3. 改进建议
    if total_balance < 0:
        s = {"category": "改进建议", "type": "danger", "content": "当前处于亏损状态，建议：1）审查高支出科目寻找降本点；2）拓展高毛利服务增加收入。"}
    elif bal_rate < 5:
        s = {"category": "改进建议", "type": "warning", "content": f"结余率仅{bal_rate}%，建议优化非必要支出、提升服务收费合理性。"}
    else:
        s = {"category": "改进建议", "type": "info", "content": "建议优化人力排班降低闲置率，同时推进数字化管理工具应用提升运营效率。"}
    s["id"] = suggestion_hash(s["content"])
    suggestions.append(s)

    # 4. 异常现象
    expense_items = data.get("expense_items", [])
    high_item = None
    max_ratio = 0
    for item in expense_items:
        ratio = item.get("金额", 0) / total_expense * 100 if total_expense else 0
        if ratio > max_ratio:
            max_ratio = ratio
            high_item = item
    if high_item and max_ratio > 40:
        s = {"category": "异常现象", "type": "warning", "content": f"支出科目"{high_item.get('科目','')}"占比达{max_ratio:.0f}%，远超正常水平，需重点审查。"}
    else:
        s = {"category": "异常现象", "type": "info", "content": "暂未发现明显异常数据点，各科目支出分布相对合理。"}
    s["id"] = suggestion_hash(s["content"])
    suggestions.append(s)

    # 5. 管理动作
    s = {"category": "管理动作", "type": "info", "content": "下季度建议：1）制定月度预算审核机制；2）推动服务标准化降低单位成本。"}
    if total_balance < 0:
        s["content"] = "下季度紧急行动：1）两周内完成成本结构审查；2）指定专人对亏损板块限期扭亏。"
        s["type"] = "danger"
    s["id"] = suggestion_hash(s["content"])
    suggestions.append(s)

    return suggestions
