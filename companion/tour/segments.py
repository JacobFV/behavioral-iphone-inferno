# segments.py OUT.json BOOTDIR... : per app, the recorded frames (time,path) within its tour window, across all tour boots
import json,sys,glob,os
out=sys.argv[1]; segs=[]
for B in sys.argv[2:]:
    caps=[]
    for r in sorted(glob.glob(B+"/rec/chunk-*/report.json")):
        try: d=json.load(open(r))
        except Exception: continue
        caps+=[(c["time"],c["path"]) for c in d.get("captures",[]) if os.path.exists(c["path"])]
    caps.sort()
    for t in sorted(glob.glob(B+"/tour-*/actions.json")):
        acts=json.load(open(t)); cur=None; frozen={x["index"] for x in acts if "frozen_after" in x}
        for a in acts:
            if "app" in a: cur={"app":a["app"],"index":a.get("index"),"boot":B,"t0":a["started"]}
            if "app_end" in a and cur:
                cur["t1"]=a["finished"]; cur["frames"]=[(tt,p) for tt,p in caps if cur["t0"]<=tt<=cur["t1"]]
                cur["tainted"]= (a.get("index") in frozen) or ((a.get("index") or 0)+1 in frozen)
                segs.append(cur); cur=None
json.dump(segs,open(out,"w")); print(len(segs),"segments")
