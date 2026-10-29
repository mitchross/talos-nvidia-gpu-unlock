#!/usr/bin/env python3
import argparse,hashlib,json,pathlib
p=argparse.ArgumentParser();p.add_argument('directory',type=pathlib.Path);p.add_argument('--inputs',action='store_true');a=p.parse_args();r=pathlib.Path(__file__).resolve().parents[1];lock=json.load(open(r/'sources.lock.json'));items=lock['nvidia_inputs']if a.inputs else lock['firmware_assets']
for name,info in items.items():
 path=a.directory/name;assert path.is_file(),name;assert hashlib.file_digest(path.open('rb'),'sha256').hexdigest()==info['sha256'],name
print('Verified',len(items),'pinned input files.'if a.inputs else'pinned firmware/license files.')
