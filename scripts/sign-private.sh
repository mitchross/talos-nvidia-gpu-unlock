#!/usr/bin/env bash
set -euo pipefail
: "${COSIGN_KEY:?Set your private signing key path}"
: "${COSIGN_PUBLIC_KEY:?Set your public verification key path}"
for ref in "$@"; do
 [[ "$ref" == localhost:5000/*@sha256:* ]] || { echo 'Use an immutable private-registry reference.' >&2; exit 2; }
 cosign sign --yes --recursive --key "$COSIGN_KEY" \
  --new-bundle-format=false --use-signing-config=false --tlog-upload=false "$ref"
 # Local-key signatures omit Rekor; TLS and cryptographic verification remain enabled.
 cosign verify --key "$COSIGN_PUBLIC_KEY" \
  --new-bundle-format=false --insecure-ignore-tlog "$ref"
done
