# Extended-query correction build

Source ac586deb8f built successfully with explicit simulated SEP and KVM preserved.
The preceding integrated boot9 demonstrated original API success and first-unlock
0->1, but MKBGetDeviceLockState returned-1. Original kernel inspection proved its
query option0 shares the same DER response shape as already supported option1.
The only subsequent protocol code change accepts both valid read-only options.
Build and control-plane QMP checks passed; these do not establish guest behavior.

The next app-boot-10 also uses independently staged dictionary launcher33. Those
two changes are explicit; neither app registration nor extended-query execution
is claimed until its raw guest results are observed.
