# Install Teach Me for Codex

Teach Me for Codex provides the full repository tooling: adaptive teaching plus controlled local files, source workflows, sessions, reports, deterministic validation, and independent evaluation infrastructure. The current public version is the beta `1.0.0-beta.2`.

This page documents the installer's default `codex` target. For Claude chat and the `--target-host claude-code` option, see the [`Claude setup guide`](../claude-edition/README.md).

The installers in this repository pin that exact release and verify its archive against the published adjacent checksum. They download before changing the installation, verify before extracting, preserve an existing installation as a versioned backup, reject unsafe archive paths, and restore the previous installation if replacement fails. They never require credentials, run model evaluations, start Ollama, or recursively delete an installation.

## Fastest safe installation

If you already have a trusted checkout of this repository, run one command from its root.

### Linux or macOS

```bash
sh installers/install.sh install --version 1.0.0-beta.2
```

### Windows PowerShell

```powershell
.\installers\install.ps1 -Action install -Version 1.0.0-beta.2
```

Reload Codex after installation. The default destination is `${CODEX_HOME}/skills/teach-me` when `CODEX_HOME` is set and otherwise the user-level `.codex/skills/teach-me` directory.

## Fresh machine without a checkout

The safest bootstrap is a short download–verify–run block. It downloads the installer from the public repository, verifies the installer itself against the checksum documented in this version of the repository, and only then runs it. The installer separately verifies the pinned release archive.

### Linux

```bash
installer=$(mktemp /tmp/teach-me-installer.XXXXXX)
curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 \
  https://raw.githubusercontent.com/ahmed3bead/teach-me/main/installers/install.sh \
  --output "$installer"
printf '%s  %s\n' '9936e077b462c9892738f656bb2bad60fbdfd08d877ad37b8ad2e49b5371ee30' "$installer" | sha256sum --check -
sh "$installer" install --version 1.0.0-beta.2
rm -f "$installer"
```

### macOS

```bash
installer=$(mktemp /tmp/teach-me-installer.XXXXXX)
curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 \
  https://raw.githubusercontent.com/ahmed3bead/teach-me/main/installers/install.sh \
  --output "$installer"
printf '%s  %s\n' '9936e077b462c9892738f656bb2bad60fbdfd08d877ad37b8ad2e49b5371ee30' "$installer" | shasum -a 256 --check
sh "$installer" install --version 1.0.0-beta.2
rm -f "$installer"
```

### Windows PowerShell

```powershell
$installer = Join-Path ([System.IO.Path]::GetTempPath()) "teach-me-install.ps1"
Invoke-WebRequest -UseBasicParsing `
  -Uri "https://raw.githubusercontent.com/ahmed3bead/teach-me/main/installers/install.ps1" `
  -OutFile $installer
$expected = "ec250fab9d38d796d1a06eb91422cc11228e71f51a406234913fe6cdb7b8ab4f"
if ((Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
    throw "Teach Me installer checksum mismatch; nothing was executed."
}
& $installer -Action install -Version "1.0.0-beta.2"
Remove-Item -LiteralPath $installer -Force
```

If the repository installer changes, these checksum-pinned bootstrap blocks fail closed until this documentation is deliberately updated. Do not bypass a mismatch by executing the download directly.

## Verify, update, disable, restore, and recover

Run these from a trusted checkout, or replace the script path with the already verified temporary installer path from the bootstrap block.

| Operation | Linux or macOS | Windows PowerShell |
|---|---|---|
| Verify version | `sh installers/install.sh version` | `.\installers\install.ps1 -Action version` |
| Update to the pinned version | `sh installers/install.sh update --version 1.0.0-beta.2` | `.\installers\install.ps1 -Action update -Version 1.0.0-beta.2` |
| Disable safely | `sh installers/install.sh disable` | `.\installers\install.ps1 -Action disable` |
| Restore after disable | `sh installers/install.sh restore` | `.\installers\install.ps1 -Action restore` |
| Recover a preserved backup | `sh installers/install.sh recover` | `.\installers\install.ps1 -Action recover` |

An update keeps the prior installation at `teach-me.backup-1.0.0-beta.2`. The installer will not overwrite that backup. Preserve or move it deliberately before another replacement. Disabling moves the active directory to `teach-me.disabled`; restoring moves the same directory back, so learner files are not deleted.

## Custom destination

Use an explicit skills directory when Codex is configured somewhere else:

```bash
sh installers/install.sh install --install-root /absolute/path/to/skills
```

```powershell
.\installers\install.ps1 -Action install -InstallRoot "C:\absolute\path\to\skills"
```

The target is always a `teach-me` child of the supplied directory. Volume roots and unsafe paths are rejected.

## Failure recovery

- A download or checksum failure occurs before extraction and before the current installation changes.
- An invalid archive layout or version is rejected in a temporary staging directory.
- If replacement or final version verification fails after a prior installation was moved, the installer quarantines failed files at `teach-me.failed-1.0.0-beta.2` and reactivates the preserved backup.
- If an interruption leaves the active path missing and the versioned backup present, run the `recover` action.
- If both an active installation and a backup exist, the installer leaves both untouched and reports what requires attention.
- Failed staging data can remain only in an isolated operating-system temporary directory; the installer does not recursively delete broad paths while attempting cleanup.

Reload Codex after install, update, disable, restore, or recovery. Normal use does not require Python, Git, Ollama, or API credentials. Repository validation requires Python 3.10 or newer and the pinned development dependencies.
