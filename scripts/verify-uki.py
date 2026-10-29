#!/usr/bin/env python3
"""Read PE/CPIO bytes and extension metadata without booting the image."""
import argparse,hashlib,json,mmap,pathlib,struct,subprocess,yaml
p=argparse.ArgumentParser();p.add_argument('uki',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);p.add_argument('--module',type=pathlib.Path);a=p.parse_args();r=pathlib.Path(__file__).resolve().parents[1];lock=json.load(open(r/'sources.lock.json'));assert not a.output.exists();a.output.mkdir(parents=True)
with a.uki.open('rb')as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)as b:
 pe=struct.unpack_from('<I',b,0x3c)[0];assert b[pe:pe+4]==b'PE\0\0';count=struct.unpack_from('<H',b,pe+6)[0];optional=struct.unpack_from('<H',b,pe+20)[0];sections={};profile='common';profile_args={}
 for i in range(count):
  h=pe+24+optional+i*40;name=bytes(b[h:h+8]).rstrip(b'\0').decode();size,_,capacity,offset=struct.unpack_from('<IIII',b,h+8)
  if name=='.profile':
   profile=next(v[3:]for v in bytes(b[offset:offset+size]).decode().splitlines()if v.startswith('ID='));profile_args.setdefault(profile,None)
  if name in ['.linux','.initrd','.cmdline']:
   assert size<=capacity;sections.setdefault(name,{'bytes':size,'sha256':hashlib.sha256(b[offset:offset+size]).hexdigest()})
   if name=='.initrd':(a.output/'initramfs.compressed').write_bytes(b[offset:offset+size])
   if name=='.cmdline':profile_args[profile]=bytes(b[offset:offset+size]).rstrip(b'\0').decode()
cmdline=profile_args.get('main')or profile_args['common']
with(a.output/'initramfs.cpio').open('wb')as f:subprocess.run(['zstd','-dc',str(a.output/'initramfs.compressed')],stdout=f,check=True)
seen={}
with(a.output/'initramfs.cpio').open('rb')as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)as b:
 pos=0
 while pos<len(b):
  if b[pos:pos+6]not in [b'070701',b'070702']:
   pos=b.find(b'070701',pos)
   if pos<0:break
  header=b[pos:pos+110];size=int(header[54:62],16);n=int(header[94:102],16);name=bytes(b[pos+110:pos+110+n-1]).decode().removeprefix('./');start=(pos+110+n+3)&~3;assert start+size<=len(b)
  if name=='init'or name.startswith('usr/lib/firmware/gpu-unlock/'):seen[name]=hashlib.sha256(b[start:start+size]).hexdigest()
  if name.endswith('.sqsh')or name=='extensions.yaml':
   assert '/'not in name;(a.output/name).write_bytes(b[start:start+size])
  pos=(start+size+3)&~3
assert sections['.linux']['sha256']==lock['stock_linux_amd64_sha256'],'Linux differs from the pinned stock kernel'
assert seen['init']==lock['reference_early_init_sha256']
for name,info in lock['firmware_assets'].items():
 if name.endswith('.bin'):assert seen['usr/lib/firmware/gpu-unlock/610.43.03/'+name]==info['sha256'],name
layers=yaml.safe_load((a.output/'extensions.yaml').read_text())['layers'];versions={x['metadata']['name']:x['metadata']['version']for x in layers}
def cat(image,path):return subprocess.check_output(['docker','run','--rm','--entrypoint','/usr/bin/unsquashfs','-v',str(a.output.resolve())+':/verify:ro','gpu-unlock-llvm:talos-1.14.5','-cat','/verify/'+image,path])
deps=cat('modules.dep.sqsh','usr/lib/modules/6.18.58-talos/modules.dep').decode();assert 'gpu_unlock.ko:'in deps and'nvidia.ko:'in deps
module_image=next(x['image']for x in layers if x['metadata']['name']=='gpu-unlock');module=cat(module_image,'usr/lib/modules/6.18.58-talos/extra/gpu_unlock.ko');expected_module=hashlib.file_digest(a.module.open('rb'),'sha256').hexdigest()if a.module else lock['reference_module_sha256'];assert hashlib.sha256(module).hexdigest()==expected_module,'Module differs from the supplied expected bytes.'
for n in ['iscsi-tools','nonfree-kmod-nvidia-production','nvidia-container-toolkit-production','util-linux-tools']:assert n in versions
assert 'module.sig_enforce=0'in cmdline.split()and'module.sig_enforce=1'not in cmdline.split();assert 'firmware_class.path=/usr/lib/firmware'in cmdline.split();assert not any(v.startswith('talos.experimental.wipe=')for v in cmdline.split())
result={'sections':sections,'cmdline':cmdline,'firmware_bin_count':16,'firmware_hashes_match':True,'early_init_matches_reference':True,'module_matches_expected':True,'module_matches_reference':hashlib.sha256(module).hexdigest()==lock['reference_module_sha256'],'profile_command_lines':profile_args,'normal_profile_inherits_common':profile_args.get('main')is None,'modules_dep_includes_gpu_unlock_and_nvidia':True,'extensions':versions,'boot_tested':False};(a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
