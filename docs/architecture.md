# Architecture

The diagrams describe the tested ordering and remaining management boundary.
The currently selected loader initializes one card; the second retains its prior verified unlock.

## Build pipeline

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

[Rendered SVG](../diagrams/build.svg)

## Early boot sequence

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

[Rendered SVG](../diagrams/boot.svg)

## Registry, factory, and Omni

```mermaid
flowchart LR
  D[amd64 desktop builds and signs] -->|SSH tunnel| R[Private TLS registry on loopback 5000]
  F[Independent arm64 Image Factory host] -->|Backend auth and CA trust| R
  O[Omni catalog and schematic management] -->|Native HTTPS 8443| F
  T[Talos installer downloads] -->|Native HTTPS OCI proxy| F
  F --> S[Separate stock arm64 schematic]
  F --> G[amd64 GPU schematic]
```

[Rendered SVG](../diagrams/factory.svg)

## Passthrough to vLLM

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

[Rendered SVG](../diagrams/passthrough.svg)

## Failure and recovery

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

[Rendered SVG](../diagrams/recovery.svg)

GPU schematics are amd64-only. Stock arm64 uses a separate schematic.
The management services remain independent of Kubernetes availability.
Rendered SVGs sit beside their Mermaid sources in `diagrams/`.
