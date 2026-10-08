# Standalone importer directory-mode integration

Actual NavigationDemo006 IPA, samebytes, ordinary importer CLI under caller
umask077, followed by unchanged validate_manifest. No VM/build/staging/actions.

Before: CLI exit0/statusvalidated-not-executed, but app directory0700 and
validator rejected "Aliased or missing bundle tree". Output retained externally
at import-mode-before-1; never repaired or consumed.

After: explicit chmod0755 only newlycreated app root/descendant directories.
No process-wide umask change; existing output roots remain rejected. CLI exit0,
validatoraccepted, app directory0755, filebytespreserved, callerumaskstill077.
Fresh output import-mode-after-1 is independent of the failed attempt. No
compatibility policy or preflight rejection checks changed.

Raw stdout/stderr and source/IPA/manifest hashes are retained here. All imported
app bytes remain external. check.py reproduces the one CLI→validator boundary;
it is not guest execution or signature trust evidence. Frozen Navigation004/006
producer trees and persistent runtime consumers were not modified.
