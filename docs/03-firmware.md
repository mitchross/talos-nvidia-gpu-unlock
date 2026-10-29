# 03 — Firmware provenance and early visibility

**Start — 2 minutes:** Check the firmware layout before extracting local assets.

**You are here:** Local build · firmware.

**Done when:** All declared firmware hashes match, and the exact early image can expose their directory.

## 1. Extract locally

The NVIDIA extraction version is 610.43.03.
The running NVIDIA driver is 595.91.07; extraction version and installed driver version serve different purposes.
The upstream source pin provides `fetch_artifacts.py`, `extract_gsp.py`, and `extract_boot_assets.py`.

```bash
bash scripts/extract-firmware.sh "$PWD/work"
python3 scripts/verify-firmware.py --inputs "$PWD/work/inputs"
python3 scripts/verify-firmware.py "$PWD/work/assets"
```

The script downloads two pinned inputs, verifies their recorded hashes, and extracts them without installing the driver.
It executes only the upstream extraction code, not the NVIDIA installer.

## 2. Check the required layout

The extension contains these paths:

```text
rootfs/usr/lib/firmware/gpu-unlock/610.43.03/
  booter_load_ad102.bin      booter_load_ga102.bin
  booter_load_tu102.bin      booter_load_ga100.bin
  falcon_loader.bin         sec2_bl_tu102.bin
  gsp_ga10x.bin             gsp_tu10x.bin
  gsp_boot_ad102.bin        gsp_boot_desc_ad102.bin
  gsp_boot_ga102.bin        gsp_boot_desc_ga102.bin
  gsp_boot_tu102.bin        gsp_boot_desc_tu102.bin
  gsp_boot_ga100.bin        gsp_boot_desc_ga100.bin
  NVIDIA-LICENSE
```

All sixteen module-declared firmware files and the extracted license have hashes in `sources.lock.json`.
GA102 selects `gsp_ga10x.bin` and its family-specific Booter/GSP assets.
Include all declared assets instead of guessing the minimum required subset.

```bash
modinfo -F firmware work/kernel/module/gpu_unlock.ko
```

## 3. Verify early visibility and the `-2` fix

<details>
<summary>Why firmware existed but lookup still failed</summary>

The first early-loader attempt returned `-2` (`ENOENT`) while requesting firmware.
The imager copied all module-declared firmware into direct CPIO entries in the exact early UKI initramfs.
They existed at `/usr/lib/firmware/gpu-unlock/610.43.03/` before switch_root.
The extension also retained its packaged firmware.
Early init mounted the root and bound the early firmware directory into the new root before the custom loader.
The kernel's early lookup path did not reach `/usr/lib/firmware` through `/lib/firmware` at that moment.

</details>

The corrected normal UKI profile adds:

```text
firmware_class.path=/usr/lib/firmware
```

The corrected boot successfully opened the GA102 firmware and completed the unlock.
The correction changed the command line, not the embedded kernel or initramfs.

A path override cannot repair firmware that is absent from early boot.
Verify the exact UKI, embedded extension layers, early mounts, and runtime search directory together.
If firmware appears only after the loader, rebuild the early image instead of adding more path arguments.

## 4. Check redistribution rights

No generated firmware is included in this repository.
The open-module source license does not license NVIDIA firmware.
The extracted NVIDIA agreement includes separate binary distribution conditions.
Local extraction does not establish permission to publish an OCI image containing those bytes.
Review the pinned agreement, notices, and payload licensing before redistribution.
Hashes identify bytes; they do not grant rights.

Failure: missing input, wrong hash, absent declared asset, or inaccessible early path.
Recovery: preserve the failed log, select stock recovery, and regenerate assets in a new local directory.

---

[Guide home](../README.md) · **Next — 2 minutes:** [open the extension packaging command](04-talos-extension.md).
