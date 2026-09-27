# Teach Me | علّمني

**Open-source AI tutor and ChatGPT education plugin for step-by-step learning, lesson planning, and teaching from PDFs, books, websites, and videos.**

[English](README.md) · [العربية](README.ar.md) · [Simple usage guide](https://teach-me-guide.pages.dev/)

[![CI](https://github.com/ahmed3bead/teach-me/actions/workflows/validate.yml/badge.svg)](https://github.com/ahmed3bead/teach-me/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/ahmed3bead/teach-me?include_prereleases&label=release)](https://github.com/ahmed3bead/teach-me/releases/tag/v1.0.0-beta.2)
[![License: MIT](https://img.shields.io/github/license/ahmed3bead/teach-me)](LICENSE)

> **Availability:** the ChatGPT plugin is currently under OpenAI review. It is not yet listed publicly in the Plugins Directory. The code on `main` is newer than the submitted version; see the [current release status](docs/release-status.md) before deploying or resubmitting.

## Why Teach Me?

Teach Me is an AI tutor and lesson plan generator for learners, teachers, trainers, and parents. ChatGPT can answer a question, but a long answer is not always a good lesson. Teach Me helps ChatGPT explain ideas like a patient teacher:

- it starts from your current level;
- explains one useful step at a time;
- uses practical examples;
- tries a different explanation when something is unclear;
- asks before giving you a quiz;
- works in English and Arabic.

You can use the same plugin in three simple ways:

### Learn something yourself

Ask about any topic, say what you already know, and explain why you need it.

~~~text
Teach me Excel from zero for my work. Start with one practical example.
~~~

### Prepare a lesson

If you are a teacher, trainer, or parent, Teach Me can prepare a short teaching plan with timing, examples, activities, common mistakes, and an answer key.

~~~text
Prepare a simple 20-minute lesson about photosynthesis for 12-year-old learners.
Separate my teacher notes from the words I can say to the class.
~~~

### Explain something to your child

Include the child's age and Teach Me will simplify the vocabulary, examples, and activity.

~~~text
Explain the water cycle so I can teach it to my 10-year-old child.
Use one simple activity.
~~~

Teach Me can also work from an authorized file, PDF, book, webpage, video, YouTube playlist, course, or curriculum. It tells you what it could actually inspect instead of pretending it watched or read something unavailable.

Read the [complete feature guide](docs/features.md) or [Arabic feature guide](docs/features.ar.md) for every supported workflow.

## Quick start

After the plugin is publicly approved:

1. Open the ChatGPT Plugins Directory.
2. Add **Teach Me | علّمني**.
3. Start a normal chat and write what you need.

There is no special command to remember. `/learn`, `/teacher`, and `/kids` are optional words inside a prompt, not ChatGPT menu commands.

Try one of these:

~~~text
Teach me compound interest from zero using an everyday example.
~~~

~~~text
Prepare a 30-minute fractions lesson for fourth-grade learners.
~~~

~~~text
Teach me only from this uploaded file. Tell me what you could inspect.
~~~

You do not need a Teach Me account, API key, server, or terminal.

## Choose your edition

For most people, the **ChatGPT plugin** is the right choice.

| Edition | Who is it for? | Setup |
|---|---|---|
| **ChatGPT plugin** | Learners, teachers, trainers, and parents | Install after public approval; see [plugin status](plugins/teach-me/README.md) |
| **Claude** | People who prefer learning inside Claude | [Claude setup](claude-edition/README.md) |
| **Custom GPT** | Private testing by the project owner | [Owner setup](chatgpt-edition/README.md) |
| **Codex / Claude Code** | Developers who need local files and repeatable workflows | [Developer setup](docs/getting-started.md) |

### For developers

Codex on Linux or macOS:

~~~bash
sh installers/install.sh install --version 1.0.0-beta.2
~~~

Windows PowerShell:

~~~powershell
.\installers\install.ps1 -Action install -Version "1.0.0-beta.2"
~~~

Claude Code:

~~~text
/plugin marketplace add ahmed3bead/teach-me
/plugin install teach-me@teach-me
/teach-me:teach-me
~~~

## Documentation

| Guide | What you will find |
|---|---|
| [Simple usage guide](https://teach-me-guide.pages.dev/) | A visual guide for ordinary users |
| [Complete feature guide](docs/features.md) | Everything the plugin can do |
| [دليل المزايا بالعربية](docs/features.ar.md) | All features explained in Arabic |
| [Examples](docs/examples.md) | Prompts you can copy and use |
| [How it works](docs/how-it-works.md) | Learning, teacher, age, and source workflows |
| [Getting started](docs/getting-started.md) | Setup for every edition |
| [Privacy policy](docs/privacy-policy.md) | What the service does and does not receive |
| [Development](docs/development.md) | Tests and contribution commands |

## Status and limitations

- The ChatGPT plugin is under review and is not publicly available yet.
- Teach Me helps organize learning, but its answers are still generated by AI and can contain mistakes.
- Access to files, websites, audio, video, and images depends on the ChatGPT account and tools available.
- Important, current, medical, legal, or financial information should be checked against suitable trusted sources.

See [Limitations](docs/limitations.md), [Compatibility](docs/compatibility.md), and [release notes](RELEASE_NOTES.md).

Developers can contribute through [CONTRIBUTING.md](CONTRIBUTING.md). Released under the [MIT License](LICENSE).
