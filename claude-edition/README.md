# Teach Me for Claude and Claude Code

Teach Me uses the Agent Skills open format supported by Claude and Claude Code. The same verified release archive serves both products: upload it to Claude for ordinary conversations, or install it in Claude Code for local tools and files.

The current public version is `1.0.0-beta.1`. That archive predates the Claude compatibility corrections in this development work, so do not present it as a verified Claude package. Build a development ZIP from a checkout containing these changes for private testing; the next prerelease should publish the first verified Claude-ready archive.

## Claude chat: easiest setup

Custom skills are available on Claude Free, Pro, Max, Team, and Enterprise when **Code execution and file creation** is enabled. An uploaded personal skill stays private until its owner shares it.

1. From a trusted checkout containing the Claude support changes, build the deterministic development package:

   ```bash
   python3 scripts/package_claude_skill.py
   ```

2. Verify the generated ZIP against the adjacent `.sha256` file.
3. In Claude, open **Settings → Capabilities** and enable **Code execution and file creation**.
4. Open **Customize → Skills**.
5. Select **+ → Create skill → Upload a skill**.
6. Upload `dist/teach-me-claude-1.0.0-beta.1-development.zip` and enable **Teach Me**.
7. Start a fresh chat and write one practical learning goal, or explicitly invoke `/teach-me` when that command is shown.
8. Keep the skill private during beta and run [`ACCEPTANCE_TESTS.md`](ACCEPTANCE_TESTS.md) before sharing it.

The release archive already has the required layout: one `teach-me/` folder containing `SKILL.md` and its supporting resources. Do not unzip and re-zip the files directly at the ZIP root.

## Claude Code: marketplace setup

After the Claude marketplace changes are merged into the public repository, add the Teach Me catalog and install the plugin from inside Claude Code:

```text
/plugin marketplace add ahmed3bead/teach-me
/plugin install teach-me@teach-me
```

If Claude Code asks for a reload, run `/reload-plugins`. Then ask naturally or invoke `/teach-me:teach-me` explicitly.

The repository contains both `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`. The marketplace entry deliberately omits an explicit version, so a changed Git commit is detected as a new plugin version instead of leaving users on a stale cached copy.

This repository marketplace is available as soon as the files are merged. Listing in Anthropic's separate `claude-community` marketplace requires review and approval. Until approval is confirmed, do not advertise `teach-me@claude-community` as installable.

## Claude Code: private development fallback

Claude Code loads personal skills from `~/.claude/skills/<skill-name>/SKILL.md`. Run the installer from a trusted checkout of this repository.

First build the development ZIP with `python3 scripts/package_claude_skill.py`. Then install that exact local archive and checksum.

### Linux or macOS

```bash
archive="dist/teach-me-claude-1.0.0-beta.1-development.zip"
checksum=$(awk '{print $1}' "$archive.sha256")
sh installers/install.sh install --target-host claude-code --version 1.0.0-beta.1 \
  --archive "$archive" --checksum "$checksum"
sh installers/install.sh version --target-host claude-code
```

### Windows PowerShell

```powershell
$archive = "dist\teach-me-claude-1.0.0-beta.1-development.zip"
$checksum = (Get-Content "$archive.sha256").Split()[0]
.\installers\install.ps1 -Action install -TargetHost claude-code -Version "1.0.0-beta.1" `
  -Archive $archive -Checksum $checksum
.\installers\install.ps1 -Action version -TargetHost claude-code
```

Restart Claude Code, then ask naturally or invoke `/teach-me`.

## Update, disable, restore, and recover

Use the same host option for every lifecycle command so the installer selects Claude Code's skills directory.

| Operation | Linux or macOS | Windows PowerShell |
|---|---|---|
| Update | Repeat the verified local-archive options used for installation | Repeat the verified local-archive options used for installation |
| Disable | `sh installers/install.sh disable --target-host claude-code` | `.\installers\install.ps1 -Action disable -TargetHost claude-code` |
| Restore | `sh installers/install.sh restore --target-host claude-code` | `.\installers\install.ps1 -Action restore -TargetHost claude-code` |
| Recover | `sh installers/install.sh recover --target-host claude-code` | `.\installers\install.ps1 -Action recover -TargetHost claude-code` |

The default Claude Code destination is `~/.claude/skills/teach-me`. An explicit `--install-root` or `-InstallRoot` still overrides the default. The installer verifies the supplied package checksum, preserves an existing installation, and never starts a model evaluation or paid API. Once a Claude-ready prerelease is published and pinned, the local archive options can be removed from these commands.

## What is the same, and what differs?

Claude chat and Claude Code use the same teaching contract: goal discovery, progressive explanation, a materially different representation after confusion, assessment only after consent, evidence-bounded progress, source honesty, privacy, and English or simplified Modern Standard Arabic.

Claude Code adds local file access, repository scripts, schemas, resumable artifacts, deterministic validation, and technical workflows. Claude chat is simpler on web and supported mobile surfaces, but only capabilities exposed in the current chat may be used or claimed. Results may differ across models, tools, context windows, and product surfaces.

## Official platform references

- [Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude)
- [Create custom Claude skills](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Claude Code plugins](https://code.claude.com/docs/en/plugins)
- [Claude Code plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
