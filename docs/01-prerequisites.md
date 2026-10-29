# 01 — Prerequisites

**Start — 2 minutes:** Check console access and identify your stock recovery image.

**You are here:** Prepare → build locally.

**Done when:** Your builder tools, compatible stock NVIDIA setup, and recovery path are available.

## 1. Check Talos and recovery

Start with working stock NVIDIA GPU scheduling and inference on Talos.
This guide adds GPU Unlock; it does not bootstrap the GPU Operator or a new Kubernetes cluster.
Use the pinned Talos release, stock kernel ABI, and compatible NVIDIA extensions.
Match the kernel release, configuration, compiler family, and exported symbol CRCs.
A module compiled for a desktop kernel or another Talos release is incompatible.

Provide a console that works before the Talos API starts.
Preserve a known-good stock boot image and its SHA-256 on separate accessible storage.
Disable Secure Boot for this tested unsigned-module diagnostic path.
Do not assume disabling Secure Boot also disables kernel module signature enforcement.

<details>
<summary>Tested GPU scope</summary>

The test hardware was two GA102 RTX 3090 24 GB cards.
Only the documented hardware transactions were verified.
Other GPUs, firmware, kernels, platforms, or VBIOS revisions require their own validation.

</details>

## 2. Check the builder

Use an amd64 Linux desktop for compilation and image assembly.
Provide Git, Docker, Python 3 with PyYAML, GNU make, patch, binutils, kmod, tar, zstd, and crane.
The Go build uses `GOTOOLCHAIN=go1.26.8`.
The package-manager commands differ by distribution; their installation is not automated here.

```bash
git --version
docker version
python3 -c 'import yaml'
modinfo --version
zstd --version
crane version
df -h .
```

Reserve output space based on your filesystem and the full kernel build.
The script defaults to eight compiler jobs. Lower `JOBS` when memory is limited.
Official tool images come from Sidero's upstream registry or an existing mirror.
No GitHub Actions, GHCR account, public artifact publishing, or additional VM is required.
Upstream image downloads still require access to their registry unless already mirrored.

## 3. Choose independent services only if needed

A private registry stores OCI objects independently of the architecture that produced them.
An arm64 factory host can store amd64 artifacts, but cannot execute amd64 binaries natively.
Prebuild heavyweight amd64 artifacts on the builder. Preserve separate stock arm64 support.

Factory, registry, and recovery must remain reachable when Kubernetes is unavailable.
Do not host the only provisioning path behind the cluster it must provision.

## 4. Check the maintenance boundary

Inspect node status, scheduling, workloads, storage attachments, active replicas, and recovery access.
Quiesce every storage client affected by a shutdown, including clients scheduled elsewhere.
Refresh that map after every boot. An earlier attachment snapshot can become stale.
Do not run filesystem repair on mounted RW volumes.

Failure: no independent console or stock recovery path.
Recovery: stop before modifying the boot image. Establish recovery access first.

---

[Guide home](../README.md) · **Next — 2 minutes:** [open the module build commands](02-build-module.md).
