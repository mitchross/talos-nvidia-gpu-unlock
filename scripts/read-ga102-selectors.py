#!/usr/bin/env python3
"""Read only the feature registers defined by the pinned GA102 recipe."""
import json,mmap,os,struct
for bdf in ['0000:01:00.0','0000:02:00.0']:
 try:
  fd=os.open('/sys/bus/pci/devices/'+bdf+'/resource0',os.O_RDONLY)
  with mmap.mmap(fd,0x1000000,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ)as bar:
   values={name:hex(struct.unpack_from('<I',bar,offset)[0])for name,offset in [('plm',0x823804),('ss0',0x82381c),('ss1',0x823820)]}
  os.close(fd)
  print(json.dumps({'pci':bdf,**values,'full_selectors':values['ss0']=='0x88888888'and values['ss1']=='0x8','access':'O_RDONLY/PROT_READ'}))
 except Exception as e:print(json.dumps({'pci':bdf,'error':str(e)}))
