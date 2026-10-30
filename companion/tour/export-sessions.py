#!/usr/bin/env python3
"""export-sessions.py NAME... : encode each session's whole recording (rec/chunk-*/observed-*.png, in
capture order) to ~/inferno-chain/clips/sessions/NAME.mp4 plus a poster, at a fixed 8 frames/s, so a
session's frames survive any later prune. Skips sessions already exported. Uses ~/inferno-chain/ffmpeg."""
import glob, json, os, subprocess, sys
from PIL import Image
H = os.path.expanduser('~/inferno-chain'); A = os.path.expanduser('~/.local/share/inferno/app-import')
OUT = H + '/clips/sessions'; FF = H + '/ffmpeg'; ENV = dict(os.environ, LD_LIBRARY_PATH=FF)
os.makedirs(OUT, exist_ok=True)
index_path = OUT + '/index.json'
index = json.load(open(index_path)) if os.path.exists(index_path) else []
done = {e['session'] for e in index}
for name in sys.argv[1:]:
    if name in done or os.path.exists(f'{OUT}/{name}.mp4'):
        print('skip', name); continue
    frames = sorted(glob.glob(f'{A}/session-{name}/rec/chunk-*/observed-*.png'))
    if not frames:
        print('no frames', name); continue
    p = subprocess.Popen([FF + '/ffmpeg', '-y', '-v', 'error', '-f', 'image2pipe', '-c:v', 'png', '-framerate', '8', '-i', '-',
                          '-vf', 'scale=414:-2', '-c:v', 'libx264', '-preset', 'medium', '-crf', '22', '-pix_fmt', 'yuv420p',
                          '-movflags', '+faststart', f'{OUT}/{name}.mp4'], stdin=subprocess.PIPE, env=ENV)
    n = 0
    for f in frames:
        try:
            Image.open(f).convert('RGB').save(p.stdin, 'PNG', compress_level=1); n += 1
        except Exception:
            continue
    p.stdin.close(); p.wait()
    subprocess.run([FF + '/ffmpeg', '-y', '-v', 'error', '-ss', '%.2f' % (n / 8 * 0.5), '-i', f'{OUT}/{name}.mp4', '-frames:v', '1',
                    '-q:v', '3', f'{OUT}/{name}.jpg'], env=ENV)
    index.append({'session': name, 'file': name + '.mp4', 'poster': name + '.jpg', 'frames': n, 'seconds_at_8fps': round(n / 8, 1)})
    json.dump(index, open(index_path, 'w'), indent=1)
    print('exported', name, n, 'frames')
