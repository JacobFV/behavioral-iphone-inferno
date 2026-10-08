# Actual reproducible preparation-helper build

New external output `~/.local/share/inferno/native-probe/reproducible-helper-build-1`
was built with the retained helper60 tools and unchanged committed four sources.
The recorded compile/link/owned ad-hoc commands ran successfully, followed by
actual ldid entitlement readback. No historical artifact was converted or edited.
The executable is byte-identical to helper60:86144bytes,
SHA25666492292ea073d5710af269585058129d92db71509c16c3cd74453421e61a3e3.

The build record SHA is3cb1656f3978bfdcca7e3da80d7f8091f524c1b7593bb64a42a7a2a47f34e532.
`audit.py` compares actual executable bytes and entitlement dictionaries, checks
subprocess logs, and checks the same four source/output bindings required by
prepare-import.validate_runtime. It does not rerun full runtime/backing hashes.
The new producer preserves the consumer's strict schema. Its source revision is
90f244ac75; producer hashes are retained. Only owned code was signed. No Apple
binary, generated executable or object is tracked here, and no VM was launched.

The complete runtime/session still needs ordinary preparation validation. This
build alone neither stages the helper nor supplies firmware/cache/base lineage.
