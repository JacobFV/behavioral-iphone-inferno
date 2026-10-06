# Boot16 original-loader rejection (live snapshot)

This is a live observation, not a completed boot report. The exact command and
binary build manifest accompany the serial snapshot. Root/bootworker retain
ownership of the running guest and final report.

Original FudEarlyBoot invokes the generic kext update for registry ID4294968032.
AIDImageDownloader enters `validateFirmware` / `validateImage4` and requests
AppleImage4 validation. The concrete failure is:

    AppleImage4: Img4DecodeCopyManifestDigest: [1 end of sequence or set]
    firmwareExecutionCallback() error = 34
    ... validationComplete() kFWValidationFailed
    ... Exiting with status = 0xe0000001

This demonstrates that the normal runtime path finds the staged file and gets
past userland discovery into kernel validation. It also demonstrates that the
unsigned container's structurally optional manifest is insufficient for the
actual loader. Earlier static optional-field findings did not imply successful
validation. No synthesized manifest, ticket, signature, validation patch or skip
option was used. No firmware-loading, protocol-creation or touch success follows
from this result.

Original `FudEarlyBoot updateFWForDeviceClass:dict:` ignores the return object of
`updateFirmwareWithOptions:` (call0x10000c22c, then controller release), explaining
why `End Early Boot` alone cannot be interpreted as update success.
