#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Copy the plain rdsk IM4P payload of the pinned n104ap18A5351d profile; no decryption."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct

MAX_COMPONENT = 512 << 20


def digest(data):
    return hashlib.sha256(data).hexdigest()


def identity(st):
    return {k: getattr(st, k) for k in ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns')}


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def read_json(data):
    def invalid(value):
        raise ValueError('Nonfinite JSON value: ' + value)
    return json.loads(data, object_pairs_hook=unique_pairs, parse_constant=invalid)


def tlv(stream, offset, boundary, tag):
    """Single-byte tags, definite canonical DER lengths, bounded to component."""
    if offset + 2 > boundary:
        raise ValueError('Truncated DER header')
    stream.seek(offset)
    head = stream.read(2)
    if len(head) != 2 or head[0] != tag:
        raise ValueError('Unexpected DER tag')
    size = head[1]
    header = 2
    if size & 0x80:
        count = size & 0x7f
        if not 1 <= count <= 4 or offset + 2 + count > boundary:
            raise ValueError('Unsupported DER length')
        raw = stream.read(count)
        if len(raw) != count or raw[0] == 0:
            raise ValueError('Noncanonical/truncated DER length')
        size = int.from_bytes(raw, 'big')
        if size < 128:
            raise ValueError('Noncanonical DER long length')
        header += count
    start = offset + header
    end = start + size
    if end > boundary:
        raise ValueError('DER value exceeds parent')
    return start, size, end


def payload_info(stream, size):
    start, _, end = tlv(stream, 0, size, 0x30)
    if end != size:
        raise ValueError('Trailing container bytes')
    offset = start
    texts = []
    for expected in (b'IM4P', b'rdsk', None):
        pos, length, offset = tlv(stream, offset, end, 0x16)
        if not 1 <= length <= 128:
            raise ValueError('Unsupported IM4P string size')
        stream.seek(pos)
        text = stream.read(length)
        if any(c > 127 for c in text) or (expected is not None and text != expected):
            raise ValueError('Unsupported IM4P identity/type')
        texts.append(text.decode('ascii'))
    pos, length, finish = tlv(stream, offset, end, 0x04)
    if finish != end:
        raise ValueError('Additional IM4P fields unsupported, including keybags/encryption metadata')
    if length < 4096:
        raise ValueError('Payload too small for HFS volume')
    stream.seek(pos + 1024)
    header = stream.read(512)
    signature, version = struct.unpack_from('>2sH', header)
    if (signature, version) not in ((b'H+', 4), (b'HX', 5)):
        raise ValueError('Not supported plaintext HFS+/HFSX; no decryption/decompression attempted')
    block_size, blocks, free = struct.unpack_from('>III', header, 40)
    if not (512 <= block_size <= 1 << 20) or block_size & (block_size - 1) or blocks < 4 or free > blocks:
        raise ValueError('Invalid HFS allocation geometry')
    if block_size * blocks != length:
        raise ValueError('HFS allocation size differs from whole payload')
    return {'offset': pos, 'bytes': length, 'type': texts[1], 'description': texts[2],
            'hfs': {'signature': signature.decode(), 'version': version,
                    'block_size': block_size, 'total_blocks': blocks, 'free_blocks': free}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--profile-sha256', required=True)
    parser.add_argument('--ramdisk-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True, help='NEW external directory')
    args = parser.parse_args()
    output = None
    try:
        source = Path(__file__).resolve()
        source_hash = digest(source.read_bytes())
        profile_path = args.profile.absolute()
        if profile_path.resolve(strict=True) != profile_path or not stat.S_ISREG(profile_path.lstat().st_mode) or profile_path.stat().st_size > 1 << 20:
            raise ValueError('Profile must be bounded, regular and unaliased')
        profile_bytes = profile_path.read_bytes()
        if digest(profile_bytes) != args.profile_sha256:
            raise ValueError('Profile SHA256 mismatch')
        profile = read_json(profile_bytes)
        expected = {'device': 'iPhone12,1', 'board': 'n104ap', 'build': '18A5351d',
                    'variant': 'Research Developer Erase Install (IPSW)'}
        if profile.get('schema') != 'inferno.early-boot.v1' or any(profile.get('provenance', {}).get(k) != v for k, v in expected.items()):
            raise ValueError('Unsupported profile identity')
        pin = profile['ramdisk']
        component = Path(pin['path'])
        if not component.is_absolute() or component.resolve(strict=True) != component or pin['sha256'] != args.ramdisk_sha256:
            raise ValueError('Ramdisk path/hash binding mismatch')
        spec = importlib.util.spec_from_file_location('importer', source.parent.parent / 'app-import.py')
        importer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(importer)
        destination = importer.external_output(args.output)
        with os.fdopen(os.open(component, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
            before = identity(os.fstat(stream.fileno()))
            if not stat.S_ISREG(before['st_mode']) or not 4096 <= before['st_size'] <= MAX_COMPONENT:
                raise ValueError('Component size/type unsupported')
            if 'size' in pin and pin['size'] != before['st_size']:
                raise ValueError('Profile component size mismatch')
            if hashlib.file_digest(stream, 'sha256').hexdigest() != args.ramdisk_sha256:
                raise ValueError('Ramdisk SHA256 mismatch')
            payload = payload_info(stream, before['st_size'])
            destination.mkdir(mode=0o700)
            output = destination
            (output / 'INCOMPLETE.json').write_text('{"status":"incomplete-do-not-consume"}\n')
            target = output / 'ramdisk-payload.raw'
            stream.seek(payload['offset'])
            remaining = payload['bytes']
            checksum = hashlib.sha256()
            with target.open('xb') as dest:
                while remaining:
                    data = stream.read(min(1 << 20, remaining))
                    if not data:
                        raise ValueError('Unexpected end of payload')
                    dest.write(data)
                    checksum.update(data)
                    remaining -= len(data)
                dest.flush()
                os.fsync(dest.fileno())
            after = identity(os.fstat(stream.fileno()))
            if before != after or identity(component.stat()) != before:
                raise ValueError('Source identity changed during extraction')
            stream.seek(0)
            if hashlib.file_digest(stream, 'sha256').hexdigest() != args.ramdisk_sha256:
                raise ValueError('Source content changed during extraction')
        with target.open('rb') as check:
            if hashlib.file_digest(check, 'sha256').hexdigest() != checksum.hexdigest():
                raise ValueError('Output readback mismatch')
        if profile_path.read_bytes() != profile_bytes or digest(source.read_bytes()) != source_hash:
            raise ValueError('Profile/extractor changed during extraction')
        record = {'schema': 'inferno.plain-recovery-extraction.v1', 'status': 'extracted-plain-payload-not-booted',
                  'profile': {'path': str(profile_path), 'sha256': args.profile_sha256},
                  'source': {'path': str(component), 'sha256': args.ramdisk_sha256, 'identity': before},
                  'payload': payload, 'output': {'path': str(target), 'bytes': target.stat().st_size, 'sha256': checksum.hexdigest()},
                  'extractor': {'path': str(source), 'sha256': source_hash},
                  'limits': ['Only bare rdsk IM4P with exactly four fields and plaintext whole HFS+/HFSX payload.',
                             'No authenticity assertion, decryption, decompression, ticket/signature/key operation or VM.',
                             'Filesystem header recognition is not a complete filesystem integrity check.']}
        with (output / 'extraction.json').open('x') as dest:
            json.dump(record, dest, indent=2)
            dest.write('\n')
        (output / 'INCOMPLETE.json').unlink()
        print(json.dumps(record))
    except Exception as exc:
        if output is not None:
            (output / 'failure.json').write_text(json.dumps({'status': 'failed-do-not-consume', 'error': str(exc)}) + '\n')
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
