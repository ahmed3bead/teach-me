# Limitations

Teach Me `v1.0.0` is published as a version label, but its stable quality gates have not all passed; treat its quality evidence as beta-level. It is designed to make teaching more adaptive and evidence-aware, but it cannot guarantee a particular outcome.

## General limits

- It does not guarantee perfect factual accuracy, mastery, retention, or successful transfer.
- Important current, disputed, consequential, or high-stakes claims require suitable authoritative evidence and may require qualified professional review.
- It cannot inspect material the host cannot access. Inaccessible content is not bypassed or presented as inspected.
- Raw video bytes do not prove transcript or visual coverage; spoken and on-screen content require separate access evidence.
- It does not diagnose intelligence, disability, learning style, or a medical condition.

## Host differences

- ChatGPT and Claude model availability, context, file support, browsing, and sharing controls vary by plan and product surface.
- ChatGPT GPT creation and editing use the web Builder. The current repository package configures a private beta rather than advertising a public GPT.
- Claude Skills require Code execution and file creation to be enabled.
- Codex and Claude Code provide stronger local file and validation workflows, but their available tools and permissions still vary by environment.
- Codex PDF output depends on the pinned Python packages and required platform libraries. Validated HTML remains the accessible source of truth when rendering is unavailable.

## Quality evidence status

- The programming and photography domain packs remain experimental until qualified review.
- A complete 95-case exact-SHA behavioral run at or above the 90% threshold, with no critical failures, has not yet passed.
- The Arabic Luma closed-book simulation most recently failed a critical check.
- Earlier invalid behavioral results are not release evidence.
- Human review is owner-attested (see `human-review-attestation-2026-10-11.md`); the learner-journey and artifact reviews and the stable evidence receipt remain incomplete.

See [release notes](../RELEASE_NOTES.md), [model evaluation](model-evaluation.md), and the [release checklist](release-checklist.md) for the exact status.
