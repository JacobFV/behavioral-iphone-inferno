#!/usr/bin/env python3
"""macho-sym.py BINARY OFFSET... : name the function containing each image offset of a thin arm64
Mach-O, from its own LC_SYMTAB (no llvm-symbolizer needed). Offsets are what crash reports print as
`0xLOAD + N` for the app's own image. Works when the build kept its symbol table (most unsigned
Xcode/Linux builds here do); Swift names come out mangled."""
import struct, sys

b = open(sys.argv[1], 'rb').read()
if b[:4] != b'\xcf\xfa\xed\xfe':
    sys.exit('not a thin 64-bit Mach-O (thin it first)')
ncmds = struct.unpack_from('<I', b, 16)[0]
off, text, syms = 32, 0, []
for _ in range(ncmds):
    cmd, size = struct.unpack_from('<II', b, off)
    if cmd == 0x19 and b[off + 8:off + 24].rstrip(b'\0') == b'__TEXT':
        text = struct.unpack_from('<Q', b, off + 24)[0]
    if cmd == 0x2:
        symoff, nsyms, stroff, _ = struct.unpack_from('<IIII', b, off + 8)
        for j in range(nsyms):
            strx, typ, _, _, value = struct.unpack_from('<IBBHQ', b, symoff + 16 * j)
            if typ & 0x0e == 0x0e and value:  # N_SECT: defined in a section
                syms.append((value, b[stroff + strx:b.index(b'\0', stroff + strx)].decode(errors='replace')))
    off += size
syms.sort()
for arg in sys.argv[2:]:
    addr = text + int(arg, 0)
    best = max((s for s in syms if s[0] <= addr), default=None)
    print('%s  %s+%#x' % (arg, best[1], addr - best[0]) if best else '%s  ?' % arg)
