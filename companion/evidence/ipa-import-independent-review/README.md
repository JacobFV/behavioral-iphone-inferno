# Independent read-only importer review

Reviewed importer cba1a79f8d (integrated9b3395a25b) and staging integration
1a0c5c3789. No guest actions, imported bytes, or source code were changed by this
review. Actual retained owned fixture `validate_manifest` succeeded with tree
697b73b118021ae7f225a9ed65009e6ca0aa91c62a2b430e60e7d2b648370125.

ZIP handling bounds archive/member/expanded sizes and count, rejects encryption,
symlinks/special files, duplicate and implicit case aliases, NUL normalization,
path traversal, nested executable bundles and auxiliary payloads. Extraction uses
new files below a fresh external directory. Extracted modes are intentionally
normalized; bytes are checked. Source IPA is a required retained dependency.
Manifest revalidation reparses it, checks exact tree inventory, hashes and modes,
rejects hardlinks/symlinks, and checks file metadata stability during reads.
These checks are not a hostile concurrent-writer sandbox or atomic filesystem
snapshot; callers must retain their private inputs unchanged during use.

Mach-O preflight checks thin little-endian ARM64_ALL MH_EXECUTE, bounded load
commands, device platform, matching plist/Mach-O minimum iOS<=14.0, encryption
ranges/cryptid0, system dependency paths and LC_MAIN extent. Signature extents
are recorded, not verified for trust. Segment section semantics, actual loader
acceptance and dependency availability are not exhaustively verified. This is
compatibility preflight, not a complete Mach-O validator or launch guarantee.

Concrete issue reported to root/importer owner: LC_LAZY_LOAD_DYLIB0x20 and
LC_LOAD_DYLINKER0xe were ignored. Synthetic in-memory command insertion with
/private/var/unsupported.dylib was accepted in both cases while the returned
scope still claimed system dependencies only. The mutation only exercises the
host parser, not a valid runnable image. Reject lazy load and require bounded
/usr/lib/dyld metadata before generic staging; preserve the actual owned fixture.
No import/build/signature/guest execution claim is inferred from validation.

First recovery plan: freshly compile only the owned preparation helper with its
existing entitlements, keeping probe42 and all existing installed launcher,
readiness, HID, cache and job bytes unchanged. Prepare a fresh cloned recovery
ramdisk using the imported manifest and explicit identical-fixture tree pin.
The plan must produce exactly75930 imported bytes (app74976+Info954) with zero
mismatches, correct inventory/metadata, clean unmount/PREP_COMPLETE and normal QMP
cleanup before a stage is eligible. Use a fresh overlay from the immutable
from50-sample-1 source, not stopped73. No recovery VM is authorized by this file;
root controls the launch gate after73 retention and reviewed source fixes.
