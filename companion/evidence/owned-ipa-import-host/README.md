# Host import evidence

Run `check.py --importer companion/app-import.py --fixture /external/InfernoProbe.app --output /external/NEW`.
The retained result was produced using exec-build-22, with each original file
hashed and compared byte-for-byte after extraction. The eight rejection cases
are explicitly synthetic host checks. No VM was started. The fixture, archive,
extracted copies and negative binaries remain outside Git at the recorded paths.
The reusable check is intentionally focused on archive trust boundaries and the
shared validator, rather than a general app-compatibility test suite.
