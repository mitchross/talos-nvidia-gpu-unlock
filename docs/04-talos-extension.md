# 04 — Package the Talos extension

**Start — 2 minutes:** Check the four baseline extensions before packaging your module.

**You are here:** Local build · extension.

**Done when:** The amd64 extension passes packaging checks and preserves your existing official extensions.

## 1. Package the local extension

Use the compiled module, verified firmware directory, and pinned upstream source notices.

```bash
python3 scripts/package-extension.py \
  "$PWD/work/kernel/module/gpu_unlock.ko" "$PWD/work/assets" \
  "$PWD/work/extension" --source "$PWD/work/sources/gpu-unlock"
docker image inspect talos-gpu-unlock:2.0.0-v1.14.5-local \
  --format '{{.Architecture}}'
```

Expected architecture: `amd64`.
The package script validates vermagic and every declared firmware path before building.
It includes upstream licenses and firmware provenance notices with the local root filesystem.

```text
manifest.yaml
rootfs/usr/lib/modules/6.18.58-talos/extra/gpu_unlock.ko
rootfs/usr/lib/firmware/gpu-unlock/610.43.03/...
rootfs/usr/local/share/licenses/gpu-unlock/...
```

<details>
<summary>Manifest compatibility and artifact identity</summary>

See [extension-manifest.yaml](../examples/extension-manifest.yaml) and [Dockerfile.extension](../examples/Dockerfile.extension).
The manifest's compatibility constraint is exactly `v1.14.5`.
The local example uses a `local` version suffix; its image digest need not equal the historical reference.
The original verified r2 OCI manifest digest is in `sources.lock.json`.

</details>

## 2. Preserve official extensions

The tested worker requires all four:

- `siderolabs/iscsi-tools`
- `siderolabs/nonfree-kmod-nvidia-production`
- `siderolabs/nvidia-container-toolkit-production`
- `siderolabs/util-linux-tools`

Their exact versions and OCI digests appear in [official-extension-refs.txt](../examples/official-extension-refs.txt).
The observed NVIDIA module entries are in [machine-nvidia.yaml](../examples/machine-nvidia.yaml).
The production workload uses RuntimeClass `nvidia` with handler `nvidia`; see [runtimeclass.yaml](../examples/runtimeclass.yaml).
These are baseline snippets, not permission to replace a running machine configuration.
Merge your existing unrelated modules and preserve device-plugin/runtime configuration.
Do not add GPU Unlock to this late module list.
Discover your own installed extensions before changing an image.
Preserve other machine-specific extensions and NVIDIA runtime configuration.

## 3. Assemble and validate

```bash
python3 scripts/assemble-local.py "$PWD/work" "$PWD/work/installer" \
  --extension-tar "$PWD/work/extension/extension.rootfs.tar"
```

The script exports pinned official extension root filesystems and runs Talos's imager locally.
The imager validates manifests and generates combined module dependency metadata with depmod.
Verify the final image contains `modules.dep`, the NVIDIA modules, the unlock module, and firmware.
Packaging `gpu_unlock.ko` alone does not establish boot order.
The custom imager from chapter 05 supplies the early loader.

Failure: wrong architecture, incompatible manifest, omitted official extension, or missing dependency metadata.
Recovery: discard only the new failed output, fix the inputs, and keep the running stock or known-good boot untouched.

---

[Guide home](../README.md) · **Next — 2 minutes:** [open the early-boot diagram](05-early-boot.md).
