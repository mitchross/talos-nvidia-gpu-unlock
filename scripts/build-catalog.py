#!/usr/bin/env python3
"""Build a replacement catalog from an explicit complete extension inventory."""
import argparse,pathlib,tarfile
p=argparse.ArgumentParser();p.add_argument('official_catalog',type=pathlib.Path);p.add_argument('required_names',type=pathlib.Path);p.add_argument('custom_reference');p.add_argument('output',type=pathlib.Path);a=p.parse_args();assert not a.output.exists();assert '@sha256:'in a.custom_reference
with tarfile.open(a.official_catalog)as t:lines=t.extractfile('image-digests').read().decode().splitlines();descriptions=t.extractfile('descriptions.yaml').read()
selected=[]
for name in sorted({l.strip()for l in a.required_names.read_text().splitlines()if l.strip()and not l.startswith('#')}):
 matches=[line for line in lines if line.split('@')[0].rsplit(':',1)[0].removeprefix('ghcr.io/')==name];assert len(matches)==1,(name,matches);selected+=matches
selected.append(a.custom_reference);a.output.mkdir(parents=True);(a.output/'image-digests').write_text('\n'.join(selected)+'\n');(a.output/'descriptions.yaml').write_bytes(descriptions);(a.output/'Dockerfile').write_text('FROM scratch\nCOPY image-digests /image-digests\nCOPY descriptions.yaml /descriptions.yaml\n');print('Catalog entries',len(selected))
