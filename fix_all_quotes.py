#!/usr/bin/env python3
"""Fix ALL instances of '' inside single-quoted JS strings used in HTML event handlers"""
import subprocess, os, sys, re

path = '/app/financial-agent/frontend/index.html'
with open(path,'r',encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
changes = 0
problem_lines = []

# Find all lines with '' inside a single-quoted JS string building HTML with onclick/onchange
for i, line in enumerate(lines):
    # Pattern: inside a '...' JS string literal, there's onclick="...'' + var + ''..."
    # The '' is supposed to be an escaped single quote \'
    if ("onclick" in line or "onchange" in line) and "''" in line:
        # Check if the '' is followed by + (indicating string concat inside onclick/onchange)
        if "'' + " in line:
            problem_lines.append((i+1, line))
            # Fix: replace '' with \' but only inside the onclick/onchange attribute
            # Strategy: replace '' + with \' + and + '' with + \'
            new_line = line
            new_line = new_line.replace("'' + ", "\\' + ")
            new_line = new_line.replace(" + ''", " + \\'")
            # But be careful not to break existing '' that are proper empty strings
            # '' that are followed by + are the bad ones (they're inside onclick/onchange)
            lines[i] = new_line
            if new_line != line:
                changes += 1

print(f"Fixed {changes} lines:")
for ln, old_line in problem_lines:
    new_line = lines[ln-1]
    # Show just the relevant part
    idx = old_line.find("onclick") if "onclick" in old_line else old_line.find("onchange")
    print(f"  L{ln}: ...{old_line[max(0,idx-5):idx+80]}...")
    idx2 = new_line.find("onclick") if "onclick" in new_line else new_line.find("onchange")
    print(f"   -> ...{new_line[max(0,idx2-5):idx2+80]}...")
    print()

with open(path,'w',encoding='utf-8') as f:
    f.write('\n'.join(lines))

# Final verification
with open(path,'r',encoding='utf-8') as f:
    v = f.read()

ob = v.count('{')
cb = v.count('}')
op = v.count('(')
cp = v.count(')')
print(f"Final: Size={len(v)} Braces={ob}/{cb} {'OK' if ob==cb else 'FAIL!'} Parens={op}/{cp} {'OK' if op==cp else 'FAIL!'}")

# Copy to nginx container
NGINX = [c.strip() for c in subprocess.run(['docker','ps','--format','{{.Names}}'],capture_output=True,text=True,timeout=10).stdout.strip().split('\n') if c.strip() and 'nginx' in c.lower()][0]
input_bytes = v.encode('utf-8')
with open('/tmp/fixed_all.html','wb') as f:
    f.write(input_bytes)
subprocess.run(['docker','cp','/tmp/fixed_all.html',f'{NGINX}:/usr/share/nginx/html/index.html'],capture_output=True,text=True,timeout=10)

# Verify container
r = subprocess.run(['docker','exec',NGINX,'cat','/usr/share/nginx/html/index.html'],capture_output=True,text=True,timeout=10)
c = r.stdout
print(f"Container: Size={len(c)} Braces={c.count('{')}/{c.count('}')} Parens={c.count('(')}/{c.count(')')}")
print("DONE!")
