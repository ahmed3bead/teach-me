# Install the pinned Teach Me beta safely for Codex or Claude Code on Windows PowerShell.

[CmdletBinding()]
param(
    [ValidateSet("install", "update", "version", "disable", "restore", "recover")]
    [string]$Action = "install",
    [ValidateSet("codex", "claude-code")]
    [string]$TargetHost = "codex",
    [string]$Version = "1.0.0-beta.2",
    [string]$InstallRoot,
    [string]$Archive,
    [string]$Checksum
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PinnedVersion = "1.0.0-beta.2"
$ReleaseBase = "https://github.com/ahmed3bead/teach-me/releases/download"

$ArchiveSupplied = $PSBoundParameters.ContainsKey("Archive")
$ChecksumSupplied = $PSBoundParameters.ContainsKey("Checksum")
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
if ($ChecksumSupplied -and $Checksum -cnotmatch '^[0-9a-f]{64}$') {
    Stop-Setup "checksum must be 64 lowercase hexadecimal characters"
}
if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    if ($TargetHost -eq "claude-code") {
        $InstallRoot = Join-Path $HOME ".claude\skills"
    } elseif (-not [string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
        $InstallRoot = Join-Path $env:CODEX_HOME "skills"
    } else {
        $InstallRoot = Join-Path $HOME ".codex\skills"
    }
}
$HostLabel = if ($TargetHost -eq "claude-code") { "Claude Code" } else { "Codex" }
$ReloadMessage = if ($TargetHost -eq "claude-code") { "Restart Claude Code." } else { "Reload Codex." }
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
        Write-Output "Teach Me disabled safely for $HostLabel at $Disabled. $ReloadMessage"
        return
    }
    "restore" {
        if (-not (Test-Path -LiteralPath $Disabled -PathType Container)) { Stop-Setup "no disabled installation exists at $Disabled" }
        if (Test-Path -LiteralPath $Target) { Stop-Setup "active installation already exists at $Target" }
        Move-Item -LiteralPath $Disabled -Destination $Target
        Write-Output "Teach Me restored for $HostLabel at $Target. $ReloadMessage"
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
        Write-Output "Teach Me recovered for $HostLabel from $Backup to $Target. $ReloadMessage"
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
$ArchiveName = "teach-me-$PinnedVersion.zip"
$ArchivePath = Join-Path $WorkDirectory $ArchiveName
$ChecksumPath = "$ArchivePath.sha256"
$ExtractRoot = Join-Path $WorkDirectory "extracted"
New-Item -ItemType Directory -Path $WorkDirectory | Out-Null

function Copy-Source([string]$Source, [string]$Destination, [string]$Description) {
    if ($Source -match '^https://') {
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $Source -OutFile $Destination
        } catch {
            Stop-Setup "$Description download failed; the existing installation was not changed"
        }
    } elseif ($Source -match '^http://') {
        Stop-Setup "refusing an unencrypted $Description URL"
    } elseif ($Source -match '^file://') {
        try {
            Copy-Item -LiteralPath ([uri]$Source).LocalPath -Destination $Destination
        } catch {
            Stop-Setup "could not read local $Description"
        }
    } elseif ($Source -match '^[a-zA-Z][a-zA-Z0-9+.-]*://') {
        Stop-Setup "unsupported $Description URL scheme"
    } else {
        try {
            Copy-Item -LiteralPath $Source -Destination $Destination
        } catch {
            Stop-Setup "could not read local $Description"
        }
    }
}

if ($ArchiveSupplied) {
    if (-not $ChecksumSupplied) {
        Stop-Setup "a custom archive requires an explicit -Checksum"
    }
} else {
    if ($ChecksumSupplied) {
        Stop-Setup "-Checksum may be used only with a custom -Archive"
    }
    $PublishedReleaseBase = $ReleaseBase
    if ($env:TEACH_ME_TESTING -eq "1" -and -not [string]::IsNullOrWhiteSpace($env:TEACH_ME_TEST_RELEASE_BASE)) {
        $PublishedReleaseBase = $env:TEACH_ME_TEST_RELEASE_BASE
    }
    $Archive = "$PublishedReleaseBase/v$PinnedVersion/$ArchiveName"
    $ChecksumSource = "$Archive.sha256"
    Copy-Source $ChecksumSource $ChecksumPath "checksum file"
    $ChecksumText = [System.IO.File]::ReadAllText($ChecksumPath)
    $ChecksumMatch = [regex]::Match(
        $ChecksumText,
        '\A([0-9a-f]{64})  ([^\r\n]+)(?:\r?\n)?\z',
        [System.Text.RegularExpressions.RegexOptions]::CultureInvariant
    )
    if (-not $ChecksumMatch.Success -or $ChecksumMatch.Groups[2].Value -cne $ArchiveName) {
        Stop-Setup "published checksum file is malformed, missing, or ambiguous"
    }
    $Checksum = $ChecksumMatch.Groups[1].Value
}

Copy-Source $Archive $ArchivePath "archive"

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
    Write-Output "Teach Me $Installed installed for $HostLabel at $Target. Previous installation preserved at $Backup. $ReloadMessage"
} else {
    Write-Output "Teach Me $Installed installed for $HostLabel at $Target. $ReloadMessage"
}
