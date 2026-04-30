#!/usr/bin/env python3
"""Check product drill API data structure"""
import subprocess, json

# POST to product drill
r = subprocess.run(['curl','-s','-X','POST','http://localhost/api/product/drill',
    '-H','Content-Type: application/json',
    '-d','{"year":2026,"months":[1,2,3,4,5,6],"page":1,"page_size":20,"level":"board"}'],
    capture_output=True,text=True,timeout=15)

try:
    d = json.loads(r.stdout)
    print("Top keys:", list(d.keys()))
    print("months:", d.get('months'))
    print()
    if 'data' in d and len(d['data']) > 0:
        row = d['data'][0]
        print(f"First row keys: {list(row.keys())}")
        print(f"First row: {json.dumps(row, ensure_ascii=False)[:300]}")
        print(f"Total rows: {len(d['data'])}")
except Exception as e:
    print(f"Error: {e}")
    print(f"Response: {r.stdout[:500]}")

# Also check /api/kpi Product
r2 = subprocess.run(['curl','-s','http://localhost/api/kpi?mode=product&year=2026&months=1,2,3,4,5,6'],capture_output=True,text=True,timeout=10)
try:
    d2 = json.loads(r2.stdout)
    print(f"\nKPI keys: {list(d2.keys())}")
    print(f"KPI is_single: {d2.get('is_single')}")
    print(f"KPI months: {d2.get('months')}")
except:
    print(f"\nKPI error: {r2.stdout[:200]}")
