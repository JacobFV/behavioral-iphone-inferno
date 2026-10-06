#!/usr/bin/env python3
"""Package unchanged n104 multitouch IM4P in an explicitly unsigned IMG4 container."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def item(data, offset=0):
    """Read one definite, minimally encoded DER TLV without interpreting payload."""
    start = offset
    if offset + 2 > len(data):
        raise ValueError('truncated DER header')
    tag, length = data[offset:offset + 2]
    offset += 2
    if length & 128:
        count = length & 127
        if not count or count > 8 or offset + count > len(data):
            raise ValueError('invalid DER length')
        raw = data[offset:offset + count]
        length = int.from_bytes(raw, 'big')
        if raw[0] == 0 or length < 128:
            raise ValueError('nonminimal DER length')
        offset += count
    end = offset + length
    if end > len(data):
        raise ValueError('truncated DER content')
    return tag, data[offset:end], end, data[start:end]


def tlv(tag, content):
    n = len(content)
    raw = n.to_bytes((n.bit_length() + 7) // 8, 'big')
    length = bytes([n]) if n < 128 else bytes([128 | len(raw)]) + raw
    return bytes([tag]) + length + content


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ipsw', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    with zipfile.ZipFile(a.ipsw) as archive:
        source = archive.read('Firmware/N104_Multitouch.im4p')
    tag, content, end, _ = item(source)
    if tag != 0x30 or end != len(source):
        raise ValueError('expected one complete IM4P sequence')
    first, label, pos, _ = item(content)
    second, payload_type, _, _ = item(content, pos)
    if first != 0x16 or label != b'IM4P' or second != 0x16 or payload_type != b'mtfw':
        raise ValueError('expected original IM4P mtfw payload')
    wrapped = tlv(0x30, tlv(0x16, b'IMG4') + source)
    _, body, end, _ = item(wrapped)
    _, name, pos, _ = item(body)
    _, _, end_body, recovered = item(body, pos)
    if name != b'IMG4' or end != len(wrapped) or end_body != len(body) or recovered != source:
        raise ValueError('wrapper readback failed')
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('xb') as f:
        f.write(wrapped)
    digest = lambda b: hashlib.sha256(b).hexdigest()
    a.output.with_suffix(a.output.suffix + '.json').write_text(json.dumps({
        'source_archive': str(a.ipsw.resolve()),
        'source_member': 'Firmware/N104_Multitouch.im4p',
        'source_im4p_bytes': len(source), 'source_im4p_sha256': digest(source),
        'output_bytes': len(wrapped), 'output_sha256': digest(wrapped),
        'recovered_im4p_sha256': digest(recovered), 'recovered_im4p_exact_equal': True,
        'outer_children': ['IA5String IMG4', 'unchanged original IM4P sequence'],
        'manifest_present': False, 'signature_created': False, 'ticket_created': False,
        'meaning': 'Unsigned format packaging only; no claim of personalization, authentication or successful guest loading.',
        'tool_sha256': digest(Path(__file__).read_bytes())
    }, indent=2) + '\n')
    print(a.output)


if __name__ == '__main__':
    main()
