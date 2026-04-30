#!/usr/bin/env python3
"""Switch to modified version and verify syntax"""
import subprocess, os, shutil

path = '/app/financial-agent/frontend/index.html'
mod = '/app/financial-agent/frontend/index.html.modified'

if not os.path.exists(mod):
    print(f"ERROR: {mod} not found!")

# Save current as final backup
shutil.copy2(path, path + '.final_bak')
print(f"Backed up current to {path}.final_bak")

# Switch to modified version
shutil.copy2(mod, path)
print(f"Switched to modified version")

# Check brace/paren balance
with open(path,'r',encoding='utf-8') as f:
    content = f.read()

print(f"Size: {len(content)} chars")
print(f"Braces: {content.count('{')}/{content.count('}')} {'OK' if content.count('{')==content.count('}') else 'FAIL!'}")
print(f"Parens: {content.count('(')}/{content.count(')')} {'OK' if content.count('(')==content.count(')') else 'FAIL!'}")
print(f"Brackets: {content.count('[')}/{content.count(']')} {'OK' if content.count('[')==content.count(']') else 'FAIL!'}")

# Check for any null bytes (could cause issues)
nulls = content.count('\x00')
print(f"Null bytes: {nulls}")

# Check for BOM
if content.startswith('\ufeff'):
    print("WARNING: BOM found!")
else:
    print("No BOM (good)")

# Check that HTML starts correctly
print(f"\nFirst 50 chars: {repr(content[:50])}")
print(f"Last 50 chars: {repr(content[-50:])}")

# Check for common issues: missing semicolons at end of script
# Find the last script tag
import re
scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
if scripts:
    last_script = scripts[-1]
    print(f"\nLast script block: {len(last_script)} chars")
    print(f"Last 100 chars: {repr(last_script[-100:])}")
