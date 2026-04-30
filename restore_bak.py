#!/usr/bin/env python3
"""Restore the backup and verify"""
import subprocess, os, shutil

path = '/app/financial-agent/frontend/index.html'
bak = '/app/financial-agent/frontend/index.html.current_bak'

# Backup current first
if os.path.exists(path):
    current_size = os.path.getsize(path)
    shutil.copy2(path, path + '.mybak')
    print(f"Backed up current ({current_size} bytes) to {path}.mybak")

# Restore backup
if os.path.exists(bak):
    bak_size = os.path.getsize(bak)
    shutil.copy2(bak, path)
    print(f"Restored backup ({bak_size} bytes) from {bak}")
else:
    print("ERROR: Backup not found!")
    import sys; sys.exit(1)

# Verify
with open(path,'r',encoding='utf-8') as f:
    content = f.read()
lines = content.split('\n')
print(f"Restored: {len(content)} chars, {len(lines)} lines")
print(f"Braces: {content.count('{')}/{content.count('}')}")
print(f"Parens: {content.count('(')}/{content.count(')')}")

# Show line 2182 and 2221-ish
for ln in [2181, 2220]:
    if ln < len(lines):
        print(f"L{ln+1}: {lines[ln][:200]}")
