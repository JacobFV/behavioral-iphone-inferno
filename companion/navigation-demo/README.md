# Navigation Demo IPA

A third, independently named owned fixture for original UIKit: a navigation
controller, a scrollable twelve-item catalog, a detail screen, an ordinary Back
button, a switch, and Save. `Guide.txt` is loaded from this app's bundle through
Foundation. Save changes only in-process state; no persistence or permissions
are added. The sample has no private API, entitlements, networking, nested code,
probe event transport, or new framework implementation.

**The revised006 sample completed an actual guest journey.** Original frames and
root review are retained in [boot2 visual evidence](../evidence/navigation-boot-2-visual/review.json),
with [normal shutdown and disk retention](../evidence/navigation-boot-2-actual/review.json).
Button-start scrolling, complete Guide text, navigation, switch/save and reopening
in-process state were visibly verified. Build/import success alone cannot establish UI behavior. This is a fixed 414-point portrait research fixture, not an SDK,
Xcode project build bridge, or general IPA compatibility claim.

## Host build

The producer reuses the existing self-authored UIKit header and three link stubs
without editing them. Its sample-local UIKit.tbd adds only the UIScrollView
superclass symbol to the existing UIKit declarations. Sample-local declarations describe new selector ABIs;
`NSClassFromString` obtains the original UINavigationController and UISwitch
classes. The owned CatalogScrollView subclasses original UIScrollView. Missing classes display an explicit failure screen.

Use the same hash-pinned LLVM18 tools as the earlier imported demo and a new
external output directory:

```sh
python3 companion/navigation-demo/build.py \
  --clang /usr/bin/clang \
  --linker /path/to/ld64.lld-18 \
  --output /external/new-navigation-demo
```

The script builds an ARM64 iOS14 device executable, applies LLVM ad-hoc signing
only to owned code, packages three files into `NavigationDemo.ipa`, invokes the
unchanged importer, and builds the manifest-target launcher/wrapper. Commands,
source/tool/output hashes and raw build log stay external. A failed build retains
`INCOMPLETE`; no guest is started. The target is a fresh
`/Applications/NavigationDemo.app`, `org.inferno.companion.navigationdemo`; the
probe collision exception must not be used.

## Proposed root-owned headless journey

After a separately authorized prepare/stage/boot using the ordinary manifest
pipeline, root retains actual VNC/QMP images and explicit request IDs/ACKs:

1. Review Navigation Demo with catalog items and `No saved item. Saves: 0`.
2. Open item 1; review the detail title and exact bundled Guide text. Use the
   standard navigation Back button and review the catalog again.
3. Start an upward swipe on a visible catalog button; review actual scrolling.
   Continue with explicit reviewed swipes until item 12 and the end marker are visible.
   Review those pixels before tapping item 12; no blind fixed-count scrolling.
4. Review `Detail for item 12`, bundled text, and `Option: Off`. Tap the switch
   once and review `Option: On`.
5. Tap Save and return. Review catalog summary `Saved item: 12 | Option: On`
   and `Saves: 1`. Reopen item 12 and review that the switch remains on.
6. Use ordinary Back and review the unchanged summary. Root then requests normal
   observation finish. No automatic Home/reopen, retries, or gesture driver.

Coordinates come from each reviewed actual frame; labels and accessibility IDs
assist review, not fabricated acceptance. ACK means transport acceptance only.
Unchanged pixels or missing resource text are retained as an incomplete/failed
journey, never inferred success from process presence or a build manifest.

## Actual host result

`navigation-demo-004` built from `df73d9f978` passed compile with `-Werror`,
link, IPA import/revalidation and manifest-bound helper build. The IPA is 7,926
bytes and contains a 72,544-byte executable plus Info.plist and Guide.txt. Its
three executable outputs are byte-identical to audited build003: all 110 imported
symbols resolve in the supplied original cache, and all three dynamically named
UIKit classes are exported through UIKitCore. This does not execute their
selectors. Raw host logs, pins and the two earlier failed host attempts are
retained in `evidence/`; all IPA/binary products remain external.

## Sample-only revision after the first actual journey

Root observed the original build's catalog, item1 detail, Back, margin-start
scrolling to item12, switch On and Save with summary item12/Saves1. Its bundled
Guide text was clipped, and a swipe starting on a button did not move the catalog.
Those limitations remain part of that attempt; they are not retroactively fixed.

Apple documents that `touchesShouldCancelInContentView:` defaults to NO for
UIControl children, and that NO retains touch tracking in that child rather than
starting a drag. The method is not consulted if `canCancelContentTouches` is NO.
The observed button/margin difference is consistent with this policy, not direct
proof of the original runtime branch. Sources: [touchesShouldCancel(in:)](https://developer.apple.com/documentation/uikit/uiscrollview/touchesshouldcancel(in:))
and [canCancelContentTouches](https://developer.apple.com/documentation/uikit/uiscrollview/cancancelcontenttouches).

CatalogScrollView now returns YES for UIButton children, otherwise forwarding to
super, and explicitly enables content-touch cancellation. Ordinary button actions
and default delaysContentTouches are unchanged. The resource label grows from
170 to200 points, ending at y390 before the y405 option row. A new guest journey
must verify button-start scrolling, normal taps and full Guide text; neither
this layout choice nor documentation establishes successful rendering.


The revised host producer built `navigation-demo-006` from `eda2b7c31f`.
It passed strict compile/link/import and manifest launcher build. The ZIP again
contains exactly three app files. All115 executable imports passed the original
cache audit on byte-identical executables from005, including the new UIScrollView
superclass reference. Build005 is retained but superseded because its producer
also packaged the local link declaration;006 corrects that copy list. Revised
raw host evidence is in `evidence/scroll-revision-006/`. No revised guest run is
claimed, and the old004 producer/output remains untouched.
