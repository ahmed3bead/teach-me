# Safe improvement loop

The skill may adapt to one learner at runtime, but product-wide evolution happens only through reviewed releases.

## Failure categories

- `knowledge-error`
- `missing-context`
- `bad-source`
- `level-mismatch`
- `teaching-failure`
- `assessment-failure`
- `language-failure`
- `memory-failure`
- `unsafe-advice`
- `tool-failure`

## Release loop

1. Collect minimal, consented, structured feedback.
2. Group repeated failures without treating correlation as proof.
3. Create a reproducible evaluation case.
4. Propose the narrowest instruction, reference, or tool change.
5. Compare old and candidate versions for learning, accuracy, safety, language, latency, and cost.
6. Require human review for global changes and specialist review for consequential domains.
7. Release with a version, changelog entry, staged exposure, monitoring, and rollback.

Never optimize only for ratings or engagement. A pleasant but inaccurate lesson is a regression. Never train on or publish raw learner content without explicit permission.

## Local feedback pipeline

When the user explicitly consents to recording a minimized event, validate it against `schemas/feedback.schema.json`, set `contains_personal_data` accurately, and append it locally with `scripts/record_feedback.py`. The recorder rejects missing consent, events marked as containing personal data, malformed records, and duplicate event identifiers.

Before sharing feedback, use `scripts/aggregate_feedback.py` with a minimum group size of at least three. The aggregate contains counts and structured dimensions only; it excludes free-text summaries and suppresses small groups. Human review is still required before publication or a product-wide change. These scripts do not upload, retrain, rewrite the skill, or create a release automatically.
