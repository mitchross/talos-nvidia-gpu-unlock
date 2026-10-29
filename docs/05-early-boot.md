# 05 — The early initramfs loader

This is the essential integration. A normal system extension alone is insufficient.

## Exact insertion point

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

## Barrier contract

1. Parse exactly one `gpu_unlock.targets=` command-line argument.
2. If absent, preserve the normal boot path without inserting GPU Unlock.
3. Discover supported NVIDIA PCI devices from sysfs.
4. Reject empty, absent, malformed, unsupported, or duplicate selected addresses.
5. Require `/sys/module/module/parameters/sig_enforce` to report `N`.
6. Require NVIDIA, nouveau, and GPU Unlock to be absent.
7. Require each selected device to have no bound driver.
8. Drain existing kernel messages, then call `finit_module` synchronously.
9. Pass `targets=...` explicitly to the module.
10. Require a fresh exact `pci <BDF>: gpu_unlock: unlocked` record for every selected device.
11. Permit `machined` only after every check succeeds.

A zero module insertion return is insufficient because per-card failures can still occur.
Old log records cannot satisfy the fresh-message barrier.
`EALREADY` is never converted into success.
Failure returns an early-init error and stops normal boot before the Talos API becomes available.
The diagnostic `panic=0` setting keeps the failure available for console inspection.

The current working argument selects only `0000:01:00.0`.
The second card retains its separate successful initialization.
The parser supports an explicit list or `all`; that does not prove a repeatable two-card restart.
Do not change targets blindly on retained hardware.

## Build the early imager

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

## Signature enforcement

The stock configuration has `CONFIG_MODULE_SIG_FORCE=n`, but the normal boot command line enforces signatures.
The diagnostic construction removes the original enforcement argument and supplies exactly:

```text
module.sig_enforce=0
```

In imager/schematic customization, `-module.sig_enforce` is removal syntax, not a literal Linux argument.
Appending `=0` after an existing `=1` cannot clear this kernel's enable-only enforcement setting.
Verify the final UKI command line and the live sysfs value.
This exception weakens module trust and does not constitute a Secure Boot solution.

## Correct the diagnostic UKI

The tested diagnostic fixed firmware lookup and added serial diagnostics after base image assembly.
[assemble-local.py](../scripts/assemble-local.py) preserves that workflow:

- Build a base installer with the custom early imager and all extensions.
- Extract its `usr/install/amd64/vmlinuz.efi` into a new file.
- Apply [patch-reference-uki.py](../scripts/patch-reference-uki.py) to produce `diagnostic.efi`.
- Preserve `.linux` and `.initrd` bytes while correcting the normal command line.
- Refuse wipe arguments or contradictory signature settings.

The OCI installer itself remains unchanged. `diagnostic.efi` is a sidecar.
The original known-good UKI hash is `9a43833365fb36f7d90126054dc7cc6b34f8fe3170f3ac9a67db898b4a666910`.
A source rebuild with different extension metadata can produce a different UKI hash.
[Reference replay](../scripts/replay-reference.py) checks byte-exact reproduction only when the exact preserved base archive is supplied.
That private base archive is not distributed here.

## Why late loading fails

`machine.kernel.modules` is handled after early init and cannot implement this barrier.
Putting GPU Unlock first in a YAML list does not prove it finishes before NVIDIA binds.
An initramfs extension and correct firmware paths are necessary, but the early execution point and fresh-success barrier provide ordering.

Recovery: select the preserved stock boot entry through the out-of-band console.
Do not select reset-to-maintenance or an entry that wipes STATE/EPHEMERAL.
