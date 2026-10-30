"""Shared target and UKI checks for local image construction."""
import hashlib
import mmap
import re
import struct

PCI_BDF = re.compile(r"^[0-9a-f]{4}:[0-9a-f]{2}:[01][0-9a-f]\.[0-7]$")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def parse_targets(value):
    targets = [part.strip().lower() for part in value.split(",")]
    if not targets or any(not PCI_BDF.fullmatch(part) for part in targets):
        raise ValueError("Use explicit guest PCI addresses, separated by commas; 'all' is not accepted.")
    if len(set(targets)) != len(targets):
        raise ValueError("Duplicate GPU PCI target.")
    return ",".join(targets)


def read_uki(path):
    sections = {}
    profiles = {}
    current = "common"
    with path.open("rb") as source, mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as data:
        if data[:2] != b"MZ":
            raise ValueError("Not a PE/UKI image.")
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe:pe + 4] != b"PE\0\0":
            raise ValueError("Invalid PE signature.")
        if struct.unpack_from("<H", data, pe + 4)[0] != 0x8664:
            raise ValueError("The installer UKI must use the amd64 PE machine type.")
        count = struct.unpack_from("<H", data, pe + 6)[0]
        optional = struct.unpack_from("<H", data, pe + 20)[0]
        for index in range(count):
            header = pe + 24 + optional + index * 40
            name = bytes(data[header:header + 8]).rstrip(b"\0").decode()
            size, _, capacity, offset = struct.unpack_from("<IIII", data, header + 8)
            if name not in (".profile", ".cmdline", ".linux", ".initrd"):
                continue
            if size > capacity or offset + size > len(data):
                raise ValueError("PE section exceeds its file bounds.")
            if name == ".profile":
                identifiers = [line[3:] for line in bytes(data[offset:offset + size]).decode().splitlines() if line.startswith("ID=")]
                if len(identifiers) != 1 or identifiers[0] in profiles:
                    raise ValueError("Missing or duplicate UKI profile ID.")
                current = identifiers[0]
                profiles[current] = None
            if name == ".cmdline":
                if current in profiles and profiles[current] is not None:
                    raise ValueError("Duplicate command line in one UKI profile.")
                profiles[current] = bytes(data[offset:offset + size]).rstrip(b"\0").decode()
                if current == "common":
                    sections[name] = {"offset": offset, "bytes": size, "capacity": capacity, "header": header}
            if name in (".linux", ".initrd"):
                if name in sections:
                    raise ValueError("Duplicate kernel or initramfs section.")
                digest = hashlib.sha256()
                for start in range(offset, offset + size, 1024 * 1024):
                    digest.update(data[start:min(start + 1024 * 1024, offset + size)])
                sections[name] = {"offset": offset, "bytes": size, "sha256": digest.hexdigest()}
    for required in (".linux", ".initrd", ".cmdline"):
        if required not in sections:
            raise ValueError("Missing UKI section: " + required)
    normal = profiles.get("main")
    if normal is None:
        normal = profiles.get("common")
    if not normal:
        raise ValueError("Missing normal-profile command line.")
    return sections, profiles, normal


def check_normal_arguments(cmdline, expected_targets=None):
    args = cmdline.split()
    for key, expected in (("module.sig_enforce", "0"), ("firmware_class.path", "/usr/lib/firmware")):
        values = [a.partition("=")[2] if "=" in a else None for a in args if a == key or a.startswith(key + "=")]
        if values != [expected]:
            raise ValueError("Require exactly one " + key + "=" + expected)
    targets = [a.partition("=")[2] for a in args if a == "gpu_unlock.targets" or a.startswith("gpu_unlock.targets=")]
    if len(targets) != 1:
        raise ValueError("Require exactly one explicit gpu_unlock.targets argument.")
    actual = parse_targets(targets[0])
    if expected_targets is not None and actual != parse_targets(expected_targets):
        raise ValueError("UKI GPU targets differ from the requested targets.")
    if any(a == "talos.experimental.wipe" or a.startswith("talos.experimental.wipe=") for a in args):
        raise ValueError("The selected normal profile must not wipe storage.")
    return actual
