# bringup.py BOOTDIR : after unlock, dismiss system alerts until the app screen is clear, then press Home
# (unless BRINGUP_NO_HOME=1, which leaves the launched app in the foreground for recording).
import json,os,subprocess,sys,time
from PIL import Image
from pathlib import Path
B=sys.argv[1]; R=str(Path(__file__).resolve().parent.parent / "run")
sock=[x for x in json.load(open(B+"/command.json")) if "vnc.sock" in str(x)][0][5:]
n=[0]; RUN=int(time.time())
def look():
    n[0]+=1; o=f"{B}/bring-{RUN}-{n[0]:03d}"
    subprocess.run([R,"observe","--socket",sock,"--output",o],capture_output=True)
    return Image.open(o+"/settled.png").convert("RGB")
def tap(x,y):
    n[0]+=1
    subprocess.run([R,"owned-control","--report",B,"--output",f"{B}/bring-{RUN}-{n[0]:03d}-tap","tap",str(round(x/832*32767)),str(round(y/1792*32767)),"--duration-ms","120"],capture_output=True)
def alert(im):
    # A system alert: white body at mid-screen and blue button text on its button row (y~1014).
    body = im.getpixel((416, 880)); row = [im.getpixel((x, y)) for x in range(200, 640, 4) for y in (1006, 1014, 1022)]
    return min(body) > 225 and any(p[2] > 150 and p[2] - p[0] > 60 for p in row)
if os.environ.get("BRINGUP_NO_HOME")=="1":
    # Imported apps can be any colour, so don't infer "lock screen" from saturation: just close
    # alerts on top of the launched app and leave it in the foreground.
    for k in range(8):
        im=look()
        if alert(im): tap(278,1014); time.sleep(20); continue
        if k >= 2: break
        time.sleep(20)
    print("alerts cleared, app left in foreground"); sys.exit(0)
clear_since=None; deadline=time.time()+900
while time.time()<deadline:
    im=look(); px=im.getpixel((60,1500)); sat=max(px)-min(px); val=sum(px)/3
    if sat>40:  # wallpaper: still on the lock screen (or Home), so unlock
        clear_since=None
        n[0]+=1
        subprocess.run([R,"owned-control","--report",B,"--output",f"{B}/bring-{RUN}-{n[0]:03d}-unlock","swipe",str(round(416/832*32767)),str(round(1765/1792*32767)),str(round(416/832*32767)),str(round(500/1792*32767)),"--duration-ms","1500"],capture_output=True)
        time.sleep(45); continue
    if val<230:  # uniform grey: an app dimmed by a system alert
        clear_since=None
        # Close on the beta alert spans the full width; on the setup alert x=278 is Not Now.
        tap(278,1010)
        time.sleep(20); continue
    clear_since=clear_since or time.time()
    if time.time()-clear_since>90: break
    time.sleep(15)
if os.environ.get("BRINGUP_NO_HOME")=="1":
    print("clear, app left in foreground", time.time()-deadline+900); sys.exit(0)
subprocess.run([R,"observe","--socket",sock,"--home-button","--output",f"{B}/bring-{RUN}-home"],capture_output=True)
time.sleep(20); print("home", time.time()-deadline+900)
