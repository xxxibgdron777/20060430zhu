#!/usr/bin/env python3
"""Check drill API with more params"""
import subprocess, json

# Try product drill with different params
payloads = [
    {"year":2026,"months":[3],"page":1,"page_size":50,"level":"board"},
    {"year":2026,"months":[1,2,3],"page":1,"page_size":50,"level":"board"},
    {"year":2026,"months":[1,2,3,4,5,6],"page":1,"page_size":50,"level":"board","detail":"true"},
    {"year":2026,"months":[3],"page":1,"page_size":50,"level":"product"},
    {"year":2026,"months":[3],"page":1,"page_size":50,"level":"detail"},
]

for i, payload in enumerate(payloads):
    r = subprocess.run(['curl','-s','-X','POST','http://localhost/api/product/drill',
        '-H','Content-Type: application/json',
        '-d',json.dumps(payload)],
        capture_output=True,text=True,timeout=15)
    try:
        d = json.loads(r.stdout)
        keys = list(d.keys())
        if 'data' in d and len(d['data']) > 0:
            row = d['data'][0]
            print(f"\nPayload {i}: {json.dumps(payload)}")
            print(f"  keys: {keys}")
            print(f"  months: {d.get('months')}")
            print(f"  row keys: {list(row.keys())}")
            print(f"  row: {json.dumps(row, ensure_ascii=False)[:200]}")
        else:
            print(f"\nPayload {i}: no data, keys={keys}, response={r.stdout[:200]}")
    except Exception as e:
        print(f"\nPayload {i}: Error: {e}, response={r.stdout[:200]}")
