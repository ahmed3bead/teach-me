#!/bin/sh
# Install the pinned Teach Me beta safely on Linux or macOS.

set -eu

PINNED_VERSION="1.0.0-beta.1"
PINNED_SHA256="e924647f3bcd11c8e090fe51a12ef4d2fbbfcd30001be76c9631e1733abde728"
RELEASE_BASE="https://github.com/ahmed3bead/teach-me/releases/download"

fail() {
    printf '%s\n' "Teach Me setup failed: $*" >&2
    exit 1
}

usage() {
    printf '%s\n' \
        "Usage: sh installers/install.sh [install|update|version|disable|restore|recover] [options]" \
        "Options:" \
        "  --version VERSION       Must match the version pinned by this installer." \
        "  --install-root PATH     Skills directory (default: CODEX_HOME/skills or ~/.codex/skills)." \
        "  --archive URL_OR_PATH   Release archive override; HTTPS, file://, or local path." \
        "  --checksum SHA256       Expected archive checksum (64 lowercase hexadecimal characters)."
}

action="install"
if [ "$#" -gt 0 ]; then
    case "$1" in
        install|update|version|disable|restore|recover) action="$1"; shift ;;
        -h|--help) usage; exit 0 ;;
    esac
fi

requested_version="$PINNED_VERSION"
install_root=""
archive_source=""
expected_checksum="$PINNED_SHA256"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --version|--install-root|--archive|--checksum)
            [ "$#" -ge 2 ] || fail "$1 requires a value"
            option="$1"
            value="$2"
            shift 2
            case "$option" in
                --version) requested_version="$value" ;;
                --install-root) install_root="$value" ;;
                --archive) archive_source="$value" ;;
                --checksum) expected_checksum="$value" ;;
            esac
            ;;
        -h|--help) usage; exit 0 ;;
        *) fail "unknown option: $1" ;;
    esac
done

[ "$requested_version" = "$PINNED_VERSION" ] || fail "this installer supports only version $PINNED_VERSION"
case "$expected_checksum" in
    *[!0-9a-f]*|'') fail "checksum must be 64 lowercase hexadecimal characters" ;;
esac
[ "${#expected_checksum}" -eq 64 ] || fail "checksum must be 64 lowercase hexadecimal characters"

if [ -z "$install_root" ]; then
    if [ -n "${CODEX_HOME:-}" ]; then
        install_root="$CODEX_HOME/skills"
    else
        [ -n "${HOME:-}" ] || fail "HOME is unavailable; pass --install-root"
        install_root="$HOME/.codex/skills"
    fi
fi

case "$install_root" in
    ''|/) fail "refusing unsafe install root" ;;
esac
if printf '%s' "$install_root" | grep '[[:cntrl:]]' >/dev/null 2>&1; then
    fail "refusing an install root containing control characters"
fi

target="$install_root/teach-me"
disabled="$install_root/teach-me.disabled"
backup="$install_root/teach-me.backup-$PINNED_VERSION"
failed="$install_root/teach-me.failed-$PINNED_VERSION"

installed_version() {
    [ -f "$1/SKILL.md" ] || return 1
    awk '
        /^metadata:/ { in_metadata=1; next }
        in_metadata && /^[^ ]/ { in_metadata=0 }
        in_metadata && $1 == "version:" {
            value=$2
            gsub(/["'\'' ]/, "", value)
            print value
            exit
        }
    ' "$1/SKILL.md"
}

case "$action" in
    version)
        value=$(installed_version "$target") || fail "Teach Me is not installed at $target"
        printf '%s\n' "Teach Me $value is installed at $target"
        exit 0
        ;;
    disable)
        [ -d "$target" ] || fail "Teach Me is not installed at $target"
        [ ! -e "$disabled" ] || fail "disabled installation already exists at $disabled"
        mv "$target" "$disabled"
        printf '%s\n' "Teach Me disabled safely at $disabled. Reload Codex."
        exit 0
        ;;
    restore)
        [ -d "$disabled" ] || fail "no disabled installation exists at $disabled"
        [ ! -e "$target" ] || fail "active installation already exists at $target"
        mv "$disabled" "$target"
        printf '%s\n' "Teach Me restored at $target. Reload Codex."
        exit 0
        ;;
    recover)
        if [ -d "$target" ]; then
            value=$(installed_version "$target") || fail "active path exists but is not a valid Teach Me installation: $target"
            printf '%s\n' "Teach Me $value is already active at $target; no recovery was needed."
            exit 0
        fi
        [ -d "$backup" ] || fail "no recoverable backup exists at $backup"
        mv "$backup" "$target"
        printf '%s\n' "Teach Me recovered from $backup to $target. Reload Codex."
        exit 0
        ;;
esac

if [ "$action" = "update" ]; then
    [ -d "$target" ] || fail "cannot update because Teach Me is not installed at $target"
fi
[ ! -e "$backup" ] || fail "backup already exists at $backup; preserve or move it before replacing the installation"
[ ! -e "$failed" ] || fail "failed-install quarantine already exists at $failed; preserve or move it before replacing the installation"

mkdir -p "$install_root"
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/teach-me-install.XXXXXX") || fail "could not create a temporary directory"
archive="$work_dir/teach-me-$PINNED_VERSION.zip"
extract_root="$work_dir/extracted"
archive_source=${archive_source:-"$RELEASE_BASE/v$PINNED_VERSION/teach-me-$PINNED_VERSION.zip"}

case "$archive_source" in
    https://*)
        command -v curl >/dev/null 2>&1 || fail "curl is required to download the pinned release"
        curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 "$archive_source" --output "$archive" \
            || fail "download failed; the existing installation was not changed"
        ;;
    http://*) fail "refusing an unencrypted archive URL" ;;
    file://*) cp "${archive_source#file://}" "$archive" || fail "could not read local archive" ;;
    *://*) fail "unsupported archive URL scheme" ;;
    *) cp "$archive_source" "$archive" || fail "could not read local archive" ;;
esac

if command -v sha256sum >/dev/null 2>&1; then
    actual_checksum=$(sha256sum "$archive" | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
    actual_checksum=$(shasum -a 256 "$archive" | awk '{print $1}')
else
    fail "sha256sum or shasum is required; the download was not executed"
fi
[ "$actual_checksum" = "$expected_checksum" ] || fail "checksum mismatch; the download was not extracted or executed"

command -v unzip >/dev/null 2>&1 || fail "unzip is required; the verified archive was not installed"
if unzip -Z1 "$archive" | awk '
    /^\// || /(^|\/)\.\.($|\/)/ || /\\/ { unsafe=1 }
    END { exit unsafe ? 0 : 1 }
'; then
    fail "archive contains an unsafe path and was not extracted"
fi
mkdir "$extract_root"
unzip -q "$archive" -d "$extract_root" || fail "the verified archive could not be extracted"
staged="$extract_root/teach-me"
[ -f "$staged/SKILL.md" ] || fail "archive layout is invalid: teach-me/SKILL.md is missing"
[ "$(installed_version "$staged")" = "$PINNED_VERSION" ] || fail "archive version does not match $PINNED_VERSION"
if find "$staged" -type l -print -quit | grep . >/dev/null 2>&1; then
    fail "archive contains a symbolic link and was not installed"
fi

did_backup=0
if [ -e "$target" ]; then
    [ -d "$target" ] || fail "target exists and is not a directory: $target"
    mv "$target" "$backup"
    did_backup=1
fi

if [ "${TEACH_ME_TESTING:-}" = "1" ] && [ "${TEACH_ME_TEST_FAIL_AFTER_BACKUP:-}" = "1" ]; then
    if [ "$did_backup" -eq 1 ]; then
        mv "$backup" "$target" || fail "injected failure occurred and the previous installation could not be restored"
    fi
    fail "injected failure; the previous installation was restored"
fi

if ! mv "$staged" "$target"; then
    if [ -e "$target" ]; then
        mv "$target" "$failed" || fail "installation failed and the partial target could not be quarantined; run recover"
    fi
    if [ "$did_backup" -eq 1 ]; then
        mv "$backup" "$target" || fail "installation failed and automatic recovery also failed; run recover"
    fi
    fail "installation failed; the previous installation was restored when possible"
fi

if [ "${TEACH_ME_TESTING:-}" = "1" ] && [ "${TEACH_ME_TEST_FAIL_AFTER_INSTALL:-}" = "1" ]; then
    value="injected-invalid-version"
else
    value=$(installed_version "$target") || value=""
fi
if [ "$value" != "$PINNED_VERSION" ]; then
    mv "$target" "$failed" || fail "installed version verification failed and the target could not be quarantined; run recover"
    if [ "$did_backup" -eq 1 ]; then
        mv "$backup" "$target" || fail "installed version verification failed and automatic recovery also failed; run recover"
    fi
    fail "installed version verification failed; failed files were quarantined at $failed and the previous installation was restored when available"
fi

rm -f "$archive"
rmdir "$extract_root" 2>/dev/null || true
rmdir "$work_dir" 2>/dev/null || true

if [ "$did_backup" -eq 1 ]; then
    printf '%s\n' "Teach Me $value installed at $target. Previous installation preserved at $backup. Reload Codex."
else
    printf '%s\n' "Teach Me $value installed at $target. Reload Codex."
fi
