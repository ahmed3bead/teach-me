# Teach Me

**Adaptive teaching that starts from your goal, explains step by step, and changes approach when you get stuck.**

[English](README.md) · [العربية](README.ar.md)

[![CI](https://github.com/ahmed3bead/teach-me/actions/workflows/validate.yml/badge.svg)](https://github.com/ahmed3bead/teach-me/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/ahmed3bead/teach-me?include_prereleases&label=release)](https://github.com/ahmed3bead/teach-me/releases/tag/v1.0.0-beta.2)
[![License: MIT](https://img.shields.io/github/license/ahmed3bead/teach-me)](LICENSE)
[![Languages: ar-MSA | en](https://img.shields.io/badge/languages-ar--MSA%20%7C%20en-0f766e)](README.ar.md)

> **Beta:** the current public release is `v1.0.0-beta.2`. It is ready for testing, but the corrected 90-case evaluation and human review are still required before stable `v1.0.0`.

## Why Teach Me?

- Starts from what the learner wants to achieve and already knows.
- Breaks difficult topics into manageable steps.
- Changes the explanation instead of repeating it when confusion continues.
- Supports English and simplified Modern Standard Arabic.
- Can teach from authorized files and clearly separates sources from added explanation.
- Never claims mastery without evidence or starts routine assessment without consent.

## Choose your edition

| Edition | Best for | Setup |
|---|---|---|
| **ChatGPT plugin** | The easiest path for ordinary learners on the web, phone, or tablet | Install from ChatGPT after marketplace approval; [plugin status](plugins/teach-me/README.md) |
| **Custom GPT** | Private owner testing before the public plugin is listed | [Owner setup](chatgpt-edition/README.md) |
| **Claude** | Learning in a normal Claude conversation | [Claude setup](claude-edition/README.md) |
| **Codex** | Structured learning with local files, reports, and validation | [Codex setup](docs/codex-installation.md) |
| **Claude Code** | The full workflow inside Claude Code | [Claude Code setup](claude-edition/README.md#claude-code-marketplace-setup) |

Not sure? Start with the ChatGPT plugin or Claude. Choose Codex or Claude Code only when you need local files, reproducible workflows, or technical artifacts.

## Quick start

Give Teach Me one practical outcome:

```text
Teach me Docker from zero. I am a Laravel developer and want to run a real Laravel project locally with Docker.
```

The public ChatGPT plugin package is ready for marketplace review. It uses only bundled teaching instructions: no separate account, API key, server, or terminal is required for learners. Repository availability does not mean the plugin has already been approved or listed.

For Claude Code:

```text
/plugin marketplace add ahmed3bead/teach-me
/plugin install teach-me@teach-me
/teach-me:teach-me
```

For Codex on Linux or macOS:

```bash
sh installers/install.sh install --version 1.0.0-beta.2
```

Windows PowerShell:

```powershell
.\installers\install.ps1 -Action install -Version "1.0.0-beta.2"
```

See [Getting started](docs/getting-started.md) for the complete first-session walkthrough and update instructions.

## How it teaches

Teach Me follows a simple loop:

1. Understand the goal and starting point.
2. Choose the smallest useful next objective.
3. Explain with an example.
4. Change strategy when the learner is stuck.
5. Offer a short check only after a meaningful unit and with consent.

Read [How Teach Me works](docs/how-it-works.md) for learner, educator, and source-grounded workflows.

## Documentation

| Guide | What it covers |
|---|---|
| [Getting started](docs/getting-started.md) | Edition choice, setup, updates, and first session |
| [How it works](docs/how-it-works.md) | Teaching method and supported workflows |
| [Example prompts](docs/examples.md) | Ready-to-use English and Arabic prompts |
| [Limitations](docs/limitations.md) | Current beta boundaries and host differences |
| [Development](docs/development.md) | Local validation and contributor commands |
| [Compatibility](docs/compatibility.md) | Detailed host capability matrix |
| [ChatGPT plugin submission](docs/chatgpt-plugin-submission.md) | Public-review boundary and publisher checklist |
| [Model evaluation](docs/model-evaluation.md) | Behavioral and simulation evidence protocol |
| [Release checklist](docs/release-checklist.md) | Gates required for stable release |

Platform-specific guides:

- [ChatGPT Edition](chatgpt-edition/README.md)
- [Claude and Claude Code](claude-edition/README.md)
- [Codex installation](docs/codex-installation.md)

## Status and limitations

Teach Me does not guarantee perfect accuracy, mastery, retention, or a particular learning outcome. Available models, tools, files, and context differ between hosts. Important current or high-stakes claims need suitable authoritative evidence.

See [Limitations](docs/limitations.md) and [release notes](RELEASE_NOTES.md) before production or high-stakes use.

## Contributing

Contributions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md) and do not include personal data, credentials, private transcripts, protected curricula, generated reports, or model outputs.

## Security

Report vulnerabilities through [GitHub Private Vulnerability Reporting](https://github.com/ahmed3bead/teach-me/security/advisories/new). See [SECURITY.md](SECURITY.md).

## License

Released under the [MIT License](LICENSE).
