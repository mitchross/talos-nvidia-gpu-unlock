#!/usr/bin/env python3
"""Reproduce the historical corrected UKI from its exact private base archive."""
import argparse,hashlib,json,os,pathlib,shutil,subprocess,tarfile
p=argparse.ArgumentParser();p.add_argument('archive',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);a=p.parse_args();r=pathlib.Path(__file__).resolve().parents[1];lock=json.load(open(r/'sources.lock.json'));assert not a.output.exists();assert hashlib.file_digest(a.archive.open('rb'),'sha256').hexdigest()==lock['base_candidate_archive_sha256'];a.output.mkdir(parents=True)
with tarfile.open(a.archive)as image:
 manifest=json.load(image.extractfile('manifest.json'))[0]
 with tarfile.open(fileobj=image.extractfile(manifest['Layers'][-1]),mode='r|*')as layer:
  for m in layer:
   if m.name.lstrip('./')=='usr/install/amd64/vmlinuz.efi':
    with(a.output/'base.efi').open('xb')as f:shutil.copyfileobj(layer.extractfile(m),f)
    break
assert(a.output/'base.efi').exists()
subprocess.run(['objcopy','--dump-section','.cmdline='+str(a.output/'base.cmdline'),str(a.output/'base.efi')],env=os.environ|{'SOURCE_DATE_EPOCH':'1793226839'},check=True)
subprocess.run(['python3',str(r/'scripts/patch-reference-uki.py'),str(a.output/'base.efi'),str(a.output/'working.efi')],check=True)
h=hashlib.file_digest((a.output/'working.efi').open('rb'),'sha256').hexdigest();assert h==lock['diagnostic_uki_sha256'];print('Exact reference reproduced:',h)
