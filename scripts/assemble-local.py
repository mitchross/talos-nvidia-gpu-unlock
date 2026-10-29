#!/usr/bin/env python3
"""Assemble locally, then export a corrected diagnostic UKI sidecar."""
import argparse,hashlib,json,pathlib,shutil,subprocess,tarfile
import yaml
p=argparse.ArgumentParser();p.add_argument('work',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);p.add_argument('--official-dir',type=pathlib.Path);p.add_argument('--extension-tar',type=pathlib.Path);p.add_argument('--stock',action='store_true');a=p.parse_args();r=pathlib.Path(__file__).resolve().parents[1];lock=json.load(open(r/'sources.lock.json'));assert a.output.is_absolute()and not a.output.exists();a.output.mkdir(parents=True);official=a.official_dir or a.work/'official';official.mkdir(parents=True,exist_ok=True)
refs=lock['official_extension_references'];tarballs=[]
for ref in refs:
 name=ref.split('/')[-1].split(':')[0];target=official/(name+'.rootfs.tar')
 if not target.exists():subprocess.run(['crane','export','--platform','linux/amd64',ref,str(target)],check=True)
 tarballs.append(str(target.resolve()))
if not a.stock:
 assert a.extension_tar and a.extension_tar.is_file(),'Provide --extension-tar for a candidate'
 tarballs.append(str(a.extension_tar.resolve()))
profile=yaml.safe_load((r/'examples/installer.yaml').read_text());profile['input']['systemExtensions']=[{'tarballPath':'/inputs/'+str(i)+'.tar'}for i in range(len(tarballs))]
if a.stock:profile.pop('customization',None)
(a.output/'profile.yaml').write_text(yaml.safe_dump(profile,sort_keys=False));cmd=['docker','run','--rm','-i','--privileged','--network','host','-v',str(a.output)+':/out']
for i,path in enumerate(tarballs):cmd+=['-v',path+':/inputs/'+str(i)+'.tar:ro']
cmd+=[lock['tool_images']['imager']if a.stock else'talos-gpu-unlock-imager:local','-']
with(a.output/'build.log').open('w')as log:subprocess.run(cmd,input=yaml.safe_dump(profile).encode(),stdout=log,stderr=subprocess.STDOUT,check=True)
archives=list(a.output.glob('*.tar'));assert len(archives)==1,archives
with tarfile.open(archives[0])as image:
 manifest=json.load(image.extractfile('manifest.json'))[0]
 found=False
 for layer in reversed(manifest['Layers']):
  with tarfile.open(fileobj=image.extractfile(layer),mode='r|*')as t:
   for m in t:
    if m.name.lstrip('./')=='usr/install/amd64/vmlinuz.efi':
     with(a.output/'base.efi').open('xb')as dest:shutil.copyfileobj(t.extractfile(m),dest)
     found=True;break
  if found:break
 assert found
if not a.stock:subprocess.run(['python3',str(r/'scripts/patch-reference-uki.py'),str(a.output/'base.efi'),str(a.output/'diagnostic.efi')],check=True)
(a.output/'SHA256SUMS').write_text(''.join(hashlib.file_digest(f.open('rb'),'sha256').hexdigest()+'  '+f.name+'\n'for f in archives+list(a.output.glob('*.efi'))))
print('Local assembly complete. The corrected diagnostic UKI is a sidecar; the OCI installer is not silently rewritten.')
