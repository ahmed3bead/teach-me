# Teach Me

Teach Me is an open-source Agent Skill that turns learning goals and trusted sources into adaptive, evidence-backed teaching in simplified Modern Standard Arabic and English.

[![CI](https://github.com/ahmed3bead/teach-me/actions/workflows/validate.yml/badge.svg)](https://github.com/ahmed3bead/teach-me/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/ahmed3bead/teach-me?include_prereleases&label=release)](https://github.com/ahmed3bead/teach-me/releases/tag/v1.0.0-beta.1)
[![License: MIT](https://img.shields.io/github/license/ahmed3bead/teach-me)](https://github.com/ahmed3bead/teach-me/blob/main/LICENSE)
[![Languages: ar-MSA | en](https://img.shields.io/badge/languages-ar--MSA%20%7C%20en-0f766e)](https://github.com/ahmed3bead/teach-me#supported-languages)

It is designed for learners who want progressive instruction, educators who need traceable teaching materials, and people studying from books, documents, courses, websites, recordings, or accessible audiovisual sources.

> The current release, `v1.0.0-beta.1`, is a **public beta**. It is not the stable `v1.0.0` release.

## Overview

Teach Me begins with the learner's goal and demonstrated starting point. It teaches the smallest useful next objective, offers an understanding check only at an appropriate learning boundary, and changes strategy when the first explanation does not work.

For current, specialized, disputed, or consequential claims, it requires evidence and communicates uncertainty. When a source governs the lesson, it records what was actually inspected and separates source claims from external verification and added explanation.

## Quick start

Install the skill, reload Codex, and try a prompt. Git is required; Python is needed only for repository validation and optional bundled tooling.

### Codex on Linux or macOS

```bash
skills_dir="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skills_dir"
git clone https://github.com/ahmed3bead/teach-me.git "$skills_dir/teach-me"
```

### Codex on Windows PowerShell

```powershell
$skillsDir = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME "skills" } else { Join-Path $HOME ".codex\skills" }
New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null
git clone https://github.com/ahmed3bead/teach-me.git (Join-Path $skillsDir "teach-me")
```

Restart or reload Codex, then invoke `$teach-me` explicitly or ask naturally:

```text
Teach me SQL from zero so I can analyze customer-support data. Use short examples and adapt when I get stuck.
```

## Why Teach Me

- **Adaptive instruction:** starts from evidence of current ability and changes pace, representation, or prerequisites when needed.
- **Evidence-backed claims:** cites important claims, distinguishes verification from inference, and corrects errors visibly.
- **Demonstrated progress:** treats application and transfer—not “I understand”—as learning evidence.
- **Learner control:** explains before testing and asks permission before routine understanding checks.
- **Bilingual teaching:** supports simplified Modern Standard Arabic and English while preserving technical terms in their original script.
- **Source discipline:** never claims to have inspected inaccessible documents, audio, video, or paid material.

## Key capabilities

- Goal discovery, lightweight diagnosis, progressive lessons, examples, practice, feedback, and misconception repair.
- Learner Mode, Educator Mode, topic-led teaching, and Source-Grounded Mode in compatible combinations.
- Structured curricula and lesson plans for whole books, courses, broad subjects, and authorized educator materials.
- Traceable source coverage, claims, objectives, lessons, assessments, progress, and resume checkpoints.
- Consent-gated local learner profiles and evidence-derived progress when persistent files are available.
- Accessible mixed Arabic/English HTML and an optional validated PDF derivative when rendering tools are available.
- Experimental programming and photography domain packs, both marked `needs-qualified-review`.

## How it works

1. **Establish the goal.** Teach Me identifies the desired real-world outcome, constraints, available time, and demonstrated starting point.
2. **Choose the next objective.** It selects the smallest useful step and an appropriate teaching strategy instead of producing an unstructured lecture.
3. **Teach coherently.** It explains, demonstrates, and gives the learner a manageable activity.
4. **Check by consent.** After a complete lesson, topic, module objective, or practical skill, it offers a short check and waits for the learner to opt in.
5. **Adapt from evidence.** It records what the learner demonstrated and changes strategy when progress stalls.
6. **Research when required.** It verifies important claims and narrows the promised scope when suitable evidence or source access is unavailable.

## Example prompts

### English

```text
Teach me Python functions from zero. My goal is to automate a weekly CSV report, and I have 30 minutes a day.
```

```text
Study the attached chapter, tell me what you could actually inspect, verify its important claims, and teach it to me progressively.
```

```text
I have attached our onboarding curriculum. Prepare a 90-minute workshop for new managers with practice, a rubric, and source traceability.
```

### العربية

```text
علّمني أساسيات تحليل البيانات من الصفر حتى أستطيع فهم تقارير المبيعات، ولديّ 30 دقيقة يوميًا.
```

```text
ادرس هذا الكتاب، وحدد ما استطعت فحصه فعليًا، ثم تحقّق من الادعاءات المهمة وعلّمني المحتوى تدريجيًا بالعربية الفصحى المبسطة.
```

```text
هذا منهج علوم للصف الرابع. حلّله أولًا، ثم أنشئ بعد موافقتي خطة حصة مدتها 40 دقيقة مع نشاط وأسئلة تقيس الفهم.
```

## Learner, Educator, and Source-Grounded modes

Teach Me routes requests along two independent axes: the audience and the input. A learner or educator can use either topic-led teaching or Source-Grounded Mode.

| Mode | Use it for | What Teach Me does |
|---|---|---|
| Learner Mode | Learning, practising, reviewing, or getting unstuck | Diagnoses the starting point, teaches progressively, adapts, and tracks demonstrated progress when authorized |
| Educator Mode | Lesson, workshop, curriculum, activity, differentiation, or assessment design | Maps authorized material, flags gaps and conflicts, preserves traceability, and waits for approval before producing learner-facing materials when required |
| Source-Grounded Mode | Books, documents, videos, playlists, courses, websites, recordings, or curricula | Records actual access and coverage, checks understanding of the source, verifies important claims, and avoids pretending to reproduce inaccessible material |

## Supported languages

- Simplified Modern Standard Arabic (`ar-MSA`), including responses to learners who write in an Arabic dialect.
- English (`en`).
- Technical terms and proper names in their original language and script, such as `API`, `Replication`, `Contract Test`, `Prompt`, and `Database`.

The retired `ar-EG` value is accepted only as a compatibility alias and is normalized to `ar-MSA`; it does not request Egyptian Arabic. Mixed-direction Arabic HTML and PDF output isolates left-to-right terms, code, numbers, paths, and URLs.

## Installation

The [quick start](#quick-start) installs Teach Me as a user-level Codex skill with `SKILL.md` at `teach-me/SKILL.md`. Avoid a nested `teach-me/teach-me/SKILL.md` directory.

Normal teaching requires a compatible Agent Skills host that can read `SKILL.md` and its references. Repository development and validation require Python 3.10 or newer plus the exact packages in `requirements-dev.txt`.

Other Agent Skills-compatible hosts may use a project-level or user-level skills directory. Follow the host's documentation and preserve the repository root layout. Capability-specific behavior is documented in [`docs/compatibility.md`](docs/compatibility.md).

## Updating and disabling

### Linux or macOS

```bash
skills_dir="${CODEX_HOME:-$HOME/.codex}/skills"

# Update.
git -C "$skills_dir/teach-me" pull --ff-only

# Disable without deleting.
mv "$skills_dir/teach-me" "$skills_dir/teach-me.disabled"

# Restore.
mv "$skills_dir/teach-me.disabled" "$skills_dir/teach-me"
```

### Windows PowerShell

```powershell
$skillsDir = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME "skills" } else { Join-Path $HOME ".codex\skills" }
$skillPath = Join-Path $skillsDir "teach-me"
$disabledPath = Join-Path $skillsDir "teach-me.disabled"

# Update.
git -C $skillPath pull --ff-only

# Disable without deleting.
Move-Item -Path $skillPath -Destination $disabledPath

# Restore.
Move-Item -Path $disabledPath -Destination $skillPath
```

Reload Codex after installing, updating, disabling, or restoring the skill.

## Optional capabilities

Teach Me remains usable for core conversational teaching without optional integrations. It uses a capability only when the host exposes it.

| Capability | What it enables | Fallback when unavailable |
|---|---|---|
| File read/write | Connected curricula, lessons, evidence, and resumable local sessions | Teach in chat and provide a portable `TEACH-ME:v2` locator |
| Web research | Current, specialized, and broad-source verification | Disclose the limit and narrow the claim or lesson scope |
| Document or PDF extraction | Evidence-bounded inspection of supplied files | Ask for accessible text or teach an independently researched scope |
| Audio, transcript, or video-frame access | Timestamped spoken-content or sampled visual coverage | Do not claim audiovisual coverage |
| HTML/PDF rendering | Validated bidirectional learning packs and checked PDF output | Provide structured chat or source HTML |
| Persistent scheduling | Authorized evidence-based review reminders | Provide a portable review plan |

The repository includes an optional local Ollama evaluation adapter. Ollama is **not required for normal use**, is not contacted by deterministic validation, and should run only when someone explicitly chooses local model evaluation. External hosts, models, search, transcription, storage, and rendering services may have their own costs.

## Project status and current limitations

`v1.0.0-beta.1` is the latest public beta, not the stable `v1.0.0` release.

- Accuracy and learning outcomes are not guaranteed.
- Important, current, disputed, consequential, or high-stakes claims require suitable evidence and may require qualified professional review.
- Source support depends on host capabilities; inaccessible material is not bypassed, reconstructed, or presented as inspected.
- Raw video bytes do not prove transcript or visual understanding. Spoken and on-screen coverage must be established separately.
- PDF rendering depends on the pinned Python packages and platform libraries required by WeasyPrint; validated HTML remains the accessible source of truth when rendering is unavailable.
- The programming and photography domain packs remain experimental until qualified review.
- The corrected full 90-case exact-SHA behavioral run remains a requirement for the stable release. Earlier invalid behavioral results are not release evidence.

See [`RELEASE_NOTES.md`](RELEASE_NOTES.md) for beta details and [`CHANGELOG.md`](CHANGELOG.md) for version history.

## Documentation

| Document | Purpose |
|---|---|
| [`SKILL.md`](SKILL.md) | Authoritative teaching, evidence, language, safety, and routing contract |
| [`RELEASE_NOTES.md`](RELEASE_NOTES.md) | Current public-beta highlights, evidence status, and limitations |
| [`CHANGELOG.md`](CHANGELOG.md) | Version-by-version history |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution standards and privacy requirements |
| [`SECURITY.md`](SECURITY.md) | Supported versions and private vulnerability reporting |
| [`docs/compatibility.md`](docs/compatibility.md) | Host capability matrix, fallbacks, and cost model |
| [`docs/model-evaluation.md`](docs/model-evaluation.md) | Behavioral and simulation evaluation protocol |
| [`docs/release-checklist.md`](docs/release-checklist.md) | Stable-release evidence gates |
| [`domain-packs/README.md`](domain-packs/README.md) | Domain-pack contract and implemented pilots |

## Development and validation

Install Python 3.10 or newer and the pinned development dependencies. The Linux `validate` job in [`.github/workflows/validate.yml`](.github/workflows/validate.yml) defines the complete deterministic command set:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pip check
python3 scripts/check_dependency_pins.py
python3 scripts/check_context_budget.py
python3 scripts/validate.py
python3 scripts/validate_schemas.py
python3 scripts/validate_evals.py
python3 scripts/validate_domain_packs.py
python3 scripts/validate_simulations.py
python3 scripts/run_behavioral_evals.py --validate-only
python3 scripts/run_agent_simulations.py --validate-only
python3 scripts/test_behavioral_eval_runner.py
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

This suite validates structure, schemas, evaluation definitions, domain packs, runner behavior, packaging, rendering, source inspection, and connected fixtures. `scripts/test_ollama_eval_adapter.py` runs unit tests only; it does not start or contact Ollama. Deterministic validation does not establish real-model teaching quality—see [`docs/model-evaluation.md`](docs/model-evaluation.md).

## Contributing

Contributions are welcome when they provide a reproducible teaching failure, an authoritative correction, a bilingual language improvement, an accessibility improvement, or an evaluation grounded in observable behavior.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request. Remove personal data, private transcripts, protected curricula, and other material you are not authorized to share.

## Security

Report suspected vulnerabilities privately through [GitHub Private Vulnerability Reporting](https://github.com/ahmed3bead/teach-me/security/advisories/new). Do not include learner data, credentials, private curricula, or unrelated personal information. See [`SECURITY.md`](SECURITY.md) for the full policy.

## License

Teach Me is released under the [MIT License](LICENSE).

## لمحة بالعربية

`Teach Me` مهارة مفتوحة المصدر للتعليم المتكيف والمدعوم بالأدلة. تبدأ من هدف المتعلم وما يستطيع تطبيقه فعليًا، ثم تقدم شرحًا تدريجيًا بالعربية الفصحى المبسطة أو الإنجليزية، وتغيّر طريقة التعليم عند الحاجة. كما تساعد المعلّمين على تحويل المناهج المصرح باستخدامها إلى خطط وأنشطة وتقييمات قابلة للتتبع، وتوضح دائمًا ما استطاعت فحصه من المصادر.

الإصدار الحالي `v1.0.0-beta.1` نسخة تجريبية عامة، وليس الإصدار المستقر `v1.0.0`. لا تضمن المهارة دقة كاملة أو نتيجة تعليمية محددة، لذلك تتطلب الادعاءات المهمة أدلة مناسبة وتعرض حدود الوصول وعدم اليقين بوضوح.
