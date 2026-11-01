import socket
import concurrent.futures
import subprocess

ip = '10.23.32.178'

def check_port(p):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.2)
    res = s.connect_ex((ip, p))
    s.close()
    return p if res == 0 else None

print(f"Scanning {ip} for wireless debugging port...")
with concurrent.futures.ThreadPoolExecutor(max_workers=200) as ex:
    open_ports = [p for p in ex.map(check_port, range(30000, 50000)) if p]

print(f"Open ports: {open_ports}")
for p in open_ports:
    print(f"Testing adb connect {ip}:{p}...")
    res = subprocess.run(["adb", "connect", f"{ip}:{p}"], capture_output=True, text=True)
    print(res.stdout)
