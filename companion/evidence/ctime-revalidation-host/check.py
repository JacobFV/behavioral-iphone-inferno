#!/usr/bin/env python3
"""Real filesystem operations on synthetic bytes only; no guest or retained disk changes."""
import hashlib,importlib.util,json,os,pathlib,tempfile
root=pathlib.Path(__file__).resolve().parents[3];tool=root/'companion/disk_overlay.py';spec=importlib.util.spec_from_file_location('overlay',tool);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checks=[]
def reject(name,call):
 try:call();raise AssertionError(name+' accepted')
 except ValueError as e:checks.append({'name':name,'rejected':str(e)})
with tempfile.TemporaryDirectory(prefix='inferno-ctime-fixture-') as tmp:
 p=pathlib.Path(tmp);base=p/'root.raw';base.write_bytes(b'owned synthetic backing\n'*32);base.chmod(0o444);original=m.validate_base(base,m.digest(base));source=p/'historical.json';source.write_text(json.dumps({'dependencies':[original]}));base.chmod(0o444);actual=m.validate_base(base,original['sha256']);assert actual!=original and {k for k in actual if actual[k]!=original[k]}=={'ctime_ns'}
 attestation=m.attest_ctime(base,source,original['ctime_ns']);journal=[];assert m.validate_base(base,original['sha256'],journal=journal)==original and journal[0]['actual_verified']==actual;checks.append({'name':'same-mode-chmod-exact-normalization','original':original,'actual':actual,'journal':journal,'original_source_unchanged':m.digest(source)==attestation['historical_source']['sha256']})
 reject('exclusive-attestation',lambda:m.attest_ctime(base,source,original['ctime_ns']))
 side=m.ctime_sidecar(base);side.chmod(0o644);reject('writable-sidecar',lambda:m.validate_base(base,original['sha256']));side.chmod(0o444)
 original_source=source.read_bytes();source.write_bytes(original_source+b' ');reject('changed-historical-source',lambda:m.validate_base(base,original['sha256']));source.write_bytes(original_source)
 base.chmod(0o444);reject('subsequent-same-mode-chmod',lambda:m.validate_base(base,original['sha256']))
 base.chmod(0o644);base.write_bytes(b'changed bytes');base.chmod(0o444);reject('changed-content',lambda:m.validate_base(base,original['sha256']))
 second=p/'writer.raw';second.write_bytes(b'writer fixture');fd=os.open(second,os.O_WRONLY);second.chmod(0o444)
 try:reject('retained-writable-descriptor',lambda:m.validate_base(second,m.digest(second)))
 finally:os.close(fd)
 altered=dict(original);altered['mtime_ns']+=1;reject('non-ctime-difference',lambda:m.check_ctime_pair(original,altered))
 result={'scope':'Actual host filesystem fixture, synthetic owned bytes only. No firmware/guest/retained backing or historical report mutated.','source_sha256':m.digest(tool),'checks':checks}
pathlib.Path(__file__).with_name('execution.json').write_text(json.dumps(result,indent=2)+'\n')
