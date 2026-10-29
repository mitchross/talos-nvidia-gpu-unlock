# 10 — Verify the running implementation

**Start — 2 minutes:** Identify the three evidence levels before checking a running worker.

**You are here:** Verification · packaged → executed → in use.

**Done when:** Boot logs, UUIDs, selectors, NVIDIA use, scheduling, and real inference agree.

Keep these three evidence levels separate.

| Level | Evidence | What it does not prove |
|---|---|---|
| Packaged | Module, firmware, `/init`, manifest, and hashes inside the exact image | That firmware selected this image or the unlock ran |
| Executed | Fresh per-target success, post-FLR selectors, barrier completion before NVIDIA | That a later restart is repeatable |
| In use | Same GPU UUIDs in NVIDIA/vLLM, current selector readback, inference HTTP 200 | A guaranteed performance gain for every model |

The module need not stay loaded after early boot.
`lsmod` alone is not an unlock verification strategy.

## 1. Check Talos and boot identity

```bash
talosctl -n "$TALOS_NODE" version
talosctl -n "$TALOS_NODE" read /proc/cmdline
talosctl -n "$TALOS_NODE" read /sys/module/module/parameters/sig_enforce
talosctl -n "$TALOS_NODE" get extensions -o yaml
talosctl -n "$TALOS_NODE" dmesg > kernel.log
```

Expected in the verified case: Talos v1.14.5, Linux 6.18.58-talos, signature value `N`, and all four official extensions plus GPU Unlock.
Record the selected firmware boot entry and hash its actual UKI bytes through a read-only platform path.
A matching schematic or a filename alone is not a UKI checksum.
The preserved current diagnostic hash appears in `sources.lock.json`.

Require this sequence in the boot log:

```text
gpu-unlock barrier: inserting module; targets=...
pci <selected-BDF>: gpu_unlock: unlocked
gpu-unlock barrier: complete; targets=...; permitting machined
NVIDIA initialization
```

Use actual preserved messages, not this schematic excerpt, as evidence.
The current working boot freshly initializes GPU A only.
GPU B has a prior successful transaction and current verified retained selectors.
Do not invent a fresh GPU B success record in the current boot.

## 2. Verify identities and actual workload use

Run NVIDIA commands inside an existing authorized NVIDIA container on the GPU worker.
Do not run them on a passthrough host or an AMD-only builder.

```bash
kubectl exec -n "$GPU_NAMESPACE" "$NVIDIA_POD" -- \
  nvidia-smi --query-gpu=uuid,pci.bus_id,driver_version,power.limit,enforced.power.limit --format=csv
kubectl exec -n "$GPU_NAMESPACE" "$NVIDIA_POD" -- \
  nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory --format=csv
```

The verified service uses both original UUIDs, NVIDIA 595.91.07, and 200 W limits.
A process name can appear as `[Not Found]` across container PID namespaces.
Correlate its PID with the vLLM engine worker processes and its GPU UUID; do not infer CPU fallback from that name.
Tensor Core execution was recorded in the preserved FP16/BF16/TF32 profiler evidence.
No new stress test is needed solely to collect documentation.

<details>
<summary>Read-only GA102 selector interpretation</summary>

For the tested GA102 recipe, post-boot readback expects SS0 `0x88888888` and SS1 `0x8`.
Both verified cards also reported PLM `0xffffffff`.
`read-ga102-selectors.py` uses read-only BAR mapping at the pinned recipe's offsets.
Use it only on the verified device family with an already authorized diagnostic container.
It is not a preboot permission to ignore EALREADY, and arbitrary all-ones MMIO reads do not prove success.

</details>

## 3. Check scheduling and inference

```bash
kubectl get nodes
kubectl get node "$GPU_NODE" -o json
kubectl get pods -n "$VLLM_NAMESPACE" -o wide
```

### Restore scheduling only when required

Only when the inspected node is cordoned:

```bash
kubectl uncordon "$GPU_NODE"
```

Only when that exact experiment taint is present:

```bash
kubectl taint node "$GPU_NODE" gpu-unlock-bench=reserved:NoSchedule-
```

Preserve all unrelated taints and permanent NVIDIA runtime settings.
Do not remove the Omni lock or disable Argo CD for scheduling restoration.
In this finalization, the node was already uncordoned and untainted, so no scheduling mutation was needed.

### Confirm a real inference response

```bash
curl --fail-with-body "$VLLM_URL/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.8-27b","messages":[{"role":"user","content":"Reply OK."}],"max_tokens":8,"temperature":0,"chat_template_kwargs":{"enable_thinking":false}}'
```

Use your deployment's authentication mechanism when required. Never commit its token.
Require HTTP 200 and a real completion, not just a successful TCP connection.
Failure recovery: preserve the working boot, diagnose identity or scheduling evidence, and avoid a reboot solely for documentation.

---

[Guide home](../README.md) · **Next — 2 minutes:** [find the first observed error if a check failed](11-troubleshooting.md).
