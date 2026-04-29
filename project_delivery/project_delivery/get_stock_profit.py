"""
东方财富 - 获取股票净利润数据
用法: python get_stock_profit.py 股票代码
例如: python get_stock_profit.py sz300604
"""
import requests
import json
import sys

def get_stock_profit(stock_code):
    """
    从东方财富获取股票的净利润数据
    
    Args:
        stock_code: 股票代码，格式如 sz300604, sh600519
    """
    # 判断交易所前缀
    code = stock_code.lower()
    if code.startswith('sh') or code.startswith('sz') or code.startswith('bj'):
        # 标准格式直接使用
        pass
    elif code.startswith('6'):
        code = 'sh' + code
    elif code.startswith('0') or code.startswith('3'):
        code = 'sz' + code
    elif code.startswith('8') or code.startswith('4'):
        code = 'bj' + code
    else:
        code = 'sz' + code
    
    # 东方财富API接口
    url = f"https://datacenter.eastmoney.com/securities/api/data/v1/get"
    
    params = {
        "reportName": "RPT_LICO_FN_CPD",
        "columns": "ALL",
        "filter": f'(SECURITY_CODE="{code[2:]}")',
        "pageNumber": 1,
        "pageSize": 50,
        "sortTypes": -1,
        "sortColumns": "REPORTDATE",
        "source": "HSF10",
        "client": "HSF10"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://data.eastmoney.com/"
    }
    
    try:
        print(f"正在获取 {code} 的净利润数据...\n")
        response = requests.get(url, params=params, headers=headers, timeout=15)
        data = response.json()
        
        if data.get("result") and data["result"].get("data"):
            items = data["result"]["data"]
            
            print(f"{'报告期':<15} {'净利润(元)':<18}")
            print("-" * 35)
            
            for item in items:
                report_date = item.get("REPORTDATE", "")
                # 格式化日期
                if report_date:
                    report_date = str(report_date)[:10]
                
                # 净利润 - PARENT_NETPROFIT 是母公司净利润
                net_profit = item.get("PARENT_NETPROFIT", "")
                if net_profit is None or net_profit == "":
                    net_profit = "-"
                else:
                    net_profit = format_currency(net_profit)
                
                print(f"{report_date:<15} {net_profit:<18}")
            
            print(f"\n共获取到 {len(items)} 条记录")
        else:
            print(f"未获取到数据，请检查股票代码是否正确: {code}")
            print(f"响应: {data}")
            
    except requests.exceptions.Timeout:
        print("请求超时，请检查网络连接")
    except Exception as e:
        print(f"获取数据时出错: {e}")

def format_currency(value):
    """格式化金额显示"""
    try:
        val = float(value)
        if abs(val) >= 1e8:  # 亿
            return f"{val/1e8:.2f}亿"
        elif abs(val) >= 1e4:  # 万
            return f"{val/1e4:.2f}万"
        else:
            return f"{val:.2f}"
    except:
        return str(value)

def get_stock_profit_by_url(stock_code):
    """
    通过f10接口获取数据（备选方案）
    """
    code = stock_code.lower()
    if code.startswith('6'):
        market = 'sh'
    elif code.startswith('0') or code.startswith('3'):
        market = 'sz'
    elif code.startswith('8') or code.startswith('4'):
        market = 'bj'
    else:
        if len(code) == 6:
            market = 'sz'  # 默认深市
        else:
            market = code[:2]
            code = code[2:]
    
    url = f"http://f10.eastmoney.com/ProfitStatement/ProfitStatementAjax"
    params = {"code": f"{market.upper()}{code}"}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        print(f"\n尝试备用接口获取 {stock_code} 数据...\n")
        response = requests.get(url, params=params, headers=headers, timeout=15)
        data = response.json()
        
        if data and "data" in data:
            items = data["data"]
            if items:
                print(f"{'报告期':<15} {'净利润(元)':<18}")
                print("-" * 35)
                
                for item in items:
                    report_date = item.get("REPORTDATE", "")[:10] if item.get("REPORTDATE") else ""
                    net_profit = item.get("PARENT_NETPROFIT", "")
                    if net_profit:
                        net_profit = format_currency(net_profit)
                    else:
                        net_profit = "-"
                    print(f"{report_date:<15} {net_profit:<18}")
                return True
        print("备用接口也未获取到数据")
        return False
    except Exception as e:
        print(f"备用接口出错: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        stock_code = sys.argv[1]
    else:
        stock_code = input("请输入股票代码（如 300604 或 sz300604）: ").strip()
    
    if not stock_code:
        print("股票代码不能为空")
        sys.exit(1)
    
    # 先尝试主接口
    get_stock_profit(stock_code)
    
    # 如果主接口失败，尝试备用接口
    # get_stock_profit_by_url(stock_code)
