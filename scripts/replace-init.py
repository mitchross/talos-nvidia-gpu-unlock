#!/usr/bin/env python3
"""Replace only /init in the pinned stock amd64 initramfs."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(__file__).resolve().parent
src=Path(sys.argv[1]) if len(sys.argv)>1 else root/'artifacts/initramfs-stock-amd64.xz'
binary=Path(sys.argv[2]) if len(sys.argv)>2 else root/'artifacts/init-amd64'
dst=Path(sys.argv[3]) if len(sys.argv)>3 else root/'artifacts/initramfs-early-amd64.xz'
assert not dst.exists(),'Preserve the existing output before rebuilding.'
data=subprocess.check_output(['zstd','-dc',str(src)]);replacement=binary.read_bytes()
out=bytearray();pos=0;changed=[];unchanged=[]
while pos<len(data) and data[pos:pos+6] in (b'070701',b'070702'):
 header=bytearray(data[pos:pos+110]);size=int(header[54:62],16);namesize=int(header[94:102],16)
 name=data[pos+110:pos+110+namesize-1].decode();start=(pos+110+namesize+3)&~3;end=(start+size+3)&~3
 if name.lstrip('./')=='init':
  assert not changed;changed.append(name);header[54:62]=f'{len(replacement):08x}'.encode()
  if header[:6]==b'070702':header[102:110]=f'{sum(replacement)&0xffffffff:08x}'.encode()
  out.extend(header);out.extend(data[pos+110:start]);out.extend(replacement);out.extend(b'\0'*((-len(out))%4))
 else:out.extend(data[pos:end]);unchanged.append({'name':name,'sha256':hashlib.sha256(data[start:start+size]).hexdigest()})
 pos=end
assert len(changed)==1
out.extend(data[pos:])
subprocess.run(['zstd','-T8','-10','-o',str(dst)],input=bytes(out),check=True)
(dst.parent/'initramfs-replacement.json').write_text(json.dumps({'changed':changed,'unchanged_entries':unchanged,'stock_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'patched_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'boot_tested':False},indent=2)+'\n')
