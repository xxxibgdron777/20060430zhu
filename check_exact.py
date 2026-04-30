#!/usr/bin/env python3
"""Read and show line 2221 exactly"""
path = '/app/financial-agent/frontend/index.html'
with open(path,'r',encoding='utf-8') as f:
    lines = f.read().split('\n')

l = lines[2220]
print(f"RAW: {repr(l)}")
print(f"LEN: {len(l)}")
print(f"ONCLICK: {'onclick' in l}")
print(f"SQ+  : {chr(39)+chr(39)+'+' in l}")
print(f"+ SQ : {'+ '+chr(39)+chr(39) in l}")
print(f"SQ   : {chr(39)+chr(39) in l}")

# Check character by character around the onclick area
idx = l.find('onclick')
if idx >= 0:
    print(f"AREA: {repr(l[idx:idx+80])}")
    for j, c in enumerate(l[idx:idx+80]):
        if c == chr(39):
            print(f"  SINGLE QUOTE at position {idx+j}")
