#!/usr/bin/env python3
"""Wrap one source APFS partition in a disposable 4096-byte-sector GPT disk."""
import argparse, pathlib, struct, zlib, hashlib, json, uuid
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=pathlib.Path, required=True)
p.add_argument('--output', type=pathlib.Path, required=True)
a = p.parse_args()
src = a.source.resolve()
out = a.output.resolve()
r = out.parent
r.mkdir(parents=True, exist_ok=True)
if out.exists():
    p.error('output already exists')
bs = 4096
size = 8 * 1024 ** 3
last = size // bs - 1
first = 256
with src.open('rb') as f:
    f.seek(512)
    g = f.read(512)
    assert g[:8] == b'EFI PART', 'source requires 512-byte GPT'
    assert struct.unpack_from('<Q', g, 72)[0] == 2
    stored_crc = struct.unpack_from('<I', g, 16)[0]
    gh = bytearray(g[:92])
    struct.pack_into('<I', gh, 16, 0)
    assert zlib.crc32(gh) == stored_crc, 'source GPT header CRC mismatch'
    f.seek(1024)
    table = f.read(16384)
    assert zlib.crc32(table) == struct.unpack_from('<I', g, 88)[0], 'source GPT table CRC mismatch'
    entry = bytearray(table[:128])
    assert not any(table[128:]), 'exactly one source partition required'
    assert entry[:16] == uuid.UUID('7c3457ef-0000-11aa-aa11-00306543ecac').bytes_le, 'APFS partition required'
    s, e = struct.unpack_from('<QQ', entry, 32)
    off = s * 512
    n = (e - s + 1) * 512
    assert n % bs == 0
    assert first + n // bs <= last - 4, 'source partition too large for 8GiB wrapper'
    entries = bytearray(128 * 128)
    struct.pack_into('<QQ', entry, 32, first, first + n // bs - 1)
    entries[:128] = entry
    crc = zlib.crc32(entries)
    guid = uuid.UUID('75737bd4-7ef4-4842-a2b8-3b942af0611a').bytes_le

    def header(cur, other, table):
        b = bytearray(bs)
        struct.pack_into('<8sIIIIQQQQ16sQIII', b, 0, b'EFI PART', 65536, 92, 0, 0, cur, other, 6, last - 5, guid, table, 128, 128, crc)
        struct.pack_into('<I', b, 16, zlib.crc32(b[:92]))
        return b
    mbr = bytearray(bs)
    mbr[446:462] = struct.pack('<B3sB3sII', 0, b'\x00\x02\x00', 238, b'\xff\xff\xff', 1, last)
    mbr[510:512] = b'U\xaa'
    h = hashlib.sha256()
    with out.open('wb') as d:
        d.truncate(size)
        d.write(mbr)
        d.write(header(1, last, 2))
        d.write(entries)
        d.seek((last - 4) * bs)
        d.write(entries)
        d.write(header(last, 1, last - 4))
        d.seek(first * bs)
        f.seek(off)
        left = n
        while left:
            b = f.read(min(left, 8 * 1024 * 1024))
            assert b
            left -= len(b)
            h.update(b)
            d.write(b)
    with out.open('rb') as d:
        d.seek(first * bs)
        left = n
        verify = hashlib.sha256()
        while left:
            b = d.read(min(left, 8 * 1024 * 1024))
            left -= len(b)
            verify.update(b)
    assert h.digest() == verify.digest()
print('Payload copy verified; hashing wrapper', flush=True)
record = {'source': str(src), 'source_apfs_offset': off, 'apfs_bytes': n, 'apfs_sha256': h.hexdigest(), 'output': str(out), 'output_bytes': size, 'logical_block_size': bs, 'apfs_start_lba': first, 'apfs_end_lba': first + n // bs - 1, 'output_sha256': hashlib.file_digest(out.open('rb'), 'sha256').hexdigest(), 'wrapper_sha256': hashlib.file_digest(open(__file__, 'rb'), 'sha256').hexdigest(), 'note': 'Only GPT sector geometry changes; original APFS payload byte-identical; container not grown and Data volume absent.'}
out.with_suffix(out.suffix + '.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2), flush=True)
