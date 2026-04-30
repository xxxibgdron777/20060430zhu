"""Check SSH connection to the correct server."""
import subprocess

host = "122.51.134.23"
user = "root"
key = r"c:\Users\carrie\.ssh\id_rsa"
ssh = r"C:\Windows\System32\OpenSSH\ssh.exe"

cmd = "echo connected && hostname && ls -la /app/financial-agent/frontend/ 2>/dev/null || echo 'frontend dir not found'"

result = subprocess.run(
    [ssh, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15",
     "-i", key, f"{user}@{host}", cmd],
    capture_output=True, timeout=30
)
stdout = result.stdout.decode('utf-8', errors='replace')
stderr = result.stderr.decode('utf-8', errors='replace')
print("STDOUT:", stdout)
if stderr:
    for line in stderr.splitlines():
        if not line.startswith("debug1:"):
            print("STDERR:", line)
print("EXITCODE:", result.returncode)
