# Official OS image inspection and direct-boot experiment

These downstream AI-assisted utilities decode a local, unencrypted UDIF image
and adjust its GPT sector geometry for Inferno's 4096-byte NVMe namespaces.
They do not download firmware, decrypt anything, create tickets, sign Apple
components, install iOS, or prepare a Data volume. Keep all inputs and outputs
outside Git. Treat resulting disks as source artifacts: boot disposable copies.

The narrow supported input is the stored ZIP member `038-44337-083.dmg` from
iPhone11,8/iPhone12,1 iOS 14.0 beta 5, 18A5351d. Its BuildManifest marks OS
`Personalize = false`. Decoder supports raw, zero and LZFSE UDIF chunks and fails
other chunk types. It verifies ZIP CRC and records SHA256 hashes. Use the same
locally pinned liblzfse as the emulator build. Geometry wrapper requires one APFS
partition in a 512-byte GPT source, checks GPT CRCs, copies its contents unchanged
into an 8GiB disk with 4096-byte GPT sectors, and verifies the payload copy hash.
It preserves the APFS container size and volume metadata. Free space after the
partition is not yet usable by APFS.

```sh
python3 companion/os-image/decode-udif.py \
  --ipsw /absolute/local/firmware.ipsw \
  --member 038-44337-083.dmg \
  --liblzfse /absolute/build/packages/usr/lib/aarch64-linux-gnu/liblzfse.so.1.0 \
  --output-dir /absolute/local/os-inspection
python3 companion/os-image/wrap-gpt4k.py \
  --source /absolute/local/os-inspection/official-os.raw \
  --output /absolute/local/os-inspection/official-os-4k.raw
```

Both refuse to overwrite their image output. JSON provenance goes alongside
images. Interrupted/failed runs may leave an incomplete image without a completed
JSON report; never treat that image as verified.

## Actual inspection on 2026-10-06

An initial scratch version of these scripts decoded and wrapped the official
image. Raw source scripts and their hashes remain with runtime evidence under
`/home/brandonin/.local/share/inferno/images/ios14b5/os-inspection/`. The committed
versions expose arguments and add source GPT validation. Output geometry is the
same; they have not yet repeated the full conversion.

- Original DMG: `cae20aff4f69e72b78f80fdaf92f26d1f3dac7890c66ca00d16bb6f3270368dd`.
- Decoded raw: `96bebe305f5e0ab41ba61e976e52687646bfa1f189918956069caeda107ee9d6`.
- APFS payload: `54f0ea7d88b76756b43263eaf40cd5580aaf8871c7e15218822152e73fede44f`.
- 4096-byte GPT wrapper: `93f97dae602a8fc844f0f88819d3fe358b1cf14ee5e193b0beb7009376032594`.

7-Zip 23.01 actually parsed the decoded GPT/APFS and enumerated 213316 files and
90047 directories. APFS container has one volume, oid 1026,
`AzulSeed18A5351d.N104N841DeveloperOS`; latest observed volume superblock xid 56,
role `0x1` (System), flags `0x1` (unencrypted), no snapshots. No Data volume exists.
Source partition starts at byte 17408 and has 7695577088 bytes. Wrapper partition
starts at 1MiB (4096-byte LBA 256), ending at LBA 1879058.

This is evidence of readable firmware contents and correct disk preparation,
not installed-system boot or an application journey. Direct boot must establish
what additional Data-volume initialization and userspace adjustments are needed.

## Source references

UDIF chunk offset interpretation follows the existing upstream
`block/dmg.c:dmg_read_mish_block`; decompression uses liblzfse's
`lzfse_decode_buffer`, as does upstream `block/dmg-lzfse.c`. Original upstream
licenses and notices remain in their files. APFS structures and role/flag values
were cross-checked against [apfs-fuse DiskStruct.h](https://github.com/sgan81/apfs-fuse/blob/master/ApfsLib/DiskStruct.h).
