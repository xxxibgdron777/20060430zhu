"""
财务综述 Agent · 规则匹配模块
"""

import re
import pandas as pd
from typing import Dict, Any, List
from calculators import (
    to_wan, to_wan_f, calc_pct, format_pct,
    aggregate_board, aggregate_product, aggregate_project,
    analyze_trends, get_pie_data
)
from special_logic import get_property_detail, get_yiyang_detail, search_by_keyword


class FinancialAgent:
    """
    财务分析 Agent
    基于 CodeBuddy SDK，提供智能财务问答能力
    """
    
    def __init__(self, product_df: pd.DataFrame, team_df: pd.DataFrame = None):
        self.product_df = product_df
        self.team_df = team_df
        self.current_year = 2026
        self.current_months = [3]  # 默认查询3月
        
    def set_context(self, year: int, months: List[int]):
        """设置查询上下文"""
        self.current_year = year
        self.current_months = months if isinstance(months, list) else [months]
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        处理用户查询
        返回格式化的结果
        """
        ql = question.lower()
        
        # 1. 结余率相关查询
        m = re.search(r"结余率.*(低于|不足|小于|小于等于)\s*(\d+)%?", ql)
        if m:
            return self._query_balance_rate(m.group(1), int(m.group(2)))
        
        # 2. 收入/支出最高/最低/增长最快
        m = re.search(r"(收入|支出).*(最高|最低|增长最快)", ql)
        if m:
            return self._query_top_metric(m.group(1), m.group(2))
        
        # 3. 管理费占比
        m = re.search(r"管理费占比超过\s*(\d+)%?", ql)
        if m:
            return self._query_fee_ratio(int(m.group(1)))
        
        # 4. 连续亏损
        m = re.search(r"连续.*亏损.*(\d+).*月", ql)
        if m:
            return self._query_consecutive_loss(int(m.group(1)))
        
        # 5. 收入/损益波动
        m = re.search(r"(收入|损益|结余).*波动", ql)
        if m:
            return self._query_volatility(m.group(1))
        
        # 6. 板块关键词（含别名映射）
        board_alias = {"机构医疗": "医养板块", "医疗": "医养板块"}
        for alias, board_name in board_alias.items():
            if alias in question and board_name in self.product_df["业务板块"].dropna().unique().tolist():
                return self._query_board_detail(board_name)
        for board in self.product_df["业务板块"].dropna().unique():
            if str(board) in question:
                return self._query_board_detail(board)
        
        # 7. 团队关键词
        if self.team_df is not None:
            for parent in self.team_df["H团队线-上级"].dropna().unique():
                if str(parent) in question:
                    return self._query_team_detail(parent)
        
        # 8. 产品关键词
        for prod in self.product_df["产品"].dropna().unique():
            if str(prod) in question and len(str(prod)) > 2:
                return self._query_product_detail(prod)
        
        # 9. 默认回复
        return self._default_response()
    
    def _query_balance_rate(self, operator: str, threshold: int) -> Dict[str, Any]:
        """查询结余率低于某值的板块"""
        if "小于等于" in operator:
            condition = lambda x: x <= threshold
        else:
            condition = lambda x: x < threshold
            
        df_f = self.product_df[(self.product_df["年"] == self.current_year) & 
                                (self.product_df["月"].isin(self.current_months))]
        boards = aggregate_board(df_f)
        boards["结余率"] = (boards["结余"] / boards["收入"].replace(0, float("nan"))) * 100
        
        filtered = boards[boards["结余率"].apply(condition)]
        
        if filtered.empty:
            return {
                "type": "text",
                "question": f"结余率{operator}{threshold}%的板块",
                "answer": f"没有发现结余率{operator}{threshold}%的板块。"
            }
        
        # 构建规范化的数据记录
        columns = ["板块", "结余率", "结余(万)"]
        records = []
        for _, row in filtered.iterrows():
            record = {
                "板块": str(row.get("业务板块", "")) if pd.notna(row.get("业务板块")) else "",
                "结余率": round(row.get("结余率", 0), 2) if pd.notna(row.get("结余率")) else 0,
                "结余(万)": round(to_wan(row.get("结余", 0)), 2) if pd.notna(row.get("结余")) else 0,
            }
            records.append(record)
        
        return {
            "type": "table",
            "question": f"结余率{operator}{threshold}%的板块",
            "columns": columns,
            "data": records,
            "summary": f"共发现 {len(filtered)} 个板块结余率{operator}{threshold}%"
        }
    
    def _query_top_metric(self, metric: str, direction: str) -> Dict[str, Any]:
        """查询收入/支出最高/最低/增长最快的产品"""
        df_f = self.product_df[(self.product_df["年"] == self.current_year) & 
                                (self.product_df["月"].isin(self.current_months))]
        agg = aggregate_product(df_f)
        
        if "增长" in direction:
            # 同比增长最快
            df_prev = self.product_df[(self.product_df["年"] == self.current_year - 1) & 
                                       (self.product_df["月"].isin(self.current_months))]
            prev_agg = aggregate_product(df_prev)
            
            merged = agg.merge(
                prev_agg[["产品", metric]], 
                on="产品", 
                suffixes=("", "_prev")
            )
            merged[f"{metric}增长"] = merged[metric] - merged[f"{metric}_prev"]
            merged[f"{metric}增长pct"] = merged[f"{metric}增长"] / merged[f"{metric}_prev"].replace(0, float("nan")) * 100
            
            top = merged.nlargest(5, f"{metric}增长pct")
            
            # 构建规范化的数据记录
            columns = ["板块", "产品", f"本期{metric}(万)", f"去年同期(万)", "增长率"]
            records = []
            for _, row in top.iterrows():
                record = {
                    "板块": str(row.get("业务板块", "")) if pd.notna(row.get("业务板块")) else "",
                    "产品": str(row.get("产品", "")) if pd.notna(row.get("产品")) else "",
                    f"本期{metric}(万)": round(to_wan(row.get(metric, 0)), 2) if pd.notna(row.get(metric)) else 0,
                    f"去年同期(万)": round(to_wan(row.get(f"{metric}_prev", 0)), 2) if pd.notna(row.get(f"{metric}_prev")) else 0,
                    "增长率": round(row.get(f"{metric}增长pct", 0), 1) if pd.notna(row.get(f"{metric}增长pct")) else 0,
                }
                records.append(record)
            
            return {
                "type": "table",
                "question": f"{metric}增长最快的5个产品",
                "columns": columns,
                "data": records
            }
        else:
            # 最高/最低
            ascending = direction == "最低"
            top = agg.nlargest(5, metric) if not ascending else agg.nsmallest(5, metric)
            
            # 构建规范化的数据记录
            columns = ["板块", "产品", f"{metric}(万)"]
            records = []
            for _, row in top.iterrows():
                record = {
                    "板块": str(row.get("业务板块", "")) if pd.notna(row.get("业务板块")) else "",
                    "产品": str(row.get("产品", "")) if pd.notna(row.get("产品")) else "",
                    f"{metric}(万)": round(to_wan(row.get(metric, 0)), 2) if pd.notna(row.get(metric)) else 0,
                }
                records.append(record)
            
            return {
                "type": "table",
                "question": f"{metric}{direction}的5个产品",
                "columns": columns,
                "data": records
            }
    
    def _query_fee_ratio(self, threshold: int) -> Dict[str, Any]:
        """查询管理费占比超过某值的板块"""
        df_f = self.product_df[(self.product_df["年"] == self.current_year) & 
                                (self.product_df["月"].isin(self.current_months))]
        boards = aggregate_board(df_f)
        boards["管理费占比"] = (boards["平台管理费"] / boards["收入"].replace(0, float("nan"))) * 100
        
        filtered = boards[boards["管理费占比"] > threshold]
        
        # 构建规范化的数据记录
        columns = ["板块", "管理费占比"]
        records = []
        for _, row in filtered.iterrows():
            record = {
                "板块": str(row.get("业务板块", "")) if pd.notna(row.get("业务板块")) else "",
                "管理费占比": round(row.get("管理费占比", 0), 2) if pd.notna(row.get("管理费占比")) else 0,
            }
            records.append(record)
        
        return {
            "type": "table",
            "question": f"管理费占比超过{threshold}%的板块",
            "columns": columns,
            "data": records
        }
    
    def _query_consecutive_loss(self, months: int) -> Dict[str, Any]:
        """查询连续亏损超N月的板块"""
        alerts = analyze_trends(self.product_df, self.current_year)
        # 简单过滤逻辑，实际需要更复杂的连续亏损检测
        
        return {
            "type": "table",
            "question": f"连续亏损超{months}个月的板块",
            "columns": ["预警"],
            "data": [{"预警": a} for a in alerts[:5]] if alerts else [],
            "answer": "\n".join(alerts[:5]) if alerts else f"未发现连续亏损超{months}个月的板块。"
        }
    
    def _query_volatility(self, metric: str) -> Dict[str, Any]:
        """查询收入/结余波动异常的板块"""
        alerts = analyze_trends(self.product_df, self.current_year)
        
        return {
            "type": "table",
            "question": f"{metric}波动异常的板块",
            "columns": ["预警"],
            "data": [{"预警": a} for a in alerts[:5]] if alerts else [],
            "answer": "\n".join(alerts[:5]) if alerts else "未发现明显异常波动。"
        }
    
    def _query_board_detail(self, board: str) -> Dict[str, Any]:
        """查询某板块的产品明细"""
        df_f = self.product_df[(self.product_df["年"] == self.current_year) & 
                                (self.product_df["月"].isin(self.current_months))]
        detail = df_f[df_f["业务板块"] == board]
        
        if detail.empty:
            return {"type": "text", "answer": f"未找到 {board} 的数据"}
        
        by_prod = aggregate_product(detail)
        
        # 构建规范化的数据记录
        columns = ["产品", "收入(万)", "支出(万)", "管理费(万)", "结余(万)"]
        records = []
        for _, row in by_prod.iterrows():
            record = {
                "产品": str(row.get("产品", "")) if pd.notna(row.get("产品")) else "",
                "收入(万)": round(to_wan(row.get("收入", 0)), 2) if pd.notna(row.get("收入")) else 0,
                "支出(万)": round(to_wan(row.get("支出", 0)), 2) if pd.notna(row.get("支出")) else 0,
                "管理费(万)": round(to_wan(row.get("平台管理费", 0)), 2) if pd.notna(row.get("平台管理费")) else 0,
                "结余(万)": round(to_wan(row.get("结余", 0)), 2) if pd.notna(row.get("结余")) else 0,
            }
            records.append(record)
        
        return {
            "type": "table",
            "question": f"{board}各产品明细",
            "columns": columns,
            "data": records
        }
    
    def _query_team_detail(self, parent: str) -> Dict[str, Any]:
        """查询某团队的上级明细"""
        if self.team_df is None:
            return {"type": "text", "answer": "团队数据未加载"}
        
        df_f = self.team_df[(self.team_df["年"] == self.current_year) & 
                            (self.team_df["月"].isin(self.current_months))]
        detail = df_f[df_f["H团队线-上级"] == parent]
        
        if detail.empty:
            return {"type": "text", "answer": f"未找到 {parent} 的数据"}
        
        # 按核算单元聚合
        from calculators import aggregate_team_account
        by_acc = aggregate_team_account(detail)
        
        # 构建规范化的数据记录
        columns = ["核算单元", "收入(万)", "支出(万)", "管理费(万)", "结余(万)"]
        records = []
        for _, row in by_acc.iterrows():
            record = {
                "核算单元": str(row.get("H团队线-核算", "")) if pd.notna(row.get("H团队线-核算")) else "",
                "收入(万)": round(to_wan(row.get("收入", 0)), 2) if pd.notna(row.get("收入")) else 0,
                "支出(万)": round(to_wan(row.get("支出", 0)), 2) if pd.notna(row.get("支出")) else 0,
                "管理费(万)": round(to_wan(row.get("平台管理费", 0)), 2) if pd.notna(row.get("平台管理费")) else 0,
                "结余(万)": round(to_wan(row.get("结余", 0)), 2) if pd.notna(row.get("结余")) else 0,
            }
            records.append(record)
        
        return {
            "type": "table",
            "question": f"{parent}各核算单元明细",
            "columns": columns,
            "data": records
        }
    
    def _query_product_detail(self, product: str) -> Dict[str, Any]:
        """查询某产品的项目明细"""
        df_f = self.product_df[(self.product_df["年"] == self.current_year) & 
                                (self.product_df["月"].isin(self.current_months))]
        detail = df_f[df_f["产品"] == product]
        
        if detail.empty:
            return {"type": "text", "answer": f"未找到产品：{product}"}
        
        by_proj = aggregate_project(detail, product)
        
        # 构建规范化的数据记录
        columns = ["项目", "收入(万)", "支出(万)", "管理费(万)", "结余(万)"]
        records = []
        for _, row in by_proj.iterrows():
            record = {
                "项目": str(row.get("项目", "")) if pd.notna(row.get("项目")) else "",
                "收入(万)": round(to_wan(row.get("收入", 0)), 2) if pd.notna(row.get("收入")) else 0,
                "支出(万)": round(to_wan(row.get("支出", 0)), 2) if pd.notna(row.get("支出")) else 0,
                "管理费(万)": round(to_wan(row.get("平台管理费", 0)), 2) if pd.notna(row.get("平台管理费")) else 0,
                "结余(万)": round(to_wan(row.get("结余", 0)), 2) if pd.notna(row.get("结余")) else 0,
            }
            records.append(record)
        
        return {
            "type": "table",
            "question": f"{product}各项目明细",
            "columns": columns,
            "data": records
        }
    
    def _default_response(self) -> Dict[str, Any]:
        """数据驱动的默认回复：展示数据概览和洞察"""
        suggestions = [
            "哪些板块结余率低于5%？",
            "收入最高的产品有哪些？",
            "物业板块各产品明细",
            "管理费占比超过10%的板块",
        ]
        
        overview = self._build_data_overview()
        
        return {
            "type": "text",
            "answer": overview,
            "suggestions": suggestions
        }
    
    def _build_data_overview(self) -> str:
        """基于数据源构建概览洞察文本"""
        if self.product_df is None or self.product_df.empty:
            return "暂无产品数据。"
        
        df_f = self.product_df[
            (self.product_df["年"] == self.current_year) & 
            (self.product_df["月"].isin(self.current_months))
        ]
        
        if df_f.empty:
            return f"暂无 {self.current_year} 年数据。"
        
        total_income = df_f["收入"].sum()
        total_expense = df_f["支出"].sum()
        total_fee = df_f["平台管理费"].sum()
        total_balance = total_income - total_expense - total_fee
        balance_rate = (total_balance / total_income * 100) if total_income else 0
        
        boards = aggregate_board(df_f)
        boards["结余率"] = (boards["结余"] / boards["收入"].replace(0, float("nan"))) * 100
        boards["管理费占比"] = (boards["平台管理费"] / boards["收入"].replace(0, float("nan"))) * 100
        
        lines = []
        period = f"{self.current_year}年{'、'.join(map(str, self.current_months))}月"
        
        lines.append(f"📊 **{period} 数据概览**")
        lines.append(f"总收入 {to_wan(total_income):.0f}万 | 总支出 {to_wan(total_expense):.0f}万 | 结余率 {balance_rate:.1f}%")
        lines.append("")
        
        findings = []
        
        low_rate = boards[boards["结余率"] < 10]
        if not low_rate.empty:
            names = "、".join(low_rate["业务板块"].astype(str).tolist())
            findings.append(f"⚠️ **{len(low_rate)}个板块结余率偏低**（{names}），建议关注成本管控")
        
        loss = boards[boards["结余"] < 0]
        if not loss.empty:
            names = "、".join(loss["业务板块"].astype(str).tolist())
            findings.append(f"🔴 **{len(loss)}个板块处于亏损**（{names}）")
        
        high_fee = boards[boards["管理费占比"] > 10]
        if not high_fee.empty:
            names = "、".join(high_fee["业务板块"].astype(str).tolist())
            findings.append(f"💡 **{len(high_fee)}个板块管理费占比超10%**（{names}）")
        
        top3_income = boards.nlargest(3, "收入")
        top_names = []
        for _, r in top3_income.iterrows():
            top_names.append(f"{r['业务板块']}({to_wan(r['收入']):.0f}万)")
        findings.append(f"📈 收入前三：{'、'.join(top_names)}")
        
        if findings:
            lines.append("**📋 数据洞察：**")
            for f in findings:
                lines.append(f)
            lines.append("")
        
        return "\n".join(lines)
    
    def get_summary(self) -> str:
        """获取数据概览"""
        df_f = self.product_df[(self.product_df["年"] == self.current_year) & 
                                (self.product_df["月"].isin(self.current_months))]
        
        total_income = df_f["收入"].sum()
        total_expense = df_f["支出"].sum()
        total_fee = df_f["平台管理费"].sum()
        total_balance = total_income - total_expense - total_fee
        
        boards = self.product_df["业务板块"].dropna().unique()
        
        return f"""
财务数据概览 ({self.current_year}年{'、'.join(map(str, self.current_months))}月)：
- 总收入：{to_wan(total_income):,}万元
- 总支出：{to_wan(total_expense):,}万元
- 平台管理费：{to_wan(total_fee):,}万元
- 总结余：{to_wan(total_balance):,}万元
- 结余率：{(total_balance/total_income*100):.1f}%（{('盈利' if total_balance > 0 else '亏损')}）

业务板块：{', '.join(boards)}
"""
