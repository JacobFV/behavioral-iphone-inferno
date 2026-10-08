# Extract the supplied plain recovery payload

`extract-raw-recovery.py` accepts only the pinned n104ap iOS14.0b5/18A5351d research
erase profile and its existing ramdisk component. It copies the plain `rdsk`
IM4P OCTET STRING unchanged into a new external directory. No firmware download,
decryption, decompression, signing, ticket, key or VM operation occurs.

```sh
python3 companion/native-probe/extract-raw-recovery.py \
  --profile /external/original/profile.json --profile-sha256 PROFILE_SHA256 \
  --ramdisk-sha256 ORIGINAL_COMPONENT_SHA256 --output /external/NEW-raw-recovery
```

It verifies the full component hash before and after copying, canonical bounded
DER and exactly four IM4P fields, expected type, HFS+/HFSX signature/version and
whole-volume allocation geometry. Optional fields, encryption metadata, other
containers, compressed/non-HFS payloads and geometry mismatches are unsupported.
Output readback SHA must match. `extraction.json` records source/profile pins,
file identity, exact payload offset/length, filesystem header metadata and output
hash. Failed outputs retain INCOMPLETE/failure markers and must not be consumed.
This narrow recognizer is not complete filesystem integrity or authenticity
verification; inspect the new output with the retained HFS tool read-only.

Use the resulting raw file as native-probe/prepare.py's explicit --raw-ramdisk
input only after validation. The existing consumers and profile remain unchanged;
this record is not a substitute for prepare.py's own preparation.json or actual
recovery readbacks. It does not initialize Data, keybags, setup or an app runtime.
