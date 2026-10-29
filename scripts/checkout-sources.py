#!/usr/bin/env python3
"""Fetch pinned source trees without changing an existing checkout."""
import argparse,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('work',type=pathlib.Path);a=p.parse_args();r=pathlib.Path(__file__).resolve().parents[1];lock=json.load(open(r/'sources.lock.json'));a.work.mkdir(parents=True,exist_ok=True)
for key,name,url in [('gpu_unlock','gpu-unlock','https://github.com/Zagitta/gpu-unlock.git'),('talos','talos','https://github.com/siderolabs/talos.git'),('talos_packages','pkgs','https://github.com/siderolabs/pkgs.git'),('image_factory','image-factory','https://github.com/siderolabs/image-factory.git')]:
 dest=a.work/'sources'/name;pin=lock['source_commits'][key]
 if not dest.exists():
  subprocess.run(['git','init',str(dest)],check=True);subprocess.run(['git','-C',str(dest),'remote','add','origin',url],check=True);subprocess.run(['git','-C',str(dest),'fetch','--depth=1','origin',pin],check=True);subprocess.run(['git','-C',str(dest),'checkout','--detach','FETCH_HEAD'],check=True)
 assert subprocess.check_output(['git','-C',str(dest),'rev-parse','HEAD'],text=True).strip()==pin
 print(name,pin)
