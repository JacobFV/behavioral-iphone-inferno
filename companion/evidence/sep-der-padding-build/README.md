# Original IPC blob alignment correction

Committed source6fce1464b8 built with simulated SEP and KVM. Actual boot10 still
returned selector17 e00002bc after valid query options were accepted. Original
__blob decoding requires the13-byte DER payload rounded to16 transport bytes.
This build adds only three zero padding bytes; the declared DER length remains13.
Build and QMP control-plane checks passed. Actual original state-query execution
remains the next required check. No state or notification behavior was changed.
