#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
work=$(realpath "${1:?Usage: extract-firmware.sh WORK_DIRECTORY}")
test ! -e "$work/assets" && test ! -e "$work/assets.src" || { echo 'Preserve the existing assets directory.' >&2; exit 2; }
make -C "$work/sources/gpu-unlock" inputs INPUTS="$work/inputs"
python3 "$repo/scripts/verify-firmware.py" --inputs "$work/inputs"
make -C "$work/sources/gpu-unlock" firmware INPUTS="$work/inputs" ASSETS="$work/assets"
python3 "$repo/scripts/verify-firmware.py" "$work/assets"
