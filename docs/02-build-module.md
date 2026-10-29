# 02 — Build the external kernel module

## What changes

The installed Talos Linux kernel stays stock.
A full local kernel build supplies matching generated headers and `Module.symvers` for an external `gpu_unlock.ko`.
Do not install the locally built Linux kernel on Talos or the builder.
Only the external module enters the extension.

## Commands

```bash
python3 scripts/checkout-sources.py "$PWD/work"
JOBS=8 bash scripts/rebuild-module.sh "$PWD/work" "$PWD/work/kernel"
modinfo -F vermagic "$PWD/work/kernel/module/gpu_unlock.ko"
sha256sum "$PWD/work/kernel/module/gpu_unlock.ko"
```

Expected vermagic:

```text
6.18.58-talos SMP preempt mod_unload modversions
```

The script downloads Linux 6.18.58 and verifies its pinned archive hash.
It applies the pinned Sidero kernel patches, configuration, and certificate inputs.
It combines the pinned Sidero LLVM and tools images using [Dockerfile.toolchain](../scripts/Dockerfile.toolchain).
The actual compiler sequence is:

```bash
make olddefconfig
make -j "$JOBS"
make -j "$JOBS" modules
make -C /src M=/module modules
```

These commands run inside the amd64 tool container with `ARCH=x86` and `LLVM=1`.
The complete Docker commands are preserved in [rebuild-module.sh](../scripts/rebuild-module.sh).

## Validate

Verify `include/config/kernel.release` equals `6.18.58-talos`.
Preserve the full build log, final `.config`, and complete `Module.symvers`.
The reference symvers file is about 1.2 MB; an empty file is invalid.
`modules_prepare` alone does not supply the required symbol CRCs with `CONFIG_MODVERSIONS=y`.

```bash
cat work/kernel/src/include/config/kernel.release
test -s work/kernel/src/Module.symvers
modprobe --dump-modversions work/kernel/module/gpu_unlock.ko
```

`--dump-modversions` reads metadata; it does not insert the module.
Never run plain `modprobe gpu_unlock` or upstream `make install` on the builder.

The working module hash is recorded in `sources.lock.json` as `reference_module_sha256`.
A new build can differ because of paths, timestamps, or build metadata.
Do not treat matching vermagic alone as proof of matching CRCs or successful boot.

## Failures and recovery

`Invalid module format` usually indicates an ABI or vermagic mismatch.
Symbol-version errors indicate incompatible exports or generated headers.
Rebuild from clean pinned inputs in a new output directory.
Restore the stock boot path if insertion blocks early boot.
Do not replace active NVIDIA extensions to make an incompatible module load.
