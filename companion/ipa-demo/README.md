# Imported demo IPA

An independently named, self-authored ARM64 iOS14 application for the manifest import route. It has one increment button, a count label, and reads `Message.txt` using original Foundation `NSBundle` and `NSString` APIs. A resource-load failure is shown explicitly. It has no probe event transport, lifecycle measurement, entitlement file, or special grants.

Build outside every Git worktree:

```sh
python3 companion/ipa-demo/build.py --output /external/fresh-demo --linker /path/to/ld64.lld
```

The script compiles and ad-hoc signs our executable, packages a deterministic ZIP, validates its IPA through `app-import.py`, then builds the fixed manifest-target launcher and mobile wrapper. It reuses self-authored declarations and link stubs from `app-probe` without changing the probe. It is not an Xcode project build pathway.

Actual host build `ipa-demo-001` passed importer validation. All 86 combined app/launcher/wrapper imports resolved through the installed original cache's export tries. Raw commands, tool/source/output hashes, import manifest and audit are retained under `evidence/`. Binaries, IPA and extracted tree stay outside Git.

**Not executed in a guest.** Resource display and button operation need actual VM observation. Expected initial resource text is “Resource loaded from this imported app bundle.” and count is zero. A single increment should display one. Unlike the probe, no serial lifecycle marker is expected. The fixed 414-point portrait layout targets this research VM's current logical screen; it is not a general adaptive-layout application.

Fresh target: `/Applications/ImportedDemo.app`, identifier `org.inferno.companion.ipademo`. Stage the validated manifest with the native manifest stager, and separately merge the generated owned launcher job/cache plus stage its two helper binaries. Never use the identical-probe collision exception for this different app. Existing target collisions must fail. Runtime acceptance, process presence and pixels are separate evidence; successful host packaging is not launch proof.
