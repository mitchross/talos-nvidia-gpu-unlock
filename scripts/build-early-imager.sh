#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
work=$(realpath "${1:?Usage: build-early-imager.sh WORK_DIRECTORY NEW_OUTPUT_DIRECTORY}")
out=${2:?Use a new absolute output directory}
[[ "$out" = /* && ! -e "$out" ]] || exit 2
mkdir -p "$out/talos"
git -C "$work/sources/talos" archive dad8d3edfe7ca381044d7cad259fdf3030efa700 | tar -x -C "$out/talos"
patch --batch -p1 -d "$out/talos" < "$repo/patches/talos-early-loader.patch"
GOTOOLCHAIN=go1.26.8 GOMAXPROCS=8 go -C "$out/talos" test -race -p 4 ./internal/pkg/gpuunlock > "$out/loader-tests.log" 2>&1
GOTOOLCHAIN=go1.26.8 GOMAXPROCS=8 CGO_ENABLED=0 GOOS=linux GOARCH=amd64 GOAMD64=v1 \
  go -C "$out/talos" build -buildvcs=false -p 4 -trimpath \
  -ldflags '-s -w -X github.com/siderolabs/talos/pkg/machinery/version.Tag=v1.14.5 -X github.com/siderolabs/talos/pkg/machinery/version.SHA=dad8d3ed' \
  -o "$out/init-amd64" ./internal/app/init > "$out/init-build.log" 2>&1
image=ghcr.io/siderolabs/imager:v1.14.5@sha256:ef33373986bb0765132f0558ea43c9f8fee2c3839f1d1a4232693b77092d7350
cid=$(docker create --platform linux/amd64 "$image")
trap 'docker rm "$cid" >/dev/null' EXIT
docker cp "$cid:/usr/install/amd64/initramfs.xz" "$out/initramfs-stock-amd64.xz"
printf '%s  %s\n' 8c36de2d10f180767c132f903a7e6bafbb7afae668aa06db15d5e7fa7faf4324 "$out/initramfs-stock-amd64.xz" | sha256sum -c -
python3 "$repo/scripts/replace-init.py" "$out/initramfs-stock-amd64.xz" "$out/init-amd64" "$out/initramfs-early-amd64.xz"
printf '*\n!initramfs-early-amd64.xz\n' > "$out/.dockerignore"
docker build --platform linux/amd64 -f "$repo/examples/Dockerfile.imager" -t talos-gpu-unlock-imager:local "$out"
sha256sum "$out/init-amd64" "$out/initramfs-early-amd64.xz" > "$out/SHA256SUMS"
