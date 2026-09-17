#!/usr/bin/env python3
"""Exercise installer lifecycle and recovery only in isolated temporary roots."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0-beta.2"


def bundle(directory: Path, marker: str, filename: str | None = None) -> tuple[Path, str]:
    directory.mkdir(parents=True, exist_ok=True)
    archive = directory / (filename or f"teach-me-{marker}.zip")
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


def published_bundle(directory: Path, marker: str) -> tuple[Path, str]:
    release = directory / f"v{VERSION}"
    archive, digest = bundle(release, marker, f"teach-me-{VERSION}.zip")
    archive.with_suffix(".zip.sha256").write_text(
        f"{digest}  {archive.name}\n",
        encoding="utf-8",
    )
    return archive, digest


def command(
    action: str,
    install_root: Path,
    archive: Path | str | None = None,
    checksum: str | None = None,
    target_host: str = "codex",
) -> list[str]:
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
            "-TargetHost",
            target_host,
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
        "--target-host",
        target_host,
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
    archive: Path | str | None = None,
    checksum: str | None = None,
    *,
    succeeds: bool = True,
    injected_failure: bool = False,
    injected_post_install_failure: bool = False,
    target_host: str = "codex",
    release_base: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["TEACH_ME_TESTING"] = "1"
    if release_base is not None:
        environment["TEACH_ME_TEST_RELEASE_BASE"] = str(release_base)
    if injected_failure:
        environment["TEACH_ME_TEST_FAIL_AFTER_BACKUP"] = "1"
    if injected_post_install_failure:
        environment["TEACH_ME_TEST_FAIL_AFTER_INSTALL"] = "1"
    completed = subprocess.run(
        command(action, install_root, archive, checksum, target_host),
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


def assert_published_sidecar_defaults() -> None:
    expected_fragments = {
        "installers/install.sh": (
            'PINNED_VERSION="1.0.0-beta.2"',
            'checksum_source="$archive_source.sha256"',
            "a custom archive requires an explicit --checksum",
        ),
        "installers/install.ps1": (
            '$PinnedVersion = "1.0.0-beta.2"',
            '$ChecksumSource = "$Archive.sha256"',
            "a custom archive requires an explicit -Checksum",
        ),
    }
    for relative, fragments in expected_fragments.items():
        installer = (ROOT / relative).read_text(encoding="utf-8")
        for fragment in fragments:
            assert fragment in installer
        assert "PINNED_SHA256" not in installer
        assert not re.search(r'^\s*\[string\]\$Checksum\s*=', installer, flags=re.MULTILINE)
        assert "predates verified Claude support" not in installer


def main() -> int:
    assert_published_sidecar_defaults()
    with tempfile.TemporaryDirectory(prefix="teach-me-installer-tests-") as raw:
        temp = Path(raw)
        first, first_checksum = bundle(temp, "first")
        second, second_checksum = bundle(temp, "second")

        published_release = temp / "published-release"
        published_bundle(published_release, "published")
        published_root = temp / "published-install" / "skills"
        run("install", published_root, release_base=published_release)
        assert marker(published_root / "teach-me") == "published"

        invalid_sidecars = (
            "missing",
            "malformed",
            "wrong-filename",
            "wrong-digest",
            "ambiguous",
        )
        for case in invalid_sidecars:
            release_base = temp / f"{case}-release"
            archive, digest = published_bundle(release_base, case)
            sidecar = archive.with_suffix(".zip.sha256")
            if case == "missing":
                sidecar.unlink()
            elif case == "malformed":
                sidecar.write_text("not-a-sha256-record\n", encoding="utf-8")
            elif case == "wrong-filename":
                sidecar.write_text(f"{digest}  wrong-name.zip\n", encoding="utf-8")
            elif case == "wrong-digest":
                sidecar.write_text(f"{'0' * 64}  {archive.name}\n", encoding="utf-8")
            else:
                sidecar.write_text(
                    f"{digest}  {archive.name}\n{digest}  {archive.name}\n",
                    encoding="utf-8",
                )
            rejected_root = temp / f"{case}-install" / "skills"
            rejected = run("install", rejected_root, succeeds=False, release_base=release_base)
            output = rejected.stdout + rejected.stderr
            if case == "wrong-digest":
                assert "checksum mismatch" in output
            else:
                assert "checksum" in output
            assert not (rejected_root / "teach-me").exists()

        custom_without_checksum = temp / "custom-without-checksum" / "skills"
        missing_explicit = run("install", custom_without_checksum, first, succeeds=False)
        assert "requires an explicit" in (missing_explicit.stdout + missing_explicit.stderr)
        assert not (custom_without_checksum / "teach-me").exists()

        insecure = temp / "insecure-http" / "skills"
        insecure_result = run(
            "install",
            insecure,
            "http://example.invalid/teach-me.zip",
            first_checksum,
            succeeds=False,
        )
        assert "unencrypted archive URL" in (insecure_result.stdout + insecure_result.stderr)
        assert not (insecure / "teach-me").exists()

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

        claude = temp / "claude" / "skills"
        claude_target = claude / "teach-me"
        claude_disabled = claude / "teach-me.disabled"
        installed = run("install", claude, first, first_checksum, target_host="claude-code")
        assert marker(claude_target) == "first"
        assert "Claude Code" in installed.stdout
        run("disable", claude, target_host="claude-code")
        assert not claude_target.exists() and marker(claude_disabled) == "first"
        restored = run("restore", claude, target_host="claude-code")
        assert marker(claude_target) == "first" and not claude_disabled.exists()
        assert "Restart Claude Code" in restored.stdout

    platform = "Windows PowerShell" if os.name == "nt" else "POSIX shell"
    print(
        f"Teach Me installer tests passed ({platform}: Codex and Claude Code install, verify, "
        "update, disable, restore, recover, failures)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
