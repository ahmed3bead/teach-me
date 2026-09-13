# Release checklist

## Candidate integrity

- [ ] `SKILL.md` metadata version matches the changelog and release tag.
- [ ] Fresh Linux/macOS and Windows installation keeps `SKILL.md` at `teach-me/SKILL.md`.
- [ ] Update uses a fast-forward Git pull; removal is recoverable.
- [ ] All local structural, schema, integration, resume, and runner tests pass.
- [ ] The always-loaded skill and routed references pass `scripts/check_context_budget.py`.
- [ ] `skills-ref validate` or the host's official Agent Skills validator passes when available.

## Behavioral quality

- [ ] Run all committed evals against the candidate and the previous release using a named response model and independent grader.
- [ ] Candidate case pass rate is at least 90%.
- [ ] No case marked `critical` fails.
- [ ] No safety, privacy, evidence, Arabic-language, accessibility, or learner-control regression is accepted for aggregate gains.
- [ ] Review a sample of grader decisions manually in both Arabic and English.
- [ ] Test at least one complete learner journey and one educator/source-grounded journey.
- [ ] Run the zero-knowledge teacher/learner simulations; meet gain and transfer thresholds with no critical failure.
- [ ] Keep real-model reports with exact model versions and commands; fixture adapters count only as plumbing tests.

## Artifact quality

- [ ] Render and inspect one mixed Arabic/English HTML learning pack.
- [ ] Generate its PDF derivative and inspect every page for bidi, clipping, links, and code readability.
- [ ] Validate one full connected fixture across session, sources, curriculum, claims, lesson, assessment, and progress.
- [ ] Inspect a real local PDF through `scripts/inspect_source.py` and confirm transcript-only video evidence does not claim visual coverage.

## Governance and release

- [ ] Feedback examples are consented, minimized, reproducible, and contain no raw learner transcript or personal data.
- [ ] Consequential domain changes have an appropriate reviewer.
- [ ] Changelog documents migrations, known limitations, and rollback.
- [ ] Package checksum is published with the release.
- [ ] Create the signed/tagged release only after the candidate commit passes the checks above.
- [ ] Create a `real-release` evidence receipt matching `schemas/release-evidence.schema.json`; stable packaging must verify it.
