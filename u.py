"""Upload and execute helper for 122.51.134.23."""
import subprocess, sys, base64
HOST,USER,KEY,SSH = "122.51.134.23","root",r"c:\Users\carrie\.ssh\skey-temp.pem",r"C:\Windows\System32\OpenSSH\ssh.exe"

def run(cmd):
    r = subprocess.run([SSH,"-o","StrictHostKeyChecking=no","-o","ConnectTimeout=15","-i",KEY,f"{USER}@{HOST}",cmd],capture_output=True,timeout=60)
    return r.stdout.decode("utf-8",errors="replace"), r.stderr.decode("utf-8",errors="replace"), r.returncode

def upload(local, remote):
    with open(local,"rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    p = subprocess.Popen([SSH,"-o","StrictHostKeyChecking=no","-o","ConnectTimeout=15","-i",KEY,f"{USER}@{HOST}",
        f"python3 -c \"import sys,base64; open('{remote}','wb').write(base64.b64decode(sys.stdin.read().strip()))\""],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    so,se = p.communicate(input=b64,timeout=30)
    return so,se,p.returncode

if __name__=="__main__":
    if len(sys.argv)==2:
        so,se,rc = run(sys.argv[1])
        if se.strip() and "debug1" not in se:
            sys.stdout.buffer.write(se.encode("utf-8", errors="replace"))
            sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.write(so.encode("utf-8", errors="replace"))
    elif len(sys.argv)==4 and sys.argv[1]=="up":
        upload(sys.argv[2],sys.argv[3])
