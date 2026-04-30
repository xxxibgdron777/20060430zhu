#!/usr/bin/env python3
"""Deep diagnosis of modified version - check ALL syntax patterns"""
import subprocess, os, re

# Check both mybak and modified versions
for path in ['/app/financial-agent/frontend/index.html.mybak',
              '/app/financial-agent/frontend/index.html.modified']:
    if not os.path.exists(path):
        print(f"{path}: NOT FOUND")
        continue
    
    with open(path,'r',encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    print(f"\n{'='*60}")
    print(f"FILE: {path}")
    print(f"Size: {len(content)} chars, {len(lines)} lines")
    print(f"Braces: {content.count('{')}/{content.count('}')} {'OK' if content.count('{')==content.count('}') else 'MISMATCH!'}")
    print(f"Parens: {content.count('(')}/{content.count(')')} {'OK' if content.count('(')==content.count(')') else 'MISMATCH!'}")
    print(f"Brackets: {content.count('[')}/{content.count(']')} {'OK' if content.count('[')==content.count(']') else 'MISMATCH!'}")
    
    # Find ALL lines with '' and analyze context
    print(f"\n--- Lines with '' in JS string building HTML (#{chr(39)}) ---")
    for i, line in enumerate(lines):
        if "onclick" in line or "onchange" in line:
            sq_count = line.count(chr(39))  # count single quotes
            if sq_count > 4:  # more than just outer quotes
                print(f"L{i+1} ({sq_count} quotes): {line[:200]}")
    
    # Check for template literals that might be broken
    print(f"\n--- Backticks ---")
    bt_count = content.count('`')
    print(f"Backtick count: {bt_count} (should be even: {'OK' if bt_count%2==0 else 'ODD!'})")
    
    # Check for common syntax errors: missing closing
    # Find all script tags
    scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
    print(f"\n--- Script blocks: {len(scripts)} ---")
    for j, script in enumerate(scripts):
        # Check line number of this script
        line_no = content.find(f'<script>{script}</script>')
        leading = content[:line_no].count('\n') + 1
        
        ob = script.count('{')
        cb = script.count('}')
        op = script.count('(')
        cp = script.count(')')
        
        if ob != cb or op != cp:
            print(f"  Script #{j+1} (starts L{leading}): Braces {ob}/{cb} Parens {op}/{cp} *** MISMATCH ***")
