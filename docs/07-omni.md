# 07 — Optional Omni integration

**Start — 2 minutes:** Compare the desired schematic with the actual running boot image.

**You are here:** Optional infrastructure · Omni.

**Done when:** You can distinguish managed image intent, actual UKI bytes, and the machine lock.

Omni is not required for the module, firmware, or early-loader mechanism.
A standalone Talos operator still needs the matching image and validated recovery path.

## 1. Compare desired and running images

A schematic identifies extensions and image customizations.
An Omni desired schematic is not an attestation of the exact UKI currently executing.
A manually corrected diagnostic UKI can differ from the installer behind that schematic.

Read-only commands used in this implementation:

```bash
omnictl get machinestatus MACHINE_ID -o yaml
omnictl get machineconfiggenoptions MACHINE_ID -o yaml
omnictl get machinesetnode MACHINE_ID -o yaml
```

The lock is the `omni.sidero.dev/locked` annotation on **MachineSetNodes**.
Reading ClusterMachines alone does not establish its presence or absence.
Kubernetes cordoning and taints are independent of this Omni lock.
Do not unlock Omni just to uncordon a node.

## 2. Review the tested staging sequence

The operator first advertised the replacement community catalog and verified its signatures and pulls.
The staging schematic included the extension and official NVIDIA support without activating GPU Unlock.
The candidate schematic added one explicit target and removed signature enforcement.
The worker retained its stock recovery image before activation.
A corrected diagnostic UKI then fixed early firmware lookup outside the original candidate OCI image.

Example schematic files are in `examples/`.
They describe the tested configurations; they are not instructions to apply a live upgrade.
Do not change another machine's schematic or the primary factory endpoint to reproduce a local build.

## 3. Keep the lock across the management gap

The live desired schematic still points to the pre-correction candidate family.
The running corrected diagnostic UKI has not become a replacement, verified OCI installer in the managed lifecycle.
Its kernel arguments include the firmware path and serial diagnostics absent from that original schematic.
The active loader targets GPU A only. GPU B retains its previous verified state.
Automatic updates or blind warm reboots can therefore lose availability or hit the closed barrier.

Keep the machine locked until these artifact checks pass:

1. Encode the corrected early image and command line in a reproducible managed artifact.
2. Publish it by immutable digest and verify signatures and full downloads.
3. Define safe initialization for both fresh and retained GPU states.

Then review the maintenance and reconciliation checks:

1. Test cold and warm VM starts with stock recovery still accessible.
2. Define storage-client quiescence and recovery for every current attachment.
3. Compare Omni's desired resources with the actual running artifact.

No automatic upgrade, endpoint replacement, unlock, or rollout is part of this documentation workflow.
Failure recovery: retain the lock, restore the known-good stock boot, and diagnose desired/running drift before further reconciliation.

---

[Guide home](../README.md) · **Next — 2 minutes:** [open Proxmox recovery if your platform uses it](08-proxmox.md).
