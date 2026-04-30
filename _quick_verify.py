#!/usr/bin/env python3
import subprocess
NGINX = [c.strip() for c in subprocess.run(['docker','ps','--format','{{.Names}}'],capture_output=True,text=True,timeout=10).stdout.strip().split('\n') if c.strip() and 'nginx' in c.lower()][0]
r = subprocess.run(['docker','exec',NGINX,'cat','/usr/share/nginx/html/index.html'],capture_output=True,text=True,timeout=10)
c = r.stdout
print(f"Size: {len(c)}")
print(f"Has monthly: {'detail-monthly' in c}")
print(f"Braces OK: {c.count('{')==c.count('}')}")
print(f"Parens OK: {c.count('(')==c.count(')')}")
print(f"RefreshTeamTab OK: {'loadKPITeam()' in c and 'loadChartsTeam()' in c}")
