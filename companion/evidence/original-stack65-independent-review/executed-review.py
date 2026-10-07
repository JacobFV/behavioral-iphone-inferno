import pathlib,json,subprocess,hashlib,re,tempfile,struct,uuid,mmap
M=pathlib.Path('/home/brandonin/Documents/behavioral-iphone-inferno');E=M/'companion/evidence/original-stack-samples-65';O=pathlib.Path(tempfile.mkdtemp(prefix='inferno-symbol65-review-'));results=[]
def sha(p):
 with pathlib.Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
for target in ['backboardd','springboard']:
 d=E/target;a=json.loads((d/'symbolication-audit.json').read_text());prov=a['provenance'];argv=['python3',str(E/'symbolize-sample.py')]
 for k in ['sample','cache','patch_plan','symbolizer','standalone']:
  assert sha(prov[k]['path'])==prov[k]['sha256'];argv+=['--'+k.replace('_','-'),prov[k]['path']]
 argv+=['--output',str(O/target)];v=subprocess.run(argv,capture_output=True,text=True);assert v.returncode==0,v.stderr
 equal={n:(O/target/n).read_bytes()==(d/n).read_bytes() for n in ['symbolized.txt','symbolizer-raw.txt','symbolizer-stderr.txt','symbolication-audit.json']};assert all(equal.values())
 raw=(d/'original-output.txt').read_text();sym=(d/'symbolized.txt').read_text();assert '\n'.join(x.split('  => ',1)[0] for x in sym.splitlines())+'\n'==raw
 pcs={int(x,16) for x in re.findall(r'\[(0x[0-9a-f]+)\]',raw)};mapped={int(x.split('\t')[0],16)+int(a['actual_slide'],16) for x in (d/'symbolizer-raw.txt').read_text().splitlines() if '\t' in x};unknown={int(x,16) for x in a['unmapped_PCs']};assert mapped.isdisjoint(unknown) and mapped|unknown==pcs
 rr=json.loads((d/'result.json').read_text());serial=(M/'.local-build/reports/app-boot-65/serial.log').read_bytes();assert hashlib.sha256(serial[:rr['serial']['bytes']]).hexdigest()==rr['serial']['sha256'];assert sha(d/'original-output.txt')==rr['decoded_sha256'];assert rr['transport_complete']
 results.append({'target':target,'actual_replay_exit':v.returncode,'stdout':v.stdout,'all_four_outputs_identical':equal,'original_lines_preserved_after_annotation_removal':True,'all_unique_PCs_partitioned_without_omission':{'total':len(pcs),'mapped':len(mapped),'explicit_unknown':len(unknown)},'exact_serial_prefix_hash_matches_final65':True,'raw_sample_hash_matches_transport':True,'provenance_all_input_hashes_match':True})
r={'scope':'Independent read-only review of actual65 attribution; no guest action, binaries changed or implementation patch','results':results,'replay_directory':str(O),'source_sha256':sha(E/'symbolize-sample.py'),'limits':['Nearest symbol is not function extent proof. Runtime image ends originate from original tool Binary Images; helper cross-checks UUID/base and chosen image, not every segment extent.','Standalone UUIDs checked separately; standalone and kernel PCs remain explicitly unmapped.','49 comparison describes sampled windows only; no claim wait branch never occurs in healthy operation.','Transport-complete diagnostic output does not by itself prove causal interpretation.']};(O/'review.json').write_text(json.dumps(r,indent=2)+'\n');print(O)
