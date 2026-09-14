# Install the pinned Teach Me beta safely on Windows PowerShell.

[CmdletBinding()]
param(
    [ValidateSet("install", "update", "version", "disable", "restore", "recover")]
    [string]$Action = "install",
    [string]$Version = "1.0.0-beta.1",
    [string]$InstallRoot,
    [string]$Archive,
    [string]$Checksum = "e924647f3bcd11c8e090fe51a12ef4d2fbbfcd30001be76c9631e1733abde728"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PinnedVersion = "1.0.0-beta.1"
$ReleaseBase = "https://github.com/ahmed3bead/teach-me/releases/download"

function Stop-Setup([string]$Message) {
    throw "Teach Me setup failed: $Message"
}

function Get-InstalledVersion([string]$Directory) {
    $SkillFile = Join-Path $Directory "SKILL.md"
    if (-not (Test-Path -LiteralPath $SkillFile -PathType Leaf)) {
        return $null
    }
    $InMetadata = $false
    foreach ($Line in Get-Content -LiteralPath $SkillFile) {
        if ($Line -eq "metadata:") {
            $InMetadata = $true
            continue
        }
        if ($InMetadata -and $Line -match "^[^ ]") {
            $InMetadata = $false
        }
        if ($InMetadata -and $Line -match '^  version:\s*["'']?([^"'']+)["'']?\s*$') {
            return $Matches[1].Trim()
        }
    }
    return $null
}

if ($Version -ne $PinnedVersion) {
    Stop-Setup "this installer supports only version $PinnedVersion"
}
if ($Checksum -notmatch '^[0-9a-f]{64}$') {
    Stop-Setup "checksum must be 64 lowercase hexadecimal characters"
}
if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    if (-not [string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
        $InstallRoot = Join-Path $env:CODEX_HOME "skills"
    } else {
        $InstallRoot = Join-Path $HOME ".codex\skills"
    }
}
$FullRoot = [System.IO.Path]::GetFullPath($InstallRoot)
$VolumeRoot = [System.IO.Path]::GetPathRoot($FullRoot)
if ($FullRoot -eq $VolumeRoot) {
    Stop-Setup "refusing to use a volume root as the install root"
}

$Target = Join-Path $FullRoot "teach-me"
$Disabled = Join-Path $FullRoot "teach-me.disabled"
$Backup = Join-Path $FullRoot "teach-me.backup-$PinnedVersion"
$Failed = Join-Path $FullRoot "teach-me.failed-$PinnedVersion"

switch ($Action) {
    "version" {
        $Observed = Get-InstalledVersion $Target
        if ($null -eq $Observed) { Stop-Setup "Teach Me is not installed at $Target" }
        Write-Output "Teach Me $Observed is installed at $Target"
        return
    }
    "disable" {
        if (-not (Test-Path -LiteralPath $Target -PathType Container)) { Stop-Setup "Teach Me is not installed at $Target" }
        if (Test-Path -LiteralPath $Disabled) { Stop-Setup "disabled installation already exists at $Disabled" }
        Move-Item -LiteralPath $Target -Destination $Disabled
        Write-Output "Teach Me disabled safely at $Disabled. Reload Codex."
        return
    }
    "restore" {
        if (-not (Test-Path -LiteralPath $Disabled -PathType Container)) { Stop-Setup "no disabled installation exists at $Disabled" }
        if (Test-Path -LiteralPath $Target) { Stop-Setup "active installation already exists at $Target" }
        Move-Item -LiteralPath $Disabled -Destination $Target
        Write-Output "Teach Me restored at $Target. Reload Codex."
        return
    }
    "recover" {
        if (Test-Path -LiteralPath $Target -PathType Container) {
            $Observed = Get-InstalledVersion $Target
            if ($null -eq $Observed) { Stop-Setup "active path is not a valid Teach Me installation: $Target" }
            Write-Output "Teach Me $Observed is already active at $Target; no recovery was needed."
            return
        }
        if (-not (Test-Path -LiteralPath $Backup -PathType Container)) { Stop-Setup "no recoverable backup exists at $Backup" }
        Move-Item -LiteralPath $Backup -Destination $Target
        Write-Output "Teach Me recovered from $Backup to $Target. Reload Codex."
        return
    }
}

if ($Action -eq "update" -and -not (Test-Path -LiteralPath $Target -PathType Container)) {
    Stop-Setup "cannot update because Teach Me is not installed at $Target"
}
if (Test-Path -LiteralPath $Backup) {
    Stop-Setup "backup already exists at $Backup; preserve or move it before replacing the installation"
}
if (Test-Path -LiteralPath $Failed) {
    Stop-Setup "failed-install quarantine already exists at $Failed; preserve or move it before replacing the installation"
}

New-Item -ItemType Directory -Force -Path $FullRoot | Out-Null
$WorkDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("teach-me-install-" + [guid]::NewGuid().ToString("N"))
$ArchivePath = Join-Path $WorkDirectory "teach-me-$PinnedVersion.zip"
$ExtractRoot = Join-Path $WorkDirectory "extracted"
New-Item -ItemType Directory -Path $WorkDirectory | Out-Null

if ([string]::IsNullOrWhiteSpace($Archive)) {
    $Archive = "$ReleaseBase/v$PinnedVersion/teach-me-$PinnedVersion.zip"
}
if ($Archive -match '^https://') {
    Invoke-WebRequest -UseBasicParsing -Uri $Archive -OutFile $ArchivePath
} elseif ($Archive -match '^http://') {
    Stop-Setup "refusing an unencrypted archive URL"
} elseif ($Archive -match '^file://') {
    Copy-Item -LiteralPath ([uri]$Archive).LocalPath -Destination $ArchivePath
} elseif ($Archive -match '^[a-zA-Z][a-zA-Z0-9+.-]*://') {
    Stop-Setup "unsupported archive URL scheme"
} else {
    Copy-Item -LiteralPath $Archive -Destination $ArchivePath
}

$ActualChecksum = (Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ActualChecksum -ne $Checksum) {
    Stop-Setup "checksum mismatch; the download was not extracted or executed"
}

New-Item -ItemType Directory -Path $ExtractRoot | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
$Zip = [System.IO.Compression.ZipFile]::OpenRead($ArchivePath)
try {
    foreach ($Entry in $Zip.Entries) {
        $Name = $Entry.FullName.Replace("\", "/")
        if ($Name.StartsWith("/") -or $Name.Split("/") -contains "..") {
            Stop-Setup "archive contains an unsafe path and was not extracted"
        }
    }
} finally {
    $Zip.Dispose()
}
Expand-Archive -LiteralPath $ArchivePath -DestinationPath $ExtractRoot
$Staged = Join-Path $ExtractRoot "teach-me"
$Observed = Get-InstalledVersion $Staged
if ($null -eq $Observed) { Stop-Setup "archive layout is invalid: teach-me/SKILL.md is missing" }
if ($Observed -ne $PinnedVersion) { Stop-Setup "archive version does not match $PinnedVersion" }

$DidBackup = $false
try {
    if (Test-Path -LiteralPath $Target) {
        if (-not (Test-Path -LiteralPath $Target -PathType Container)) { Stop-Setup "target exists and is not a directory: $Target" }
        Move-Item -LiteralPath $Target -Destination $Backup
        $DidBackup = $true
    }

    if ($env:TEACH_ME_TESTING -eq "1" -and $env:TEACH_ME_TEST_FAIL_AFTER_BACKUP -eq "1") {
        Stop-Setup "injected failure"
    }

    Move-Item -LiteralPath $Staged -Destination $Target
    $Installed = Get-InstalledVersion $Target
    if ($env:TEACH_ME_TESTING -eq "1" -and $env:TEACH_ME_TEST_FAIL_AFTER_INSTALL -eq "1") {
        $Installed = "injected-invalid-version"
    }
    if ($Installed -ne $PinnedVersion) { Stop-Setup "installed version verification failed" }
} catch {
    if (Test-Path -LiteralPath $Target) {
        Move-Item -LiteralPath $Target -Destination $Failed
    }
    if ($DidBackup -and (Test-Path -LiteralPath $Backup -PathType Container)) {
        Move-Item -LiteralPath $Backup -Destination $Target
    }
    throw "$_ Failed files were quarantined at $Failed when present, and the previous installation was restored when available. Run recover if a backup remains."
}

Remove-Item -LiteralPath $ArchivePath -Force
Remove-Item -LiteralPath $ExtractRoot -Force
Remove-Item -LiteralPath $WorkDirectory -Force

if ($DidBackup) {
    Write-Output "Teach Me $Installed installed at $Target. Previous installation preserved at $Backup. Reload Codex."
} else {
    Write-Output "Teach Me $Installed installed at $Target. Reload Codex."
}
