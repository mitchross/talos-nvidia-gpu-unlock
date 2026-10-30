# GPU Unlock on Talos Linux

**Start with the [simple guide](SIMPLE-GUIDE.md). Allow 5 minutes for the overview, then use the detailed chapters below.**

This guide reconstructs Zagitta GPU Unlock 2.0 on Talos v1.14.5.
Keep the stock Talos kernel. Build a matching external module.
Run GPU Unlock in early initramfs, before NVIDIA binds the selected GPU.

| Working now | Still unfinished |
|---|---|
| Two RTX 3090s serve Qwen through vLLM | Repeatable automatic dual-card cold/warm boot |
| Early loader requires fresh per-target success | Corrected diagnostic UKI as an Omni-managed installer |
| Module, firmware, and boot evidence preserved | Fresh-install and bare-metal validation |

> **Deployment boundary:** the current diagnostic boot initializes one card.
> The second retains a previous verified unlock.
> Keep the Omni machine lock until the managed lifecycle receives review.

## 1. Choose your route

| Your setup | Read | Skip when unused |
|---|---|---|
| Talos without Omni | Build, early boot, installation, verification, recovery | Factory and Omni |
| Bare-metal Talos | The same generic requirements | Proxmox; validate your own boot and console path |
| Omni-managed Talos | Generic chapters plus Factory and Omni | Proxmox if unused |
| Proxmox-hosted Talos | Generic chapters plus Proxmox | Factory and Omni if unused |

The tested platform is an amd64 `nocloud` VM.
This guide reconstructs a successful diagnostic integration. It does not claim a validated unattended fresh installation.

## 2. Follow five stages

Open one stage at a time. Each chapter starts with one action and a completion check.
Time estimates cover reading or preparation, unless a page states otherwise.

1. **Prepare:** [01 — Prerequisites](docs/01-prerequisites.md).
2. **Build locally:** [02 — Module](docs/02-build-module.md) → [03 — Firmware](docs/03-firmware.md) → [04 — Extension](docs/04-talos-extension.md).
3. **Establish boot order:** [05 — Early loader](docs/05-early-boot.md).
4. **Choose optional infrastructure:** [06 — Factory](docs/06-image-factory.md), [07 — Omni](docs/07-omni.md), [08 — Proxmox](docs/08-proxmox.md).
5. **Validate and recover:** [09 — Installation](docs/09-installation.md) → [10 — Verification](docs/10-verification.md).

<details>
<summary>Open recovery and reference pages</summary>

- [11 — Troubleshooting](docs/11-troubleshooting.md): find the observed failure and its next check.
- [12 — Rollback](docs/12-rollback.md): preserve data and select stock recovery.
- [13 — Known limitations](docs/13-known-limitations.md): review the production acceptance work.
- [Architecture](docs/architecture.md): five diagrams and their sources.
- [Benchmarks](docs/benchmarks.md) · [Technical write-up](docs/blog.md): supporting evidence and the implementation story.

</details>

## 3. See the build path

![Source pins become a matching module, extension, early imager, and diagnostic UKI.](diagrams/build.svg)

**Done when:** local checks pass, recovery is preserved, and the remaining boot limitations are understood.
Local build success does not establish hardware boot success.

<details>
<summary>Open the local build command sequence</summary>

Run these commands from the repository root on an amd64 Linux builder.
Provide Docker, Go toolchain support, Python, PyYAML, kmod, zstd, patch, and GNU binutils.
Read chapters 01–05 before starting the full build.

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
The script does **not** publish that sidecar as an Omni-managed installer.
Read installation and rollback before any live boot change.
Do not run upstream `make install` on the builder.

</details>

## 4. Check the tested scope

The original full kernel/module build, extension packaging, early-loader boot, firmware access, and diagnostic recovery succeeded on existing hardware.
The original reference UKI was reproduced byte-for-byte from preserved inputs.
Read [build-validation.json](evidence/build-validation.json) for each portable script's validation scope.

> **Not validated:** a fresh installation or repeatable managed dual-target restart.
> Preserve the working diagnostic image while testing a new output.

<details>
<summary>Open exact versions, source pins, and artifact distinctions</summary>

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


</details>

No firmware, kernel module, boot image, certificate, credential, or private signing key is distributed here.
Extract licensed firmware locally. Review redistribution rights before publishing firmware-containing images.

## 5. Verify this source bundle

Run both commands from the repository root:

```bash
sha256sum --check SHA256SUMS
python3 scripts/validate-guide.py
```

**Pass:** checksums match, links resolve, examples parse, and source pins agree.
The validator does not execute installation commands or prove a fresh boot.

**Next — 2 minutes:** open [01 — Prerequisites](docs/01-prerequisites.md) and check recovery access.
