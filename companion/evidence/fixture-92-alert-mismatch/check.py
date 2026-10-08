#!/usr/bin/env python3
"""Read-only actual image comparison; no classifier or image normalization."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image
ROOT=Path('/home/brandonin/Documents/behavioral-iphone-inferno');E=ROOT/'companion/evidence';A=Path('/home/brandonin/.local/share/inferno/app-import/fixed-timing-92-1');pins={};crop=(0,250,828,1450)
def rgb(p):
 raw=p.read_bytes();pins[str(p)]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
 with Image.open(p) as im:
  assert im.mode=='RGB' and im.size==(832,1792)
  return np.asarray(im)[250:1450,:828].copy()
def compare(a,b):
 d=b.astype(np.int16)-a.astype(np.int16);mask=np.any(d!=0,axis=2);y,x=np.where(mask);hist=np.unique(np.abs(d).max(2)[mask],return_counts=True)
 return {'changed_pixels':int(mask.sum()),'bbox_relative_crop':None if not mask.any() else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)],'max_abs_channel_difference':int(np.abs(d).max()),'mean_abs_changed_rgb':np.abs(d)[mask].mean(0).tolist() if mask.any() else [0,0,0],'mean_signed_changed_rgb':d[mask].mean(0).tolist() if mask.any() else [0,0,0],'pixel_max_abs_difference_histogram':{str(int(k)):int(v) for k,v in zip(*hist)},'reference_exact_black_pixels':int(np.all(a==0,axis=2).sum()),'reference_exact_black_changed':int((np.all(a==0,axis=2)&mask).sum())}
ref=rgb(E/'imported-fixture-91-visual/after-unlock-002/settled.png');actual=rgb(A/'before-beta/settled.png');result={'92_vs_91':compare(ref,actual),'92_before_vs_settled':compare(rgb(A/'before-beta/before.png'),actual)}
for run in [89,91]:
 records=[]
 for p in sorted((E/f'imported-fixture-{run}-visual/after-unlock-002').glob('*.png')):
  data=rgb(p);stats=compare(ref,data);records.append({'path':str(p),'crop_sha256':hashlib.sha256(data.tobytes()).hexdigest(),'changed_vs91':stats['changed_pixels'],'bbox_vs91':stats['bbox_relative_crop']})
 result[str(run)+'_within_attempt']=records
assert result['92_vs_91']['changed_pixels']==129964 and result['92_vs_91']['bbox_relative_crop']==[144,512,684,809]
assert result['92_before_vs_settled']['changed_pixels']==0
for name in ['sequence.json','before-beta/report.json']:
 p=A/name;raw=p.read_bytes();pins[str(p)]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
sequence=json.loads((A/'sequence.json').read_text());report=json.loads((A/'before-beta/report.json').read_text());initial=sequence['initial_unlock']['started_time'];settled=next(x for x in report['captures'] if x['path'].endswith('/settled.png'))
result.update({'scope':'Offline exact RGB comparison only; no threshold used to accept or authorize input','crop':list(crop),'full_image_geometry':[832,1792],'inputs':pins,'timing':{'second_unlock_submission_start':initial,'actual_settled_received':settled['received_time'],'elapsed_seconds':settled['received_time']-initial},'driver_error':sequence['error'],'observed_facts':['Outside full-image alert panel bbox(144,762,684,1059), all centralROI pixels match91 exactly.','Run89 nineteen frames have one internally identical alert crop, different from91 only within same panel.','Run91 five settled/observed frames share one crop; initial before.png is another screen and is not an alert reference.','Run92 before and settled central crops are identical.','Actual visible wording, panel geometry and Close control were personally reviewed in91 and92; no semantic classifier generated.'],'inference':'A stable cross-run alert material/backdrop/color variation is consistent with the low-amplitude panel-only differences. Pixel evidence cannot identify the original rendering mechanism, random seed, GPU/compositor cause, or whether hidden backdrop content at presentation differs.','recommendation':'Do not add pixel tolerances or expand exact templates blindly. Root can explicitly review each current same-run state and separately schedule its one fixed tap with the existing receiver deadline. Capture and review inside each43/18/13second budget; if review or source gate is late, abort that action. Preserve actual submission and write times, no automatic retry.','limits':['No new input, VM, capture or renderer source modification occurred in this analysis.','The92 rejection precedes beta dismissal/counter; it is not a counter-rendering failure.','No claim that longer settling will repair a cross-run exact template mismatch; retained within-run stability argues against that explanation but does not prove indefinite stability.']})
Path(__file__).with_name('audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['92_vs_91']))
