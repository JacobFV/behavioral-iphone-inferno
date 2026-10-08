# Actual plain recovery extraction

The new extractor ran once against the original supplied profile/component,
without altering either or any preparation consumer. Strict rdsk DER parsing
selected offset27/104685568bytes. Payload HFSX version5 uses4096-byte blocks and
25558 allocation blocks. Actual output SHA256:
5eff57f37009c1d996d6de3d6a069029a855cdc978fd54af0977cac49b42689e.

A separate streaming comparison proved byte-for-byte equality with the retained
ramdisk-payload.raw. The existing pinned hfsplus tool read only the new output
with `ls /`, exited0 and listed recognizable original System/usr/sbin contents.
The raw external listing is hashed; JSON retains it escaped (including the HFS
private-directory NUL name). Filesystem bytes remain outside Git. Header geometry
and listing do not constitute complete filesystem integrity/authenticity proof.

Actual command, extraction provenance, HFS-tool identity and validation are
retained. `parser-check.py` separately rejects six labeled synthetic unsupported
formats, including encryption-metadata fields/non-HFS payloads. It performs no
firmware or guest execution. No decryption, key/signature/ticket operation, VM,
repair, historical mutation or installed-runtime initialization occurred.
