#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
archify=$(realpath "${1:?Usage: render-diagrams.sh ARCHIFY_CHECKOUT NEW_ABSOLUTE_OUTPUT_DIRECTORY}")
out=${2:?Use a new absolute output directory}
[[ "$out" = /* && ! -e "$out" ]] || { echo 'Use a new absolute output directory.' >&2; exit 2; }
[[ "$(git -C "$archify" rev-parse HEAD)" = 208acba8d412335185b2056fedf54b3405df43fb ]] || { echo 'Archify does not match the toolchain pin.' >&2; exit 2; }
mkdir -p "$out"
cd "$repo"
for name in build boot factory proxmox-boot; do
  type=workflow
  [[ "$name" != factory ]] || type=architecture
  node "$archify/archify/bin/archify.mjs" finalize "$type" \
    "$repo/diagrams/archify/$name.$type.json" "$out/$name.html" \
    --repo-root "$repo" --quality showcase --json > "$out/$name.command.json"
done
