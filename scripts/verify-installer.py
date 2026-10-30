#!/usr/bin/env python3
"""Validate and inspect the UKI inside a Docker installer archive; never execute its installer."""
import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import tarfile
from boot_image import parse_targets, require

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("archive", type=pathlib.Path)
p.add_argument("output", type=pathlib.Path)
p.add_argument("--targets", required=True)
expected = p.add_mutually_exclusive_group()
expected.add_argument("--module", type=pathlib.Path)
expected.add_argument("--module-sha256")
a = p.parse_args()
try:
    a.targets = parse_targets(a.targets)
except ValueError as error:
    p.error(str(error))
if a.output.exists():
    p.error("use a new output directory")
subprocess.run(["crane", "validate", "--tarball", str(a.archive)], check=True)
image_digest = subprocess.check_output(["crane", "digest", "--tarball", str(a.archive)], text=True).strip()
a.output.mkdir(parents=True)
asset_path = "usr/install/amd64/vmlinuz.efi"
asset = pathlib.PurePosixPath(asset_path)
whiteouts = {str(parent / ".wh..wh..opq") for parent in asset.parents}
whiteouts |= {str(part.parent / (".wh." + part.name)) for part in [asset, *asset.parents] if part.name}
found = None
with tarfile.open(a.archive) as image:
    manifests = json.load(image.extractfile("manifest.json"))
    if len(manifests) != 1:
        raise ValueError("Expected one amd64 installer image.")
    manifest = manifests[0]
    config_bytes = image.extractfile(manifest["Config"]).read()
    config = json.loads(config_bytes)
    require(config["architecture"] == "amd64" and config["os"] == "linux", "Require a linux/amd64 image.")
    require(config["config"]["Entrypoint"] == ["/bin/installer"], "Unexpected installer entrypoint.")
    root = pathlib.Path(__file__).resolve().parents[1]
    lock = json.loads((root / "sources.lock.json").read_text())
    require("VERSION=" + lock["talos_version"] in config["config"]["Env"], "Unexpected Talos version.")
    for index, layer in enumerate(manifest["Layers"]):
        with tarfile.open(fileobj=image.extractfile(layer), mode="r|*") as archive:
            for member in archive:
                name = member.name.removeprefix("./")
                if name in whiteouts:
                    raise ValueError("A layer whiteout affects the installer UKI.")
                if name == asset_path:
                    if not member.isfile():
                        raise ValueError("Installer UKI must be a regular file.")
                    found = a.output / ("layer-" + str(index) + "-uki.efi")
                    with found.open("xb") as dest:
                        shutil.copyfileobj(archive.extractfile(member), dest)
if found is None:
    raise ValueError("Installer archive does not contain its amd64 UKI.")
uki = a.output / "installer.efi"
found.rename(uki)
command = ["python3", str(root / "scripts/verify-uki.py"), str(uki), str(a.output / "uki"), "--targets", a.targets]
if a.module:
    command += ["--module", str(a.module)]
if a.module_sha256:
    command += ["--module-sha256", a.module_sha256]
subprocess.run(command, check=True)
uki_report = json.loads((a.output / "uki/report.json").read_text())
result = {"installer_archive_sha256": hashlib.file_digest(a.archive.open("rb"), "sha256").hexdigest(),
          "installer_manifest_digest": image_digest, "architecture": "amd64", "os": "linux",
          "embedded_uki_path": asset_path, "embedded_uki_sha256": uki_report["uki_sha256"],
          "gpu_targets": uki_report["gpu_targets"], "normal_cmdline": uki_report["cmdline"],
          "archive_validated": True, "embedded_uki_validated": True, "requires_separate_uki_patch": False,
          "uki_checks": uki_report, "fresh_install_validated": False, "boot_tested": False}
(a.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({key: value for key, value in result.items() if key != "uki_checks"}, indent=2))
