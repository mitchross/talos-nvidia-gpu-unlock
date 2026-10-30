# Architecture

**Start — 2 minutes:** follow the early-boot diagram before reading the source patches.

**You are here:** visual reference · five system views.

**Done when:** you can locate the early barrier and the remaining managed-image gap.

**Interactive views:** [open the Archify diagram index](../diagrams/archify/README.md).
The five Mermaid views below remain available as static references.

The diagrams describe the tested ordering and remaining management boundary.
The currently selected loader initializes one card; the second retains its prior verified unlock.

## 1. Build pipeline

![Build pipeline](../diagrams/build.svg)

<details>
<summary>Open Mermaid source</summary>

```mermaid
flowchart LR
  A[GPU Unlock source pin] --> B[External module]
  K[Pinned Linux and Sidero config] --> C[Full local kernel build]
  C --> S[Headers and Module.symvers]
  S --> B
  F[NVIDIA inputs extracted locally] --> E[amd64 extension rootfs]
  B --> E
  T[Pinned Talos source plus loader patch] --> I[Early init binary]
  I --> M[Local custom imager]
  E --> M
  N[All required official extensions] --> M
  M --> O[Base installer archive]
  O --> P[Corrected diagnostic UKI sidecar]
  X[Stock Talos Linux binary stays unchanged] -.-> M
```

</details>

## 2. Early boot sequence

![Early boot sequence](../diagrams/boot.svg)

<details>
<summary>Open Mermaid source</summary>

```mermaid
flowchart TD
  A[UEFI selects diagnostic UKI] --> B[Stock kernel and embedded initramfs]
  B --> C[Early init mounts root and extension layers]
  C --> D[Bind firmware before custom loader]
  D --> E{Explicit GPU target argument?}
  E -->|Absent| H[Switch root and start machined]
  E -->|Present| F[Check signatures, targets, and no bound driver]
  F --> G[Synchronous finit_module with targets parameter]
  G --> V{Fresh success for every selected GPU?}
  V -->|Yes| H
  V -->|No| Z[Closed barrier; preserve console failure]
  H --> J[NVIDIA initializes GPUs]
  J --> Q[Verify UUIDs and selectors]
  Q --> W[vLLM CUDA inference]
```

</details>

## 3. Registry, factory, and Omni

![Registry, factory, and Omni](../diagrams/factory.svg)

<details>
<summary>Open Mermaid source</summary>

```mermaid
flowchart LR
  D[amd64 desktop builds and signs] -->|SSH tunnel| R[Private TLS registry on loopback 5000]
  F[Independent arm64 Image Factory host] -->|Backend auth and CA trust| R
  O[Omni catalog and schematic management] -->|Native HTTPS 8443| F
  T[Talos installer downloads] -->|Native HTTPS OCI proxy| F
  F --> S[Separate stock arm64 schematic]
  F --> G[amd64 GPU schematic]
```

</details>

## 4. Passthrough to vLLM

![Passthrough to vLLM](../diagrams/passthrough.svg)

<details>
<summary>Open Mermaid source</summary>

```mermaid
flowchart LR
  A[Physical GPU A] --> V[VFIO and isolated PCI functions]
  B[Physical GPU B] --> V
  V --> P[Proxmox VM with UEFI and serial console]
  P --> T[Early barrier initializes selected GPU A]
  T --> N[NVIDIA driver and container runtime]
  R[GPU B retains its preceding verified unlock] --> N
  N --> K[Kubernetes GPU allocation]
  K --> W[vLLM TP2 on both verified GPU UUIDs]
  M[Omni machine lock] -. management guard .-> P
```

</details>

## 5. Failure and recovery

![Failure and recovery](../diagrams/recovery.svg)

<details>
<summary>Open Mermaid source</summary>

```mermaid
flowchart TD
  A[Select candidate with stock recovery preserved] --> B[Early initialization]
  B --> C{Fresh transaction and handoff succeed?}
  C -->|Yes| D[Verify NVIDIA, selectors, scheduling, inference]
  C -->|No| E[Barrier stops before Talos API]
  E --> F[Capture serial or recovered kernel evidence]
  F --> G[Select normal stock boot through console]
  G --> H[Preserve every data disk and restore services]
  D --> I[Keep Omni lock until lifecycle review]
  H --> I
  R[Retained GPU state on a warm restart] -. can fail .-> B
  I --> J[No automatic retry or host power cycle]
```

</details>

GPU schematics are amd64-only. Stock arm64 uses a separate schematic.
The management services remain independent of Kubernetes availability.
Rendered SVGs sit beside their Mermaid sources in `diagrams/`.

<details>
<summary>Render all five diagram sources locally</summary>

### Render the Mermaid sources

Use a headless Chromium configuration at `PUPPETEER_CONFIG`.
The recorded local renderer was Mermaid CLI 11.12.0.

```bash
PUPPETEER_SKIP_DOWNLOAD=1 npm exec --yes --package=@mermaid-js/mermaid-cli@11.12.0 -- \
  mmdc -p "$PUPPETEER_CONFIG" -i diagrams/boot.mmd -o diagrams/boot.svg
```

Repeat for the other four source files. Rendering does not contact Talos or change a VM.

</details>

---

[Guide home](../README.md) · **Next — 2 minutes:** [open the early-loader insertion point](05-early-boot.md).
