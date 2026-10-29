#!/usr/bin/env python3
"""Append a firmware search path and serial diagnostics to a copied test UKI."""
from pathlib import Path
import hashlib
import json
import struct
import sys
source, target = map(Path, sys.argv[1:3])
assert not target.exists(), "Use a new output file."
original = source.read_bytes()
data = bytearray(original)
pe = struct.unpack_from("<I", data, 0x3c)[0]
assert data[pe:pe+4] == b"PE\0\0"
count = struct.unpack_from("<H", data, pe+6)[0]
optional = struct.unpack_from("<H", data, pe+20)[0]
headers = [pe+24+optional+i*40 for i in range(count)]
header = [h for h in headers if data[h:h+8].rstrip(b"\0") == b".cmdline"][0]
length, address, capacity, offset = struct.unpack_from("<IIII", data, header+8)
args = data[offset:offset+length].rstrip(b"\0").decode().split()
args = [a for a in args if a != "console=ttyS0"]
args += ["console=ttyS0,115200n8", "earlycon=uart8250,io,0x3f8,115200n8",
         "ignore_loglevel", "loglevel=8", "firmware_class.path=/usr/lib/firmware"]
command_line = " ".join(args).encode()+b"\0"
assert len(command_line) <= capacity
assert not any(a.startswith("talos.experimental.wipe=") for a in args)
assert "gpu_unlock.targets=0000:01:00.0" in args
assert "module.sig_enforce=0" in args and "module.sig_enforce=1" not in args
# The common command line precedes profile overrides; preserve the reset-maintenance profile.
data[offset:offset+capacity] = command_line+b"\0"*(capacity-len(command_line))
struct.pack_into("<I", data, header+8, len(command_line))
for h in headers:
    name = bytes(data[h:h+8]).rstrip(b"\0")
    size, raw = struct.unpack_from("<II", data, h+16)
    if name in (b".linux", b".initrd"):
        assert data[raw:raw+size] == original[raw:raw+size]
target.write_bytes(data)
print(json.dumps({"sha256":hashlib.sha256(data).hexdigest(), "cmdline":args,
                  "kernel_and_initramfs_unchanged":True}))
