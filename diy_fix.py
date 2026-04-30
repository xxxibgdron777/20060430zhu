#!/usr/bin/env python3
"""Direct fix: read file, fix ALL problem lines, write back"""
import subprocess, os, sys

path = '/app/financial-agent/frontend/index.html'
with open(path,'r',encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# Find ALL lines with '' in onclick/onchange handlers
problem_indices = []
for i, line in enumerate(lines):
    # Check if this line builds HTML with inline event handler containing '' + var + ''
    if ('onclick' in line or 'onchange' in line):
        # Check inside the JS string (between outer single-quotes) for '' pattern
        # that's used for concatenation with variables
        if "''" in line and ("+ " in line or " +" in line):
            # Make sure this is actually inside an onclick/onchange (has the pattern)
            if "'' +" in line or "+ ''" in line:
                problem_indices.append(i)
                print(f"  FOUND L{i+1}: {line[:150]}")

print(f"\nTotal problem lines found: {len(problem_indices)}")

# Fix them all
for i in problem_indices:
    line = lines[i]
    # Replace '' + with \' + and + '' with + \'
    # But we must only replace '' that's inside the JS string building HTML
    # Strategy: find the onclick/onchange attribute and fix within it
    new_line = line
    new_line = new_line.replace("'' + ", "\\' + ")
    new_line = new_line.replace(" + ''", " + \\'")
    lines[i] = new_line
    if new_line != line:
        print(f"  FIXED L{i+1}: {lines[i][:150]}")
    else:
        print(f"  SKIP L{i+1}: no change needed")

# Write back
with open(path,'w',encoding='utf-8') as f:
    f.write('\n'.join(lines))

# Verify
with open(path,'r',encoding='utf-8') as f:
    v = f.read()

ob = v.count('{')
cb = v.count('}')
op = v.count('(')
cp = v.count(')')
print(f"\nFinal: Size={len(v)} Braces={ob}/{cb} {'OK' if ob==cb else 'FAIL!'} Parens={op}/{cp} {'OK' if op==cp else 'FAIL!'}")

# Copy to nginx container
NGINX = [c.strip() for c in subprocess.run(['docker','ps','--format','{{.Names}}'],capture_output=True,text=True,timeout=10).stdout.strip().split('\n') if c.strip() and 'nginx' in c.lower()][0]
input_bytes = v.encode('utf-8')
with open('/tmp/fixed_final.html','wb') as f:
    f.write(input_bytes)
r = subprocess.run(['docker','cp','/tmp/fixed_final.html',f'{NGINX}:/usr/share/nginx/html/index.html'],capture_output=True,text=True,timeout=10)
print(f"docker cp rc={r.returncode}: {r.stderr[:100] if r.stderr else 'OK'}")

# Verify container
r2 = subprocess.run(['docker','exec',NGINX,'cat','/usr/share/nginx/html/index.html'],capture_output=True,text=True,timeout=10)
c = r2.stdout
print(f"Container: Size={len(c)} Braces={c.count('{')}/{c.count('}')} Parens={c.count('(')}/{c.count(')')}")

# Show fixed lines in container
clines = c.split('\n')
for idx in problem_indices:
    if idx < len(clines):
        print(f"Container L{idx+1}: ...{clines[idx][150:180]}...")
