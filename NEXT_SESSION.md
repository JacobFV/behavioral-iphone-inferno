# Continue active Inferno companion work

Workspace: `/home/brandonin/Documents/behavioral-iphone-inferno`.
Read AGENTS.md, companion/README.md and PROGRESS.md. This is the Inferno pivot;
do not resume the archived framework implementation. The user explicitly wants
continuous work across status questions and intermediate milestones. Parallel
workers are authorized for independent work; use isolated worktrees and commit.
No handoff or pause has been requested.

## Current execution, 2026-10-06 10:49 local

**Boot33 AND34 completed the strict real UIKit journey. No VM currently live.**
Both use frozen48/app19/reader52/launcher13/HID45/e3da emulator. Two consecutive
passes with genuine lifecycle/tap1, root-reviewed0→1 and both strictQMPcaptures.
No statisticalreliability claim;32 is interrupted, never countit asstrictcomplete.

34 report `.local-build/reports/app-boot-34/report.json`, normalQMPquit33/emulator0/
errornull/306.12654s. All7hashes andall4backingancestorsunchanged. Root141426688bytes
SHA37888e60f0654a3088d64a1ed35a9ff8eace071645d9c76fba684e5e411a65b4.
QMPbeforeSHAf54fb9ed7354a8d8b95a90087541a66e91245f7fda5b613088a6c32f288580f7;
afterSHAcf314295d9a451e0fc2a9c98957b4bc50e5d34397e2ea95082669eea43c91fad.
Both PNGderivatives reviewed/pixelequal; capture-conversion.json ready. Bootworker
preservingfull34evidence. Rootobserver87083finished; observations tracked separately.

33 normalemulator0/errornull/285.89601s, root97779712bytesSHA
118a7ae8db7902db87d3449c212fb2dd59dcaae30ef44bb4528c1e931b60fb87.
Evidence `companion/evidence/owned-loopback-strict-journey-33*`, cae829e719/462d24353c;
actualhostarrivals `app-loopback-33-observations`,de305a4732.

32 provedtransport+visual0→1 butSignal15 beforestrictafter. Senderunknown; observers
read-only. 33/34dedicatedsessionsremove toolsessiondependency, notproofthepriorcause.
32rawevidence6bad3afdb7/resourcesd3a83032aa/hosttimeline2c92865d5a.

**Active nextwork**: nativeworker implementing firstlaunchmeasurement candidate
per `companion/evidence/owned-launch-timing-design.json`6501e1c7bc. App fixedbuffer
rawguestmachtime atmain/delegatelaunch/windowrequest/appeared/active, nofile/network/
NSLogbeforemeasuredboundaries; deferflushviaordinarymaincallback. Separatebounded
versionedtimingrecords; preserveexistingstrictmarkers. Launcherstampsbeforeoriginal
open+callbackentry, printsaftercallback. No kill/relaunchcontrol yet. No newgrants.
Worker ownsapp/relay/launcher/build; rootreviewhashes beforebootworkerstage49/boot35.
Stage49 MUSTbranch44andreplacethreechangedcomponents, retainingHID45. Notyetbuilt.

Read-only `probe-status` mailbox now integrated48ca4f1132; actualfirmware-free
plumbingpassed, noinput/QMP/statechange. Future35willtestactualguestlivestate.
Do notstopatmilestones. No handoffrequested.

## Strict journey / operator input recipe

Default journey sends ZERO automatic input. Runner is sole QMP owner; use mailbox.
Review every relevant actual frame. Lifecycle markers alone do not prove visibility.
Normal sequence: review lock → explicit swipe → review still-cover if present →
second swipe → wait/review actual beta dialog → explicit Close → wait/review
unobstructed counter0 → strictbefore → onecountertap → reviewcounter1 → strictafter.
Animations can take tens of hostseconds; a transport ACK does not prove UI change.
Never blindly replay a request whose outcome is uncertain.

Capture (no input):
`python3 companion/vnc-control.py --socket CURRENT/vnc.sock --output NEWDIR`

Unique input utility (label must be new):
`python3 /tmp/inferno-explicit-gesture-34.py LABEL 'JSON'`

- Swipe: `{"kind":"swipe","x0":16384,"y0":32270,"x1":16384,"y1":9145,"duration_ms":1500}`
- Beta Close: `{"kind":"tap","x":16384,"y":18560,"duration_ms":150}`
- Counter: `{"kind":"tap","x":16384,"y":20316,"duration_ms":150}`

After reviewing unobstructed0 and actual appeared0:
`python3 companion/qmp_control.py --report ABS_REPORT probe-capture-before`
After one explicit tap, realtap1 and reviewedcounter1:
`python3 companion/qmp_control.py --report ABS_REPORT probe-capture-after`

**After-capture completes journey and normally stops VM.** Do not delay it for
resource sampling; complete60s sample32 already exists. RawQMPframes828x1792;
VNC832x1792includespadding. view_image cannotreadPPM; convert losslessly withPillow,
assert decoded bytes equal, retain both hashes. Do not AI-regenerate screenshots.
While live, report.json initially remains stale; current mailbox replies are live.

## Exact current binaries and policy boundaries

Emulator `.local-build/build/qemu-system-aarch64`, SHA
 e3da84b179ce328e06a0f917aabb8e4d80c8a4cf64701212464831a270e1741e,
source1cebf0c00be038e7156d82578214c2cafa109873. TCG2CPU/4GiB, simulatedSEP,
upstream direct-kernel patches, software renderer. Never describe as unmodified
physical-device execution. No emulator rebuild needed for repeat.
Profile `~/.local/share/inferno/images/ios14b5/verified-profile/profile.json`.
Recovery binary archive `.local-build/binaries/simulated-sep-7e7033796707/`.

App19 `~/.local/share/inferno/app-probe/exec-build-19/InfernoProbe.app/InfernoProbe`,
73680bytes SHA94cac3cdc252bacdef3c23e9b9dd9b7354fbe8e27d7b46def2d746084d1dbc44.
Reader52 `~/.local/share/inferno/native-probe/helper-build-52/inferno-readiness`,
69680bytes SHA7a8c6d97003613f29a4f144f0ba3471fa7effbcb4e1474db56783df96969141f.
Launcher13 `~/.local/share/inferno/app-probe/exec-build-13/inferno-launcher-open-error`,
68592bytes SHA8dbc2086d0f13614cb5a8c2efb4cf85c0438ea423979b1b8f5c7bfa4f0eefbf0.
HID45 `~/.local/share/inferno/native-probe/helper-build-45/inferno-hid-input`,
69664bytes SHA0c0a5d9990cb5b0101f6491b7d2df0d6959cb0db5bde1cdfa9f40e6eabe69932.
Owned bundle `org.inferno.companion.probe`, `/Applications/InfernoProbe.app`.

App journals through original own Foundation cache and sends same actual records
on bounded TCPguest127.0.0.1:37373, oneconnectionpermarker. Reader validates bootUUID,
claimedPID exactowned executable+uid501, grammar, sequence and counts. Proven32/33.
It explicitly reports peer_pid_authenticated=0; this is fixturetelemetry.
No hostports, externalnetwork, newentitlements or guardchanges were introduced.
Reader lifetime7200s/max64connections/512records, boundednonblockingI/O.
Never inject synthetic lifecycle/tap markers or fake system notifications.

Keep existing original launch dictionary System classification ONLY exactownedpath,
not signer/profile/trustmetadata. Registration correction required normalrestart25.
NSObject isa ABI fixedapp14 after actual25startupcrash; preserve it.
HID owns Virtual/Built-In identity, originaltwoentitlements, serialexplicitrequests;
max32/7200s, no automaticreplay. Home gesture from app still needs executionproof.

## Immutable overlay retention / next staging

Never remove, move or modify any backing root below. Exact paths live under
`.local-build/reports/`. KEEP markers deliberately defeat old retirement guards.
Max4qcowlayers. Run34layer4→stage48layer3→stage44layer2→boot27layer1→stage43raw.

- stage43 `disk-preparation-43/disks/root.raw`,34359738368logicalbytes,
  SHA69e8378c71d1f29840baa7ae16811d3f6285bf27042501a79e8139f8a5ad61d5.
- boot27 `app-boot-27/disks/root.qcow2`,140443648bytes,
  SHA6898ad82af6bfb96168d2b7dd8febcfa977ef703679739197a40a08d735b6d4c.
- stage44 `disk-preparation-44/disks/root.qcow2`,3145728bytes,
  SHAa26c50b4f51e5bb8a7c67889e2078649324851849f826f0eb754680f91f66f5d.
- stage48 `disk-preparation-48/disks/root.qcow2`,2818048bytes,
  SHA5f33b4830d17374c79b20587213c2d22fdf909b749b1a740bdf36a9ac49db2f8.

All0444+KEEP. Stages45/46/47 also retained because used by actualboots29/30/31.
Repeatboot uses `--overlay-base-report ABS/disk-preparation-48/report.json`.
It validates recursiveheaders+hashes, pairedaux6copies, no writableFD, normalpriorquit,
all7manifest. Postflight rehashes allancestors. No rawcopy/flatten required.
Newbinary staging must branch **44**, replace ALL components changed from44
(app16/readiness48), create newlayer3, freezeafterreadback/normalstop/all7/noFD;
thenbootlayer4. Do not stagefrom48or32–34 then addanotherbootlayer.
Bootworker owns staging/recovery; root verifies and freezes with modelscript
`/tmp/inferno-freeze-stage48.py`. Keep binaries/disks outsideGit.

## Measurements and historical failure boundaries

Current60s aftercounter32:61samples,16.93CPU-seconds,28.2166%onehostlogicalcore,
peak5737791488bytes(5.343735GiB),8threads. Wholeemulator RSS, notguestappmemory.
Raw/proc measurements and arrival records tracked underapp-loopback-32-observations.
Hosttap-send→record414ms includesguestrelay+hostpolling; notnativeintrinsiclatency.
No rigorouscold/warmtiming, reliabilitypercentage, densityorcostclaimyet.

Filetransport failures are established; do not repeat detours or addgrants:
28globalfileopenEPERM;29ownFoundationcachewriterworks/LSdataContainerURLnil;
30MCMreadonlycreateNO returns55 clientnotentitled;31originalprocfdlookupfinds exact
ownedfile/uid501/0600/inode110058 butreaderopenEPERM. Physicalcontainer DID exist.
Loopback52 avoids crosscontainerfileaccess normally. Actualsource/buildauditad30a5919e,
0fae1865a3/97b64a9fde/e71e4072f5, actualrawproof632fd19604/cae829e719.

OriginalinstallediOS/setup/Home/Clock andvisualcounter26/27/28 precede strict33.
Firstunlockkernel/mobilekeybag was fixedviaactualSEPwire1cebf0c00b, notnotifyinjection.
HardwareMT-SPI firmwareFUDvalidation stillunsupported; separateownedvirtualHIDworks.
Allactualboottuples1–34 and baseline21 retained. Priorpreparationretirements are
recorded in PROGRESS/history; never treat retiredcopies asavailable.
Full historical NEXT_SESSION retained in Git before de305a4732/6501e1c7bc.

## Worker ownership

- boot_runner: `/tmp/inferno-qmp-control`, currentVM/staging/stoppedraw evidence.
- native_probe: `/tmp/inferno-native-event-relay`, ownedapp/helpers andclockdesign.
- disk_path: `/tmp/inferno-disk-overlay-chain`, overlayaudit/currentprobe-statuswork.

Use followup_task to reactivate completed agents; send_message does not activate.
Do not spawn more unless needed; preserve others' changes. Root handles allUIinput,
integration/docs and actualvisualreview. Never open windows on the user'sdisplay.
