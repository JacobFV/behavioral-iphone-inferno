# Navigation Demo IPA

A third, independently named owned fixture for original UIKit: a navigation
controller, a scrollable twelve-item catalog, a detail screen, an ordinary Back
button, a switch, and Save. `Guide.txt` is loaded from this app's bundle through
Foundation. Save changes only in-process state; no persistence or permissions
are added. The sample has no private API, entitlements, networking, nested code,
probe event transport, or new framework implementation.

**Not yet executed in a guest.** Build/import success cannot establish any UI
behavior. This is a fixed 414-point portrait research fixture, not an SDK,
Xcode project build bridge, or general IPA compatibility claim.

## Host build

The producer reuses the existing self-authored UIKit header and four link stubs
without editing them. Sample-local declarations describe new selector ABIs;
`NSClassFromString` obtains the original UINavigationController, UIScrollView,
and UISwitch classes. Missing classes display an explicit failure screen.

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
3. Swipe upward inside the catalog until item 12 and the end marker are visible.
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
