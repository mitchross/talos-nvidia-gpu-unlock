# 09 — Installation sequence and validation boundary

**Start — 2 minutes:** Run offline verification before planning a live boot change.

**You are here:** Installation boundary · build first.

**Done when:** Offline checks pass and a reviewed platform-specific boot and recovery procedure exists.

## 1. Build without changing a running machine

Complete chapters 01–05 in a new local work directory.
Preserve the module, symvers, firmware hashes, build logs, installer archive, diagnostic UKI, and stock recovery image.
Run the offline verification commands before planning maintenance.
Do not run scripts from a directory containing an existing reference output.

```bash
python3 scripts/verify-firmware.py work/assets
modinfo -F vermagic work/kernel/module/gpu_unlock.ko
sha256sum work/installer/diagnostic.efi
python3 scripts/verify-uki.py work/installer/diagnostic.efi work/verify \
  --module work/kernel/module/gpu_unlock.ko
```

> **Stop if:** the selected normal profile contains a wipe argument or conflicting signature settings.

Require one `module.sig_enforce=0`, no `module.sig_enforce=1`, an explicit target, and the firmware search path.
Reject any `talos.experimental.wipe=` argument in the selected normal profile.
The UKI also contains a separate destructive reset-maintenance profile.

<details>
<summary>UKI profile checks and PE inspection details</summary>

GNU objcopy can normalize a PE image while dumping sections.
Inspect a disposable copy when byte-exact preservation matters.
The profile-aware verifier checks normal `main` inheritance rather than treating the final `.cmdline` section as the default.

</details>

## 2. Preserve recovery before selecting a candidate

Save the stock EFI image and a current EFI-partition backup.
Verify the backup hashes and console boot selection while the stock system still works.
Record OS and data-disk identities privately.
Do not choose reset-to-maintenance or reprovisioning as a recovery shortcut.

The original recovery ESP hash is recorded in `sources.lock.json`.
Another installation will have different image contents and partition identifiers.
Do not use this case's whole-disk hash or geometry as your own write target.

## 3. Plan your platform-specific boot

**Tested existing-VM procedure:** stop storage writers, stop the VM, lock it against concurrent host edits, and copy a corrected UKI into a preserved EFI filesystem.
The guarded writer backed up EFI and verified unchanged GPT, META, STATE, and data-disk identities.
It modified only the EFI partition.
The raw-disk writer is intentionally not distributed as a generic installation script.
Its safeguards depended on private machine and disk identities.

<details>
<summary>Offline ESP adaptation; not a validated fresh-install procedure</summary>

For offline inspection, copy an ESP image to a new file and inspect it with mtools:

```bash
cp --reflink=auto YOUR_STOCK_ESP_IMAGE work/test-esp.img
mdir -i work/test-esp.img ::/EFI/Linux
```

The following is a **machine-specific adaptation**, not a validated fresh-install command:

```bash
mcopy -i work/test-esp.img work/installer/diagnostic.efi ::/EFI/Linux/YOUR_TEST_ENTRY.efi
fsck.fat -n work/test-esp.img
```

It changes only the offline copy. It does not install the image or select a boot entry.
Confirm your loader configuration and normal profile before any approved live deployment.
Bare-metal platform profiles, boot managers, and fresh Talos provisioning remain separately unvalidated.
An ISO or installer-image change alone does not prove the corrected UKI is selected by firmware.

</details>

## 4. Initialize only a verified target

The known-good diagnostic selects one explicit guest BDF.
Require a clean, eligible device state and no bound NVIDIA driver before early insertion.
Preserve stock recovery and out-of-band access for the first boot.
Do not repeatedly retry a retained card after `-114`.
The successful two-card state used separate, guarded transactions, not a proven unattended dual-target boot.

## 5. Verify before scheduling production GPU work

Collect the fresh transaction success, early barrier completion, NVIDIA initialization order, UUID mapping, and selector readback.
Then verify vLLM's two GPU processes, Ready status, and a real inference response.
Restore normal scheduling independently of the Omni lock.
Chapter 10 provides read-only verification and idempotent scheduling restoration examples.

Failure recovery: preserve logs and select stock recovery. Do not overwrite the known-good candidate while investigating a new image.

---

[Guide home](../README.md) · **Next — 2 minutes:** [open the three evidence levels](10-verification.md).
