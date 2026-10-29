import json,sys,glob
from PIL import Image,ImageDraw
B=sys.argv[1]; tour=sys.argv[2]; out=sys.argv[3]
caps=[]
for r in sorted(glob.glob(B+"/rec/chunk-*/report.json")):
    try: d=json.load(open(r))
    except Exception: continue
    caps+= [(c["time"],c["path"]) for c in d.get("captures",[])]
caps.sort()
acts=json.load(open(tour+"/actions.json"))
apps=[];cur=None
for a in acts:
    if "app" in a: cur=[a["app"],a["started"],None]; apps.append(cur)
    if "app_end" in a and cur: cur[2]=a["finished"]
rows=[]
for name,t0,t1 in apps:
    t1=t1 or (caps[-1][0] if caps else t0)
    fr=[p for t,p in caps if t0<=t<=t1]
    if not fr: continue
    pick=[fr[int(i*(len(fr)-1)/5)] for i in range(6)]
    row=Image.new("RGB",(6*208,448+30),"white")
    for i,p in enumerate(pick): row.paste(Image.open(p).convert("RGB").resize((208,448)),(i*208,30))
    ImageDraw.Draw(row).text((5,5),name,fill="black"); rows.append(row)
W=Image.new("RGB",(6*208,len(rows)*478),"white")
for i,r in enumerate(rows): W.paste(r,(0,i*478))
W.save(out); print(len(rows),"apps",len(caps),"caps")
