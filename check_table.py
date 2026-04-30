#!/usr/bin/env python3
"""Find and show loadTableProduct function"""
import subprocess, os, re

path = '/app/financial-agent/frontend/index.html'
with open(path,'r',encoding='utf-8') as f:
    content = f.read()

# Find loadTableProduct function
idx = content.find('async function loadTableProduct(')
if idx < 0:
    idx = content.find('async function loadTableProduct()')

if idx >= 0:
    # Extract function by brace matching
    brace_count = 0
    while idx < len(content) and content[idx] != '{':
        idx += 1
    idx += 1
    brace_count = 1
    start = idx
    while brace_count > 0 and idx < len(content):
        if content[idx] == '{': brace_count += 1
        elif content[idx] == '}': brace_count -= 1
        idx += 1
    func = content[start-1:idx]  # include the opening brace
    
    # Check if function references 'months' in the API response
    print("=== loadTableProduct function ===")
    # Print first 500 chars
    print(func[:1000])
    
    print("\n\n=== Second part ===")
    print(func[1000:2000])
else:
    print("loadTableProduct not found!")
    
# Also check KPI API for cumulative data fields
print("\n\n=== Full KPI response for May (month 5) ===")
r = subprocess.run(['curl','-s','http://localhost/api/kpi?mode=product&year=2026&months=5'],capture_output=True,text=True,timeout=10)
print(r.stdout[:500])
