import re
with open('/app/financial-agent/backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = 'os.path.dirname(__file__), "..", "frontend"'
new = 'os.path.dirname(__file__), "frontend"'
content = content.replace(old, new)

with open('/app/financial-agent/backend/main.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("main.py fixed")
