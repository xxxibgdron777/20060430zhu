#!/usr/bin/env python3
"""Check line 2221 for syntax errors"""
import subprocess, os, sys

path = '/app/financial-agent/frontend/index.html'
with open(path,'r',encoding='utf-8') as f:
    lines = f.read().split('\n')

print(f"Line 2221 (index 2220):")
for i in range(2215, 2227):
    if 0 <= i < len(lines):
        marker = " >>>" if i == 2220 else "    "
        print(f"{marker} {i+1}: {lines[i][:120]}")

# Search for '' patterns that might cause issues
print("\n\nSearching for all '' patterns in the file (empty string literals)...")
for i, line in enumerate(lines):
    if "''" in line and i > 2000:  # only look at lines after 2000
        print(f"Line {i+1}: {line[:100]}")
