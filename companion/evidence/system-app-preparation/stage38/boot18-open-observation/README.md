# Boot 18 live original open result

Raw serial lines 768–775 establish original IOHIDResource matching succeeded:
class IOHIDResource, registry ID 4294968036, identity/class query status0.
Original type0 IOServiceOpen then returned0xe00002e2 with connection0. The
unchanged IOHIDUserDeviceCreate returned NULL, backend initialization -103.
The legacy descriptor parser export was absent and was not called.

The helper has not sent a report. Console READY records only operator transport
readiness, not a functioning virtual service or delivered gesture. Boot17's
roundtrip demonstrated the parser, not input delivery. This observation isolates
an original userclient-open authorization result before descriptor creation.
Exact original policy analysis remains pending; no additional entitlement,
descriptor change or policy bypass is justified by this result alone.

The guest remained live when this snapshot was taken. Its disks were not read,
hashed or called stopped. Original source and staged byte provenance are recorded
in the adjacent stage38 evidence; the root runner owns boot18 lifecycle.
