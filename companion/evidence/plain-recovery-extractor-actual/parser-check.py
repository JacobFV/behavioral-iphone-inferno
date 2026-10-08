# SPDX-License-Identifier: AGPL-3.0-or-later
"""Small synthetic unsupported-format checks; never firmware or guest evidence."""
import importlib.util,io,json,struct,sys
from pathlib import Path
source=Path(sys.argv[1]);spec=importlib.util.spec_from_file_location('extractor',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def tlv(tag,data):
 n=len(data);length=bytes([n]) if n<128 else bytes([0x82])+n.to_bytes(2,'big');return bytes([tag])+length+data
payload=bytearray(4096);struct.pack_into('>2sH',payload,1024,b'HX',5);struct.pack_into('>III',payload,1064,512,8,1)
def image(p=payload,kind=b'rdsk',extra=b''):return tlv(0x30,tlv(0x16,b'IM4P')+tlv(0x16,kind)+tlv(0x16,b'0')+tlv(4,p)+extra)
assert m.payload_info(io.BytesIO(image()),len(image()))['hfs']['total_blocks']==8
invalid={'indefinite_length':b'\x30\x80','wrong_type':image(kind=b'krnl'),'extra_encryption_metadata':image(extra=tlv(0x30,b'')),'non_hfs_payload':image(p=bytes(4096)),'truncated_value':image()[:-1],'trailing_container_bytes':image()+b'\x00'}
results={}
for name,data in invalid.items():
 try:m.payload_info(io.BytesIO(data),len(data))
 except ValueError as e:results[name]=str(e)
 else:raise AssertionError('Accepted '+name)
print(json.dumps({'scope':'Synthetic format rejection only; actual extraction/HFS evidence separate','synthetic_plain_header_accepted':True,'rejected':results},indent=2))
