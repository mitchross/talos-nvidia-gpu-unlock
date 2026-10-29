# GPU Unlock on Talos Linux

This guide reconstructs a working Zagitta GPU Unlock 2.0 integration on Talos v1.14.5.
It keeps the **stock Linux kernel** and adds an ABI-compatible external module plus a synchronous **early initramfs loader**.
The loader finishes before NVIDIA can bind a selected GPU.

**Status:** both RTX 3090s operate unlocked and serve Qwen through vLLM.
The current diagnostic boot initializes one card; the other retains a previous verified unlock.
A repeatable, automatic dual-card cold/warm boot and its Omni lifecycle remain unfinished.
Do not interpret a successful diagnostic session as a production-ready installer.

No firmware, kernel module, boot image, certificate, credential, or private signing key is distributed here.
Download pinned upstream sources and extract licensed firmware locally.

## Choose your path

| Reader | Required sections | Optional sections |
|---|---|---|
| Any Talos operator | 01–05, 09–13 | Factory, Omni, Proxmox |
| Bare-metal Talos | The same module, firmware, signature, and early-ordering requirements | Your platform's installer and console recovery need separate validation |
| Omni operator | Generic sections plus 06–07 | Proxmox |
| Proxmox operator | Generic sections plus 08 | Factory and Omni |

The tested platform profile is `nocloud` on an amd64 VM.
Bare-metal boot and a fresh Talos installation were **not** validated.
This is an evidence-backed diagnostic integration guide, not a universal unattended installation script.

## Installation guide

1. [Prerequisites and validation scope](docs/01-prerequisites.md)
2. [Build the compatible external module](docs/02-build-module.md)
3. [Extract and verify firmware](docs/03-firmware.md)
4. [Package a Talos extension](docs/04-talos-extension.md)
5. [Install the early loader and construct the diagnostic UKI](docs/05-early-boot.md)
6. [Optional Image Factory and private registry](docs/06-image-factory.md)
7. [Optional Omni management](docs/07-omni.md)
8. [Optional Proxmox passthrough and recovery](docs/08-proxmox.md)
9. [Installation sequence and deployment boundary](docs/09-installation.md)
10. [Verify actual GPU use](docs/10-verification.md)
11. [Troubleshoot observed failures](docs/11-troubleshooting.md)
12. [Rollback without deleting storage](docs/12-rollback.md)
13. [Known limitations and production work](docs/13-known-limitations.md)

[Architecture](docs/architecture.md) · [Supporting benchmarks](docs/benchmarks.md) · [Technical write-up](docs/blog.md)

## Pinned implementation

| Component | Version |
|---|---|
| Talos / stock Linux | v1.14.5 / 6.18.58-talos |
| GPU Unlock | 2.0.0, `0532473b4b105ed216948ed9c5aaeab0fa5c734f` |
| NVIDIA production driver | 595.91.07 |
| Firmware extraction source | 610.43.03; this is not the required installed driver version |
| Talos source | `dad8d3edfe7ca381044d7cad259fdf3030efa700` |
| Talos packages | `f4bda77bb9f8202cac8443a7284ce1c7aa129f38` |
| Image Factory source | `45d147aba6b28d66d83a6229f21104d28ddb44a8` |
| Observed Omni | v1.12.4 |

Read [sources.lock.json](sources.lock.json) for tool images, hashes, official extensions, and reference artifact digests.
The published OCI candidate predates the diagnostic firmware-path correction.
Its digest must not be substituted for the working diagnostic UKI hash.

## Quick start: local build only

Run these commands on an amd64 Linux builder with Docker, Go toolchain support, Python, PyYAML, kmod, zstd, patch, and GNU binutils.
They do not upgrade a Talos node.

```bash
python3 scripts/checkout-sources.py "$PWD/work"
JOBS=8 bash scripts/rebuild-module.sh "$PWD/work" "$PWD/work/kernel"
bash scripts/extract-firmware.sh "$PWD/work"
python3 scripts/package-extension.py \
  "$PWD/work/kernel/module/gpu_unlock.ko" "$PWD/work/assets" \
  "$PWD/work/extension" --source "$PWD/work/sources/gpu-unlock"
bash scripts/build-early-imager.sh "$PWD/work" "$PWD/work/early"
python3 scripts/assemble-local.py "$PWD/work" "$PWD/work/installer" \
  --extension-tar "$PWD/work/extension/extension.rootfs.tar"
```

The output includes a base installer and a corrected `diagnostic.efi` sidecar.
The script does **not** silently republish that sidecar as an Omni-managed installer.
Read the installation and rollback chapters before any live boot change.
Do not run upstream `make install` on the builder.

## Reproduction status

The original full kernel/module build, extension packaging, early-loader boot, firmware access, and diagnostic recovery succeeded on existing hardware.
The original reference UKI was reproduced byte-for-byte from preserved inputs.
Portable scripts in this repository are validated separately in [build-validation.json](evidence/build-validation.json).
A fresh installation and a repeatable managed dual-target restart are not claimed.

## Verify this source bundle

```bash
sha256sum --check SHA256SUMS
python3 scripts/validate-guide.py
```

The validator checks local links, Bash examples, YAML/JSON parsing, source-lock relationships, and private-value patterns.
It does not execute installation commands or prove a fresh boot.
