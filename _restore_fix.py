#!/usr/bin/env python3
"""Restore known-working backup and ONLY fix refreshTeamTab"""
import subprocess, os, shutil

path = '/app/financial-agent/frontend/index.html'
bak = '/app/financial-agent/frontend/index.html.current_bak'
final_bak = '/app/financial-agent/frontend/index.html.final_bak'

# Use current_bak (original working version, 163134 chars)
if os.path.exists(bak):
    shutil.copy2(bak, path)
    print(f"Restored backup from {bak}")
else:
    print(f"ERROR: {bak} not found!")
    # Try final_bak (my backup of the last known state)
    if os.path.exists(final_bak):
        shutil.copy2(final_bak, path)
        print(f"Restored from {final_bak}")
    else:
        print("No backup found!")

# Read the restored file
with open(path,'r',encoding='utf-8') as f:
    content = f.read()

# Check the refreshTeamTab function
idx = content.find('async function refreshTeamTab()')
if idx >= 0:
    # Find what it currently does
    brace_start = content.find('{', idx)
    brace_end = content.find('}', brace_start)
    current_func = content[idx:brace_end+1]
    print(f"Current refreshTeamTab:\n{current_func}\n")
    
    # Fix it - replace the body
    old_body = content[brace_start:brace_end+1]
    new_body = "{\n  await Promise.all([loadKPITeam(), loadChartsTeam(), loadTableTeam()]);\n}"
    content = content[:brace_start] + new_body + content[brace_end+1:]
    print(f"Fixed to:\n{content[idx:idx+len('async function refreshTeamTab()')+len(new_body)+1]}\n")
else:
    print("ERROR: refreshTeamTab not found!")

# Write fixed file
with open(path,'w',encoding='utf-8') as f:
    f.write(content)

# Verify
ob = content.count('{')
cb = content.count('}')
op = content.count('(')
cp = content.count(')')
print(f"Final: Size={len(content)}, Braces={ob}/{cb} {'OK' if ob==cb else 'FAIL!'}, Parens={op}/{cp} {'OK' if op==cp else 'FAIL!'}")
