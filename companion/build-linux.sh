#!/usr/bin/env bash
# Companion-only build driver. No global installs, guest images or firmware.
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source_repo=$(git -C "$script_dir" rev-parse --show-toplevel)
build_root=""
jobs=8
simulated_sep=false
kvm_option=--disable-kvm
while (($#)); do
    case "$1" in
        --build-root) build_root=$2; shift 2 ;;
        --jobs) jobs=$2; shift 2 ;;
        --simulated-sep) simulated_sep=true; shift ;;
        --enable-kvm) kvm_option=--enable-kvm; shift ;;
        *) echo "Usage: $0 --build-root ABSOLUTE_PATH [--jobs 1..8] [--simulated-sep] [--enable-kvm]" >&2; exit 2 ;;
    esac
done
[[ "$build_root" = /* && "$jobs" =~ ^[1-8]$ ]] || { echo 'Require absolute build root and 1..8 jobs' >&2; exit 2; }
mkdir -p "$build_root"
build_root=$(cd "$build_root" && pwd)
python3 "$script_dir/bootstrap-linux.py" "$build_root"
if [[ ! -x "$build_root/venv/bin/python" ]]; then python3 -m venv "$build_root/venv"; fi
"$build_root/venv/bin/python" -m pip --cache-dir "$build_root/pip-cache" install --disable-pip-version-check --no-deps --only-binary=:all: --require-hashes -r "$script_dir/build-tools-arm64.txt"
export PATH="$build_root/venv/bin:/usr/bin:/bin"
packages="$build_root/packages/usr"
deps="$build_root/deps"
mkdir -p "$deps" "$build_root/downloads" "$build_root/sources"
export PKG_CONFIG_PATH="$deps/lib/pkgconfig:$deps/lib64/pkgconfig:$packages/lib/aarch64-linux-gnu/pkgconfig:$packages/share/pkgconfig"
export LD_LIBRARY_PATH="$deps/lib:$deps/lib64:$packages/lib/aarch64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export CPPFLAGS="-I$deps/include -I$packages/include -I$packages/include/aarch64-linux-gnu"
if $simulated_sep; then
    export CPPFLAGS="$CPPFLAGS -DINFERNO_SIMULATED_SEP"
fi
export LDFLAGS="-L$deps/lib -L$deps/lib64 -L$packages/lib/aarch64-linux-gnu -Wl,-rpath,$deps/lib -Wl,-rpath,$deps/lib64 -Wl,-rpath,$packages/lib/aarch64-linux-gnu"
nettle_archive="$build_root/downloads/nettle-3.10.2.tar.gz"
if [[ ! -f "$nettle_archive" ]]; then
    for base in https://mirrors.kernel.org/gnu https://ftp.gnu.org/gnu https://ftpmirror.gnu.org/gnu; do
        if curl --fail --location --retry 1 --connect-timeout 15 --max-time 120 \
            "$base/nettle/nettle-3.10.2.tar.gz" --output "$nettle_archive.part"; then
            mv "$nettle_archive.part" "$nettle_archive"
            break
        fi
    done
fi
printf '%s  %s\n' fe9ff51cb1f2abb5e65a6b8c10a92da0ab5ab6eaf26e7fc2b675c45f1fb519b5 "$nettle_archive" | sha256sum -c -
if [[ ! -f "$deps/lib/pkgconfig/nettle.pc" && ! -f "$deps/lib64/pkgconfig/nettle.pc" ]]; then
    tar -xf "$nettle_archive" -C "$build_root/sources"
    (cd "$build_root/sources/nettle-3.10.2"
     ./configure --prefix="$deps" --disable-documentation
     make -j"$jobs"
     make install)
fi
# A durable detached source clone keeps Meson wrap downloads and mlib local.
source_tree="$build_root/source"
if [[ ! -d "$source_tree/.git" ]]; then
    git clone --no-hardlinks "$source_repo" "$source_tree"
fi
upstream_base=cc4302a99167abec69b714cfd00c38caece7e7de
source_commit=$(git -C "$source_repo" rev-parse HEAD)
git -C "$source_repo" merge-base --is-ancestor "$upstream_base" "$source_commit" || {
    echo 'Fork revision is not descended from the reviewed upstream base' >&2; exit 1;
}
git -C "$source_tree" diff --quiet && git -C "$source_tree" diff --cached --quiet || {
    echo 'Durable source has tracked changes; preserve/review them before rebuilding' >&2; exit 1;
}
git -C "$source_tree" fetch "$source_repo" "$source_commit"
git -C "$source_tree" checkout --detach "$source_commit"
printf 'Building upstream %s plus committed fork %s\n' "$upstream_base" "$source_commit"
git -C "$source_tree" submodule update --init util/mlib
mkdir -p "$build_root/build"
(cd "$build_root/build"
 "$source_tree/configure" --target-list=aarch64-softmmu --without-default-features \
   "$kvm_option" \
   --enable-tcg --enable-pixman --enable-png --enable-fdt=system --enable-slirp \
   --enable-lzfse --enable-nettle --enable-gnutls --enable-vnc \
   --disable-gtk --disable-sdl --disable-opengl --disable-guest-agent \
   --disable-tools --disable-install-blobs --disable-werror \
   --extra-cflags="$CPPFLAGS" --extra-ldflags="$LDFLAGS"
 ninja -j"$jobs" qemu-system-aarch64 trace/trace-events-all)
python3 "$script_dir/build-manifest.py" "$build_root"
printf 'Binary: %s\n' "$build_root/build/qemu-system-aarch64"
