# Teach Me v1.0.0-beta.1 release notes

`v1.0.0-beta.1` is a public beta. It is not the stable `v1.0.0` release and does not satisfy the stable behavioral-evidence gate.

## Validation status

- The complete deterministic validation suite passes.
- The zero-knowledge Luma Arabic simulation passed.
- The zero-knowledge Vela English simulation passed.
- The previous 90-case behavioral report with a 25.5556% pass rate is invalid because its evaluation procedure was not trustworthy. It is retained only as failed historical evidence and is not release evidence.
- The behavioral evaluator has been corrected and independently reviewed, but it has not yet been used for a complete exact-SHA model run. No behavioral release claim is made from the corrected evaluator in this beta.

## Highlights

- Adaptive teaching that can begin from genuine zero knowledge and build toward demonstrated application.
- Learner Mode for direct teaching and Educator Mode for transforming authorized curricula into traceable lesson plans and materials.
- Topic-led and Source-Grounded workflows for books, documents, accessible videos or transcripts, playlists, courses, websites, recordings, and curricula.
- Lawful independent learning paths when paid or inaccessible material cannot be inspected, without claiming to reproduce the unavailable source.
- Clear simplified Modern Standard Arabic (`ar-MSA`) and English (`en`), with foreign and technical terms preserved in their original language and script.
- Explain-first lessons, optional assessment only after learner opt-in, refusal without pressure, and a materially different representation when confusion persists.
- Traceable evidence, citations, uncertainty labels, and explicit separation between source claims, external verification, and teaching additions.
- Consent-gated resumable learning artifacts, evidence-derived progress, profile lifecycle controls, and portable non-mastery resume locators.
- Validated bidirectional HTML for mixed Arabic/English material and an optional visually inspected PDF derivative.
- Provider-neutral behavioral and teacher/learner simulation tooling, deterministic guards, and privacy-minimized feedback workflows.

## Language support

- Simplified Modern Standard Arabic (`ar-MSA`) and English (`en`) are supported.
- Technical terms and proper names remain in their original language and script.

## Limitations

- Claude and Claude Code support is prepared on the post-beta development branch and is not retroactively claimed as validated release evidence for `v1.0.0-beta.1`.
- Optional research, document, PDF, audio, transcript, video-frame, rendering, storage, and scheduling capabilities depend on the host.
- Inaccessible source content is not bypassed, reconstructed, or reproduced. An independent path is not a verified representation of that source.
- Raw video bytes are not automatically treated as watched or understood; transcript and visual coverage are recorded separately.
- Consequential, current, disputed, or high-stakes claims still require authoritative verification and may require qualified professional help.
- Domain packs marked `needs-qualified-review` remain experimental and must not be presented as expert-reviewed.
- Teach Me does not guarantee perfect factual accuracy or learning outcomes. It provides traceable evidence, explicit uncertainty, and correction paths.

## Report beta problems

Please report reproducible problems involving teaching behavior, language quality, assessment consent, source grounding, accessibility, or bidirectional and PDF rendering. Remove personal information and learner transcripts before filing a public issue.
