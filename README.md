# Teach Me

Teach Me is an open-source adaptive teaching system for English and simplified Modern Standard Arabic. It starts from a learner's real goal and current knowledge, explains progressively, changes strategy when confusion persists, and treats demonstrated ability—not confidence alone—as evidence of progress.

[![CI](https://github.com/ahmed3bead/teach-me/actions/workflows/validate.yml/badge.svg)](https://github.com/ahmed3bead/teach-me/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/ahmed3bead/teach-me?include_prereleases&label=release)](https://github.com/ahmed3bead/teach-me/releases/tag/v1.0.0-beta.1)
[![License: MIT](https://img.shields.io/github/license/ahmed3bead/teach-me)](LICENSE)
[![Languages: ar-MSA | en](https://img.shields.io/badge/languages-ar--MSA%20%7C%20en-0f766e)](#supported-languages)

The current public repository release is **`v1.0.0-beta.1`**, a public beta rather than stable `v1.0.0`. The ChatGPT configuration and Claude support are also beta; no public Teach Me GPT is currently advertised.

## Choose how you want to use Teach Me

### Teach Me for ChatGPT — easiest when the Builder is available

Use normal ChatGPT conversations on supported phones, tablets, or the web. There is no terminal, GitHub knowledge, Ollama, programming knowledge, or local installation for learners. It is best for ordinary learning conversations and learning from files the current ChatGPT surface can inspect.

The ready-to-configure private beta package is in [`chatgpt-edition/`](chatgpt-edition/README.md). Builder access varies by account and current product controls. If the GPT editor opens and the **Create** button is available, the owner can proceed with the checklist. Learners can use the resulting private GPT on supported mobile, tablet, and web surfaces.

### Teach Me for Claude — easiest Claude setup

Upload a verified Teach Me Skill ZIP, enable it, and start a normal conversation. Claude currently supports personal custom skills on Free, Pro, Max, Team, and Enterprise plans when Code execution and file creation is enabled. The public `v1.0.0-beta.1` archive predates the Claude compatibility work, so private testing currently uses a development ZIP built from the updated checkout. Follow the [`Claude setup guide`](claude-edition/README.md).

### Teach Me for Codex or Claude Code — full tooling

Use the complete Agent Skill when you need structured learning workflows, educator materials, source processing, validation, resumable sessions, controlled local files, reports, artifacts, independent evaluation infrastructure, or HTML/PDF generation. The same teaching contract follows the open Agent Skills format. Use the pinned installer for [`Codex`](docs/codex-installation.md) or the [`Claude Code marketplace`](claude-edition/README.md#claude-code-marketplace-setup).

| Host | Setup | Best for | Additional capabilities |
|---|---|---|---|
| ChatGPT | Configure a private GPT | Ordinary learning on web, phone, or tablet | Current ChatGPT chat, files, and enabled tools |
| Claude | Upload the generated Skill ZIP | Ordinary learning on Claude chat | Current Claude chat, files, and enabled tools |
| Codex | Install into the Codex skills directory | Structured and technical learning workflows | Local files, scripts, schemas, artifacts, and validators |
| Claude Code | Install into `~/.claude/skills` | The same full workflow inside Claude Code | Local files, scripts, schemas, artifacts, and validators |

Every edition preserves the same essential method—goal discovery, progressive explanation, confusion recovery, assessment consent, evidence-bounded progress, bilingual teaching, source honesty, privacy, and age-appropriate delivery. Codex and Claude Code are more powerful for automation, validation, reporting, reproducibility, local file workflows, and technical control. The hosts are not technically identical, and results can differ because available models, tools, context, and execution environments differ.

## Which edition should I choose?

- Choose **ChatGPT** when you want to open a conversation on a phone, tablet, or browser and learn without setup.
- Choose **Claude** for the same simple chat experience when Claude is your preferred product.
- Choose **Codex** or **Claude Code** when the learning project needs files, repeatable validation, source ledgers, educator deliverables, reports, local sessions, or technical inspection.
- Start with a chat edition when uncertain. Move to a coding host only when the extra workflow control is useful.

## Quick start

### ChatGPT learner

If an owner has shared the private beta with you, open it in ChatGPT and send one practical goal:

```text
Teach me SQL from zero so I can analyze customer-support data. I have 30 minutes a day; use short examples and adapt when I get stuck.
```

No public GPT is currently advertised. Owners can create a private draft by following the [`ChatGPT Edition setup checklist`](chatgpt-edition/README.md).

### Claude learner

Build, upload, and enable the private development ZIP using the [`Claude setup guide`](claude-edition/README.md), then send the same practical learning goal in a normal Claude chat.

### Codex user

From a trusted checkout, the minimal pinned commands are:

```bash
sh installers/install.sh install --version 1.0.0-beta.1
sh installers/install.sh version
```

```powershell
.\installers\install.ps1 -Action install -Version "1.0.0-beta.1"
.\installers\install.ps1 -Action version
```

For a fresh machine, Linux, macOS, update, disable, restore, and recovery commands, see [`docs/codex-installation.md`](docs/codex-installation.md). Reload Codex, then invoke `$teach-me` explicitly or ask naturally.

### Claude Code user

After the marketplace files are merged into the public repository, run these commands inside Claude Code:

```text
/plugin marketplace add ahmed3bead/teach-me
/plugin install teach-me@teach-me
```

If Claude Code requests it, run `/reload-plugins`. Then invoke `/teach-me:teach-me` or ask naturally. For local development before merge, use the verified archive fallback in the [`Claude setup guide`](claude-edition/README.md#claude-code-private-development-fallback).

## First-session walkthrough

1. Tell Teach Me what you want to be able to do, what you already know, and any time or accessibility constraints that matter.
2. Correct its stated assumptions if needed. Teach Me begins with the smallest useful objective rather than an unstructured full course.
3. Read the explanation and example. If it does not click, say what feels confusing; Teach Me should change representation or revisit a prerequisite.
4. At a meaningful boundary, Teach Me may offer a short understanding check. It must wait for your consent, and you can decline without pressure.
5. Continue from what you actually demonstrate. Codex and Claude Code users may authorize local progress artifacts; chat users rely only on the visible conversation and features the platform actually provides.

## Example prompts

### English

```text
Teach me Python functions from zero. My goal is to automate a weekly CSV report, and I have 30 minutes a day.
```

```text
Study the attached chapter, tell me what you could actually inspect, verify its important claims, and teach it to me progressively.
```

```text
I have attached an onboarding curriculum I am authorized to use. Prepare a 90-minute workshop for new managers with practice and source traceability.
```

### العربية

```text
علّمني أساسيات تحليل البيانات من الصفر حتى أستطيع فهم تقارير المبيعات، ولديّ 30 دقيقة يوميًا.
```

```text
ادرس هذا الملف، وحدد ما استطعت فحصه فعليًا، ثم تحقّق من الادعاءات المهمة وعلّمني المحتوى تدريجيًا بالعربية الفصحى المبسطة.
```

```text
هذا منهج علوم للصف الرابع ومصرّح لي باستخدامه. حلّله أولًا، ثم أنشئ خطة حصة مدتها 40 دقيقة مع نشاط مناسب للعمر.
```

## How Teach Me works

1. **Establish the goal and starting point.** It asks only the questions that materially change where teaching begins.
2. **Choose one useful next objective.** It controls scope and cognitive load.
3. **Explain and demonstrate.** It uses an appropriate representation and a relevant example.
4. **Adapt to confusion.** Repeated confusion triggers a materially different representation or prerequisite intervention.
5. **Check only by consent.** Routine assessment begins only after a meaningful unit and explicit opt-in.
6. **Treat evidence honestly.** Reading or confidence alone does not establish mastery or retention.
7. **Respect sources and privacy.** It distinguishes inspected content, external verification, inference, and access limits.

The shared cross-edition behavior is maintained in [`references/core-teaching-policy.md`](references/core-teaching-policy.md). ChatGPT instructions are generated from shared repository sources, while Claude and Claude Code consume the same Agent Skill release archive.

## Learner, educator, and source-grounded workflows

Teach Me routes along two independent axes: audience and input. A learner or educator can use either topic-led teaching or source-grounded teaching.

| Workflow | Use it for | Behavior |
|---|---|---|
| Learner Mode | Learning, practising, reviewing, or getting unstuck | Starts from current evidence, teaches progressively, adapts, and tracks only demonstrated progress |
| Educator Mode | Authorized lesson, workshop, curriculum, activity, or assessment design | Maps material, flags gaps and conflicts, preserves traceability, and separates teacher-only details |
| Source-Grounded Mode | Books, documents, accessible videos or transcripts, playlists, courses, websites, recordings, or curricula | Records actual access and coverage, verifies important claims, and never presents inaccessible material as inspected |

## Supported languages

- Simplified Modern Standard Arabic (`ar-MSA`), including responses to learners who write in an Arabic dialect.
- English (`en`).
- Technical terms and proper names remain in their original language and script, such as `API`, `Replication`, `Contract Test`, `Prompt`, and `Database`.

The retired `ar-EG` value is accepted only as a compatibility alias and is normalized to `ar-MSA`; it does not request Egyptian Arabic. Mixed-direction Codex HTML and PDF output isolates left-to-right terms, code, numbers, paths, and URLs.

## Limitations

- Teach Me does not guarantee perfect factual accuracy, mastery, retention, or a particular learning outcome.
- Important current, disputed, consequential, or high-stakes claims require suitable authoritative evidence and may require qualified professional review.
- Source coverage depends on actual host access. Inaccessible material is not bypassed, reconstructed, or presented as inspected.
- Raw video bytes do not prove transcript or visual understanding; spoken and on-screen coverage must be established separately.
- ChatGPT model availability, context, file support, browsing, and builder controls vary by plan and product surface. GPT creation and editing use the web Builder; an owner who can open the editor and use **Create** can follow the repository checklist.
- OpenAI has announced a planned retirement of Custom GPTs and recommends migration to Plugins; this ChatGPT Edition package is a beta bridge whose current migration path must be rechecked before public launch.
- Claude Skills require Code execution and file creation to be enabled. Available models, tools, context, and sharing controls vary by plan and product surface.
- Codex PDF rendering depends on the pinned Python packages and required platform libraries; validated HTML remains the accessible source of truth when rendering is unavailable.
- The programming and photography domain packs remain experimental until qualified review.
- The corrected full 90-case exact-SHA behavioral run remains a requirement for a stable release. Earlier invalid behavioral results are not release evidence.

See [`RELEASE_NOTES.md`](RELEASE_NOTES.md) for beta evidence and [`docs/compatibility.md`](docs/compatibility.md) for the host capability matrix.

## Documentation

| Document | Purpose |
|---|---|
| [`chatgpt-edition/README.md`](chatgpt-edition/README.md) | ChatGPT Edition package, owner checklist, settings, and compatibility |
| [`chatgpt-edition/ACCEPTANCE_TESTS.md`](chatgpt-edition/ACCEPTANCE_TESTS.md) | Manual core and phone/tablet acceptance suite |
| [`claude-edition/README.md`](claude-edition/README.md) | Claude upload and Claude Code installation guide |
| [`claude-edition/ACCEPTANCE_TESTS.md`](claude-edition/ACCEPTANCE_TESTS.md) | Manual Claude and Claude Code acceptance suite |
| [`docs/codex-installation.md`](docs/codex-installation.md) | Pinned verified install, update, disable, restore, and recovery |
| [`SKILL.md`](SKILL.md) | Codex teaching, evidence, language, safety, routing, and artifact contract |
| [`RELEASE_NOTES.md`](RELEASE_NOTES.md) | Current public-beta evidence status and limitations |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history |
| [`docs/compatibility.md`](docs/compatibility.md) | Host capability matrix, fallbacks, and cost model |
| [`docs/pedagogy-basis.md`](docs/pedagogy-basis.md) | Research mapping and evidence limitations |
| [`docs/model-evaluation.md`](docs/model-evaluation.md) | Behavioral and simulation evaluation protocol |
| [`docs/release-checklist.md`](docs/release-checklist.md) | Stable-release evidence gates |
| [`SECURITY.md`](SECURITY.md) | Supported versions and private vulnerability reporting |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution and privacy requirements |

## Development and validation

Repository development requires Python 3.10 or newer and the exact packages in `requirements-dev.txt`. Installer tests use isolated temporary roots and local fixture archives; they never modify the user's real skill installation. Deterministic commands do not start Ollama, call paid APIs, or run behavioral model generation.

The Linux `validate` job in [`.github/workflows/validate.yml`](.github/workflows/validate.yml) defines the canonical complete deterministic command set:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pip check
python3 scripts/check_dependency_pins.py
python3 scripts/check_context_budget.py
python3 scripts/build_chatgpt_edition.py --check
python3 scripts/check_product_docs.py
python3 scripts/check_markdown_links.py
python3 scripts/test_installers.py
bash -n installers/install.sh
python3 scripts/validate.py
python3 scripts/validate_schemas.py
python3 scripts/validate_evals.py
python3 scripts/validate_domain_packs.py
python3 scripts/validate_simulations.py
python3 scripts/run_behavioral_evals.py --validate-only
python3 scripts/run_agent_simulations.py --validate-only
python3 scripts/test_behavioral_eval_runner.py
python3 scripts/test_openai_api_eval_adapter.py
python3 scripts/test_agent_simulations.py
python3 scripts/test_ollama_eval_adapter.py
python3 scripts/test_package_release.py
python3 scripts/test_feedback_pipeline.py
python3 scripts/test_validate_bidi_html.py
python3 scripts/test_validate_session.py
python3 scripts/test_validate_resume.py
python3 scripts/test_session_manager.py
python3 scripts/test_profile_lifecycle.py
python3 scripts/test_render_learning_pack.py
python3 scripts/test_inspect_source.py
python3 scripts/validate_session.py fixtures/session/learning-session.json \
  --coverage fixtures/session/source-coverage.json \
  --knowledge-base fixtures/session/knowledge-base.json \
  --curriculum-map fixtures/session/curriculum-map.json \
  --curriculum fixtures/session/study-curriculum.json \
  --claims fixtures/session/claim-ledger.json \
  --lesson fixtures/session/lesson-plan.json \
  --progress fixtures/session/progress.json
```

The portable-core matrix runs the applicable shared checks on macOS and Windows, including the native installer lifecycle. `scripts/test_ollama_eval_adapter.py` is a unit test and does not start or contact Ollama. Dynamic model simulations and paid behavioral evaluation are separate, explicitly invoked workflows and are not part of this task's deterministic validation.

## Contributing

Contributions are welcome when they provide a reproducible teaching failure, authoritative correction, bilingual language improvement, accessibility improvement, or observable evaluation. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) first. Remove personal data, private transcripts, protected curricula, credentials, generated reports, and model output before contributing.

## Security

Report suspected vulnerabilities through [GitHub Private Vulnerability Reporting](https://github.com/ahmed3bead/teach-me/security/advisories/new), not a public issue. Do not include learner data, credentials, private curricula, or unrelated personal information. See [`SECURITY.md`](SECURITY.md).

## License

Teach Me is released under the [MIT License](LICENSE).

## لمحة بالعربية

`Teach Me` نظام مفتوح المصدر للتعليم المتكيف والمدعوم بالأدلة. يبدأ من هدف المتعلم وما يعرفه فعليًا، ثم يقدّم شرحًا تدريجيًا بالعربية الفصحى المبسطة أو الإنجليزية، ويغيّر طريقة الشرح عند استمرار الالتباس. نسختا `ChatGPT` و`Claude` هما الأسهل للمحادثات العادية، بينما يضيف `Codex` و`Claude Code` أدوات الملفات المحلية، والجلسات، والتقارير، والتحقق الحتمي، ومسارات المصادر.

الإصدار الحالي `v1.0.0-beta.1` نسخة تجريبية عامة للمستودع، وليس الإصدار المستقر `v1.0.0`. لا يضمن النظام دقة كاملة أو نتيجة تعليمية محددة، لذلك يتطلب الادعاءات المهمة أدلة مناسبة ويعرض حدود الوصول وعدم اليقين بوضوح.
