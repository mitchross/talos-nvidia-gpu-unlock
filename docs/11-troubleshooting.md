# 11 — Failures observed in this implementation

| Symptom | Observed cause or remaining uncertainty | Action |
|---|---|---|
| Firmware error `-2` | Kernel could not find early firmware through its initial search path | Verify exact early assets; add the verified `/usr/lib/firmware` override to the normal UKI profile |
| Error `-114` (`EALREADY`) | PLM eligibility check rejected retained GPU state | Stop blind retries; preserve logs and selectors; review a supported, isolated reset plan |
| Barrier stops boot | Insertion or fresh per-card success verification failed | Recover through console and stock boot; Talos API may never start |
| Signature rejection | Effective enforcement remained enabled | Remove the original `=1` during image construction; verify `N` live |
| Invalid module format or CRC errors | Wrong kernel release, configuration, or symbol versions | Rebuild against exact pinned Talos kernel inputs |
| Wrong or absent PCI target | Host BDF, guest BDF, or CUDA enumeration was confused | Map UUID and guest PCI explicitly; never guess by GPU index |
| Factory download authentication failure | Native proxy did not authenticate to its private registry | Apply the pinned authenticated transport patch and verify CA/keychain configuration |
| GPU schematic on arm64 fails | Custom extension has no arm64 image | Use a separate stock schematic; never silently omit the requested extension |
| Omni desired/running mismatch | Manually corrected diagnostic UKI differs from managed candidate | Keep the machine lock and reconcile through a reviewed image migration |
| Warm reboot fails despite earlier success | GPU hardware state survived guest restart | Distinguish guest reboot, FLR, isolated bridge reset, and physical power removal |
| Drain stalls | Storage replicas or higher-priority GPU workloads block maintenance | Quiesce affected clients; do not force-delete replicas or change cluster-wide drain policy |
| vLLM preempts a benchmark | Argo CD restored its high-priority workload | Use an authorized node-scoped maintenance plan for destructive tests; production runtime benchmarks need no extra Pod |
| iSCSI lost-write/journal warnings | Storage clients were not fully quiesced, including attachments added after a prior boot | Preserve logs, recover applications, and refresh the full attachment map before another shutdown |

The pinned Linux signature setter is enable-only.
A trailing `module.sig_enforce=0` does not neutralize an earlier `=1`.
A successful module insertion does not override a failed per-card transaction.
A selector snapshot does not turn `-114` into a successful fresh initialization.

## Retained-state source checks

Inspect `kernel/gpu_unlock/unlock_610.c` at the pinned upstream commit.
Its GFW PLM eligibility checks can return EALREADY.
Its pre/post-FLR checks require the expected speed selectors.
Read [issue #208](https://github.com/Zagitta/gpu-unlock/issues/208) as a related report, not a universal reset prescription.
Do not patch out the PLM check or weaken the early barrier to make boot proceed.

## Storage incident boundary

An earlier maintenance sequence exposed existing ClickHouse damage and shutdown-time iSCSI/journal warnings.
Later healthy Longhorn volumes and Ready applications established availability, not complete application data integrity.
Additional attachments appeared after the first boot and were missing from an earlier shutdown map.
No mounted RW filesystem repair is part of this guide.
Do not repeat a storage-disruptive experiment to improve documentation.

For all failures, preserve the exact image hash and first failure log before changing an input.
Keep the known-good diagnostic and stock recovery separate from new outputs.
