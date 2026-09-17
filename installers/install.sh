#!/bin/sh
# Install the pinned Teach Me beta safely for Codex or Claude Code on Linux or macOS.

set -eu

PINNED_VERSION="1.0.0-beta.2"
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
        "  --target-host HOST      codex (default) or claude-code." \
        "  --install-root PATH     Override the selected host's skills directory." \
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
target_host="codex"
install_root=""
archive_source=""
expected_checksum=""
archive_supplied=0
checksum_supplied=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --version|--target-host|--install-root|--archive|--checksum)
            [ "$#" -ge 2 ] || fail "$1 requires a value"
            option="$1"
            value="$2"
            shift 2
            case "$option" in
                --version) requested_version="$value" ;;
                --target-host) target_host="$value" ;;
                --install-root) install_root="$value" ;;
                --archive) archive_source="$value"; archive_supplied=1 ;;
                --checksum) expected_checksum="$value"; checksum_supplied=1 ;;
            esac
            ;;
        -h|--help) usage; exit 0 ;;
        *) fail "unknown option: $1" ;;
    esac
done

[ "$requested_version" = "$PINNED_VERSION" ] || fail "this installer supports only version $PINNED_VERSION"
case "$target_host" in
    codex)
        host_label="Codex"
        reload_message="Reload Codex."
        ;;
    claude-code)
        host_label="Claude Code"
        reload_message="Restart Claude Code."
        ;;
    *) fail "target host must be codex or claude-code" ;;
esac
if [ "$checksum_supplied" -eq 1 ]; then
    case "$expected_checksum" in
        *[!0-9a-f]*|'') fail "checksum must be 64 lowercase hexadecimal characters" ;;
    esac
    [ "${#expected_checksum}" -eq 64 ] || fail "checksum must be 64 lowercase hexadecimal characters"
fi

if [ -z "$install_root" ]; then
    [ -n "${HOME:-}" ] || fail "HOME is unavailable; pass --install-root"
    case "$target_host" in
        codex)
            if [ -n "${CODEX_HOME:-}" ]; then
                install_root="$CODEX_HOME/skills"
            else
                install_root="$HOME/.codex/skills"
            fi
            ;;
        claude-code) install_root="$HOME/.claude/skills" ;;
    esac
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
        printf '%s\n' "Teach Me disabled safely for $host_label at $disabled. $reload_message"
        exit 0
        ;;
    restore)
        [ -d "$disabled" ] || fail "no disabled installation exists at $disabled"
        [ ! -e "$target" ] || fail "active installation already exists at $target"
        mv "$disabled" "$target"
        printf '%s\n' "Teach Me restored for $host_label at $target. $reload_message"
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
        printf '%s\n' "Teach Me recovered for $host_label from $backup to $target. $reload_message"
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
archive_name="teach-me-$PINNED_VERSION.zip"
archive="$work_dir/$archive_name"
checksum_file="$archive.sha256"
extract_root="$work_dir/extracted"

copy_source() {
    source=$1
    destination=$2
    description=$3
    case "$source" in
    https://*)
        command -v curl >/dev/null 2>&1 || fail "curl is required to download the pinned release"
        curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 "$source" --output "$destination" \
            || fail "$description download failed; the existing installation was not changed"
        ;;
    http://*) fail "refusing an unencrypted $description URL" ;;
    file://*) cp "${source#file://}" "$destination" || fail "could not read local $description" ;;
    *://*) fail "unsupported $description URL scheme" ;;
    *) cp "$source" "$destination" || fail "could not read local $description" ;;
    esac
}

if [ "$archive_supplied" -eq 1 ]; then
    [ "$checksum_supplied" -eq 1 ] || fail "a custom archive requires an explicit --checksum"
else
    [ "$checksum_supplied" -eq 0 ] || fail "--checksum may be used only with a custom --archive"
    release_base="$RELEASE_BASE"
    if [ "${TEACH_ME_TESTING:-}" = "1" ] && [ -n "${TEACH_ME_TEST_RELEASE_BASE:-}" ]; then
        release_base=$TEACH_ME_TEST_RELEASE_BASE
    fi
    archive_source="$release_base/v$PINNED_VERSION/$archive_name"
    checksum_source="$archive_source.sha256"
    copy_source "$checksum_source" "$checksum_file" "checksum file"
    expected_checksum=$(awk -v expected="$archive_name" '
        {
            sub(/\r$/, "")
            digest = substr($0, 1, 64)
            separator = substr($0, 65, 2)
            filename = substr($0, 67)
            if (length(digest) != 64 || digest ~ /[^0-9a-f]/ || separator != "  " || filename != expected) {
                malformed = 1
            } else {
                records++
                value = digest
            }
        }
        END {
            if (malformed || records != 1) exit 1
            print value
        }
    ' "$checksum_file") || fail "published checksum file is malformed, missing, or ambiguous"
fi

copy_source "$archive_source" "$archive" "archive"

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
    printf '%s\n' "Teach Me $value installed for $host_label at $target. Previous installation preserved at $backup. $reload_message"
else
    printf '%s\n' "Teach Me $value installed for $host_label at $target. $reload_message"
fi
