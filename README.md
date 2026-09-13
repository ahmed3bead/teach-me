# Teach Me

An open Agent Skill for adaptive, evidence-backed teaching in **Arabic and English**.

Teach Me first understands the learner's goal and demonstrated level, then selects a suitable teaching strategy, checks understanding through application, and changes approach when learning fails. Important claims are researched and cited when needed.

It also includes an **Educator Mode** for teachers, trainers, and parents who want to turn an authorized curriculum into age-appropriate lesson plans, explanations, activities, differentiated materials, and assessments while preserving traceability to the source.

**Source-Grounded Mode** lets a learner study from a book, video, playlist, course, website, or recording. The agent records what it actually inspected, tests its understanding before teaching, and clearly separates the source's claims from verification and added explanation.

The **Integration Core** treats audience and source as independent choices, so source-grounded learning also works for educators. Connected session, objective, lesson, assessment, evidence, and checkpoint identifiers let the agent resume from demonstrated learning instead of repeating onboarding or confusing content completion with mastery.

For any named book, field, course, tool, framework, or standard, Teach Me performs a broad research sweep before substantial instruction. It builds a role-based knowledge base across relevant official, academic, audiovisual, practical, community, paid, and free sources while clearly recording what was actually accessible and inspected.

For a detailed whole-book, course, curriculum, or broad-subject request, Teach Me now creates a structured curriculum artifact before teaching at length. Markdown is the editable default; print-ready PDF is available on request. Modules, lessons, outcomes, sources, practice, assessment, and resume checkpoints replace unstructured chat lectures.

`v0.5.0` adds a beginner-safe entry experience. A learning pack starts with `START-HERE.md`, explains the benefit and full journey in plain language, delivers the first real lesson instead of empty folders, and always ends with one exact action. When files or persistent memory are unavailable, Chat-only Mode teaches progressively and provides a portable `TEACH-ME` resume code.

> Teach for demonstrated progress, not information volume.

## Languages

- Modern Standard Arabic (`ar-MSA`)
- Natural Egyptian Arabic (`ar-EG`)
- English (`en`)
- Natural bilingual use when technical terminology benefits from it

## Install

Copy the `teach-me` directory into the skills directory supported by your agent. For Codex:

```bash
git clone https://github.com/ahmed3bead/teach-me.git
mkdir -p ~/.codex/skills
cp -R teach-me ~/.codex/skills/teach-me
```

Restart or reload the agent after installation. Other Agent Skills-compatible clients may use a project-level or user-level skills directory; follow the client's documentation.

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
اشرح لي الكتاب كله بالتفصيل بالعربي المصري، واعمل الأول ملف Markdown كمنهج منظم أقدر أمشي عليه وأرجع له.
```

## Domain teaching packs

The core skill remains general. Optional packs specialize how a subject should be taught without duplicating the teacher, evidence, privacy, or safety rules. Planned first packs cover AI literacy, English communication, programming, data and spreadsheets, design, digital marketing, photography and video, and project management.

See [`domain-packs/README.md`](domain-packs/README.md) and [`docs/domain-roadmap.md`](docs/domain-roadmap.md).

## Trust model

Teach Me does not promise perfect accuracy. It requires traceable evidence for consequential claims, distinguishes verified information from inference or disagreement, and includes a correction protocol. Product-wide changes are reviewed and evaluated; the skill never rewrites itself from one user's feedback.

## Contributing

Useful contributions include reproducible teaching failures, bilingual language improvements, authoritative-source corrections, accessibility improvements, and evaluation cases. Remove personal information before opening an issue. Do not submit raw learner transcripts without explicit permission.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md). Run the repository checks with:

```bash
python3 scripts/validate.py
```

For saved connected artifacts, validate cross-file identifiers with:

```bash
python3 scripts/validate_session.py learning-session.json \
  --knowledge-base knowledge-base.json \
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

`v0.5.0` — guided learning packs across chat-only, single-file, and full workspace environments. Feedback and real-world evaluation are welcome.

## License

MIT
