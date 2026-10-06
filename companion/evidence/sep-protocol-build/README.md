# Partial simulated SEP protocol build

Actual ARM64 build of committed source 7a32314605 completed with exit0.
Both explicit simulated-unencrypted SEP mode and Linux companion KVM remain enabled.
The retained QMP smoke passed with no guest CPU; it is only executable/control-plane
validation, not iOS boot or unlock evidence. Original build075b221 remains archived
outside Git. The next integrated comparison uses unchanged disk-preparation-32.

The upstream change is restricted by INFERNO_SIMULATED_SEP to a bounded, volatile
empty-secret system-bag transition and consistent first-unlock queries. Unknown
extended-state fields are omitted, not guessed. No notifications are injected.
See ../sep-unlock-protocol-inspection.json for original-protocol evidence and limits.
