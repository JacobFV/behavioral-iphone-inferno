"""Assemble the app-tour video from real emulator captures.

build_tour.py CUTS.json OUT.mp4 FFMPEG_DIR

CUTS.json: {"sections": [{"kind": "card", "title": ..., "body": ..., "seconds": 3}
                         | {"kind": "clip", "label": ..., "caption": ..., "frames": [[t, path], ...],
                            "speed": N, "interval": 1}]}
A clip shows each capture (taken every `interval` s) for interval/speed seconds (frames are never generated or
edited, only scaled); the corner tag states the speed-up.
"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

CUTS, OUT, FF = json.load(open(sys.argv[1])), Path(sys.argv[2]), Path(sys.argv[3])
W, H, FPS = 1920, 1080, 30
BG, T1, T2, T3, ACC = (9, 10, 13), (238, 238, 240), (170, 172, 178), (112, 114, 122), (122, 196, 255)
FD = '/usr/share/fonts/truetype/ubuntu/'
f = lambda name, size: ImageFont.truetype(FD + name, size)
F_KICK, F_HEAD, F_BODY, F_TAG, F_FOOT = f('UbuntuMono-B.ttf', 24), f('Ubuntu-B.ttf', 72), f('Ubuntu-R.ttf', 34), f('UbuntuMono-B.ttf', 26), f('Ubuntu-R.ttf', 22)
FOOT = 'Real iOS 14.0 beta 5 on an emulated iPhone 11 · QEMU (ChefKiss Inferno) on an aarch64 Linux server · frames captured from the emulator display'
PH = 980
cache = {}


def phone(path):
    if path not in cache:
        im = Image.open(path).convert('RGB')
        w = round(im.width * PH / im.height)
        im = im.resize((w, PH), Image.LANCZOS)
        mask = Image.new('L', im.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, PH - 1), 54, fill=255)
        cache.clear(); cache[path] = (im, mask)
    return cache[path]


def wrap(draw, text, font, width):
    lines, line = [], ''
    for word in text.split():
        trial = (line + ' ' + word).strip()
        if draw.textlength(trial, font=font) > width and line:
            lines.append(line); line = word
        else:
            line = trial
    return lines + ([line] if line else [])


def base():
    im = Image.new('RGB', (W, H), BG)
    ImageDraw.Draw(im).text((80, H - 44), FOOT, font=F_FOOT, fill=T3)
    return im


def card(sec):
    im = base(); d = ImageDraw.Draw(im)
    d.text((160, 330), sec.get('kicker', 'IPHONE ON LINUX'), font=F_KICK, fill=ACC)
    y = 380
    for line in wrap(d, sec['title'], F_HEAD, 1500):
        d.text((160, y), line, font=F_HEAD, fill=T1); y += 86
    y += 20
    for line in wrap(d, sec.get('body', ''), F_BODY, 1400):
        d.text((160, y), line, font=F_BODY, fill=T2); y += 48
    return im


def clip_frame(sec, path, n, total):
    im = base(); d = ImageDraw.Draw(im)
    ph, mask = phone(path)
    x = 240
    im.paste(ph, (x, (H - PH) // 2 - 10), mask)
    tx = x + ph.width + 120
    d.text((tx, 250), sec.get('kicker', 'APP'), font=F_KICK, fill=ACC)
    y = 296
    for line in wrap(d, sec['label'], F_HEAD, W - tx - 100):
        d.text((tx, y), line, font=F_HEAD, fill=T1); y += 86
    y += 16
    for line in wrap(d, sec.get('caption', ''), F_BODY, W - tx - 120):
        d.text((tx, y), line, font=F_BODY, fill=T2); y += 48
    tag = 'REAL CAPTURE · %s' % ('1x' if sec['speed'] == 1 else '%gx' % sec['speed'])
    d.rounded_rectangle((tx, 760, tx + d.textlength(tag, font=F_TAG) + 36, 806), 8, outline=T3, width=2)
    d.text((tx + 18, 769), tag, font=F_TAG, fill=T2)
    return im


proc = subprocess.Popen([str(FF / 'ffmpeg'), '-y', '-v', 'error', '-f', 'image2pipe', '-c:v', 'png', '-framerate', str(FPS), '-i', '-',
                         '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(OUT)],
                        stdin=subprocess.PIPE, env={'LD_LIBRARY_PATH': str(FF)})
seconds = 0.0
for sec in CUTS['sections']:
    if sec['kind'] == 'card':
        im = card(sec); n = round(sec.get('seconds', 3) * FPS)
        for _ in range(n): im.save(proc.stdin, 'PNG', compress_level=1)
        seconds += n / FPS
    else:
        hold = max(1, round(FPS * sec.get('interval', 1) / sec['speed']))
        for i, (_, path) in enumerate(sec['frames']):
            im = clip_frame(sec, path, i, len(sec['frames']))
            for _ in range(hold): im.save(proc.stdin, 'PNG', compress_level=1)
            seconds += hold / FPS
proc.stdin.close(); proc.wait()
print(json.dumps({'out': str(OUT), 'seconds': round(seconds, 1), 'rc': proc.returncode}))
