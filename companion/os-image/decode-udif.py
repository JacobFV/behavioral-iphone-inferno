#!/usr/bin/env python3
"""Decode stored, unencrypted UDIF from a local IPSW; never download firmware."""
import argparse, zipfile, struct, plistlib, ctypes, pathlib, json, hashlib, zlib
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--ipsw', type=pathlib.Path, required=True)
p.add_argument('--member', required=True)
p.add_argument('--liblzfse', required=True)
p.add_argument('--output-dir', type=pathlib.Path, required=True)
a = p.parse_args()
root = a.output_dir.resolve()
root.mkdir(parents=True, exist_ok=True)
src = a.ipsw.resolve()
libpath = str(pathlib.Path(a.liblzfse).resolve())
if (root / 'official-os.raw').exists():
    p.error('output already exists')
lib = ctypes.CDLL(libpath)
dec = lib.lzfse_decode_buffer
dec.restype = ctypes.c_size_t
dec.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p]
z = zipfile.ZipFile(src)
i = z.getinfo(a.member)
assert i.compress_type == 0
f = src.open('rb')
f.seek(i.header_offset)
hdr = f.read(30)
base = i.header_offset + 30 + sum(struct.unpack_from('<HH', hdr, 26))
f.seek(base + i.file_size - 512)
t = f.read(512)
assert t[:4] == b'koly'
o, n = struct.unpack_from('>QQ', t, 216)
f.seek(base + o)
xml = f.read(n)
meta = plistlib.loads(xml)
(root / 'udif.plist').write_bytes(xml)
sectors = struct.unpack_from('>Q', t, 492)[0]
fork = struct.unpack_from('>Q', t, 24)[0]
out = root / 'official-os.raw'
rec = {'input': str(src), 'member': i.filename, 'input_member_bytes': i.file_size, 'zip_crc32': hex(i.CRC), 'liblzfse': libpath, 'liblzfse_sha256': hashlib.file_digest(open(libpath, 'rb'), 'sha256').hexdigest(), 'decoder_sha256': hashlib.file_digest(open(__file__, 'rb'), 'sha256').hexdigest(), 'output': str(out), 'output_bytes': sectors * 512, 'maps': []}
with out.open('wb') as dst:
    dst.truncate(sectors * 512)
    for m in meta['resource-fork']['blkx']:
        d = m['Data']
        assert d[:4] == b'mish'
        first, count, off = struct.unpack_from('>QQQ', d, 8)
        nr = struct.unpack_from('>I', d, 200)[0]
        rec['maps'].append({'name': m['Name'], 'first_sector': first, 'sectors': count, 'runs': nr})
        for r in range(nr):
            typ, _, s, c, co, cl = struct.unpack_from('>IIQQQQ', d, 204 + 40 * r)
            if typ in (4294967295, 2147483646):
                continue
            assert first + s + c <= sectors
            if typ in (0, 2):
                continue
            f.seek(base + fork + off + co)
            b = f.read(cl)
            assert len(b) == cl
            if typ == 2147483655:
                buf = ctypes.create_string_buffer(c * 512)
                n = dec(buf, len(buf), b, len(b), None)
                assert n == c * 512, (n, c)
                b = buf.raw
            elif typ == 1:
                assert len(b) == c * 512
            else:
                raise ValueError(hex(typ))
            dst.seek((first + s) * 512)
            dst.write(b)
            if r and r % 1000 == 0:
                print(m['Name'], r, '/', nr, flush=True)
print('Decoded; hashing original member and raw', flush=True)
f.seek(base)
h = hashlib.sha256()
crc = 0
left = i.file_size
while left:
    b = f.read(min(left, 8 * 1024 * 1024))
    assert b
    left -= len(b)
    h.update(b)
    crc = zlib.crc32(b, crc)
assert crc == i.CRC
rec['input_member_sha256'] = h.hexdigest()
rec['output_sha256'] = hashlib.file_digest(out.open('rb'), 'sha256').hexdigest()
(root / 'conversion.json').write_text(json.dumps(rec, indent=2) + '\n')
print(json.dumps(rec, indent=2), flush=True)
