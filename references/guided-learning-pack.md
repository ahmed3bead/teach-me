# Guided learning pack

Use this contract for learners starting a subject, whole-source journeys, and delivery across environments with different file or continuity capabilities.

## Capability routing

Inspect available capabilities silently and choose the strongest supported delivery:

1. **Pack mode:** when folders and files can be created, produce `START-HERE.md`, `CURRICULUM.md`, the first real lesson, its practice, and a progress artifact. Do not create empty module scaffolding.
2. **Single-file mode:** when one maintained file is practical, create or update one Markdown learning guide containing onboarding, curriculum, current lesson, practice, and checkpoint.
3. **Chat-only mode:** when files cannot be created, teach one bounded lesson per turn and include a portable resume code. Never imply that a file or persistent memory exists.

PDF is a presentation format, not the only progress record. Keep a Markdown or structured checkpoint when continuity is available.

## Beginner-safe onboarding

Assume no subject knowledge until demonstrated, but do not erase transferable experience. An experienced programmer new to distributed systems may skip basic programming explanations after a tiny diagnostic.

The entry experience must explain in plain language:

- what the subject is and why it matters for the learner's goal;
- what the learner will be able to do, with concrete examples;
- the complete journey at a high level and why it is ordered that way;
- expected time, tools, prerequisites, costs, and safe alternatives;
- how a lesson works: explanation, example, action, evidence, feedback, review;
- what “understood” means and how mastery is demonstrated;
- what to do when confused, blocked, short on time, or returning later;
- exactly where to begin now.

Define every new term on first use. Reduce optional choices early. Prefer a tiny diagnostic that reveals relevant prior knowledge without making the learner design the course.

## START-HERE contract

Use `templates/start-here.md` where files are supported. This file is a learner-facing guide, not project metadata. It must link to the curriculum and first real lesson, name the expected response from the learner, and show one worked example of completing a lesson.

Keep a small dashboard near the top: goal, current module and lesson, demonstrated state, estimated time for the current action, one current action, and the next checkpoint.

Every referenced path must exist when the pack is delivered. If only the first lesson exists, label later lessons as planned in the curriculum rather than linking to missing files.

## One-action handoff

End each learner-facing turn with one instruction containing the exact file and section or chat activity, the expected time, and what the learner should send back. Do not end with multiple equal options unless the learner must make a material choice.

## Portable resume code

In Chat-only Mode, and optionally in file modes, include a compact checkpoint:

`TEACH-ME:v1:<subject-slug>:<language>:<module-id>:<lesson-id>:<state>`

Allowed states are `not-started`, `introduced`, `practised-with-help`, `applied-independently`, `transferred`, and `retained`. Use non-sensitive identifiers only. The code is a locator, not proof of mastery or a replacement for evidence.

When resuming, validate and restate the interpreted checkpoint, request only missing material context, and continue from the next unproven objective. Never claim access to earlier answers that are not present.
