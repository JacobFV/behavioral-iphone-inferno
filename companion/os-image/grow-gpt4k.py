#!/usr/bin/env python3
"""Expand a disposable 4KiB GPT disk; never edit its APFS metadata."""
import argparse
import hashlib
import json
import pathlib
import struct
import subprocess
import uuid
import zlib

BLOCK = 4096
TABLE_BYTES = 16384
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=pathlib.Path, required=True)
parser.add_argument('--source-sha256', required=True)
parser.add_argument('--output', type=pathlib.Path, required=True)
args = parser.parse_args()
source = args.source.resolve()
output = args.output.resolve()
if output.exists():
    parser.error('output already exists')
source_hash = hashlib.file_digest(source.open('rb'), 'sha256').hexdigest()
if source_hash != args.source_sha256:
    parser.error('source SHA256 mismatch')
old_bytes = source.stat().st_size
new_bytes = 32 * 1024 ** 3
if old_bytes % BLOCK or old_bytes >= new_bytes:
    parser.error('source must be block aligned and smaller than 32GiB')
old_last = old_bytes // BLOCK - 1
new_last = new_bytes // BLOCK - 1

def read_header(file, lba, alternate):
    file.seek(lba * BLOCK)
    header = bytearray(file.read(BLOCK))
    assert header[:8] == b'EFI PART'
    assert struct.unpack_from('<II', header, 8) == (0x10000, 92)
    saved = struct.unpack_from('<I', header, 16)[0]
    struct.pack_into('<I', header, 16, 0)
    assert zlib.crc32(header[:92]) == saved, 'GPT header CRC mismatch'
    struct.pack_into('<I', header, 16, saved)
    assert struct.unpack_from('<QQ', header, 24) == (lba, alternate)
    table_lba, count, entry_size, crc = struct.unpack_from('<QIII', header, 72)
    assert (count, entry_size) == (128, 128)
    file.seek(table_lba * BLOCK)
    table = file.read(TABLE_BYTES)
    assert len(table) == TABLE_BYTES and zlib.crc32(table) == crc
    return header, bytearray(table)

with source.open('rb') as file:
    primary, entries = read_header(file, 1, old_last)
    backup, backup_entries = read_header(file, old_last, 1)
    assert entries == backup_entries and primary[56:72] == backup[56:72]
    assert struct.unpack_from('<Q', primary, 72)[0] == 2
    assert struct.unpack_from('<Q', backup, 72)[0] == old_last - 4
    assert not any(entries[128:]), 'exactly one APFS partition required'
    assert entries[:16] == uuid.UUID('7c3457ef-0000-11aa-aa11-00306543ecac').bytes_le
    start, old_end = struct.unpack_from('<QQ', entries, 32)
    assert start >= 6 and start <= old_end <= old_last - 5
    file.seek(start * BLOCK + 32)
    assert file.read(4) == b'NXSB'

output.parent.mkdir(parents=True, exist_ok=True)
# Reflink preserves a fast independent copy where supported; never a hard link.
subprocess.run(['cp', '--reflink=auto', '--sparse=always', '--', str(source), str(output)], check=True)
new_end = new_last - 5
struct.pack_into('<Q', entries, 40, new_end)
crc = zlib.crc32(entries)

def update_header(header, current, other, table_lba):
    struct.pack_into('<I', header, 16, 0)
    struct.pack_into('<QQ', header, 24, current, other)
    struct.pack_into('<Q', header, 48, new_end)
    struct.pack_into('<Q', header, 72, table_lba)
    struct.pack_into('<I', header, 88, crc)
    struct.pack_into('<I', header, 16, zlib.crc32(header[:92]))
    return header

with output.open('r+b') as file:
    file.truncate(new_bytes)
    file.seek(458)
    file.write(struct.pack('<I', new_last))
    file.seek(BLOCK)
    file.write(update_header(primary, 1, new_last, 2))
    file.write(entries)
    # Retire only the previous backup GPT, outside the original partition.
    file.seek((old_last - 4) * BLOCK)
    file.write(bytes(5 * BLOCK))
    file.seek((new_last - 4) * BLOCK)
    file.write(entries)
    file.write(update_header(backup, new_last, 1, new_last - 4))
    file.flush()
    import os
    os.fsync(file.fileno())
with output.open('rb') as file:
    p, t = read_header(file, 1, new_last)
    b, u = read_header(file, new_last, 1)
    assert t == u and p[56:72] == b[56:72]
    assert struct.unpack_from('<QQ', t, 32) == (start, new_end)

def payload_hash(path):
    digest = hashlib.sha256()
    remaining = (old_end - start + 1) * BLOCK
    with path.open('rb') as file:
        file.seek(start * BLOCK)
        while remaining:
            chunk = file.read(min(8 * 1024 ** 2, remaining))
            assert chunk
            digest.update(chunk)
            remaining -= len(chunk)
    return digest.hexdigest()

payload = payload_hash(source)
assert payload_hash(output) == payload, 'original APFS contents changed'
record = {'source': str(source), 'source_sha256': source_hash,
          'output': str(output), 'output_bytes': new_bytes,
          'output_sha256': hashlib.file_digest(output.open('rb'), 'sha256').hexdigest(),
          'original_apfs_sha256': payload, 'block_size': BLOCK,
          'partition_start_lba': start, 'partition_end_lba': new_end,
          'partition_bytes': (new_end - start + 1) * BLOCK,
          'script_sha256': hashlib.file_digest(open(__file__, 'rb'), 'sha256').hexdigest(),
          'apfs_resized': False, 'note': 'GPT only; original APFS metadata/content unchanged. Guest APFS API growth still required.'}
output.with_suffix(output.suffix + '.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2), flush=True)
