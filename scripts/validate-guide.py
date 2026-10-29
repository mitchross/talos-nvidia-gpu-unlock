#!/usr/bin/env python3
"""Validate public text, examples, links, pins, and Mermaid render outputs."""
import ast,json,pathlib,re,subprocess,sys
import yaml
r=pathlib.Path(__file__).resolve().parents[1];errors=[];counts={'markdown':0,'yaml':0,'json':0,'python':0,'shell':0,'mermaid':0}
for p in sorted(r.rglob('*')):
 if not p.is_file()or any(v in p.relative_to(r).parts for v in ['.git','work','node_modules','__pycache__','validation-output']):continue
 if p.suffix in ['.ko','.bin','.efi','.key','.pem','.crt','.tar','.xz','.gz']:errors.append('Forbidden executable, firmware, credential, or archive: '+str(p.relative_to(r)))
 if p.suffix not in ['.md','.yaml','.json','.py','.sh','.mmd','.patch','.txt','.svg']and p.name not in ['.gitignore','Dockerfile.toolchain','Dockerfile.extension','Dockerfile.imager']:continue
 text=p.read_text()
 for pattern in [r'(?<![0-9])192[.]168[.][0-9]+[.][0-9]+',r'(?<![0-9])10[.][0-9]+[.][0-9]+[.][0-9]+',r'(?<![0-9])172[.](?:1[6-9]|2[0-9]|3[01])[.][0-9]+[.][0-9]+',r'/home/[a-z][a-z0-9_-]+',r'GPU-[0-9a-f]{8}-',r'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----']:
  if re.search(pattern,text,re.I):errors.append('Private value matched in '+str(p.relative_to(r)))
 if p.suffix=='.md':
  counts['markdown']+=1
  for target in re.findall(re.escape('](')+r'([^)]+)'+re.escape(')'),text):
   if target.startswith(('https://','http://','#')):continue
   if not(p.parent/target.split('#')[0]).exists():errors.append('Broken link '+str(p.relative_to(r))+': '+target)
  for i,code in enumerate(re.findall('```bash'+chr(10)+r'(.*?)```',text,re.S)):
   x=subprocess.run(['bash','-n'],input=code,text=True,capture_output=True)
   if x.returncode:errors.append('Invalid Bash example '+str(p.relative_to(r))+': '+x.stderr)
 if p.suffix=='.yaml':list(yaml.safe_load_all(text));counts['yaml']+=1
 if p.suffix=='.json':json.loads(text);counts['json']+=1
 if p.suffix=='.py':ast.parse(text);counts['python']+=1
 if p.suffix=='.sh':
  x=subprocess.run(['bash','-n',str(p)],capture_output=True,text=True);counts['shell']+=1
  if x.returncode:errors.append(str(p.relative_to(r))+': '+x.stderr)
 if p.suffix=='.mmd':
  counts['mermaid']+=1
  if not p.with_suffix('.svg').exists():errors.append('Missing Mermaid render '+str(p))
lock=json.load(open(r/'sources.lock.json'));case=json.load(open(r/'evidence/verified-case.json'));build=json.load(open(r/'evidence/build-validation.json'))
assert case['active_uki_sha256']==lock['diagnostic_uki_sha256'];assert build['original_reference_uki_replay_sha256']==lock['diagnostic_uki_sha256'];assert build['early_init_sha256']==lock['reference_early_init_sha256'];assert build['fresh_install_validated']is False and build['newly_built_candidate_boot_tested']is False
assert counts['mermaid']==5
if errors:print('\n'.join(errors),file=sys.stderr);raise SystemExit(1)
print(json.dumps({'checks':counts,'private_values_detected':False,'links_valid':True,'examples_parse':True,'source_pin_relationships_valid':True,'fresh_boot_claimed':False},indent=2))
