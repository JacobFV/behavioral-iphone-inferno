#!/bin/bash
# Isolated experiment build: a worktree of the pinned source revision plus the
# completion-delay patch, configured exactly like build-linux.sh, in its own build dir.
set -euo pipefail
X2=${1:-}   # optional suffix: build-exp.sh 2 -> source-exp2, build-exp2, build-exp2-manifest.json
R=$HOME/Documents/behavioral-iphone-inferno; B=$R/.local-build
[ -x $B/venv/bin/python ] || python3 -m venv $B/venv
$B/venv/bin/python -m pip --cache-dir $B/pip-cache install --disable-pip-version-check --no-deps --only-binary=:all: --require-hashes -r $R/companion/build-tools-arm64.txt -q
export PATH="$B/venv/bin:$B/packages-exp/usr/bin:/usr/bin:/bin"
packages=$B/packages/usr; deps=$B/deps; X=$B/packages-exp/usr  # dev headers this host lacks (see journal)
export PKG_CONFIG_PATH="$X/lib/aarch64-linux-gnu/pkgconfig:$X/share/pkgconfig:$deps/lib/pkgconfig:$deps/lib64/pkgconfig:$packages/lib/aarch64-linux-gnu/pkgconfig:$packages/share/pkgconfig"
export LD_LIBRARY_PATH="$X/lib/aarch64-linux-gnu:$deps/lib:$deps/lib64:$packages/lib/aarch64-linux-gnu"
export CPPFLAGS="-I$X/include -I$deps/include -I$packages/include -I$packages/include/aarch64-linux-gnu -DINFERNO_SIMULATED_SEP"
export LDFLAGS="-L$X/lib/aarch64-linux-gnu -Wl,-rpath,$X/lib/aarch64-linux-gnu -L$deps/lib -L$deps/lib64 -L$packages/lib/aarch64-linux-gnu -Wl,-rpath,$deps/lib -Wl,-rpath,$deps/lib64 -Wl,-rpath,$packages/lib/aarch64-linux-gnu"
S=$B/source-exp$X2
if [ ! -d $S ]; then git -C $B/source worktree add --detach $S $(git -C $B/source rev-parse HEAD); git -C $S submodule update --init util/mlib; fi
cp $R/hw/display/apple_displaypipe_v4.c $S/hw/display/apple_displaypipe_v4.c
mkdir -p $B/build-exp$X2; cd $B/build-exp$X2
rm -rf meson-private meson-logs; [ -f build.ninja ] || $S/configure --target-list=aarch64-softmmu --without-default-features --enable-kvm \
   --enable-tcg --enable-pixman --enable-png --enable-fdt=system --enable-slirp \
   --enable-lzfse --enable-nettle --enable-gnutls --enable-vnc \
   --disable-gtk --disable-sdl --disable-opengl --disable-guest-agent \
   --disable-tools --disable-install-blobs --disable-werror \
   --extra-cflags="$CPPFLAGS" --extra-ldflags="$LDFLAGS"
nice -n 5 ninja -j12 qemu-system-aarch64 trace/trace-events-all
python3 - <<P
import json,hashlib
m=json.load(open("$B/build-manifest.json"))
b="$B/build-exp$X2/qemu-system-aarch64"
m["binary"]["path"]=b; m["binary"]["sha256"]=hashlib.sha256(open(b,"rb").read()).hexdigest()
m["source_diff"]="experiment: hw/display/apple_displaypipe_v4.c completion-delay-ns, vblank-ns, complete-at-vblank properties (default off); see companion/FREEZE_EXPERIMENT_1.md and _2.md"
m["purpose"]="EXPERIMENT build for freeze A/B; not the pinned runtime"
json.dump(m,open("$B/build-exp$X2-manifest.json","w"),indent=2)
print("BUILD-EXP-DONE", m["binary"]["sha256"])
P
