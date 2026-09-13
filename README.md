# Teach Me

An open Agent Skill for adaptive, evidence-backed teaching in **Arabic and English**.

Teach Me first understands the learner's goal and demonstrated level, then selects a suitable teaching strategy, checks understanding through application, and changes approach when learning fails. Important claims are researched and cited when needed.

It also includes an **Educator Mode** for teachers, trainers, and parents who want to turn an authorized curriculum into age-appropriate lesson plans, explanations, activities, differentiated materials, and assessments while preserving traceability to the source.

**Source-Grounded Mode** lets a learner study from a book, video, playlist, course, website, or recording. The agent records what it actually inspected, tests its understanding before teaching, and clearly separates the source's claims from verification and added explanation.

The **Integration Core** treats audience and source as independent choices, so source-grounded learning also works for educators. Connected session, objective, lesson, assessment, evidence, and checkpoint identifiers let the agent resume from demonstrated learning instead of repeating onboarding or confusing content completion with mastery.

For any named book, field, course, tool, framework, or standard, Teach Me performs a broad research sweep before substantial instruction. It builds a role-based knowledge base across relevant official, academic, audiovisual, practical, community, paid, and free sources while clearly recording what was actually accessible and inspected.

For a detailed whole-book, course, curriculum, or broad-subject request, Teach Me creates a structured curriculum artifact before teaching at length. Markdown remains the editable default for single-direction material. Mixed Arabic/English learning packs use semantic HTML so technical terms, code, numbers, and punctuation keep the correct visual order; print-ready PDF can be generated from the same validated HTML. Modules, lessons, outcomes, sources, practice, assessment, and resume checkpoints replace unstructured chat lectures.

`v0.5.0` adds a beginner-safe entry experience. A learning pack starts with `START-HERE.md`, explains the benefit and full journey in plain language, delivers the first real lesson instead of empty folders, and always ends with one exact action. When files or persistent memory are unavailable, Chat-only Mode teaches progressively and provides a portable `TEACH-ME` resume code.

`v0.6.0` adds the teaching core: prerequisite diagnosis, a progressive lesson arc, cognitive-load controls, misconception repair, graduated hints, observable mastery decisions, and an Arabic teaching style contract.

`v0.7.0` extends teaching across time: adaptive retrieval and spacing, contextual learner-model updates, accessible equivalents, ethical recovery from disengagement, and a simpler learner-facing pack separated from internal evidence files.

`v0.7.1` adds an optional integration foundation for multimodal video inspection, capability providers, external-skill adoption, research rigor review, and reuse-first simplicity. Teach Me remains functional without external tools.

`v0.8.0` makes bidirectional rendering part of teaching correctness. Mixed Arabic/English packs default to accessible HTML with isolated left-to-right terms and code, while PDF becomes a validated derivative rather than a separate source.

`v0.8.1` hardens language continuity, inaccessible-modality recovery, portable resume validation, and learner-data lifecycle controls after a two-agent adversarial evaluation.

`v0.8.2` separates learner-facing explanation from internal assessment. Beginner journeys now default to coherent explain-first teaching, with low-pressure checks at natural boundaries instead of a quiz after every concept.

`v0.8.3` defines those boundaries precisely. Routine questions are offered only after a complete lesson, topic, module objective, or practical skill—not after a page or paragraph—and begin only when the learner opts in. Accepted checks use a few diagnostic questions to adapt the next teaching step rather than manufacture a score.

`v1.0.0-rc.1` turns the contract into a release candidate with evidence-derived progress, crash-safe sessions, profile lifecycle enforcement, closed-book teacher/learner simulations, checked HTML-to-PDF output, evidence-bounded source intake, pinned automation dependencies, and a stable-release evidence receipt.

> Teach for demonstrated progress, not information volume.

## Languages

- Modern Standard Arabic (`ar-MSA`)
- Natural Egyptian Arabic (`ar-EG`)
- English (`en`)
- Natural bilingual use when technical terminology benefits from it

## Install

Clone directly into the skills directory supported by your agent. This avoids the nested `teach-me/teach-me` folder produced when a copy command is repeated.

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

Restart or reload the agent, then ask it to use `$teach-me`. Other Agent Skills-compatible clients may use a project-level or user-level skills directory; follow that client's documentation and keep `SKILL.md` at the root of the installed `teach-me` directory.

### Verify, update, or safely remove

```bash
skills_dir="${CODEX_HOME:-$HOME/.codex}/skills"
test -f "$skills_dir/teach-me/SKILL.md"
python3 "$skills_dir/teach-me/scripts/validate.py"

# Update an existing Git clone.
git -C "$skills_dir/teach-me" pull --ff-only

# Recoverable removal: move it out of the active skills directory.
mv "$skills_dir/teach-me" "$skills_dir/teach-me.disabled"
```

If an older copy has `teach-me/teach-me/SKILL.md`, move the inner folder to a temporary location, remove or archive the outer duplicate, then install fresh with the command above. See [`docs/compatibility.md`](docs/compatibility.md) for capability-dependent behavior and costs.

## Use

Invoke `$teach-me` explicitly or ask naturally:

```text
Teach me photography from zero so I can take better product photos with my phone.
```

```text
علّمني الإنجليزي من الصفر عشان أقدر أتعامل مع العملاء في الشغل.
```

The skill can run without persistent files. If the environment supports files and the learner wants continuity, it can maintain a local learner profile and progress record after asking permission.

### Educator examples

```text
I have attached our onboarding curriculum. Prepare a 90-minute workshop for new managers, including practice, a rubric, and source traceability.
```

```text
ده منهج العلوم للصف الرابع. حلله الأول، وبعد موافقتي جهز الحصة الأولى للأطفال في 40 دقيقة مع نشاط بسيط وأسئلة تقيس الفهم.
```

The agent first maps the supplied curriculum and flags gaps, inferred objectives, external additions, and possible conflicts. The educator approves that map before student-facing materials are produced.

### Source-grounded examples

```text
Study this YouTube playlist, verify the important claims, then teach it to me progressively in Egyptian Arabic.
```

```text
This paid course page is inaccessible. Use only its public topic and learning outcomes to build an independent path from lawful, authoritative sources. Do not claim to reproduce the course.
```

```text
اشرح لي الكتاب كله بالتفصيل بالعربي المصري، واعمل منهج HTML منظم يحافظ على اتجاه العربي والمصطلحات الإنجليزية.
```

## Domain teaching packs

The core skill remains general. Optional packs specialize how a subject should be taught without duplicating the teacher, evidence, privacy, or safety rules. The first testable pilots cover programming and photography; both are explicitly marked as needing qualified review. Future candidates include AI literacy, English communication, data and spreadsheets, design, digital marketing, video, and project management.

See [`domain-packs/README.md`](domain-packs/README.md) and [`docs/domain-roadmap.md`](docs/domain-roadmap.md).

## Trust model

Teach Me does not promise perfect accuracy. It requires traceable evidence for consequential claims, distinguishes verified information from inference or disagreement, and includes a correction protocol. Product-wide changes are reviewed and evaluated; the skill never rewrites itself from one user's feedback.

## Contributing

Useful contributions include reproducible teaching failures, bilingual language improvements, authoritative-source corrections, accessibility improvements, and evaluation cases. Remove personal information before opening an issue. Do not submit raw learner transcripts without explicit permission.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md). Install development dependencies and run the repository checks with:

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate.py
python3 scripts/validate_schemas.py
python3 scripts/validate_evals.py
python3 scripts/validate_domain_packs.py
python3 scripts/validate_simulations.py
python3 scripts/check_dependency_pins.py
python3 scripts/check_context_budget.py
python3 scripts/test_validate_session.py
python3 scripts/test_validate_resume.py
python3 scripts/test_behavioral_eval_runner.py
python3 scripts/test_agent_simulations.py
python3 scripts/test_render_learning_pack.py
python3 scripts/test_inspect_source.py
```

Fixture model adapters prove runner plumbing only. See [`docs/model-evaluation.md`](docs/model-evaluation.md) before making model-quality or release claims.

For saved connected artifacts, validate cross-file identifiers with:

```bash
python3 scripts/validate_session.py learning-session.json \
  --knowledge-base knowledge-base.json \
  --curriculum-map curriculum-map.json \
  --curriculum study-curriculum.json \
  --coverage source-coverage.json \
  --claims claim-ledger.json \
  --lesson lesson-plan.json \
  --progress progress.json
```

## العربية

`Teach Me` هي مهارة مفتوحة المصدر تحول الـAI إلى مدرس متكيف، وليس مجرد مولّد شرح. تفهم هدف المتعلم ومستواه من خلال أدلة عملية، وتدعم العربية الفصحى والمصرية والإنجليزية، وتغيّر طريقة التدريس عندما لا تنجح المحاولة الأولى.

لا تعتبر قول المتعلم «فهمت» دليلًا كافيًا، ولا تعرض الادعاءات المهمة بدرجة ثقة أكبر مما تسمح به مصادرها.

## Status

`v1.0.0-rc.1` technical candidate. Repository tests, simulated runner plumbing, connected artifacts, and Arabic/English PDF rendering are executable. Stable `v1.0.0` remains blocked until real named-model evaluation and recorded Arabic/English human review satisfy the release receipt.

## License

MIT
