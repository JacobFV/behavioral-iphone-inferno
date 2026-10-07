# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only independent review of completed conversion, no duplicate disk hash."""
import copy,hashlib,json,struct,zlib
from pathlib import Path
D=Path(__file__).resolve().parent
S=Path('/home/brandonin/.local/share/inferno/images/ios14b5/stage50-flatten-source-1')
rawprov=(S/'flatten-provenance.json').read_bytes();p=json.loads(rawprov);assert p['status']=='verified'
h=lambda b:hashlib.sha256(b).hexdigest()
def norm(v):
 v=copy.deepcopy(v)
 for e in v.get('metadata_revalidation',[]):e.pop('verified_time',None)
 return v
assert norm(p['source_before'])==norm(p['source_after'])
assert p['source_identities_before']==p['source_identities_after']
for path,ident in p['source_identities_after'].items():
 s=Path(path).stat();assert all(getattr(s,k)==v for k,v in ident.items())
commands=p['commands'];conv=[x for x in commands if x['argv'][1]=='convert'];cmp=[x for x in commands if x['argv'][1]=='compare'];assert len(conv)==len(cmp)==1
assert conv[0]['exit_code']==cmp[0]['exit_code']==0
assert conv[0]['argv'][2:8]==['-f','qcow2','-O','raw','-S','4k']
assert cmp[0]['argv'][2:6]==['-f','qcow2','-F','raw']
assert conv[0]['argv'][-2:]==cmp[0]['argv'][-2:]==[p['source_before']['layers'][0]['path'],str(S/'root.raw')]
final=p['raw_final'];s=(S/'root.raw').stat();assert s.st_size==34359738368 and (s.st_mode&0o777)==0o444
for k,v in [('device',s.st_dev),('inode',s.st_ino),('bytes',s.st_size),('ctime_ns',s.st_ctime_ns),('mtime_ns',s.st_mtime_ns)]:assert final[k]==v
assert final['sha256']==p['raw_sha256_before_compare']
markerraw=(S/'KEEP-OVERLAY-BACKING.json').read_bytes();marker=json.loads(markerraw);assert marker['backing']['path']==final['path'] and marker['backing']['sha256']==final['sha256'];assert marker['provenance_sha256']==h(rawprov)
# Independently reread just GPT sectors/entry arrays, not the whole32GiB image.
with (S/'root.raw').open('rb') as f:
 for key in ['primary','backup']:
  g=p['gpt'][key];f.seek(g['lba']*4096);b=f.read(4096);assert b[:8]==b'EFI PART';size=struct.unpack_from('<I',b,12)[0];hdr=bytearray(b[:size]);hdr[16:20]=b'\0'*4;assert zlib.crc32(hdr)&0xffffffff==g['header_crc32']
  lba,n,sz,crc=struct.unpack_from('<QIII',b,72);f.seek(lba*4096);entries=f.read(n*sz);assert len(entries)==n*sz and zlib.crc32(entries)&0xffffffff==g['entries_crc32']==crc
result={'verdict':'Completed conversion evidence and current bounded metadata/GPT checks pass; no guest execution or staging approval implied.','provenance_sha256':h(rawprov),'marker_sha256':h(markerraw),'raw_identity':final,'allocated_bytes':p['allocated_bytes'],'source_layer_count':len(p['source_after']['layers']),'source_identical_pre_post':True,'current_source_metadata_matches_postflight':True,'logical_compare_exit0':True,'independent_GPT_CRC_recheck':True,'new_raw_mode':'0444','marker_backing_schema_compatible':True,'limits':['Full source/output hashing and logical qemu-img comparison are evidenced by the conversion worker transcript and reviewed script, not duplicated by reviewer.','Independent review reread bounded GPT metadata only; unchanged source identities are current stat comparisons plus recorded fullhash/postflight.','No disk mutation, chmod, attestation creation, VM, staging or control action performed by reviewer.']}
(D/'review.json').write_text(json.dumps(result,indent=2)+'\n');(D/'flatten-provenance.json').write_bytes(rawprov);(D/'KEEP-OVERLAY-BACKING.json').write_bytes(markerraw);print(json.dumps(result,indent=2))
