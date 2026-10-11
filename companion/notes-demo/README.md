# Notes Demo IPA

A fourth owned fixture (after ImportedDemo and NavigationDemo) exercising a
different UIKit surface: a `UITableView` fed from `NSUserDefaults`, a
`UITextField` with a return-key/Add button, and a Clear button. A launch counter
and the note list are stored in `NSUserDefaults`, so a relaunch should show the
earlier notes. No private API, entitlements, networking, nested code, bundled
resources or new framework implementation. Classes beyond the shared probe stubs
are resolved with `NSClassFromString`; a missing class shows an explicit failure
screen.

**Status: host build/import only.** Nothing here has been staged, booted or
launched; table rendering, keyboard entry, and whether guest `NSUserDefaults`
can persist across relaunch are unverified. Target:
`/Applications/NotesDemo.app`, `org.inferno.companion.notesdemo`.

```sh
python3 companion/notes-demo/build.py \
  --clang /usr/bin/clang \
  --linker /path/to/ld64.lld-18 \
  --output /external/new-notes-demo
```

Same hash-pinned LLVM18 tools, ad-hoc signing, unchanged importer and
manifest-target launcher as [navigation-demo](../navigation-demo/README.md).
Proposed journey for a later authorized boot: review empty list and
`Launches: 1 | Notes: 0`; tap the field, type through the guest keyboard path
(HID input support for text entry is itself unverified), Add; review the row;
relaunch and review `Launches: 2` with the retained note.
