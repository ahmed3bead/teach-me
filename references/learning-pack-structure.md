# Learning pack structure

Keep internal teaching machinery separate from the learner's path.

## Learner-facing surface

The learner starts only at `START-HERE.md`. Keep these visible and navigable:

- `START-HERE.md`: dashboard and one current action;
- `CURRICULUM.md`: the complete map, with later lessons marked planned until created;
- `lessons/<lesson-id>.md`: the current lesson;
- `practice/<lesson-id>.md`: activity and submission instructions;
- `PROGRESS.md`: understandable evidence, reviews, and resume point.

Teacher-facing research, coverage, claims, diagnostics, rubrics, and misconception maps belong under `internal/` when the environment supports folders. Do not ask the learner to inspect them.

## Progressive creation

Deliver the first real lesson and practice with the initial pack. Create later lesson files just in time after prerequisite evidence and plan adjustments. Never link to a file that does not exist; planned curriculum items may be plain text.

Update the dashboard after a meaningful assessment or plan change, not after every conversational message. Keep one authoritative current action and one authoritative checkpoint. Archive superseded generated material when practical instead of leaving contradictory active instructions.

## Chat and single-file equivalents

In Single-file Mode, use a table of contents and clearly mark `Dashboard`, `Curriculum`, `Current lesson`, `Practice`, and `Checkpoint`. In Chat-only Mode, show only the current lesson state, one action, and portable resume block; do not dump internal ledgers.
