# second-host-reproduction-1: the deterministic front of the chain, on another machine

2026-10-29, on `promaxgb10-4dfb` (machine-id `96ac3ff3…`, Ubuntu 24.04 arm64, GB10),
not the original development host. The repository and `.local-build` were copied to
the same absolute path; the IPSW was copied to `$INFERNO_HOME/ipsw/`. Outputs live
outside Git under that host's `~/.local/share/inferno/images/ios14b5/`.

## Ran, and what matched

- `companion/run status` / `check`: the copied rebuilt emulator matches its build
  manifest (and therefore `runtime_rebuild`'s substitution record) and passed the
  firmware-free QMP smoke (`smoke-report.json`). Not an iOS boot.
- `companion/run prepare --ipsw …`: n104ap research erase identity selected; component
  hashes in `profile.json` (paths are that host's).
- `os-image/decode-udif.py` then `wrap-gpt4k.py`: every hash equals the values recorded
  in `companion/os-image/README.md` from the original host:
  DMG `cae20aff…`, decoded raw `96bebe30…`, APFS payload `54f0ea7d…`,
  4096-byte GPT wrapper `93f97dae…` (`decode-report.json`, `wrapper-report.json`).

## Not done

No recovery stage ran. The external tool roots deleted on 2026-10-26 (pinned overlay
`qemu-img`, `ld64.lld-18`, ldid, hfsplus) are not yet re-provisioned on this host, so
raw-recovery extraction, helper builds, initial volumes, Data seed/flatten/growth, SEP
keybag and flatten, runtime inspection, renderer cache patch, runtime artifacts,
fresh-runtime stage and `boot-fresh` remain. Setup Assistant to Home on a fresh image
is still the open milestone from fresh-boot-6.
