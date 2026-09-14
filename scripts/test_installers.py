#!/usr/bin/env python3
"""Exercise installer lifecycle and recovery only in isolated temporary roots."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0-beta.1"


def bundle(directory: Path, marker: str) -> tuple[Path, str]:
    archive = directory / f"teach-me-{marker}.zip"
    skill = (
        "---\n"
        "name: teach-me\n"
        "metadata:\n"
        f'  version: "{VERSION}"\n'
        "---\n\n"
        "# Isolated installer fixture\n"
    )
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        output.writestr("teach-me/SKILL.md", skill)
        output.writestr("teach-me/marker.txt", marker)
    return archive, hashlib.sha256(archive.read_bytes()).hexdigest()


def command(action: str, install_root: Path, archive: Path | None = None, checksum: str | None = None) -> list[str]:
    if os.name == "nt":
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if not shell:
            raise AssertionError("PowerShell is required on Windows")
        result = [
            shell,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "installers" / "install.ps1"),
            "-Action",
            action,
            "-Version",
            VERSION,
            "-InstallRoot",
            str(install_root),
        ]
        if archive is not None:
            result.extend(["-Archive", str(archive)])
        if checksum is not None:
            result.extend(["-Checksum", checksum])
        return result
    result = [
        "sh",
        str(ROOT / "installers" / "install.sh"),
        action,
        "--version",
        VERSION,
        "--install-root",
        str(install_root),
    ]
    if archive is not None:
        result.extend(["--archive", str(archive)])
    if checksum is not None:
        result.extend(["--checksum", checksum])
    return result


def run(
    action: str,
    install_root: Path,
    archive: Path | None = None,
    checksum: str | None = None,
    *,
    succeeds: bool = True,
    injected_failure: bool = False,
    injected_post_install_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["TEACH_ME_TESTING"] = "1"
    if injected_failure:
        environment["TEACH_ME_TEST_FAIL_AFTER_BACKUP"] = "1"
    if injected_post_install_failure:
        environment["TEACH_ME_TEST_FAIL_AFTER_INSTALL"] = "1"
    completed = subprocess.run(
        command(action, install_root, archive, checksum),
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
    )
    if succeeds and completed.returncode != 0:
        raise AssertionError(f"{action} failed:\n{completed.stdout}\n{completed.stderr}")
    if not succeeds and completed.returncode == 0:
        raise AssertionError(f"{action} unexpectedly succeeded")
    return completed


def marker(path: Path) -> str:
    return (path / "marker.txt").read_text(encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teach-me-installer-tests-") as raw:
        temp = Path(raw)
        first, first_checksum = bundle(temp, "first")
        second, second_checksum = bundle(temp, "second")

        lifecycle = temp / "lifecycle" / "skills"
        target = lifecycle / "teach-me"
        backup = lifecycle / f"teach-me.backup-{VERSION}"
        disabled = lifecycle / "teach-me.disabled"

        run("install", lifecycle, first, first_checksum)
        assert marker(target) == "first"
        version_result = run("version", lifecycle)
        assert VERSION in version_result.stdout

        run("disable", lifecycle)
        assert not target.exists() and marker(disabled) == "first"
        run("restore", lifecycle)
        assert marker(target) == "first" and not disabled.exists()

        run("update", lifecycle, second, "0" * 64, succeeds=False)
        assert marker(target) == "first" and not backup.exists()
        run("update", lifecycle, second, second_checksum)
        assert marker(target) == "second" and marker(backup) == "first"

        failed_target = lifecycle / "teach-me.failed-update"
        target.rename(failed_target)
        run("recover", lifecycle)
        assert marker(target) == "first" and not backup.exists()

        recovery = temp / "recovery" / "skills"
        recovery_target = recovery / "teach-me"
        recovery_backup = recovery / f"teach-me.backup-{VERSION}"
        recovery_failed = recovery / f"teach-me.failed-{VERSION}"
        run("install", recovery, first, first_checksum)
        run("update", recovery, second, second_checksum, succeeds=False, injected_failure=True)
        assert marker(recovery_target) == "first"
        assert not recovery_backup.exists()
        run("update", recovery, second, second_checksum, succeeds=False, injected_post_install_failure=True)
        assert marker(recovery_target) == "first"
        assert marker(recovery_failed) == "second"
        assert not recovery_backup.exists()

        missing = temp / "missing" / "skills"
        error = run("update", missing, second, second_checksum, succeeds=False)
        assert "not installed" in (error.stdout + error.stderr)
        assert not (missing / "teach-me").exists()

    platform = "Windows PowerShell" if os.name == "nt" else "POSIX shell"
    print(f"Teach Me installer tests passed ({platform}: install, verify, update, disable, restore, recover, failures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
