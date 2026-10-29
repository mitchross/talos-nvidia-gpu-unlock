# Making GPU Unlock run before NVIDIA on Talos

**Start — 2 minutes:** read sections 1–2 for the core implementation.

**You are here:** technical story · commands live in the installation chapters.

**Key result:** the early loader established ordering; a system extension alone did not.

## 1. Keep the kernel; change the early execution point

GPU Unlock on Talos required more than placing a kernel module in a system extension.
The working integration kept Talos's stock Linux kernel, built a compatible external module, and changed early init ordering.

Talos's immutable image model helped package the module, firmware, and original NVIDIA support together.
It did not guarantee that an ordinary machine-level module setting ran before NVIDIA.
A small patched `/init` program supplied that ordering point after early mounts and before `machined`.

The loader rejected bound GPUs, enabled signature enforcement, invalid targets, and missing fresh success records.
It inserted the module synchronously and permitted the normal boot only after every selected device succeeded.
That closed barrier turned failures into explicit console-visible stops rather than allowing NVIDIA to bind an uncertain device.

## 2. Make firmware visible before the loader

The first firmware attempt returned `-2` even though the files were inside the exact UKI.
The early kernel lookup did not reach their `/usr/lib/firmware` location.
Adding the correct search path to the diagnostic profile fixed runtime firmware access without changing the kernel or initramfs bytes.
That result depended on the files already being available before the loader.

## 3. Separate image delivery from boot correctness

Image distribution was a separate problem.
A private OCI image was not automatically discoverable through Omni.
The community factory needed a complete replacement catalog, retained signature verification, and an authenticated TLS backend patch.
Stock arm64 images also needed to remain separate from the amd64-only GPU schematic.

## 4. Treat retained GPU state as a separate problem

The most important limitation came from hardware state.
A guest restart did not necessarily restore a fresh GPU initialization state.
A retained PLM state could produce EALREADY and close the barrier.
Separate guarded GPU transactions ultimately produced two verified unlocked cards without a host power cycle.
The current diagnostic boot still initializes only one card while the other retains its preceding successful state.

## 5. Separate measured performance from production readiness

The controlled same-card BF16 gain was 27.8% at 200 W and 39.5% at 250 W.
Real Qwen prefill improved, but decode did not show a demonstrated unlock gain.
The power study favored 200 W for energy and 225 W for an interactive tradeoff.
These measurements support the result; the early boot evidence establishes how it works.

The remaining production task is a reviewed dual-card lifecycle and a corrected managed installer.
Normal scheduling and inference can stay healthy while Omni remains locked against automatic image changes.
The guide therefore preserves both the successful implementation and the boundary it has not yet crossed.

---

[Guide home](../README.md) · **Next — 2 minutes:** [open the tested early-loader implementation](05-early-boot.md).
