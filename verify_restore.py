#!/usr/bin/env python3
"""Verify nginx container has restored version"""
import subprocess, os

NGINX = [c.strip() for c in subprocess.run(['docker','ps','--format','{{.Names}}'],capture_output=True,text=True,timeout=10).stdout.strip().split('\n') if c.strip() and 'nginx' in c.lower()][0]

r = subprocess.run(['docker','exec',NGINX,'cat','/usr/share/nginx/html/index.html'],capture_output=True,text=True,timeout=10)
c = r.stdout

print(f"Container size: {len(c)} chars")
print(f"Lines: {len(c.split(chr(10)))}")
print(f"Braces: {c.count('{')}/{c.count('}')}")
print(f"Parens: {c.count('(')}/{c.count(')')}")
print(f"Has init: {'async function init' in c}")
print(f"Has refreshProductTab: {'async function refreshProductTab' in c}")
print(f"Has refreshTeamTab: {'async function refreshTeamTab' in c}")
print(f"Has loadKPITeam: {'loadKPITeam' in c}")

# Check refreshTeamTab
import re
m = re.search(r'async function refreshTeamTab\(\) \{[\s\S]{0,200}', c)
if m:
    print(f"\nrefreshTeamTab: {m.group()}")
m2 = re.search(r'async function refreshProductTab\(\) \{[\s\S]{0,200}', c)
if m2:
    print(f"refreshProductTab: {m2.group()}")

# Check for '' onclick patterns
for i, line in enumerate(c.split('\n')):
    if 'onclick' in line and "''" in line:
        print(f"\nL{i+1} has '' onclick: {line[:200]}")

# Compare with host file
with open('/app/financial-agent/frontend/index.html','r',encoding='utf-8') as f:
    host = f.read()
print(f"\nHost size: {len(host)} chars, same as container: {len(host) == len(c)}")
