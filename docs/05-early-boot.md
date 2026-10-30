# 05 — The early initramfs loader

**Start — 2 minutes:** Trace the boot diagram from early mounts to NVIDIA.

**You are here:** Boot order · required.

**Done when:** The exact normal UKI has the loader, early firmware, signature setting, and explicit PCI target.

![Early boot checks every selected GPU before permitting machined and NVIDIA.](../diagrams/archify/boot.png)

[Explore the interactive boot and recovery diagram](../diagrams/archify/README.md).

This is the essential integration. A normal system extension alone is insufficient.

## 1. Locate the execution point

The patch changes Talos `internal/app/init/main.go`.
It calls `gpuunlock.Boot(constants.NewRoot)` after the root filesystem and firmware mounts exist.
It runs before `switchroot.Switch` starts the real root and `machined`.
NVIDIA's normal module configuration runs later.

The kernel remains the stock Talos kernel.
Only the initramfs `/init` program changes.
The module comes from the extension layers mounted under the new root.
The imager also copies module-declared firmware into direct early CPIO entries at `/usr/lib/firmware`.
The loader opens `/root/usr/lib/modules/6.18.58-talos/extra/gpu_unlock.ko`; the kernel searches the early root for firmware.
The firmware bind runs from the early directory into the new root, not from a late service into early init.

Read the actual [loader patch](../patches/talos-early-loader.patch), including its tests.

<details>
<summary>Why a late module list cannot establish this ordering</summary>

`machine.kernel.modules` is handled after early init and cannot implement this barrier.
Putting GPU Unlock first in a YAML list does not prove it finishes before NVIDIA binds.
An initramfs extension and correct firmware paths are necessary, but the early execution point and fresh-success barrier provide ordering.

</details>

## 2. Check the barrier contract

1. Select explicit guest PCI targets.
2. Check signature policy, device eligibility, and driver absence.
3. Insert GPU Unlock synchronously.
4. Require fresh success for every selected GPU.
5. Permit `machined`; NVIDIA initializes afterward.

<details>
<summary>Open all barrier checks, in execution order</summary>

### Select the transaction

1. Parse exactly one `gpu_unlock.targets=` command-line argument.
2. If absent, preserve the normal boot path without inserting GPU Unlock.
3. Discover supported NVIDIA PCI devices from sysfs.
4. Reject empty, absent, malformed, unsupported, or duplicate selected addresses.

### Check the preconditions

1. Require `/sys/module/module/parameters/sig_enforce` to report `N`.
2. Require NVIDIA, nouveau, and GPU Unlock to be absent.
3. Require each selected device to have no bound driver.

### Insert and verify

1. Drain existing kernel messages, then call `finit_module` synchronously.
2. Pass `targets=...` explicitly to the module.
3. Require a fresh exact `pci <BDF>: gpu_unlock: unlocked` record for every selected device.
4. Permit `machined` only after every check succeeds.

</details>

A zero module insertion return is insufficient because per-card failures can still occur.
Old log records cannot satisfy the fresh-message barrier.
`EALREADY` is never converted into success.
Failure returns an early-init error and stops normal boot before the Talos API becomes available.
The diagnostic `panic=0` setting keeps the failure available for console inspection.

The current working argument selects only `0000:01:00.0`.
The second card retains its separate successful initialization.
The parser supports an explicit list or `all`; that does not prove a repeatable two-card restart.
Do not change targets blindly on retained hardware.

## 3. Build the early imager

```bash
bash scripts/build-early-imager.sh "$PWD/work" "$PWD/work/early"
sha256sum work/early/init-amd64
```

The script archives pinned Talos source, applies the patch, runs its race-enabled tests, and builds amd64 `/init`.
It extracts stock initramfs bytes from the pinned official imager.
It verifies the stock initramfs hash, replaces only `/init`, and builds a local imager image.
The stock asset is named `initramfs.xz` but its recorded stream uses zstd; use `zstd -dc` for this pin.
Do not infer the compression format from the suffix.

The Go build disables VCS embedding because an archive has no Git metadata.
This prevents the surrounding guide repository from contaminating the init binary's build identity.
The reference early-init hash is in `sources.lock.json`.

## 4. Remove effective signature enforcement

The stock configuration has `CONFIG_MODULE_SIG_FORCE=n`, but the normal boot command line enforces signatures.
The diagnostic construction removes the original enforcement argument and supplies exactly:

```text
module.sig_enforce=0
```

In imager/schematic customization, `-module.sig_enforce` is removal syntax, not a literal Linux argument.
Appending `=0` after an existing `=1` cannot clear this kernel's enable-only enforcement setting.
Verify the final UKI command line and the live sysfs value.
This exception weakens module trust and does not constitute a Secure Boot solution.

## 5. Embed corrected arguments in the installer

The historical test patched a separate diagnostic UKI after assembly.
The current [assembler](../scripts/assemble-local.py) puts the correction directly into the imager profile.
It requires `--targets` with explicit guest PCI addresses and adds the early firmware search path before the UKI is built.
Talos then packages that UKI inside the installer at `usr/install/amd64/vmlinuz.efi`.
No post-build UKI patch is required for the new installer.

The assembler automatically runs [verify-installer.py](../scripts/verify-installer.py) against the resulting archive.
It validates image integrity and extracts the actual packaged UKI before checking its contents.
The normal profile must contain exactly one target argument, one `module.sig_enforce=0`, and the firmware search path.
It must not contain a wipe argument.

[patch-reference-uki.py](../scripts/patch-reference-uki.py) and [reference replay](../scripts/replay-reference.py) remain for historical evidence.
The original known-good UKI hash remains `9a43833365fb36f7d90126054dc7cc6b34f8fe3170f3ac9a67db898b4a666910`.
New native imager outputs have distinct hashes and require their own boot validation.

Recovery: select the preserved stock boot entry through the out-of-band console.
Do not select reset-to-maintenance or an entry that wipes STATE/EPHEMERAL.

---

[Guide home](../README.md) · **Next — 2 minutes:** [open the installation validation boundary](09-installation.md).
