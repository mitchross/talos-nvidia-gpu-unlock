#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
work=${1:?Usage: rebuild-module.sh WORK_DIRECTORY NEW_ABSOLUTE_OUTPUT_DIRECTORY}
work=$(realpath "$work")
cd "$work"
out=${2:?Provide a new absolute output directory}
[[ "$out" = /* && ! -e "$out" ]] || { echo 'Use a new absolute output directory.' >&2; exit 2; }
test "$(git -C sources/gpu-unlock rev-parse HEAD)" = 0532473b4b105ed216948ed9c5aaeab0fa5c734f
test "$(git -C sources/pkgs rev-parse HEAD)" = f4bda77bb9f8202cac8443a7284ce1c7aa129f38
test -z "$(git -C sources/pkgs status --porcelain -- kernel Pkgfile)"
mkdir -p "$out/src" "$out/module"
curl -fL --retry 3 https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.18.58.tar.xz -o "$out/linux.tar.xz"
printf '%s  %s\n' 069b19f9032c4dac8149ae4b6520c35debca0f42a9f6d52ee55ba6ca9b818013 "$out/linux.tar.xz" | sha256sum -c -
tar -xJf "$out/linux.tar.xz" --strip-components=1 -C "$out/src"
cp sources/pkgs/kernel/build/config-amd64 "$out/src/.config"
cp sources/pkgs/kernel/build/certs/* "$out/src/certs/"
while IFS= read -r patch_file; do
  patch --batch -d "$out/src" -p1 < "$patch_file"
done < <(find sources/pkgs/kernel/build/patches -type f -name '*.patch' | sort)
git -C sources/gpu-unlock archive HEAD kernel/gpu_unlock | tar -x -C "$out/module" --strip-components=2
docker build --platform linux/amd64 -f "$root/scripts/Dockerfile.toolchain" -t gpu-unlock-llvm:talos-1.14.5 .
docker run --rm --user "$(id -u):$(id -g)" --entrypoint /bin/bash \
  -e ARCH=x86 -e LLVM=1 -e JOBS="${JOBS:-8}" \
  -v "$out/src:/src" -v "$out/module:/module" -w /src \
  gpu-unlock-llvm:talos-1.14.5 -c \
  'make olddefconfig && make -j "$JOBS" && make -j "$JOBS" modules && make -C /src M=/module modules' \
  > "$out/build.log" 2>&1
test "$(cat "$out/src/include/config/kernel.release")" = 6.18.58-talos
modinfo "$out/module/gpu_unlock.ko" > "$out/modinfo.txt"
sha256sum "$out/module/gpu_unlock.ko" "$out/src/Module.symvers" "$out/src/.config" > "$out/SHA256SUMS"
printf 'Built %s; no module was installed or loaded.\n' "$out/module/gpu_unlock.ko"
