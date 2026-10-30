#!/usr/bin/env python3
"""Assemble an installer whose embedded UKI already has the required boot arguments."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import tarfile
import yaml
from boot_image import parse_targets

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("work", type=pathlib.Path)
p.add_argument("output", type=pathlib.Path)
p.add_argument("--official-dir", type=pathlib.Path)
p.add_argument("--extension-tar", type=pathlib.Path)
p.add_argument("--targets", help="Explicit guest PCI addresses, comma-separated; required for a GPU installer")
p.add_argument("--stock", action="store_true")
a = p.parse_args()
if a.stock and a.targets is not None:
    p.error("--targets is not allowed with --stock")
if not a.stock:
    if not a.targets:
        p.error("a GPU installer requires --targets; no PCI address is assumed")
    try:
        a.targets = parse_targets(a.targets)
    except ValueError as error:
        p.error(str(error))
    if not a.extension_tar or not a.extension_tar.is_file():
        p.error("provide an existing --extension-tar")
if not a.output.is_absolute() or a.output.exists():
    p.error("use a new absolute output directory")
root = pathlib.Path(__file__).resolve().parents[1]
lock = json.loads((root / "sources.lock.json").read_text())
module_hash = None
if not a.stock:
    with tarfile.open(a.extension_tar) as archive:
        members = [m for m in archive.getmembers() if m.name.lstrip("./") == "rootfs/usr/lib/modules/" + lock["kernel_release"] + "/extra/gpu_unlock.ko"]
        if len(members) != 1 or not members[0].isfile():
            p.error("extension must contain one regular gpu_unlock.ko at the matching kernel path")
        module_hash = hashlib.file_digest(archive.extractfile(members[0]), "sha256").hexdigest()
a.output.mkdir(parents=True)
official = a.official_dir or a.work / "official"
official.mkdir(parents=True, exist_ok=True)
tarballs = []
for ref in lock["official_extension_references"]:
    name = ref.split("/")[-1].split(":")[0]
    target = official / (name + ".rootfs.tar")
    if not target.exists():
        subprocess.run(["crane", "export", "--platform", "linux/amd64", ref, str(target)], check=True)
    tarballs.append(target.resolve())
if not a.stock:
    tarballs.append(a.extension_tar.resolve())
profile = yaml.safe_load((root / "examples/installer.yaml").read_text())
profile["input"]["systemExtensions"] = [{"tarballPath": "/inputs/" + str(i) + ".tar"} for i in range(len(tarballs))]
if a.stock:
    profile.pop("customization", None)
else:
    args = profile["customization"]["extraKernelArgs"]
    if any(arg.startswith("gpu_unlock.targets=") for arg in args):
        p.error("remove fixed GPU targets from the profile; supply --targets instead")
    args.append("gpu_unlock.targets=" + a.targets)
(a.output / "profile.yaml").write_text(yaml.safe_dump(profile, sort_keys=False))
command = ["docker", "run", "--rm", "-i", "--privileged", "--network", "host", "-v", str(a.output) + ":/out"]
for i, path in enumerate(tarballs):
    command += ["-v", str(path) + ":/inputs/" + str(i) + ".tar:ro"]
command += [lock["tool_images"]["imager"] if a.stock else "talos-gpu-unlock-imager:local", "-"]
with (a.output / "build.log").open("w") as log:
    subprocess.run(command, input=yaml.safe_dump(profile).encode(), stdout=log, stderr=subprocess.STDOUT, check=True)
archives = list(a.output.glob("*.tar"))
if len(archives) != 1:
    raise ValueError("Expected exactly one installer archive.")
if not a.stock:
    subprocess.run(["python3", str(root / "scripts/verify-installer.py"), str(archives[0]), str(a.output / "verification"),
                    "--targets", a.targets, "--module-sha256", module_hash], check=True)
(a.output / "SHA256SUMS").write_text("".join(hashlib.file_digest(f.open("rb"), "sha256").hexdigest() + "  " + f.name + "\n" for f in archives))
print("Stock installer complete; GPU Unlock and its custom arguments are omitted." if a.stock else
      "Installer complete. Its embedded UKI contains the requested GPU targets and early firmware path.")
print("No node was installed, upgraded, or booted.")
