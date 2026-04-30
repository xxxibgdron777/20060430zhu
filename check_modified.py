#!/usr/bin/env python3
"""Compare modified version with backup version for table rendering"""
import subprocess, os

files = {}
for name in ['/app/financial-agent/frontend/index.html',
              '/app/financial-agent/frontend/index.html.modified']:
    if os.path.exists(name):
        with open(name,'r',encoding='utf-8') as f:
            files[name] = f.read()
            print(f"{name}: {len(files[name])} chars, {len(files[name].split(chr(10)))} lines")
    else:
        print(f"{name}: NOT FOUND")

if len(files) < 2:
    # Check container
    NGINX = [c.strip() for c in subprocess.run(['docker','ps','--format','{{.Names}}'],capture_output=True,text=True,timeout=10).stdout.strip().split('\n') if c.strip() and 'nginx' in c.lower()][0]
    r = subprocess.run(['docker','exec',NGINX,'ls','-la','/usr/share/nginx/html/'],capture_output=True,text=True,timeout=10)
    print(f"\nContainer listing:\n{r.stdout}")

# Compare loadTableTeam functions
for name, content in files.items():
    idx = content.find('async function loadTableTeam(')
    if idx < 0:
        idx = content.find('async function loadTableTeam()')
    if idx >= 0:
        # Find header rows to see column structure
        header_idx = content.find('<th', idx)
        if header_idx > 0:
            # Get table headers
            end_idx = content.find('</thead>', header_idx)
            if end_idx > 0:
                header_html = content[header_idx:end_idx]
                print(f"\n{name} headers:\n{header_html[:500]}")
        
        # Also find how each row is rendered (renderTeamRow or inline)
        render_idx = content.find('renderTeamRow', idx)
        if render_idx > 0 and render_idx < idx + 2000:
            print(f"\n{name}: has renderTeamRow function")
        else:
            print(f"\n{name}: no renderTeamRow found in loadTableTeam vicinity")

# Check the actual modified version structure
modified_path = '/app/financial-agent/frontend/index.html.modified'
if os.path.exists(modified_path):
    with open(modified_path,'r',encoding='utf-8') as f:
        mod = f.read()
    
    # Look for how it handles per-month data in tables
    for pattern in ['1月', 'months', '逐月', 'monthly']:
        count = mod.count(pattern)
        if count > 0:
            # Find context
            idx = mod.find(pattern, mod.find(pattern) if count > 1 else 0)
            context = mod[max(0,idx-50):idx+80] if idx >= 0 else ''
            print(f"\n'{pattern}' in modified: {count} times, e.g.: {context}")
    
    # Check if the modified version has the '' onclick patterns that caused errors
    for i, line in enumerate(mod.split('\n')):
        if 'onclick' in line and "''" in line:
            print(f"\nModified L{i+1} has '' onclick: {line[:150]}")
