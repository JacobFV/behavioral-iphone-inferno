import sys,pathlib,json,hashlib,os,subprocess,time,shutil,struct,zlib,copy
M=pathlib.Path('/home/brandonin/Documents/behavioral-iphone-inferno');sys.path.insert(0,str(M/'companion'));import disk_overlay as ov
D=pathlib.Path('/home/brandonin/.local/share/inferno/images/ios14b5/stage50-flatten-source-1');S=M/'.local-build/reports/disk-preparation-50/report.json'
assert not D.exists()
for p in pathlib.Path('/proc').iterdir():
 if p.name.isdigit():
  try: assert pathlib.Path(os.readlink(p/'exe')).name!='qemu-system-aarch64','Live QEMU'
  except (FileNotFoundError,PermissionError,ProcessLookupError):pass
assert shutil.disk_usage(D.parent).free>34359738368+2*1024**3
D.mkdir(mode=0o700);R={'scope':'Host logical disk conversion only; no guest execution, staging or fabricated boot report','started':time.time(),'commands':[],'status':'running','script_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'host_revision':subprocess.check_output(['git','-C',str(M),'rev-parse','HEAD'],text=True).strip()}
def save(): (D/'flatten-provenance.json').write_text(json.dumps(R,indent=2)+'\n')
def run(*args):
 cmd=[T['binary'],*map(str,args)];env=os.environ.copy();env['LD_LIBRARY_PATH']=str(pathlib.Path(T['root'])/'root/usr/lib/aarch64-linux-gnu');start=time.time();v=subprocess.run(cmd,env=env,capture_output=True,text=True);R['commands'].append({'argv':cmd,'LD_LIBRARY_PATH':env['LD_LIBRARY_PATH'],'started':start,'ended':time.time(),'exit_code':v.returncode,'stdout':v.stdout,'stderr':v.stderr});save();v.check_returncode();return v.stdout
def identities(pre):
 paths=set(x['path'] for x in pre['layers'])|set(x['path'] for x in pre['auxiliary'].values());out={}
 for p in paths:
  s=pathlib.Path(p).stat();out[p]={k:getattr(s,k) for k in ['st_dev','st_ino','st_size','st_mode','st_mtime_ns','st_ctime_ns']}
 return out
def normalized(p):
 p=copy.deepcopy(p)
 for e in p.get('metadata_revalidation',[]):e.pop('verified_time',None)
 return p
try:
 T=ov.validate_tools(pathlib.Path('/home/brandonin/.local/share/inferno/disk-overlay-tools'));R['tool']=T;R['tool_version']=run('--version');R['source_before']=ov.load_stopped_overlay(S,T);R['source_identities_before']=identities(R['source_before']);save();print('preflight complete',flush=True)
 raw=D/'root.raw';src=pathlib.Path(R['source_before']['layers'][0]['path']);run('convert','-f','qcow2','-O','raw','-S','4k',src,raw);print('convert complete',flush=True)
 info=json.loads(run('info','--output=json','-f','raw',raw));assert info['virtual-size']==34359738368 and raw.stat().st_size==34359738368;R['raw_info']=info
 def gpt(f,lba):
  f.seek(lba*4096);b=f.read(4096);assert b[:8]==b'EFI PART';size=struct.unpack_from('<I',b,12)[0];assert 92<=size<=4096;crc=struct.unpack_from('<I',b,16)[0];h=bytearray(b[:size]);h[16:20]=b'\0'*4;assert zlib.crc32(h)&0xffffffff==crc
  cur,backup=struct.unpack_from('<QQ',b,24);assert cur==lba;entries,n,esz,ecrc=struct.unpack_from('<QIII',b,72);assert 0<n<=16384 and 128<=esz<=4096 and n*esz<=16*1024**2;f.seek(entries*4096);e=f.read(n*esz);assert len(e)==n*esz and zlib.crc32(e)&0xffffffff==ecrc
  return {'lba':lba,'backup_lba':backup,'header_crc32':crc,'entries_crc32':ecrc,'entry_count':n,'entry_size':esz}
 with raw.open('rb') as f:
  primary=gpt(f,1);backup=gpt(f,primary['backup_lba']);assert backup['backup_lba']==1 and primary['backup_lba']==raw.stat().st_size//4096-1;assert primary['entries_crc32']==backup['entries_crc32'];R['gpt']={'primary':primary,'backup':backup}
 R['raw_sha256_before_compare']=ov.digest(raw);save();run('compare','-f','qcow2','-F','raw',src,raw);print('logical comparison passed',flush=True)
 R['source_after']=ov.load_stopped_overlay(S,T);R['source_identities_after']=identities(R['source_after']);assert normalized(R['source_before'])==normalized(R['source_after']);assert R['source_identities_before']==R['source_identities_after'];assert ov.digest(raw)==R['raw_sha256_before_compare'];ov.reject_writable_handles(raw.stat());raw.chmod(0o444)
 R['raw_final']=ov.validate_base(raw,R['raw_sha256_before_compare'],allow_attestation=False);R['allocated_bytes']=raw.stat().st_blocks*512;R['status']='verified';R['ended']=time.time();save();(D/'KEEP-OVERLAY-BACKING.json').write_text(json.dumps({'purpose':'Retain this new logically flattened immutable stage50 backing and provenance. Original stage50 and ancestors also retained.','raw':R['raw_final'],'provenance_sha256':ov.digest(D/'flatten-provenance.json'),'no_guest_execution':True},indent=2)+'\n');print(json.dumps({'status':R['status'],'raw':R['raw_final'],'allocated_bytes':R['allocated_bytes']}),flush=True)
except BaseException as e:
 R['status']='failed';R['error']={'type':type(e).__name__,'detail':str(e)};save();raise
