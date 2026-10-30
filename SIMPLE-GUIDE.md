# GPU Unlock on Talos Linux — A Simple Guide

**Start here:** check the tested setup below. Allow 5 minutes to read this overview; build time depends on your computer.

This guide explains how we ran [Zagitta's GPU Unlock](https://github.com/Zagitta/gpu-unlock) on Talos with two RTX 3090 GPUs.
GPU Unlock can increase FP16/BF16 compute throughput.

Talos is immutable, so the usual Ubuntu module-installation method does not apply.
Our solution keeps the stock Talos kernel and runs GPU Unlock **before NVIDIA initializes the selected GPU**.

> **Current limit:** this is a tested diagnostic implementation, not an automatic production installation.
> Fresh-install and repeatable dual-GPU restart procedures remain unvalidated.

## 1. Get your system ready

Our tested setup used:

- Talos v1.14.5 with Linux `6.18.58-talos`.
- Two GA102 NVIDIA RTX 3090 24 GB GPUs.
- NVIDIA 595.91.07 with working Kubernetes GPU scheduling and inference.
- An amd64 Linux builder with the tools in [prerequisites](docs/01-prerequisites.md).
- An independent console and a preserved stock Talos recovery image.

Provide Docker, Git, Python with PyYAML, Go toolchain support, and the other listed build tools.
Do not install GPU Unlock on the builder.

> **Trust boundary:** the tested unsigned-module path disables module signature enforcement and does not support Secure Boot.
> Read [the signature requirements](docs/05-early-boot.md) before planning deployment.

Clone the integration repository:

```bash
git clone -b docs/reproducible-talos-gpu-unlock \
  https://gitea.vanillax.me/vanillax/talos-nvidia-gpu-unlock.git

cd talos-nvidia-gpu-unlock
```

Run the remaining commands from this repository root. Use a new `work/` directory.

**Checkpoint:** stock NVIDIA inference works, and you can reach recovery without the Talos API.

## 2. Build the module, firmware, and extension

### Build a module for this exact kernel

```bash
python3 scripts/checkout-sources.py "$PWD/work"

JOBS=8 bash scripts/rebuild-module.sh \
  "$PWD/work" "$PWD/work/kernel"
```

This produces `work/kernel/module/gpu_unlock.ko` with matching headers and symbol versions.
The full local kernel build does not replace Talos's stock kernel.

Check its kernel identity:

```bash
modinfo -F vermagic work/kernel/module/gpu_unlock.ko
```

Expected output:

```text
6.18.58-talos SMP preempt mod_unload modversions
```

### Extract firmware locally

```bash
bash scripts/extract-firmware.sh "$PWD/work"
python3 scripts/verify-firmware.py "$PWD/work/assets"
```

Firmware comes from NVIDIA 610.43.03 inputs. The extraction script does not install or change the NVIDIA driver.
Review firmware redistribution rights before publishing these assets.

### Package the extension

```bash
python3 scripts/package-extension.py \
  "$PWD/work/kernel/module/gpu_unlock.ko" \
  "$PWD/work/assets" \
  "$PWD/work/extension" \
  --source "$PWD/work/sources/gpu-unlock"
```

**Checkpoint:** packaging verifies vermagic and firmware paths.
Preserve your official extensions; [our four-extension recipe](docs/04-talos-extension.md) may need additions for your worker.

## 3. Make GPU Unlock run before NVIDIA

A system extension alone does not guarantee ordering.
Our patched early init runs before `machined` starts normal NVIDIA initialization.

1. Select explicit guest PCI targets.
2. Check signature settings, device eligibility, and absence of bound drivers.
3. Insert GPU Unlock synchronously.
4. Require a fresh success record for every selected GPU.
5. Permit Talos and NVIDIA to continue.

**Failure closes the barrier.** The Talos API may never start; preserve console access.
An `EALREADY` error (`-114`) is not accepted as successful initialization.

Build the early imager:

```bash
bash scripts/build-early-imager.sh \
  "$PWD/work" "$PWD/work/early"
```

> **Check the target before deployment:** [installer.yaml](examples/installer.yaml) selects `0000:01:00.0` for this diagnostic recipe.
> Discover your own guest PCI addresses. Do not assume CUDA device 0 has that address.
> A different target or platform requires adaptation and validation.

Assemble the image locally:

```bash
python3 scripts/assemble-local.py \
  "$PWD/work" "$PWD/work/installer" \
  --extension-tar "$PWD/work/extension/extension.rootfs.tar"
```

This produces an installer archive and a corrected `work/installer/diagnostic.efi` sidecar.
The sidecar is separate from the OCI installer; the script does not install it on a node.

Verify the corrected sidecar:

```bash
python3 scripts/verify-uki.py work/installer/diagnostic.efi work/verify \
  --module work/kernel/module/gpu_unlock.ko
```

**Checkpoint:** verification passes for the image and its normal boot profile.
Firmware must exist in early initramfs, reachable through `firmware_class.path=/usr/lib/firmware`.
That setting cannot fix assets that appear only later.

## 4. Review the boot procedure before deployment

**This remains the machine-specific part.**
We booted the corrected UKI through Proxmox with stock recovery preserved.
The correction fixed early firmware lookup.

The current boot initializes one GPU; the second retains a previous verified unlock.
Both work, but repeatable dual-target boots remain unvalidated. Retained state can make subsequent initialization fail.

The scripts do not automatically deploy the corrected sidecar through Omni or a normal Talos upgrade.
Read [installation](docs/09-installation.md) and [rollback](docs/12-rollback.md) before planning a live boot change.
Quiesce storage clients before any approved shutdown. Preserve data disks.

> **Do not replace your only working boot image.**
> Keep the Omni machine lock until the corrected managed image and retained-state lifecycle receive review.
> A Kubernetes uncordon does not require removing that lock.

Factory, Omni, and Proxmox are optional; see the [full guide](README.md).
The module, firmware, early-loader, and recovery requirements still apply without them. Bare-metal installation was not validated.

**Checkpoint:** review your boot and recovery plan before changing the live machine.

## 5. Check that it worked

Set `TALOS_NODE` to your configured Talos node address. Inspect its kernel log:

```bash
talosctl -n "$TALOS_NODE" dmesg
```

The expected sequence below is illustrative, not a substitute for preserved logs:

```text
gpu-unlock barrier: inserting module; targets=...
pci <selected-BDF>: gpu_unlock: unlocked
gpu-unlock barrier: complete; targets=...; permitting machined
NVIDIA initialization
```

**GPU Unlock must complete before NVIDIA initializes the selected GPU.**
Require fresh success for every selected target. Old logs or `lsmod` alone do not prove success.

Check Kubernetes readiness:

```bash
kubectl get nodes
```

Run this inside an existing NVIDIA-enabled container **on the Talos worker**, not on the builder or passthrough host:

```bash
nvidia-smi --query-gpu=uuid,pci.bus_id,driver_version,power.limit --format=csv
```

Map each UUID to its guest PCI address. NVIDIA visibility alone does not prove an unlock.
Follow [verification](docs/10-verification.md) to check selectors, workload use, and real inference HTTP 200.

If initialization fails, preserve its first error and select stock recovery. Do not treat `-114` as success.

**Checkpoint:** the boot evidence, GPU identities, verified selectors, and serving workload agree.

<details>
<summary>Supporting evidence: does it help?</summary>

The controlled same-card GPU 2 benchmark measured 8192 × 8192 BF16 GEMM with FP32 accumulation:

| Power limit | Stock BF16 | Unlocked BF16 | Same-card gain |
|---|---:|---:|---:|
| 200 W | 45.00 TFLOPS | 57.50 TFLOPS | 27.8% |
| 250 W | 60.29 TFLOPS | 84.09 TFLOPS | 39.5% |

The separate one-unlocked-card versus both-unlocked Qwen test improved prefill by 14–22% and output throughput by 7–11%.
Decode showed no demonstrated improvement.
Read [benchmarks](docs/benchmarks.md) for controls, baselines, and power-efficiency results.

</details>

<details>
<summary>Remaining work: what prevents automatic production installation?</summary>

The corrected sidecar needs a verified managed installer.
Dual-card cold/warm startup, retained-state handling, and automatic installation require validation.
Read [known limitations](docs/13-known-limitations.md) before approving production integration.

</details>

**Next — 2 minutes:** open [prerequisites](docs/01-prerequisites.md) and check your console and stock recovery access.
