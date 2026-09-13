# Guided learning pack

Use this contract for learners starting a subject, whole-source journeys, and delivery across environments with different file or continuity capabilities.

## Capability routing

Inspect available capabilities silently and choose the strongest supported delivery:

1. **Pack mode:** when folders and files can be created, produce `START-HERE`, `CURRICULUM`, the first real lesson, its practice, and a progress artifact in one consistent source format. Use `.html` for bidirectional Arabic/English material and `.md` where direction mixing is not a display risk. Do not create empty module scaffolding.
2. **Single-file mode:** when one maintained file is practical, create or update one learning guide containing onboarding, curriculum, current lesson, practice, and checkpoint. Use HTML for bidirectional Arabic/English material.
3. **Chat-only mode:** when files cannot be created, teach one bounded lesson per turn and include a portable resume code. Never imply that a file or persistent memory exists.

PDF is a presentation format, not the only progress record. Keep an editable HTML, Markdown, or structured checkpoint when continuity is available.

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

Define every new term on first use. Reduce optional choices early. When the learner states zero subject knowledge, accept it and teach the foundation first. Use a tiny diagnostic only for transferable prerequisites that would materially change the starting point, and make it feel like an informal example rather than a placement test.

## START-HERE contract

Use `templates/start-here.md` as a content checklist where files are supported, adapting it to HTML when required by [bidirectional-output.md](bidirectional-output.md). The result is a learner-facing guide, not project metadata. It must link to the curriculum and first real lesson, state whether the current action requires a reply, and show one worked example of completing a lesson.

Keep a small dashboard near the top: goal, current module and lesson, demonstrated state, estimated time for the current action, one current action, and the next checkpoint.

Every referenced path must exist when the pack is delivered. If only the first lesson exists, label later lessons as planned in the curriculum rather than linking to missing files.

## One-action handoff

End each learner-facing turn with one instruction containing the exact file and section or chat activity and the expected time. State what the learner should send back only when the action genuinely requires a reply. During connected explanation, the action may simply be to read, observe, or continue; do not manufacture a submission or question merely to close the turn. Do not end with multiple equal options unless the learner must make a material choice.

## Portable resume code

In Chat-only Mode, and optionally in file modes, include a compact checkpoint:

`TEACH-ME:v2:<session-id>:<subject-slug>:<language>:<module-id>:<lesson-id>`

Use non-sensitive identifiers only. The code deliberately contains no mastery state: it is a locator, not proof of learning or a replacement for evidence. Restore demonstrated state only from the connected session evidence. Legacy `v1` codes may be accepted as locators, but their embedded state is an unverified claim and must not be restored as mastery.

When resuming, validate and restate the interpreted checkpoint, request only missing material context, and continue from the next unproven objective. Never claim access to earlier answers that are not present.

When execution is available, use `scripts/validate_resume.py` before interpreting the code. Handle results as follows:

- `valid`: use the v2 locator and load available connected evidence;
- `legacy-valid`: use the v1 locator, discard its claimed state, and perform a light evidence checkpoint;
- `partial`: retain only safely parsed locator fields and run a light checkpoint;
- `unsupported-version`: do not guess a migration; explain the supported version and request a fresh checkpoint;
- `malformed`: do not infer fields; ask for the original code or restart with a small diagnostic.

The validator checks structure, not truth. Even a valid code is not mastery evidence.
