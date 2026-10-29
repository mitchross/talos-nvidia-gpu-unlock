# 08 — Optional Proxmox integration

**Start — 2 minutes:** Record guest and host PCI identities separately.

**You are here:** Optional infrastructure · Proxmox.

**Done when:** You have the passthrough map, an independent console, and a machine-specific recovery plan.

**Skip this chapter** on bare metal. Keep the generic early-boot and recovery requirements.

Bare-metal Talos users can skip this chapter.
The early-loader, firmware, signature, and retained-state requirements still apply to their hardware.

## 1. Check passthrough prerequisites

Enable platform IOMMU support and inspect actual isolation groups.
Keep the intended GPU functions bound to VFIO on the host.
Inspect the display and audio functions, parent bridges, and every device affected by a bus reset.
Do not copy another host's physical PCI addresses or assume a reset affects only one VM.

The tested VM used UEFI/OVMF, PCIe passthrough, and a serial console.
Preserve your current CPU, machine type, firmware, boot order, and data-disk mappings.
Record guest and host PCI identities separately.

```bash
# Read-only on the virtualization host.
qm status "$VMID"
qm config "$VMID"
lspci -nnk -s "$HOST_GPU_BDF"
cat "/sys/bus/pci/devices/$HOST_GPU_BDF/reset_method"
```

Inside the Talos workload's NVIDIA container:

```bash
nvidia-smi --query-gpu=uuid,pci.bus_id,name,driver_version --format=csv
```

Record a private table: GPU label, UUID, guest BDF, passthrough mapping, host display/audio functions, parent bridge.
CUDA enumeration order is not a reliable substitute for PCI/UUID mapping.
Public examples use guest addresses `0000:01:00.0` and `0000:02:00.0`; discover yours.

## 2. Capture console and kernel logs

The working UKI included:

```text
console=ttyS0,115200n8
earlycon=uart8250,io,0x3f8,115200n8
ignore_loglevel
loglevel=8
panic=0
```

A VM must already expose a compatible serial device for those arguments to help.
Capture the serial terminal before an approved boot:

```bash
qm terminal "$VMID"
```

This command attaches to an existing console. Do not add a serial device or reboot for documentation alone.
An early barrier failure can prevent the Talos API from starting.
When Talos is reachable, preserve `talosctl dmesg` before log rotation.

The initial successful boot's serial capture was empty; its success evidence came from the Talos kernel log.
Later controlled boots have actual serial transcripts.
Do not relabel a kernel-log excerpt as serial output.
<details>
<summary>Advanced fallback: kernel-specific QMP log recovery</summary>

QMP/HMP monitor recovery was used as a diagnostic fallback; access depends on the VM's configured monitor/socket.
The portable [capture-printk.py](../scripts/capture-printk.py) preserves the actual kernel-specific extractor.
It uses QMP `human-monitor-command` with HMP `memsave`, not guest disk writes.
It reads the relocated `prb` pointer, ring descriptors, metadata, and text using the recorded Linux 6.18.58 layouts.
It sorts records by sequence and preserves exact timestamps and text lengths.
Supply the matching unrelocated symbol address and the actual boot's KASLR offset.
Do not guess either value or reuse a previous boot's offset.
The portable wrapper was syntax-checked; this documentation pass did not dump guest memory again.

```bash
python3 scripts/capture-printk.py --host YOUR_CONFIGURED_PVE_ALIAS \
  --vmid "$VMID" --symbol-address "$PRB_VADDR" --kaslr-offset "$KASLR_OFFSET" \
  --remote-dir "$NEW_PRIVATE_HOST_DIRECTORY" --output "$PRIVATE_PRINTK_LOG"
```

The addresses and layouts are kernel-specific, not a universal QMP memory-extraction procedure.
The host capture directory must be new. Raw guest memory can contain credentials; preserve it privately.
Never publish the raw memory files with the installation guide.

</details>

The serial collector also has a portable wrapper:

```bash
python3 scripts/capture-serial.py --host YOUR_CONFIGURED_PVE_ALIAS \
  --vmid "$VMID" --output "$NEW_PRIVATE_SERIAL_LOG"
```

Use one serial consumer at a time. Empty serial output does not establish that no kernel failure occurred.
Prefer serial logs and supported Talos API logs whenever available.

## 3. Distinguish restart from hardware reset

A guest reboot, PCI FLR, host bridge reset, and physical power removal are different operations.
The pinned unlock path changes privileged state and verifies selector retention through its own FLR.
A subsequent VM boot can therefore see already modified PLM state before a new transaction starts.
Do not interpret that state as a fresh initialization success.

[Upstream issue #208](https://github.com/Zagitta/gpu-unlock/issues/208) reports a similar retained-state failure in a Proxmox guest.
It is corroborating context, not proof that every `-114` has one cause.
The pinned `unlock_610.c` checks PLM eligibility and can return `-EALREADY`.
Its pre/post-FLR selector checks are separate success gates.

> **Reset boundary:** do not copy this case's parent-bus reset onto another host.
> Inspect every device within the actual reset boundary first.

<details>
<summary>The isolated reset sequence observed in this experiment</summary>

For the successful experiment, the stopped VM's isolated GPU bridges supported `reset_subordinate`.
Guards verified the VM was stopped, both functions used VFIO, and no unrelated child device shared the reset boundary.
GPU B was initialized alone, then GPU A was reset and initialized alone while B retained verified selectors.
No automatic reset hook was installed.
A physical host power cycle was neither required nor performed in that successful sequence.

</details>

## 4. Preserve storage clients and data disks

Never recreate or detach persistent data disks as a GPU troubleshooting shortcut.
Before any future shutdown, refresh all clients, mounts, iSCSI sessions, and Longhorn attachments.
Shutdown warnings can affect clients outside the initially protected replica set.
See rollback and known limitations before attempting recovery.

---

[Guide home](../README.md) · **Next — 2 minutes:** [open the offline installation checks](09-installation.md).
