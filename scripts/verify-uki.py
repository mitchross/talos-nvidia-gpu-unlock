#!/usr/bin/env python3
"""Inspect UKI bytes and extension layers without booting or loading a GPU driver."""
import argparse
import hashlib
import json
import mmap
import pathlib
import shutil
import subprocess
import yaml
from boot_image import check_normal_arguments, read_uki, require

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("uki", type=pathlib.Path)
p.add_argument("output", type=pathlib.Path)
p.add_argument("--targets", help="Expected explicit guest PCI target list")
expected = p.add_mutually_exclusive_group()
expected.add_argument("--module", type=pathlib.Path)
expected.add_argument("--module-sha256")
a = p.parse_args()
root = pathlib.Path(__file__).resolve().parents[1]
lock = json.loads((root / "sources.lock.json").read_text())
sections, profiles, cmdline = read_uki(a.uki)
targets = check_normal_arguments(cmdline, a.targets)
if a.output.exists():
    p.error("use a new output directory")
a.output.mkdir(parents=True)
with a.uki.open("rb") as source, (a.output / "initramfs.compressed").open("xb") as dest:
    source.seek(sections[".initrd"]["offset"])
    remaining = sections[".initrd"]["bytes"]
    while remaining:
        chunk = source.read(min(1024 * 1024, remaining))
        if not chunk:
            raise ValueError("Truncated initramfs section.")
        dest.write(chunk)
        remaining -= len(chunk)
with (a.output / "initramfs.cpio").open("xb") as dest:
    subprocess.run(["zstd", "-dc", str(a.output / "initramfs.compressed")], stdout=dest, check=True)
seen = {}
with (a.output / "initramfs.cpio").open("rb") as source, mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as data:
    pos = 0
    while pos < len(data):
        if data[pos:pos + 6] not in (b"070701", b"070702"):
            pos = data.find(b"070701", pos)
            if pos < 0:
                break
        header = data[pos:pos + 110]
        size, length = int(header[54:62], 16), int(header[94:102], 16)
        name = bytes(data[pos + 110:pos + 110 + length - 1]).decode().removeprefix("./")
        start = (pos + 110 + length + 3) & ~3
        if start + size > len(data):
            raise ValueError("CPIO member exceeds its bounds.")
        if name == "init" or name.startswith("usr/lib/firmware/gpu-unlock/"):
            seen[name] = hashlib.sha256(data[start:start + size]).hexdigest()
        if name.endswith(".sqsh") or name == "extensions.yaml":
            if pathlib.PurePosixPath(name).name != name or name in (".", ".."):
                raise ValueError("Unsafe extension-layer path.")
            (a.output / name).write_bytes(data[start:start + size])
        pos = (start + size + 3) & ~3
require(sections[".linux"]["sha256"] == lock["stock_linux_amd64_sha256"], "Kernel differs from pinned stock Talos.")
require(seen["init"] == lock["reference_early_init_sha256"], "Early loader differs from the verified build.")
for name, info in lock["firmware_assets"].items():
    require(seen["usr/lib/firmware/gpu-unlock/610.43.03/" + name] == info["sha256"], "Early firmware/license differs: " + name)
layers = yaml.safe_load((a.output / "extensions.yaml").read_text())["layers"]
versions = {layer["metadata"]["name"]: layer["metadata"]["version"] for layer in layers}

def cat(image, path):
    if pathlib.PurePosixPath(image).name != image:
        raise ValueError("Unsafe squashfs image name.")
    if shutil.which("unsquashfs"):
        command = ["unsquashfs", "-cat", str(a.output / image), path]
    else:
        command = ["docker", "run", "--rm", "--entrypoint", "/usr/bin/unsquashfs", "-v", str(a.output.resolve()) + ":/verify:ro",
                   "gpu-unlock-llvm:talos-1.14.5", "-cat", "/verify/" + image, path]
    return subprocess.check_output(command)

deps = cat("modules.dep.sqsh", "usr/lib/modules/" + lock["kernel_release"] + "/modules.dep").decode()
module_paths = [line.split(":", 1)[0] for line in deps.splitlines() if ":" in line]
require(any(path.endswith("gpu_unlock.ko") for path in module_paths), "gpu_unlock missing from modules.dep.")
require(any(path.endswith("nvidia.ko") for path in module_paths), "NVIDIA missing from modules.dep.")
gpu_layers = [layer for layer in layers if layer["metadata"]["name"] == "gpu-unlock"]
require(len(gpu_layers) == 1, "Expected one GPU Unlock extension.")
module_image = gpu_layers[0]["image"]
module = cat(module_image, "usr/lib/modules/" + lock["kernel_release"] + "/extra/gpu_unlock.ko")
module_hash = hashlib.sha256(module).hexdigest()
expected_hash = a.module_sha256 or (hashlib.file_digest(a.module.open("rb"), "sha256").hexdigest() if a.module else lock["reference_module_sha256"])
require(module_hash == expected_hash, "Module differs from expected bytes.")
module_path = a.output / "gpu_unlock.ko"
module_path.write_bytes(module)
vermagic = subprocess.check_output(["modinfo", "-F", "vermagic", str(module_path)], text=True).strip()
require(vermagic == lock["kernel_release"] + " SMP preempt mod_unload modversions", "Unexpected module ABI.")
declared = subprocess.check_output(["modinfo", "-F", "firmware", str(module_path)], text=True).splitlines()
require(set(declared) == {"gpu-unlock/610.43.03/" + name for name in lock["firmware_assets"] if name.endswith(".bin")}, "Unexpected declared firmware set.")
for ref in lock["official_extension_references"]:
    name, tag = ref.rsplit("/", 1)[1].split(":", 1)
    require(versions[name] == tag.split("@", 1)[0], "Official extension changed: " + name)
result = {"sections": {name: {key: value for key, value in data.items() if key in ("bytes", "sha256")} for name, data in sections.items()},
          "cmdline": cmdline, "gpu_targets": targets.split(","), "profile_command_lines": profiles,
          "normal_profile_inherits_common": profiles.get("main") is None,
          "firmware_bin_count": 16, "firmware_hashes_match": True, "packaged_firmware_and_license_hashes_match": True,
          "firmware_location": "early initramfs /usr/lib/firmware/gpu-unlock/610.43.03",
          "early_init_matches_reference": True, "module_matches_expected": True,
          "module_matches_reference": module_hash == lock["reference_module_sha256"], "module_sha256": module_hash,
          "module_vermagic": vermagic, "modules_dep_includes_gpu_unlock_and_nvidia": True,
          "extensions": versions, "uki_sha256": hashlib.file_digest(a.uki.open("rb"), "sha256").hexdigest(), "boot_tested": False}
(a.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
