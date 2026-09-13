# Teach Me

An open Agent Skill for adaptive, evidence-backed teaching in **Arabic and English**.

Teach Me first understands the learner's goal and demonstrated level, then selects a suitable teaching strategy, checks understanding through application, and changes approach when learning fails. Important claims are researched and cited when needed.

It also includes an **Educator Mode** for teachers, trainers, and parents who want to turn an authorized curriculum into age-appropriate lesson plans, explanations, activities, differentiated materials, and assessments while preserving traceability to the source.

**Source-Grounded Mode** lets a learner study from a book, video, playlist, course, website, or recording. The agent records what it actually inspected, tests its understanding before teaching, and clearly separates the source's claims from verification and added explanation.

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

## العربية

`Teach Me` هي مهارة مفتوحة المصدر تحول الـAI إلى مدرس متكيف، وليس مجرد مولّد شرح. تفهم هدف المتعلم ومستواه من خلال أدلة عملية، وتدعم العربية الفصحى والمصرية والإنجليزية، وتغيّر طريقة التدريس عندما لا تنجح المحاولة الأولى.

لا تعتبر قول المتعلم «فهمت» دليلًا كافيًا، ولا تعرض الادعاءات المهمة بدرجة ثقة أكبر مما تسمح به مصادرها.

## Status

`v0.3.0` — learner, educator, and source-grounded MVP. Feedback and real-world evaluation are welcome.

## License

MIT
