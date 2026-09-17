# Teach Me v1.0.0-beta.2 release notes

`v1.0.0-beta.2` is a public testing release. It is not the stable `v1.0.0` release and does not satisfy the stable behavioral-evidence gate.

## Validation status

- The complete deterministic validation suite passes.
- The zero-knowledge Luma Arabic simulation passed.
- The zero-knowledge Vela English simulation passed.
- The immutable paid report covered 90 cases and exposed 45 failures on an earlier candidate; it was used as remediation input, not as passing release evidence.
- A forensic matrix classified every reported failure and repaired shared validator, protocol, guard, routing, and fixture causes without adding case-specific product exceptions.
- A targeted Codex subscription diagnostic covered the 14 cases previously classified as model-only: 5 passed, 8 produced educational-quality failures, and 1 produced an exact-quote grader-protocol failure.
- The targeted diagnostic had no infrastructure or response-model protocol failures and made no paid API requests.
- The targeted 14-case result is not the complete 90-case pass rate and does not authorize stable `v1.0.0` release.

## Highlights

- Public beta support for ChatGPT, Claude, Codex, and Claude Code, with host-specific setup guidance.
- Linux, macOS, and Windows installers that verify release archives against published adjacent checksums, with backup, restore, disable, and recovery flows.
- Repaired provider-neutral evaluation tooling for Ollama and Codex subscription runs.
- Privacy-minimized feedback workflows for collecting reproducible user reports without publishing learner transcripts.
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

- The stable behavioral gate has not passed; this release is intended for testing and feedback, not a stable quality claim.
- Optional research, document, PDF, audio, transcript, video-frame, rendering, storage, and scheduling capabilities depend on the host.
- Inaccessible source content is not bypassed, reconstructed, or reproduced. An independent path is not a verified representation of that source.
- Raw video bytes are not automatically treated as watched or understood; transcript and visual coverage are recorded separately.
- Consequential, current, disputed, or high-stakes claims still require authoritative verification and may require qualified professional help.
- Domain packs marked `needs-qualified-review` remain experimental and must not be presented as expert-reviewed.
- Teach Me does not guarantee perfect factual accuracy or learning outcomes. It provides traceable evidence, explicit uncertainty, and correction paths.

## Report beta problems

Please report reproducible problems involving teaching behavior, language quality, assessment consent, source grounding, accessibility, installation, or bidirectional and PDF rendering. Include the host, model, language, expected behavior, and observed behavior, but remove personal information and learner transcripts before filing a public issue.
