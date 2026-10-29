# 13 — Known limitations and production work

**Start — 2 minutes:** Read the unresolved boot lifecycle before approving production use.

**You are here:** Production boundary · review required.

**Done when:** Your rollout plan covers the unvalidated lifecycle, recovery, and current storage clients.

## 1. Check what was tested

- An external GPU Unlock 2.0 module matched stock Talos Linux 6.18.58-talos.
- Firmware assets existed in the exact early UKI environment and were readable after the path correction.
- The patched early init required fresh success before allowing NVIDIA initialization.
- Separate GPU-specific transactions produced successful unlock records.
- Both original GPUs retained full verified selectors and ran production Qwen inference.

### Reproduction and service checks

- The original corrected diagnostic UKI was reproduced from preserved reference inputs.
- Normal Kubernetes scheduling and vLLM service remained operational during final verification.

Read `evidence/verified-case.json` and `evidence/build-validation.json` for the exact validation scope.

## 2. Check what remains unsolved

The active diagnostic loader targets GPU A only.
GPU B retains a successful unlock from a preceding boot.
The module instance's managed-card lifecycle therefore does not cover both cards symmetrically.
A simultaneous dual-target image and repeatable cold/warm restart are not established by this session.

The desired Omni schematic still refers to the older candidate family.
The corrected diagnostic UKI has not become its managed OCI installer.
Keep the machine locked. Do not enable automatic updates or remove the lock for Kubernetes scheduling.

No fresh Talos installation, bare-metal boot, different GPU model, driver family, or kernel version was validated.
A new local build can have different hashes and still needs its own hardware and boot validation.
Do not treat the portable script syntax checks as a fresh installation test.

The tested path weakens kernel module signature enforcement and does not provide Secure Boot support.
Firmware distribution rights remain a separate review; this repository contains no firmware binaries.
Factory replacement catalogs require maintenance for every served release and architecture.
The native private-backend compatibility patch is local integration code, not a claim of upstream support acceptance.

## 3. Review the production acceptance gates

1. Publish a corrected, immutable, signed installer that includes the proven early path.
2. Reconcile Omni's desired artifact with that exact boot image.
3. Define eligible GPU state and safe handling of selected retained cards.
4. Test dual-card cold start, warm restart, NVIDIA handoff, and recovery.
5. Validate reset isolation on the actual host before considering any pre-start hook.

### Storage and rollout gates

1. Refresh all storage clients and attachments before every approved shutdown.
2. Validate application consistency and recoverable backups separately from replica health.
3. Keep stock recovery and the Omni lock until the lifecycle plan receives review.

These are remaining tasks, not actions performed by this guide finalization.

---

[Guide home](../README.md) · **Next — 2 minutes:** [return to the guide and choose your next stage](../README.md).
