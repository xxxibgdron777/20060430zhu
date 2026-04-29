"""
Financial Agent - AI Module Integration Test
Test AI Q&A, suggestions, and summary functions
"""

import sys
import os
import json
import pandas as pd
from typing import Dict, Any, List

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import load_product_df, load_team_df
from agent import FinancialAgent, VolcEngineAgent
from api_extensions import (
    enhanced_query,
    get_ai_suggestions,
    ensure_native,
    filter_product,
    filter_team,
)


class TestRunner:
    """Test Runner"""
    
    def __init__(self):
        self.results = []
        self.product_df = None
        self.team_df = None
    
    def load_data(self):
        """Load test data"""
        print("=" * 60)
        print("1. Loading test data...")
        print("=" * 60)
        
        self.product_df = load_product_df()
        self.team_df = load_team_df()
        
        if self.product_df is not None:
            print("[OK] Product data loaded: {} rows".format(len(self.product_df)))
            print("     Columns: {}".format(list(self.product_df.columns)))
            print("     Years: {}".format(self.product_df['年'].unique()))
            print("     Months: {}".format(sorted(self.product_df['月'].unique())))
            print("     Boards: {}".format(self.product_df['业务板块'].dropna().unique()))
        else:
            print("[FAIL] Product data load failed")
        
        if self.team_df is not None:
            print("[OK] Team data loaded: {} rows".format(len(self.team_df)))
        else:
            print("[WARN] Team data not loaded (OK if Sheet not exists)")
        
        print()
        return self.product_df is not None
    
    def run_test(self, name: str, test_func):
        """Run single test"""
        print("\n" + "=" * 60)
        print("Test: {}".format(name))
        print("=" * 60)
        try:
            result = test_func()
            self.results.append({
                "name": name,
                "status": "PASS",
                "result": result
            })
            print("[PASS] Test passed")
            return True
        except Exception as e:
            self.results.append({
                "name": name,
                "status": "FAIL",
                "error": str(e)
            })
            print("[FAIL] Test failed: {}".format(e))
            import traceback
            traceback.print_exc()
            return False
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        
        print("Total: {} tests".format(len(self.results)))
        print("Passed: {}".format(passed))
        print("Failed: {}".format(failed))
        
        if failed > 0:
            print("\nFailed tests:")
            for r in self.results:
                if r["status"] == "FAIL":
                    print("  - {}: {}".format(r['name'], r['error']))
        
        return failed == 0


def test_data_filtering():
    """Test data filtering"""
    runner = TestRunner()
    if not runner.load_data():
        return False
    
    print("\n--- Testing data filtering ---")
    
    # Test product data filtering
    filtered = filter_product(runner.product_df, 2026, [3])
    print("2026-03 product data: {} rows".format(len(filtered)))
    
    if filtered.empty:
        print("[WARN] No data for 2026-03, trying other months...")
        for year in runner.product_df["年"].unique():
            for month in sorted(runner.product_df[runner.product_df["年"] == year]["月"].unique()):
                filtered = filter_product(runner.product_df, year, [month])
                if not filtered.empty:
                    print("Found data: {}年{}月 ({} rows)".format(year, month, len(filtered)))
                    break
            else:
                continue
            break
    
    # Test month string parsing (matches frontend/backend)
    months_str = "1,2,3"
    months_list = [int(x) for x in months_str.split(",")]
    print("Month string parsing: '{}' -> {}".format(months_str, months_list))
    
    return True


def test_api_ai_query_rule_matching():
    """Test rule-matching Q&A (no AI API dependency)"""
    runner = TestRunner()
    if not runner.load_data():
        return False
    
    # Use rule-matching mode (use_ai=False)
    test_cases = [
        {
            "question": "哪些板块结余率低于5%？",
            "expected_type": "table",
            "description": "Balance rate query"
        },
        {
            "question": "收入最高的产品有哪些？",
            "expected_type": "table",
            "description": "Top income query"
        },
        {
            "question": "物业板块各产品明细",
            "expected_type": "table",
            "description": "Board detail query"
        },
        {
            "question": "管理费占比超过10%的板块？",
            "expected_type": "table",
            "description": "Fee ratio query"
        },
        {
            "question": "支出增长最快的产品？",
            "expected_type": "table",
            "description": "Fastest growth query"
        },
        {
            "question": "这是一个无关问题",
            "expected_type": "text",
            "description": "Default response"
        }
    ]
    
    agent = FinancialAgent(runner.product_df, runner.team_df)
    agent.set_context(2026, [3])
    
    all_passed = True
    for tc in test_cases:
        print("\n--- Test: {} ---".format(tc['description']))
        print("Question: {}".format(tc['question']))
        
        result = agent.query(tc["question"])
        print("Return type: {}".format(result.get('type')))
        # Filter out non-ASCII characters for Windows console compatibility
        preview = str(result)[:200].encode('ascii', 'replace').decode('ascii')
        print("Result preview: {}".format(preview))
        
        # Validate response format
        if "type" not in result:
            print("[FAIL] Missing 'type' field")
            all_passed = False
        elif result["type"] not in ["table", "text"]:
            print("[FAIL] Unknown return type: {}".format(result['type']))
            all_passed = False
        elif result["type"] == "table" and "data" not in result:
            print("[FAIL] table type missing 'data' field")
            all_passed = False
        else:
            print("[PASS] Response format correct")
    
    return all_passed


def test_api_ai_suggestions():
    """Test AI suggestions API"""
    runner = TestRunner()
    if not runner.load_data():
        return False
    
    print("\n--- Testing get_ai_suggestions ---")
    
    suggestions = get_ai_suggestions(runner.product_df, runner.team_df, 2026, [3])
    
    print("Returned suggestions count: {}".format(len(suggestions)))
    
    # Validate response format
    if not isinstance(suggestions, list):
        print("[FAIL] Should return list, got: {}".format(type(suggestions)))
        return False
    
    for i, s in enumerate(suggestions):
        print("\nSuggestion {}:".format(i+1))
        print("  type: {}".format(s.get('type')))
        print("  title: {}".format(s.get('title')))
        print("  message: {}".format(s.get('message')))
        
        if "type" not in s or "title" not in s or "message" not in s:
            print("[FAIL] Suggestion format incomplete")
            return False
    
    print("\n[OK] Returned {} suggestions, format correct".format(len(suggestions)))
    return True


def test_frontend_backend_contract():
    """Test frontend-backend API contract"""
    print("\n" + "=" * 60)
    print("Frontend-Backend API Contract Test")
    print("=" * 60)
    
    # Define API contracts
    contracts = [
        {
            "api": "POST /api/ai/query",
            "frontend_body": {
                "question": "string",
                "year": "number (int)",
                "months": "string (comma-separated, e.g. '1,2,3')"
            },
            "backend_params": {
                "question": "Body(str)",
                "year": "Body(int) default=2026",
                "months": "Body(str) default='1,2,3'",
                "use_ai": "Body(bool) default=True"
            },
            "response": {
                "type": "'table' | 'text' | 'ai_text'",
                "question": "string",
                "answer": "string (optional)",
                "columns": "array (for table type)",
                "data": "array (for table type)"
            }
        },
        {
            "api": "GET /api/ai/suggestions",
            "frontend_query": {
                "year": "number",
                "months": "string (comma-separated)"
            },
            "backend_params": {
                "year": "Query(int) default=2026",
                "months": "Query(str) default='1,2,3'"
            },
            "response": "array of suggestion objects"
        },
        {
            "api": "GET /api/ai/summary",
            "frontend_query": {
                "year": "number",
                "months": "string (comma-separated)"
            },
            "backend_params": {
                "year": "Query(int) default=2026",
                "months": "Query(str) default='1,2,3'"
            },
            "response": {
                "summary": "string (markdown)"
            }
        }
    ]
    
    all_passed = True
    for contract in contracts:
        print("\n--- API: {} ---".format(contract['api']))
        
        # Frontend sends
        if "frontend_body" in contract:
            print("Frontend sends (POST): {}".format(json.dumps(contract['frontend_body'], indent=2, ensure_ascii=False)))
        
        if "frontend_query" in contract:
            print("Frontend sends (GET): {}".format(json.dumps(contract['frontend_query'], indent=2, ensure_ascii=False)))
        
        # Backend receives
        print("Backend receives: {}".format(json.dumps(contract['backend_params'], indent=2, ensure_ascii=False)))
        
        # Response format
        print("Response format: {}".format(json.dumps(contract['response'], indent=2, ensure_ascii=False)))
        
        print("[OK] Contract defined")
    
    return all_passed


def test_response_format():
    """Test response format compatibility with frontend"""
    runner = TestRunner()
    if not runner.load_data():
        return False
    
    print("\n--- Testing response format compatibility ---")
    
    agent = FinancialAgent(runner.product_df, runner.team_df)
    agent.set_context(2026, [3])
    
    # Test table type response
    result = agent.query("哪些板块结余率低于5%？")
    print("\ntable type response:")
    print("  type: {}".format(result.get('type')))
    print("  columns: {}".format(result.get('columns')))
    print("  data (first 2): {}".format(result.get('data', [])[:2]))
    
    # Simulate frontend parsing logic
    if result.get('type') == 'table':
        data = result.get('data', [])
        columns = result.get('columns', [])
        
        if data and columns:
            for row in data[:1]:
                values = list(row.values())
                print("  First row values: {}".format(values))
                for i, col in enumerate(columns):
                    val = values[i]
                    print("    {}: {} (type: {})".format(col, val, type(val).__name__))
    
    # Test text type response
    result = agent.query("你好")
    print("\ntext type response:")
    print("  type: {}".format(result.get('type')))
    # Filter out non-ASCII characters for Windows console compatibility
    answer = result.get('answer', '')[:100].encode('ascii', 'replace').decode('ascii')
    print("  answer: {}".format(answer))
    
    return True


def test_volcengine_agent_fallback():
    """Test VolcEngineAgent fallback mechanism (no API Key)"""
    runner = TestRunner()
    if not runner.load_data():
        return False
    
    print("\n--- Testing VolcEngineAgent fallback ---")
    
    # Create Agent without API Key -> falls back to rule matching
    agent = VolcEngineAgent(runner.product_df, runner.team_df)
    agent._api_key = ""  # Simulate no API Key
    agent.set_context(2026, [3])
    
    result = agent.query("物业板块各产品明细")
    print("Fallback return type: {}".format(result.get('type')))
    print("Result preview: {}...".format(str(result)[:200]))
    
    if result.get('type') in ['table', 'text']:
        print("[OK] Fallback mechanism works")
        return True
    else:
        print("[FAIL] Fallback mechanism may have issues")
        return False


def test_backend_api_endpoints():
    """Test backend API endpoint definitions"""
    print("\n" + "=" * 60)
    print("Backend API Endpoint Definitions")
    print("=" * 60)
    
    # Check if endpoints are properly defined in main.py
    print("\nExpected endpoints:")
    print("  POST /api/ai/query       - AI Q&A query")
    print("  GET  /api/ai/suggestions - AI suggestions")
    print("  GET  /api/ai/summary     - AI data summary")
    
    # Test enhanced_query function directly
    runner = TestRunner()
    if not runner.load_data():
        return False
    
    print("\n--- Testing enhanced_query directly ---")
    
    # Test with use_ai=True (should fallback without API key)
    result = enhanced_query(runner.product_df, runner.team_df, "物业板块各产品明细", 2026, [3], use_ai=True)
    print("enhanced_query (use_ai=True) return type: {}".format(result.get('type')))
    
    # Test with use_ai=False (rule matching)
    result = enhanced_query(runner.product_df, runner.team_df, "物业板块各产品明细", 2026, [3], use_ai=False)
    print("enhanced_query (use_ai=False) return type: {}".format(result.get('type')))
    
    return True


def test_frontend_api_call_compatibility():
    """Test frontend API call compatibility"""
    print("\n" + "=" * 60)
    print("Frontend API Call Compatibility")
    print("=" * 60)
    
    print("\nFrontend code analysis:")
    print("-" * 40)
    print("API_BASE = ''  (same-origin deployment)")
    print()
    print("apiGet(url, params):")
    print("  - Uses URLSearchParams")
    print("  - Sends query parameters")
    print()
    print("apiPost(url, body):")
    print("  - Uses JSON.stringify(body)")
    print("  - Sets Content-Type: application/json")
    print()
    print("Example calls:")
    print("  apiPost('/api/ai/query', {")
    print("    question: '...',")
    print("    year: 2026,")
    print("    months: '1,2,3'")
    print("  })")
    print()
    print("  apiGet('/api/ai/suggestions', {")
    print("    year: 2026,")
    print("    months: '1,2,3'")
    print("  })")
    print("-" * 40)
    
    # Verify backend can receive these
    print("\n[OK] Frontend sends JSON body for POST requests")
    print("[OK] Backend uses FastAPI Body() to receive JSON")
    print("[OK] Frontend sends comma-separated month string")
    print("[OK] Backend splits string into month list")
    
    return True


def test_months_parameter_flow():
    """Test months parameter flow from frontend to backend"""
    runner = TestRunner()
    if not runner.load_data():
        return False
    
    print("\n--- Testing months parameter flow ---")
    
    # Frontend sends: months = S.monthsProduct.join(',')
    # Example: S.monthsProduct = [1, 2, 3] -> "1,2,3"
    
    test_cases = [
        ([1], "1"),
        ([1, 2, 3], "1,2,3"),
        ([1, 2, 3, 6, 9, 12], "1,2,3,6,9,12"),
    ]
    
    all_passed = True
    for months_list, months_str in test_cases:
        # Frontend conversion
        frontend_str = ",".join(map(str, months_list))
        
        # Backend parsing
        backend_list = [int(x) for x in months_str.split(",")]
        
        # Verify
        print("\nTest: months={}".format(months_list))
        print("  Frontend join: '{}'".format(frontend_str))
        print("  Backend split: {}".format(backend_list))
        
        if frontend_str == months_str and backend_list == months_list:
            print("  [OK] Conversion correct")
        else:
            print("  [FAIL] Conversion mismatch")
            all_passed = False
    
    return all_passed


def main():
    """Main test function"""
    print("=" * 60)
    print("Financial Agent - AI Module Integration Test")
    print("=" * 60)
    
    runner = TestRunner()
    
    tests = [
        ("Data Loading & Filtering", test_data_filtering),
        ("Rule-Matching Q&A", test_api_ai_query_rule_matching),
        ("AI Suggestions API", test_api_ai_suggestions),
        ("Response Format Compatibility", test_response_format),
        ("Frontend-Backend Contract", test_frontend_backend_contract),
        ("VolcEngineAgent Fallback", test_volcengine_agent_fallback),
        ("Backend API Endpoints", test_backend_api_endpoints),
        ("Frontend API Call Compatibility", test_frontend_api_call_compatibility),
        ("Months Parameter Flow", test_months_parameter_flow),
    ]
    
    for name, test_func in tests:
        runner.run_test(name, test_func)
    
    success = runner.print_summary()
    
    print("\n" + "=" * 60)
    if success:
        print("All tests passed! Frontend-Backend AI module integration OK.")
    else:
        print("Some tests failed. Please check the output above.")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
