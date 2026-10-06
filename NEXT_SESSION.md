# Continue active Inferno companion work

Workspace: `/home/brandonin/Documents/behavioral-iphone-inferno`.
Read AGENTS.md, companion/README.md, PROGRESS.md and companion/OWNED_JOURNEY.md.
This is the Inferno pivot; never resume the archived framework implementation.
The user explicitly wants continuous work across status questions and intermediate
milestones. No pause or handoff requested. Parallel workers are authorized for
independent work in isolated worktrees; commit progressively.

## Current execution, 2026-10-06 14:37 local

All guests through50 STOPPED.50 completed strict counter0→1, normal QMP quit,
emulator0/errornull, tracked journey verified and default all7/ancestor retention.
Evidence f388fb81e6 (worker), root visuals77ae980672. Root disk116391936 bytes,
SHA802d473d12897c72248dbb00a1e619791438db4a198e2da4ffd5a96270e2ff1d.
50bootF8081A21-B796-416F-B4E7-D15E075E9CC1/PID256/main2869435882,
countereab89cac47a841f3b5807bc1614af5b9. No samples/Home/OPEN50.
51 STOPPED healthy strict0→1, normal quit/emulator0/errornull, postflight verified16740b4bb4.
Boot71FD4D0F-EA77-4740-A7EE-74A082116AB8/PID254/main2806975603;
counterd2847363d7794abc935cadedc18d990b. QMPbefore
85395e9cd15f1a4d335d29806e5fab55b941b8dd9ba2bb62c3df5c94b85c2691,
after80a879d44c98c6d63fbe9a7afb3ab55e25ee66813643e5af780090d3def2595b.
Root visual review3856d1678f, no SAMPLE/Home/OPEN. Trace disabled duringcleanup.
51 rootSHA1f2740b53665988eb18bae8fef1e12c6b450b042f47a5ab9c3b9fb12b5e6c21e.
52 STOPPED healthy strict0→1, normal0/noerror, default retention verifiedcb2f83e0da. Root visuals6711b7a643.
Boot4D57DC44-A8B4-469E-9547-81D79A036FF0/PID255/main2828698034;
counter58985af15a484360a9c1442be4386a66. QMPbefore
 a6d6e3770ab9468bc05f7d08a66edc241db8b62804356c3e3f2a5a1a9640aead,
afterd7dbd86ff62a04a18448e026d30f37fea81de150740a3c005f07f93231ece4c9.
No SAMPLE/Home/OPEN52. Root52SHAbc57c2296671a99304913ad9b34ddac76402cbe6203a58e4e5909a61bb4ef0f7.
ONE53 LIVE runner2930546/QEMU2931057, VNC /tmp/inferno-boot-z8xj9z87/vnc.sock,
serial connected1791323387.5888894, host5355e76644, same55/670.
53 completed strict0→1 plus THREE ordinary Home/reopen cycles retaining1;
boot1C81A853-1B79-4FBC-8EBD-E365B46D4827/PID252/main2739827127.
Original Clock then opened normally, stopwatchstarted18146d88fb6d4185b9d4e31b56cf1431,
reviewed00:02.16→00:19.64. LIVE60s host resources at stopwatch-resources,
no VNC/input during interval, periodicQMP30s stays enabled. Both SAMPLEslots unused.
Keep investigatingfreeze; no fixclaim. Root owns actions and will reviewaftermeasure.
Six-run serial audit428a2c9f2f found startup IOMFB warnings shared by failed44/47
and healthy45/46/49/50; no failure-specific warning near/after counter marker.
Root owns all input; on stall collect both original samples BEFORE Home.
Goal: reproduce real display freeze and collect original compositor stacks while
stalled, comparing49 healthy baseline. No rendering behavior fix yet.

49 completed strict0→1, actual BACKBOARDD and SPRINGBOARD samples, and
Home/reopen retaining1; normalfinish/emulator0/noerror. TrackedjourneyverifierPASS/
defaultpreservationPASS1da67b8b30. Root49SHA
4369bf694076b083091a5902cb3bb3c2091e4a8d325b77e687a39fe8c44ad199.

49boot558C3965-E50B-4A05-A02B-9A5AA952F3A9/appPID244/main2485749412.
Counter878d8f31544848fe80f77d51cf9a996c; QMPbefore
 a46a85e164f1f4329f6dcb1f2024e9c1656a64a914edc5bf27078b6e1d61169e,
afterc2b09805bcb6fa8506b30c28844ba671977b59fa22411131e6319c10865d7bd6.
Trace7completecycles39601→84582, all7disabled1791321497.206beforeanysamples.
BACKBOARDDf9525a093dc5465a939ad2424822c541:PID60/unique60/version205,
13070bytes53chunks. SPRINGBOARD80a3a72d48374a67841089ae659558ef:
PID57/unique57/version117,17190bytes69chunks. Both20stackshots,originaltool0,
EOF/noerrors/truncation/kill,postidentitymatch. SharedcacheUUID11AD39C9-E3C9-3067-
A337-7287744FDCB5 slide14514000. Kernel/kextsymbolwarnings; userstacksUUIDmapped.
Healthybackboardrender-serveranddisplay.primary normalmach_msg waits.
OPEN609b0281ac2e45aab61a5e90a31047df afterHome retained1; warmparsercomplete,
diagnosticcontextnotperformancetrial. Evidence8d955f5852/original-stack-samples-49,
697cde035f/display-mmio-49-actual,97e6666ae5/owned-sample-49-visual.

47 failed and is preserved4420e9f401, rootSHA
35ba0bc4d3cd12a22524127f3d1acc317f47951cd58ecee4c24f2cb5abbb5e7f forensic_onlytrue.
Trackedverifierrejectsstrictincomplete. 48failedpreexecutionauxmode;fixed97f7230fa8.
Neitherisfuturebase. Currentbase55/ctimeattestations detailedbelow, keepallpaths.

## Prior display diagnosis

- 41: real tap1 but VNC and QMP remain counter0, including continuous30-second
  observations. Ordinary F6 Home and one OPEN produced real background/foreground
  callbacks in the same process but no visible redraw. No second counter tap.
  Strict after-capture deliberately withheld. Root SIGINT2 to runner, normal QMP
  cleanup/emulator0, attempt failed. Tracked verifier rejects it. All7 disks and
  ancestors retained; root manifest explicitly `forensic_only:true`, rejected as
  a future overlay base. Evidence `display-staleness-41*` and
  `owned-display-stale-forensic-41*`. No app-mainloop permanent block or VNC-only
  cache explanation fits the observed callbacks/shared stale QMP pixels.
- 42: unchanged baseline emulator/frozen50 guest bits. Fully tracked strict0→1,
  one ordinary Home/reopen retaining1, normal stop, verifier and disk checks pass.
  Nine fixed display-register snapshots are healthy reference only. Evidence
  `tracked-workflow-42-visual`, `display-registers-42-actual`,
  `owned-tracked-controls-stopped-42*`.
- 43: diagnostic-only emulator source0132ad93ca, SHA
  1e369a50d11a417a50d8a05d9bc8dad7ebd443ca4d9b2db0b71271e55139a6b7.
  Same frozen50 guest bits, TCG. Root reviewed counter0→single tap→1 in VNC and
  both strict QMP captures. Tracked verifier passes. Normal finish-run/emulator0,
  all7/ancestors preserved. RootSHA
  6c7e0faf7bc72db50c1bea53c4f1e79962d2fb2a2fc13525ca202033f3d36b63.
  Boot28E7DE2C-2059-488B-8290-F2BD07870CFA, PID218/main1912722120.
  Counter requestfd6aa9d92d38431e8a91b65ba8a9a4af.
  QMPbefore08d4e0485d4b4fc84905aee3d535bf8df5dbec7c2f8e1b1425fb205947624fde,
  after190911dc8e8ee21b4ad180aa4934eb4fe95d933cd51f6f223a2315448168332d.
  Trace enabled before beta Close for60seconds; actual deadline disabled all5.
  Evidence7f983d247d/`display-trace-43-visual`,93b6d271c2/
  `owned-display-trace-stopped-43*`. Native worker auditing complete raw trace.

Actual43 exposed a TELEMETRY LABEL DEFECT: original genpipe.index is never set,
so both pipes print0. Final audit81aa670542 explicitly distinguishes source-order
inference from rawlabels. Trace-onlyfix9cadee702b passes literal0/1 through draw/read
solely to tracecalls, with no migratedstate or emulationbehavior change. Actual
rebuild/control smoke26df7a776c passed: binarySHA
1545a84357982b7f9c19a134ff63c070c538022b10bec5e0cd1d6a78da953884,
sourceab7892d1acec279cb48a7a02553b4655eec87f44. No guestlabelclaim yet.
44 REPRODUCED the realfailure with diagnostictrace. Boot
4CCF1DC1-5592-4838-A1C8-BC377B6EF73E/PID239/main2500669858. Genuine single tap
 e6c9ca3795044d559048f14c967f707f and realtap1, but VNCcounter0.16framescontinuous20s
allSHA24566763bdc8ceb183927ddf29ec3ddb414f710d3d2b8ddf1bbd3ec3bb9d868d.
StrictbeforeandperiodicQMPalsoidenticalee1b21d56a3c3be58dc27c0b3bb290661985925b35da9974889df81bc253ed70.
No strictafter, no secondtap. Bytecheckpointbeforetap11096 alreadyafterlastdraw.
Firstwindowafterthatboundary:ZEROsubmit/BH/pipe,46OUTPUT_READY43W1C acknowledgments.
Correctedpipe0/1labelsactualconfirmed in5earliercompleted drawcycles.
ONEordinaryF6Home yieldedrealresign/backgroundsamePID/main, butanother16frames20s
allstill0. Secondtracewindow43OUTPUT_READY41W1C, ZEROsubmit/BH/pipe. Bothwindows
actuallydisabled. No diagnosticOPENneeded. Deviceinterruptservicecontinues butguest
stopsissuingmodeledsubmissions; no queuedBH failure or causalcompositorclaim.
Rootrecordedoperator-stop/SIGINT2torunner2778291 at1791318208.773. NormalQMPcleanup
emulator0, reportKeyboardInterruptSignal2/attempt_completedfalse; verifierrejects
strictincomplete. Trackedforensicpreservationpassedall7/ancestors,rootSHA
1cd478c6c4a831c40ed1ad7908db6598476edfd2a99dd6ab6c75af551216501a. Finalrawd62cb6170b and44binaryarchive
`.local-build/binaries/display-trace-labels-1545a8435798/` retained. Evidence5f0f05ad1c/c49724d64a display-stall-44-actual
and a6902fb090 display-stall-44-visual. Keep allfailedmilestonesdistinct.
Diagnostic-only unknownADPmain/GP/blendread/write and GPconfigurationtrace merged
09811d4d1d. NoextraDMA/state/semanticsfix; fixed7eventboundedwindow. Actualbuild/controlsmoke3 ec2ca86044 passedall7defaultoff/deadline/cleanup.
BinarySHA670caae5e8b86dbd07968b053ce0667328cce648935cefb8649357400f9c8e59,
source09811d4d1d4dfa3c10ee8f59360f282624fc1df2. ONE45authorized/launched now,
runner2790834. Rootallinput, initial10strace toassessvolume(timeboundnotbytebound).
45 completedstrictsinglecounter0→1, bothactualQMP/rootvisualreview, verifierPASS,
normalstop/all7/ancestors. RootSHAa38ea455e1934b375cf0788d79054ba48b56c9d7617a7dfc70666a9861849248.
BootC95B96C7-BE13-47B4-A0D0-85560590FD85/PID255/main2848266498.
Tap90438a0d9b3d48f4af36125a02cf08ca. Before31459033647a584013a4e7570fa8684fed1e9a11c727064e00a94412ac2dbe51,
after39edbb9493068b0a4fe856bee8bb9a69d6950ca8170bf13cbcc1c822fbdb6326.
Initial10strace volume239364newbytes~24KB/s,23drawcycles,2745unknownMMIOrecords.
Counter60swindowactualdisabledall7, bytebracket284895→324709 contained6complete
GP0drawcycles and6GP1disabled,48GPconfigwrites+423unknownMMIOevents. Zero-valued
unknownreadscoexistwithhealthydraws; notcausalalone.44lackednewMMIOeventsso cannot
compareunknownregistervalues retrospectively. Evidencecd4ce49f5d+ce6485d05d/
display-mmio-45-actual,447fe4390d/display-mmio-45-visual,rawd264d0757c/
owned-display-mmio-stopped-45*. No fix for41/44.
46 completed strict0→1 plus ordinary Home/reopen retaining1, tracked verifierPASS,
normal finish/emulator0 and all7/ancestors preserved. Evidence display-mmio-46-actual,
display-mmio-46-visual and owned-display-mmio-warm-stopped-46 (c861f267de).
RootSHA882fff64f2dc20e47958a6b2869a4f72bbe0b37324bb176b687ac1a20722b60a.
47 identical670caae5/frozen50 boot908A7F55-687E-4EA7-BDFB-9DADA365B441.
Runner2844717/QEMU2845204, privateVNC/tmp/inferno-boot-7fqpaqep/vnc.sock.
Tap99afb731b5bc4d9cb00536b6b3bd749a produced realtap1 but reviewed0; continuous20s
14frames identicaldc59a32cf4e6f5d2a67981de0779dcf263ce997f9767fc06a8924f7e523f27af.
Strictbefore277a9d366c5fc152f600332530df9dcd33b493457bac55061e63824228e7f241.
No strictafter/secondtap/OPEN. First60swindowall7off1791320219.133. Pretapbyte40424.
Nativeworker auditing fullMMIOtrace; preliminaryzero submits/configwritesaftertap,
only repeatedzeroGP0/1+184/main45004reads alsoseenhealthy. Second30sHomewindow
started1791320241, beforeHome58015. RootoneF6at1791320247.454; actualresign/backgroundPID299/main6452403977,
14Homeframesstill0. Window2all7disabled1791320271.273. Homeprefix58015→75275:
49ready/46W1C/138unknownreads,zero submits/configwrites. Firstwindowafter40424:
50ready/47W1C/141unknownreads,zero submits/configwrites. Rootvisualevidence
display-mmio-47-visual, trace display-stall-47-actual.

Originalspindumpstaticreview11dee2e9ec led to explicit fixed SAMPLE route.
Host e4d3aa7ff7+cd880116a9 requires exactonecurrentbootREADY capability, max2requests,
no arbitraryPID/argv. Guestsource d78ebc73b4 (reviewed d2ac5ba0cc), actualbuild55
retained d54e8144b1 (9a1735b60b). HID55 only newartifact88944bytes SHA
853bed149abbed99b3157150dbcd1d25292f9a873e643d0e424e66e7fc1a8538.
All33imports originalcachechecked, exact2existingHIDentitlements unchanged.
Fixed original/usr/sbin/spindump targets SpringBoard/backboardd,2s/100ms,-onlyTarget,
noBinary/noFile/stdout/noSymbolicate/timelimit20,256KiBretention,cooperative60guestsec.
Originaltool execution/stackshot acceptance proven49healthy. No SAMPLE on47(oldhelper54).
Read-only resultparser merged c280dbe200+476b108364; missingchunks/end cannotprove
completion. Validpartialprefix retained, output outsideGit/ignored, usefulness
alwaysrequiresoriginaloutputreview. Hostsyntheticchecks andactual49reconstruction pass.
Stage55 completed real recovery readbacks for all4 app22/launcher22/reader54/HID55,
normal unmounts/COMPLETE, intentionalSignal15normalQMPquit/emulator0 retained.
Evidence1ef9b0a7da/owned-sample-stage-55. Root independently rechecks all7/ancestors,
rawreadback/unmountorder, headers/readableFDs and freezes0444+KEEP before48.
Newstage55root3604480bytes SHA
00fccb3ec7542ce5c9edd7970b627a15e962856d0438f11e3e4b520cecc6be80.
48layer4→stage55layer3→stage44layer2→boot27layer1→stage43raw.
No stage50dependencyfor48; keep50forhistorical37–47. No concurrentVMs.
Resolved metadata incident: root mistakenly repeated chmod0444 on existing
readonly44/27/raw43 ancestors at1791320615119518081ns ctime. Freshfullhashaudit
proves ONLYctime changed; allbytes/dev/inode/size/mtime/mode unchanged. Oldreports
remain untouched. Evidence stage55-chmod-metadata-audit.json. Exactattestation
support f5e961bcaa validates fixedperfile .ctime-revalidation.json against source
stage55/root-overlay.json hash, historical+currentfullidentity and freshfullhash.
Threeactualsidecars created, retained stage55-actual-ctime-attestations.json.
Futurectime/content/sourcechange rejects; explicitverificationjournalretainsactual
metadata. Keep sidecars AND stage55source report forever withaffectedancestors.
NEVER chmodalreadyreadonlyancestors again; checkmodebeforeanynecessarychmod.
Root chainrevalidationPASS0ff76853bb; protectedstage55 immutable for48.
48 failed BEFOREguestexecution:QEMUexit1/noquit/serial0, readonlysourceauxmode
wasinheritedbynewprivatecopies. Evidenceprivate-aux-mode includesactualstderr.
Narrowfix97f7230fa8 reservesnewprivateauxdestination, copy/hashchecks, chmod0600
ONLYnewcopy. Actualfirmware-freeQMPquery-blockro=false/quit0; frozen55source
bytes/inode/ctime/mtime/modeunchanged, duplicateoutputreject. NotaniOSmilestone.
49completedasabove. Futureguest rootallinput; SAMPLEonlyafterreviewedjourney
outcome toavoidperturbingreproduction. UseBACKBOARDD thenSPRINGBOARD atmostonceeach,
waitEND/FAILED; errorsareevidence, no grants/retries. No nativeperformanceclaim.

## Trace and control workflow

Root owns ALL live guest input, VNC, Home, OPEN, register queries and finish-run.
Bootworker owns launch/lifecycle/postflight, with explicit root launch instruction.
One VM during this investigation. Headless Unix endpoints only; no user windows.
The runner is sole QMP owner; never open a second raw QMP connection to a guest.

Use tracked commands in companion/OWNED_JOURNEY.md:

- `companion/run owned-control --report REPORT --output NEW swipe 16384 32270 16384 9145 --duration-ms 1500`
- Lock may need a second swipe only after actual reviewed state/first completion.
- Reviewed beta Close: `tap 16384 18560 --duration-ms 150`.
- Reviewed counter: `tap 16384 20316 --duration-ms 150`, exactly once.
- `companion/run observe --socket CURRENT_UNIX --output NEW --settle-seconds 4`.
- Continuous capture: `observe ... --observe-seconds 20` (no input allowed).
- Home: `observe ... --home-button` (fixed F6→SMC Menu press/release).
- `companion/run control --report REPORT probe-capture-before`, only reviewed0.
- `... probe-capture-after`, only genuine tap1 AND reviewed1.
- `... probe-status` gives live state; live report.json is initial/stale.
- With keepalive, `... finish-run` after strict completion requests normal cleanup.
- `... query-display-registers`:18 fixed audited nonconsuming MMIO reads, sequential
  not atomic, no framebuffer DMA/arbitrary addresses.
- `... trace-display-window --arguments '{"seconds":60}'`:7 fixed events,
  integer1..60, no overlap, cooperative deadline via sole mailbox poll and cleanup.
  Journal display-trace-control.jsonl records actual results. Trace can affect timing.

Never use guest ACK or lifecycle JSON as visible success. Retain actual raw logs,
image hashes, source revisions and direct image review. QMP828×1792 vs VNC832×1792
includes padding. Convert PPM losslessly to PNG for view_image and check decoded
RGB equality. A failed first tap must not be hidden by a second tap or aftercapture.

Poststop:
`companion/run verify-journey --report REPORT --output NEW.json`
`companion/run preserve-stopped --report REPORT --output REPORT/stopped-disk-hashes.json`
Default preservation requires normal completed run. Explicit `--failed-attempt`
retains error/strict state and marks root forensic-only, while still requiring
emulator0, actual QMP shutdown, seven disks and ancestor checks. /proc descriptor
checks are scoped to readable processes; permission gaps are recorded.
Verifier checks raw markers/input/QMP/PPM hashes, not image semantics. Without an
independent arrival observer, chronology uses reviewed capture-gate source hash.

## Current immutable guest tuple

Four owned artifacts, unchanged in37–47:

- App22 `~/.local/share/inferno/app-probe/exec-build-22/InfernoProbe.app/InfernoProbe`,
  74976bytes SHA d05f1b32523684a5c89d41cb2c35fbf0207b62adf864c27fab4d5973bf8e6176.
- Launcher22 same directory `inferno-launcher-open-error`,69264bytes,
  SHA0f6626102deedabe4f5c93dafbd3c757387836c463d6b59bf3204932e550bf17.
- Reader54 `~/.local/share/inferno/native-probe/helper-build-54/inferno-readiness`,
  86448bytes SHA2440b210892898f43bd2f2afe3907ee5b682262d1d71c47e8c940757aa46c0b2.
- HID54 same directory `inferno-hid-input`,70848bytes,
  SHAf670cb9ec09933514326df8f6cb4995883b22d58852b12d7511ae075cec06943.

All172 imports checked against original cache; Info/jobs unchanged. Exact HID grants:
com.apple.developer.hid.virtual.device=true and
com.apple.security.iokit-user-client-class=[IOHIDResourceDeviceUserClient].
Owned bundleorg.inferno.companion.probe, /Applications/InfernoProbe.app;
launcher/usr/bin/inferno-launcher. Preserve original LS System classification only
for that owned path and NSObject isa ABI fix. No signer/trust metadata changes.

Baseline emulator through42: source1cebf0c00be038e7156d82578214c2cafa109873,
SHAe3da84b179ce328e06a0f917aabb8e4d80c8a4cf64701212464831a270e1741e.
Archived read-only `.local-build/binaries/simulated-sep-first-unlock-e3da84b179ce/`.
Current binary described above45–47; build command retains configuration:
`companion/run build --simulated-sep --enable-kvm` (8 jobs).
KVM compile capability does NOT mean guest native/KVM execution; iOS uses TCG2CPU/
4GiB, simulatedSEP, upstream direct-kernel patches and software rendering.
Profile `~/.local/share/inferno/images/ios14b5/verified-profile/profile.json`.
Recovery archive `.local-build/binaries/simulated-sep-7e7033796707/`.

## Backing chain: keep exact paths and every dependency

All under `.local-build/reports/`,0444+KEEP. Max4 qcow layers:
37–47 layer4 → stage50 layer3 → stage44 layer2 → boot27 layer1 → stage43raw.

- disk-preparation-43/disks/root.raw,34359738368logicalbytes,
  SHA69e8378c71d1f29840baa7ae16811d3f6285bf27042501a79e8139f8a5ad61d5.
- app-boot-27/disks/root.qcow2,140443648bytes,
  SHA6898ad82af6bfb96168d2b7dd8febcfa977ef703679739197a40a08d735b6d4c.
- disk-preparation-44/disks/root.qcow2,3145728bytes,
  SHAa26c50b4f51e5bb8a7c67889e2078649324851849f826f0eb754680f91f66f5d.
- disk-preparation-50/disks/root.qcow2,3604480bytes,
  SHA3745a6abe402cd6b645a29a7fd5a9853b7ac06e9c8e3ca6bfa9099f21db5a693.

Stage50 intentionally stopped recovery with Signal15 after verified staging,
reporterror/attempt_completed:false. Do NOT blanket-reject report errors and break
this established backing tuple; forensic_only rejects failed app attempts.
Future staging must branch44 and replace ALL components changed from44. Never
stage50 and boot another layer5. Loader verifies actual qemu-img headers, hashes,
paired auxiliary6copies and descriptors; postflight rehashes ancestors.
Keep stages45–49 and other actual used dependencies too. No retirement authorized.
Dependencies/binaries/disks/credentials outside Git. Never copy Apple binaries
into trackedtree, decrypt FairPlay, extract keys, forge signatures or impersonate iCloud.

## Completed measurements and limits

37/38: strict0→1 and three warm Home/reopen cycles each, same kernel process
identity and counter1. Warm OPEN→active747.806/709.095/735.643ms in37;
721.110/765.458/702.043ms in38. Guest lifecycle intervals, not presentation/native.
38 additionally ordinary app-switcher dismissal, original ps absence snapshot
BEFORE OPEN, newPID492/unique492/idversion1414/main33927344147 and reviewed0.
Request→active884.627917ms; caches uncontrolled. No forced kill/cache-cold claim.

39/40: actual concurrent strict journeys, both reviewed1 after a common60-second
foreground-idle sample; normal stops/all7/ancestors. 61CPU/13smaps rounds,
38.74CPU-seconds,64.566591%onehostcore, peakPSSsum11,558,389,760bytes,
peakRSSsum11,580,973,056bytes. No VNC/input during sample, periodic30sQMP/startup
MT900strace remained enabled. Evidence `density-39-40-actual`,
`density-39-40-visual`, `owned-two-guest-strict-39-40*`.
N=2 observed pair only; no maxcapacity/cost/general compatibility claim.
CPU100%=onehost logical core; emulator RSS/PSS is not app allocation.

Initial/warm/process timing parsers and process/density samplers are tracked under
companion/. Exact OPEN needs fresh32lowerhex ID and CURRENT bootUUID; owned-control
creates the ID. Home must show actual app background before OPEN. No automatic
retry; acceptance does not prove app visibility. Loopback telemetry claimed PID is
checked against original owned path/uid501 and kernel identity, but peer PID is
not transport-authenticated. No new entitlements.

## Worker ownership

- boot_runner: actual builds/launch/staging/stopped evidence; no UI/input.
- native_probe: display trace source/audits; current worktree/tmp/inferno-display-query.
- disk_path: host command evidence/checkpoint changes; isolatedworktree.
- Root: integration/docs, all actual UI and control, image review.

Use followup_task to reactivate completed existing workers. Do not revert others.
Full historical facts, failed approaches and prior evidence remain in PROGRESS.md,
evidence/ and Git history; do not repeat crosscontainer file/extra-grant detours.
