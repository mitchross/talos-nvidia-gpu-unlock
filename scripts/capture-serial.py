#!/usr/bin/env python3
"""Capture an existing serial socket; never reboot or send console input."""
import argparse,os,pathlib,shlex,subprocess
os.umask(0o077)
p=argparse.ArgumentParser();p.add_argument('--host',required=True);p.add_argument('--vmid',type=int,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
remote="import socket,time,sys\ns=socket.socket(socket.AF_UNIX)\nfor attempt in range(120):\n try:\n  s.connect('/var/run/qemu-server/VM_ID.serial0');break\n except (FileNotFoundError,ConnectionRefusedError):time.sleep(0.5)\nelse:raise RuntimeError('serial socket unavailable')\nprint('Serial capture attached',file=sys.stderr,flush=True)\ns.settimeout(900)\nwhile True:\n try:data=s.recv(65536)\n except ConnectionResetError:break\n if not data:break\n sys.stdout.buffer.write(data);sys.stdout.buffer.flush()\n"
remote=remote.replace('VM_ID',str(a.vmid))
with a.output.open('xb')as stream:subprocess.run(['ssh','-o','BatchMode=yes',a.host,'python3','-c',shlex.quote(remote)],stdout=stream,check=True)
