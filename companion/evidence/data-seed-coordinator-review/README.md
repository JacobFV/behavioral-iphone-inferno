# Seed coordinator read-only review evidence

`replay.py` ran against the retained actual historical `data-preparation-serial.txt`
and the actual new `initial-volumes-stage-2` manifest. Its output preserves source
hashes, eight negative rejections, the original copy-path records and freshly
validated two-layer/paired-seven input identities. No VM was started, no disks
were written, and no successful new seed execution is claimed.

The historical log is evidence that the parser recognizes the original helper
path; it is not a substitute for executing this new coordinator. A subsequent
reviewed run must produce new raw logs and its own normal shutdown/retention.
The result remains `seeded-not-byteverified`; the read-only comparison stage is
separate. The source-derived raw parser rejects the read-only verification log
as the wrong phase rather than using its byte equality result for seeding.
