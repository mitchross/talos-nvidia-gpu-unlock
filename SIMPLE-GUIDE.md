# GPU Unlock on Talos — Build, install, check

**Start here:** choose your guest GPU PCI addresses. Read this page in about 3 minutes.
The image build is validated offline. Fresh installation and dual-GPU cold/warm boots are **not validated**.

## 1. Prepare a supported test system

Use Talos v1.14.5, kernel `6.18.58-talos`, compatible NVIDIA extensions, and an amd64 Linux builder.
The example targets `nocloud` VMs with UEFI and Secure Boot disabled.
Keep a stock recovery image and independent console access. Review [prerequisites](docs/01-prerequisites.md).
These commands compile locally; they do not install GPU Unlock on the builder.

```bash
git clone \
  https://github.com/mitchross/talos-nvidia-gpu-unlock.git
cd talos-nvidia-gpu-unlock
export GPU_TARGETS='0000:02:00.0'
```

Replace the example with your **guest** PCI address. For two targets, use `0000:01:00.0,0000:02:00.0`.
No address is assumed by the builder. Duplicate addresses and `all` are rejected.

## 2. Build the module, firmware, and extension

Run from the repository root with a new `work/` directory:

```bash
python3 scripts/checkout-sources.py "$PWD/work"
JOBS=8 bash scripts/rebuild-module.sh "$PWD/work" "$PWD/work/kernel"
bash scripts/extract-firmware.sh "$PWD/work"
python3 scripts/package-extension.py \
  "$PWD/work/kernel/module/gpu_unlock.ko" "$PWD/work/assets" \
  "$PWD/work/extension" --source "$PWD/work/sources/gpu-unlock"
bash scripts/build-early-imager.sh "$PWD/work" "$PWD/work/early"
```

**Checkpoint:** the module matches the stock kernel. Firmware extraction does not change the installed NVIDIA driver.

## 3. Assemble and verify the deployable installer

```bash
python3 scripts/assemble-local.py "$PWD/work" "$PWD/work/installer" \
  --extension-tar "$PWD/work/extension/extension.rootfs.tar" --targets "$GPU_TARGETS"
cat work/installer/verification/report.json
```

The output is `work/installer/installer-amd64.tar`, containing the corrected UKI at `usr/install/amd64/vmlinuz.efi`.
The firmware path and target arguments are embedded during assembly. No separate EFI patch or manual copy is required.
The automatic verifier checks the **archive's own UKI**, early loader, module, 16 firmware files, license, and official extensions.
It also checks target arguments, signature policy, dependency metadata, and absence of wipe arguments in the normal profile.
**Checkpoint:** verification passes. This proves image contents, not a successful hardware boot.

## 4. Publish and install during an approved test window

Configure an authenticated TLS registry reachable by the test node; see [registry setup](docs/06-image-factory.md).
Review firmware redistribution rights before publishing. Use a new immutable tag for each target selection.

```bash
export INSTALLER_REF='registry.example.invalid/talos/gpu-unlock:v1.14.5-test'
crane push work/installer/installer-amd64.tar "$INSTALLER_REF"
export INSTALLER_IMAGE="$INSTALLER_REF@$(crane digest "$INSTALLER_REF")"
```

For an **existing standalone UEFI Talos node**, use a v1.14.5 client during approved maintenance:

```bash
talosctl -n "${TEST_NODE:?Set an approved test node}" upgrade --image "$INSTALLER_IMAGE"
```

**This command changes the node and reboots it.** Quiesce affected storage clients and preserve recovery before running it.
Do not run it on the protected production GPU worker. Omni-managed rollout requires separate review; keep its machine lock.
Fresh provisioning can reference this image through `machine.install.image`, but that path has not been tested here.
A retained GPU may fail with `-114`. Do not treat that error as success or retry resets blindly.

## 5. Verify the boot and workload

```bash
talosctl -n "$TEST_NODE" dmesg
kubectl get nodes
```

Require fresh `gpu_unlock: unlocked` for every selected target, then barrier completion, then NVIDIA initialization.
Inside an existing NVIDIA container on that worker, verify UUIDs and PCI mapping with `nvidia-smi`.
Check real inference HTTP 200; see [verification](docs/10-verification.md). NVIDIA visibility alone does not prove an unlock.
On failure, preserve the first error and select [stock recovery](docs/12-rollback.md). Never choose a wipe profile.

Advanced references: [installation details](docs/09-installation.md) · [limitations](docs/13-known-limitations.md) · [optional diagrams](diagrams/archify/README.md).

**Next — 2 minutes:** check your stock recovery and guest PCI mapping before starting the build.
