#!/usr/bin/env python3
"""Check loadTableTeam function and how it renders months"""
import subprocess, os, re

path = '/app/financial-agent/frontend/index.html'
with open(path,'r',encoding='utf-8') as f:
    content = f.read()

# Find loadTableTeam function
idx = content.find('async function loadTableTeam(')
if idx < 0:
    idx = content.find('async function loadTableTeam()')

if idx >= 0:
    # Extract function
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
    func = content[start-1:idx]
    
    print("=== loadTableTeam function (first 1500 chars) ===")
    print(func[:1500])
    
    print("\n\n=== Check for months rendering ===")
    # Look for how months are rendered in the table
    if 'months' in func and 'html' in func:
        lines = func.split('\n')
        for i, line in enumerate(lines):
            if 'month' in line.lower() or 'months' in line.lower():
                print(f"L{i}: {line}")
else:
    print("loadTableTeam not found!")

# Check the team drill API response structure
print("\n\n=== Team drill API response ===")
r = subprocess.run(['curl','-s','-X','POST','http://localhost/api/team/drill',
    '-H','Content-Type: application/json',
    '-d','{"year":2026,"months":[1,2,3],"page":1,"page_size":50,"level":"nature"}'],
    capture_output=True,text=True,timeout=15)
print(r.stdout[:800])
