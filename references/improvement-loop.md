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
