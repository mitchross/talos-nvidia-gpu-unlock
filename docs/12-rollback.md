# 12 — Recover with the stock boot image

**Start — 2 minutes:** Locate the normal stock boot entry before attempting recovery.

**You are here:** Recovery · preserve data disks.

**Done when:** The intended stock boot and required services work, with persistent disk identities preserved.

## 1. Prepare before deployment

Keep an immutable stock UKI/ESP, a current EFI backup, and independent console access.
Record the normal boot entry, filesystem geometry, OS disk, and every data disk privately.
Verify the stored hashes before a maintenance window.
The reference stock hashes in `sources.lock.json` identify this case; they are not your machine's expected disk hashes.

## 2. Recover a barrier failure

1. Preserve serial output and the candidate hash.
2. Use the existing console to select the known-good normal stock boot entry.
3. Do not choose reset-to-maintenance or any wipe profile.
4. If the VM must stop, quiesce all current storage clients before stopping it.
5. Restore only EFI through your verified, machine-scoped procedure when boot selection alone is insufficient.

### Verify recovery before returning service

1. Verify GPT, META, STATE, and all persistent data-disk identities remain unchanged.
2. Start the stock path and verify Talos, NVIDIA, scheduling, storage availability, and inference.

Never recreate the VM, reinitialize a Talos disk, delete a Longhorn replica, or overwrite an entire disk as a shortcut.
The tested guarded writer opened only the OS disk's EFI range for writing.
It never opened the VM's data disks for writing.
Its private disk-identity guards are not replaced here with a generic destructive `dd` command.

## 3. Build a stock-extension installer locally

```bash
python3 scripts/assemble-local.py "$PWD/work" "$PWD/work/rollback" --stock
```

The stock option uses the official imager, omits GPU Unlock, and retains all four official extensions.
It removes the diagnostic customizations instead of preserving the unsigned-module exception.
Do not assume an ordinary Talos upgrade can recover a system that never reaches its API.
Console recovery must already exist.

## 4. Verify normal operation

Require the intended stock boot identity, compatible kernel, normal signature policy, both NVIDIA UUIDs, and runtime configuration.
Restore only temporary scheduling taints or cordoning.
Allow Argo CD to manage vLLM normally.
Verify a real inference response and all required node readiness.
Check application-level consistency separately from Longhorn replica health.

A stock OS boot does not necessarily relock a GPU whose hardware state survived a VM restart.
Do not promise a fresh stock-performance baseline without verifying selectors and physical initialization state.
Keep the Omni lock until the desired image and retained-state lifecycle receive review.

---

[Guide home](../README.md) · **Next — 2 minutes:** [review the remaining production gates](13-known-limitations.md).
