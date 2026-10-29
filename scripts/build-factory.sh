#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
work=$(realpath "${1:?Usage: build-factory.sh WORK_DIRECTORY NEW_OUTPUT_DIRECTORY}")
out=${2:?Use a new absolute output directory}
[[ "$out" = /* && ! -e "$out" ]] || exit 2
mkdir -p "$out/source"
git -C "$work/sources/image-factory" archive 45d147aba6b28d66d83a6229f21104d28ddb44a8 | tar -x -C "$out/source"
patch --batch -p1 -d "$out/source" < "$repo/patches/image-factory-readiness.patch"
(cd "$out/source/frontend" && npm ci && npm run build) > "$out/frontend.log" 2>&1
mkdir -p "$out/source/internal/frontend/dist"
cp -a "$out/source/frontend/dist/." "$out/source/internal/frontend/dist/"
GOTOOLCHAIN=go1.27.0 GOMAXPROCS=8 go -C "$out/source" test -p 4 ./internal/registry ./internal/artifacts ./internal/frontend/http/oci > "$out/tests.log" 2>&1
for arch in amd64 arm64; do
 GOTOOLCHAIN=go1.27.0 GOMAXPROCS=8 CGO_ENABLED=0 GOOS=linux GOARCH="$arch" \
  go -C "$out/source" build -buildvcs=false -p 4 -trimpath \
  -ldflags '-s -w -X github.com/siderolabs/image-factory/internal/version.Tag=v1.7.2-14-g45d147a-readiness1' \
  -o "$out/image-factory-$arch" ./cmd/image-factory
 done
cat > "$out/Dockerfile" <<'EOF'
FROM ghcr.io/siderolabs/image-factory@sha256:d590896efe665a5c9d6707d59c62c88258015637359842e1acd52c6c473d7e88
ARG TARGETARCH
COPY image-factory-${TARGETARCH} /usr/bin/image-factory
EOF
for arch in amd64 arm64; do
 docker build --platform "linux/$arch" -t "talos-gpu-unlock-factory:local-$arch" "$out"
done
