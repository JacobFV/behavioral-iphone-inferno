# Original multitouch firmware deployment and loader

Read-only analysis of original iOS 14 beta 5 (18A5351d) assets. This is not a
firmware-load execution result. No firmware, manifest, signature, or guest files
were generated or changed by this investigation. Original implementation files
remain outside Git; provenance records exact source hashes and analysis paths.

## Observed boot and missing deployment

`app-boot-15/serial.log` lines 528–536 show original `FudEarlyBoot` executing the
`com.apple.mau.plugin.generickext` update with registry ID 4294968027, then ending
early boot. Its dictionary contains `IOMatchLaunchServiceID`, without
`FWDirectory`. There is no success/failure result in those console lines.

The original System inventory has no `/usr/standalone/firmware/FUD` directory or
Multitouch firmware asset. The original IPSW does contain
`Firmware/N104_Multitouch.im4p`; n104ap BuildManifest marks Multitouch as
`IsFUDFirmware=true`, `IsLoadedByiBoot=false`, and `Personalize=true`.

Original restored's `install_fud` creates the firmware/FUD directory at
0x100041740, formats `%s/%s.img4` at 0x100041848, and writes the supplied component
value at 0x100041954–0x100041988. Thus Multitouch normally becomes
`/usr/standalone/firmware/FUD/Multitouch.img4` within the selected installation
prefix. Merely copying the original System image does not perform this step.

## Actual userland path

Original installed `fud`, `-[FudEarlyBoot updateFWForDeviceClass:dict:]` at
0x10000c164, creates AppleFirmwareUpdateController, sets registry entry ID from
`IOMatchLaunchServiceID`, optionally sets `FWDirectory`, calls
`createFWAssetInfo`, and only on success calls `updateFirmwareWithOptions:nil`
at 0x10000c228.

AppleFirmwareUpdate recovery addresses below have corresponding original System
cache addresses at base 0x1c222b000 plus the listed address. The System image was
independently disassembled from original cache mapped segments. The analysis
container adjusts file offsets only; it is not a guest executable.

- `createFWAssetInfo` 0x136c uses explicit fwAssetDirectory if supplied; otherwise
  calls `copyPathForPersonalizedData:error:` with argument 0 and appends `FUD`.
  This is a runtime personalized-data path, not proof it always equals a fixed
  root filesystem path. It reads original service property `Image Tag` and
  optional `FDR Classes`, then searches firmware candidates by payload tag.
- Successful discovery sets signature string `IMG4` at 0x1894–0x18a4.
- `findFWAssetFromTag:tag:size:` 0x2308 reads each candidate and calls
  `_Img4DecodeInit` at 0x24c0. Decode failure skips the file and logs
  `IMG4 decode init failed - %@`. Success reads the payload type at 0x2518 and
  compares it to the original service tag at 0x2578.
- `_DERImg4Decode` 0x2d90 requires an outer sequence and compares its first tag
  to 0x494d4734 (`IMG4`) at 0x2e34–0x2e40. This requirement is also present at
  System VA 0x1c222de34–0x1c222de40. A raw IM4P is not accepted by this normal
  discovery route, even if another lower-level decoder accepts IM4P.
- `_DERImg4DecodeManifestCommon` 0x2f5c accepts an absent/zero-length manifest
  structurally: branches 0x2f8c–0x2f98 reach success 0x2fec. The System cache
  has the same checks at 0x1c222df8c–0x1c222df98. This says nothing by itself
  about subsequent kernel authentication or validation.
- `updateFirmwareWithOptions:` maps the selected file and calls
  IOConnectCallScalarMethod selector 0 at 0x1f08 with four scalars:
  address, size, signature type, firmware version. Signature type at 0x1eac
  is the BOOL result of comparison with `NONE`; the normal `IMG4` route
  therefore passes **0**, not 1. The normal version check requires version 0.

## Interpretation and next boundary

The original unchanged IM4P cannot simply be renamed `.img4` for this path.
An unsigned outer IMG4 preserving the original IM4P would be a format conversion,
not an Apple signature or personalization. No such conversion has been performed
here. Userland structural acceptance of an absent manifest does not establish
that original kernel validation accepts it; that boundary must be traced or
observed before deployment. No `NONE`, skip-validation option, fake IM4M,
personalization ticket, or altered original driver is proposed.
