"""Fail-closed target and UKI-profile checks; these tests do not boot an image."""
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from boot_image import check_normal_arguments, parse_targets, read_uki

ARGS = "module.sig_enforce=0 firmware_class.path=/usr/lib/firmware gpu_unlock.targets=0000:02:00.0"


def fixture(path, normal=None):
    sections = [(".bss", None), (".linux", b"kernel"), (".initrd", b"initrd"),
                (".cmdline", ARGS.encode() + b"\0"), (".profile", b"ID=main\n")]
    if normal is not None:
        sections.append((".cmdline", normal.encode() + b"\0"))
    sections += [(".profile", b"ID=reset-maintenance\n"), (".cmdline", b"talos.experimental.wipe=system\0")]
    data = bytearray(8192)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 128)
    data[128:132] = b"PE\0\0"
    struct.pack_into("<H", data, 132, 0x8664)
    struct.pack_into("<H", data, 134, len(sections))
    struct.pack_into("<H", data, 148, 0)
    offset = 2048
    for index, (name, payload) in enumerate(sections):
        header = 152 + index * 40
        data[header:header + 8] = name.encode().ljust(8, b"\0")
        if payload is None:
            struct.pack_into("<IIII", data, header + 8, 4096, 0, 0, 0)
            continue
        struct.pack_into("<IIII", data, header + 8, len(payload), 0, len(payload), offset)
        data[offset:offset + len(payload)] = payload
        offset += len(payload) + 16
    path.write_bytes(data)


class BootImageChecks(unittest.TestCase):
    def test_explicit_targets_and_normalization(self):
        self.assertEqual(parse_targets("0000:02:00.0"), "0000:02:00.0")
        self.assertEqual(parse_targets("0000:0A:1F.7,0000:02:00.0"), "0000:0a:1f.7,0000:02:00.0")

    def test_bad_or_ambiguous_targets_are_rejected(self):
        for value in ("", "all", "02:00.0", "0000:01:20.0", "0000:02:00.8", "0000:02:00.0,", "0000:02:00.0,0000:02:00.0"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_targets(value)

    def test_arguments_reject_wrong_target_signature_firmware_and_wipe(self):
        self.assertEqual(check_normal_arguments(ARGS, "0000:02:00.0"), "0000:02:00.0")
        for value in (ARGS + " module.sig_enforce", ARGS + " module.sig_enforce=1", ARGS + " gpu_unlock.targets=0000:01:00.0",
                      ARGS.replace("firmware_class.path=/usr/lib/firmware", ""), ARGS + " talos.experimental.wipe=system"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                check_normal_arguments(value)
        with self.assertRaisesRegex(ValueError, "differ"):
            check_normal_arguments(ARGS, "0000:01:00.0")

    def test_normal_profile_inheritance_ignores_destructive_reset_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "test.efi"
            fixture(path)
            _, profiles, normal = read_uki(path)
            self.assertIsNone(profiles["main"])
            self.assertIn("wipe=system", profiles["reset-maintenance"])
            self.assertEqual(check_normal_arguments(normal), "0000:02:00.0")

    def test_explicit_main_override_is_the_effective_normal_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "test.efi"
            fixture(path, ARGS.replace("0000:02:00.0", "0000:01:00.0"))
            _, _, normal = read_uki(path)
            with self.assertRaisesRegex(ValueError, "differ"):
                check_normal_arguments(normal, "0000:02:00.0")

    def test_missing_target_fails_before_creating_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output = pathlib.Path(temp) / "must-not-exist"
            result = subprocess.run([sys.executable, str(ROOT / "scripts/assemble-local.py"), temp, str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires --targets", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
