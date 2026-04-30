#!/usr/bin/env python3
"""Compare line 2221 between current and backup"""
import subprocess, os

NGINX = [c.strip() for c in subprocess.run(['docker','ps','--format','{{.Names}}'],capture_output=True,text=True,timeout=10).stdout.strip().split('\n') if c.strip() and 'nginx' in c.lower()][0]

# Get current file
r = subprocess.run(['docker','exec',NGINX,'cat','/usr/share/nginx/html/index.html'],capture_output=True,text=True,timeout=10)
current = r.stdout

# Get backup file if it exists in container
r2 = subprocess.run(['docker','exec',NGINX,'cat','/usr/share/nginx/html/index.html.current_bak'],capture_output=True,text=True,timeout=10)
if r2.returncode == 0:
    backup = r2.stdout
else:
    # Try host
    with open('/app/financial-agent/frontend/index.html.current_bak','r',encoding='utf-8') as f:
        backup = f.read()

cur_lines = current.split('\n')
bak_lines = backup.split('\n')

print(f"Current file size: {len(current)} bytes, {len(cur_lines)} lines")
print(f"Backup file size: {len(backup)} bytes, {len(bak_lines)} lines")

# Compare lines around 2182 and 2221
for ln in [2181, 2220]:
    print(f"\n--- Line {ln+1} ---")
    if ln < len(cur_lines):
        print(f"CURRENT: {cur_lines[ln][:150]}")
    if ln < len(bak_lines):
        print(f"BACKUP : {bak_lines[ln][:150]}")

# Search the backup for patterns
# The backup has '' inside onclick handlers. Let's see if they exist.
print("\n\n=== BACKUP: Searching for onclick handlers with '' ===")
for i, line in enumerate(bak_lines):
    if 'onclick' in line and "''" in line:
        print(f"  Line {i+1}: {line[:200]}")
        
# Now search CURRENT
print("\n=== CURRENT: Searching for onclick handlers with '' ===")
for i, line in enumerate(cur_lines):
    if 'onclick' in line and "''" in line:
        print(f"  Line {i+1}: {line[:200]}")

# Also search for \\' (fixed patterns)
print("\n=== CURRENT: Searching for onclick handlers with \\' ===")
for i, line in enumerate(cur_lines):
    if 'onclick' in line and "\\'" in line:
        print(f"  Line {i+1}: {line[:200]}")
