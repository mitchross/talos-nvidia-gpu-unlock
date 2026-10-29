#!/usr/bin/env python3
"""Package local outputs. Never install a module or execute firmware."""
import argparse,json,pathlib,shutil,subprocess,tarfile
p=argparse.ArgumentParser();p.add_argument('module',type=pathlib.Path);p.add_argument('assets',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);p.add_argument('--source',type=pathlib.Path,required=True);p.add_argument('--tag',default='talos-gpu-unlock:2.0.0-v1.14.5-local');a=p.parse_args();r=pathlib.Path(__file__).resolve().parents[1]
assert not a.output.exists(),'Use a new output directory';assert subprocess.check_output(['modinfo','-F','vermagic',str(a.module)],text=True).split()[0]=='6.18.58-talos'
subprocess.run(['python3',str(r/'scripts/verify-firmware.py'),str(a.assets)],check=True)
m=a.output/'rootfs/usr/lib/modules/6.18.58-talos/extra';m.mkdir(parents=True);shutil.copyfile(a.module,m/'gpu_unlock.ko');fw=a.output/'rootfs/usr/lib/firmware/gpu-unlock/610.43.03';fw.mkdir(parents=True)
for name in json.load(open(r/'sources.lock.json'))['firmware_assets']:shutil.copyfile(a.assets/name,fw/name)
for name in subprocess.check_output(['modinfo','-F','firmware',str(a.module)],text=True).splitlines():assert(a.output/'rootfs/usr/lib/firmware'/name).is_file(),name
licenses=a.output/'rootfs/usr/local/share/licenses/gpu-unlock';shutil.copytree(a.source/'licenses',licenses);shutil.copyfile(a.source/'firmware/NOTICE.md',licenses/'FIRMWARE-NOTICE.md')
shutil.copyfile(r/'examples/extension-manifest.yaml',a.output/'manifest.yaml');shutil.copyfile(r/'examples/Dockerfile.extension',a.output/'Dockerfile')
with tarfile.open(a.output/'extension.rootfs.tar','w')as t:t.add(a.output/'rootfs',arcname='rootfs');t.add(a.output/'manifest.yaml',arcname='manifest.yaml')
subprocess.run(['docker','build','--platform','linux/amd64','-t',a.tag,str(a.output)],check=True)
print('Extension built:',a.tag)
