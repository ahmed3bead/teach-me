# Getting started

This guide helps you choose an edition, complete setup, and begin a useful first learning session.

## Choose an edition

| You want to… | Choose |
|---|---|
| Learn in a normal browser, phone, or tablet conversation | ChatGPT or Claude |
| Work with local files, reports, validation, or repeatable technical workflows | Codex or Claude Code |

All editions follow the same essential teaching contract. Results can still differ because each host provides different models, tools, context limits, and file access.

## ChatGPT

Use the ready-to-configure private beta package in [`chatgpt-edition/`](../chatgpt-edition/README.md). Learners need no terminal or local installation after the GPT owner completes the setup.

## Claude

Build and upload the verified Skill ZIP by following the [Claude setup guide](../claude-edition/README.md). Enable Code execution and file creation, then start a normal conversation.

## Codex

From a trusted checkout, run:

```bash
sh installers/install.sh install --version 1.0.0-beta.1
sh installers/install.sh version
```

Windows PowerShell:

```powershell
.\installers\install.ps1 -Action install -Version "1.0.0-beta.1"
.\installers\install.ps1 -Action version
```

See [Codex installation](codex-installation.md) for checksum verification, updates, disable, restore, and recovery.

## Claude Code

Inside Claude Code, run:

```text
/plugin marketplace add ahmed3bead/teach-me
/plugin install teach-me@teach-me
```

Restart Claude Code when requested, then invoke:

```text
/teach-me:teach-me
```

To update later:

```text
/plugin marketplace update teach-me
/plugin update teach-me@teach-me
```

See the [Claude Code marketplace guide](../claude-edition/README.md#claude-code-marketplace-setup) for troubleshooting and the installer fallback.

## Your first session

1. State one practical outcome.
2. Add what you already know and any time or accessibility constraints that matter.
3. Correct Teach Me if its understanding of your starting point is wrong.
4. Ask for another explanation when something does not click; it should change strategy.
5. Accept or decline a short understanding check when a meaningful unit is complete.

Example:

```text
Teach me Docker from zero. I am a Laravel developer, I have 30 minutes a day, and my goal is to run a real Laravel project locally with Docker.
```

Next: browse [example prompts](examples.md) or learn [how the teaching method works](how-it-works.md).
