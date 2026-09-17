# Changelog

## Unreleased

## 1.0.0-beta.2 - 2026-09-17

- Publish the accumulated post-beta improvements as a second public beta for real-user testing and structured feedback.
- Remediate the shared artifact-validation, grader-protocol, deterministic-guard, routing, and fixture defects identified by the immutable 90-case paid report without weakening the stable release gates.
- Restore local Ollama evaluation compatibility and strict Codex subscription grader compatibility.
- Record a targeted, non-representative diagnostic of the 14 previously model-only cases: 5 passed, 8 produced educational-quality failures, and 1 produced an exact-quote grader-protocol failure. No infrastructure or response-model protocol failures occurred, and no paid API requests were made for this diagnostic.
- Keep stable `v1.0.0` deferred until the complete exact-candidate behavioral, simulation, human-review, and artifact-review gates pass.
- Add a self-hosted Claude Code plugin marketplace and plugin manifest, with commit-based update detection and documented installation commands. Community-marketplace availability remains subject to Anthropic review.
- Add Claude chat and Claude Code support through the existing Agent Skills release archive, with a Claude upload guide, acceptance checks, and host-aware cross-platform installer defaults.
- Replace the stale managed-workspace-only ChatGPT Builder claim with capability-based guidance: owners who can access the web editor and **Create** control can use the setup checklist.
- Add a maintainable private-beta ChatGPT Edition configuration generated from a shared cross-edition teaching policy, with owner, mobile/tablet, compatibility, and manual acceptance guidance.
- Add Linux, macOS, and Windows PowerShell installers that verify release archives against published adjacent checksums, with safe backup, disable, restore, version verification, and failure-recovery lifecycles tested only in isolated temporary directories.
- Reframe the README around the ChatGPT, Claude, Codex, and Claude Code editions while keeping the ChatGPT Edition private rather than advertising a public GPT.

## 1.0.0-beta.1 - 2026-09-14

- Publish a public beta, not the stable `v1.0.0` release.
- Replace the invalid earlier behavioral evaluator procedure with a reproducible exact-SHA harness featuring a typed fixture registry, capability enforcement, credential isolation, chronological grader evidence, and fail-closed retry and checkpoint controls. Teaching behavior, protected evaluation data, thresholds, and release gates are unchanged.
- Record that deterministic validation and the Luma Arabic and Vela English simulations passed, while the earlier 90-case behavioral report remains invalid and is not release evidence.
- Defer stable release readiness until the corrected evaluator completes a full exact-SHA model run and the remaining stable gates are satisfied.

- Derive progress from evidence type, support level, outcome, task identity, and time instead of accepting caller-selected mastery states.
- Require a fresh unsupported retrieval at least 24 hours after distinct independent evidence before recording retention, and downgrade retained state after later failure.
- Add locked, optimistic, crash-recoverable session updates plus consent, retention, renewal, and deletion enforcement for learner profiles.
- Add closed-book zero-knowledge teacher/learner simulations with baseline-to-transfer gain, provider-neutral adapters, thresholds, and critical-failure blocking.
- Add a validated Arabic/English HTML-to-tagged-PDF reference path with PDF/UA output, title/text checks, and rendered visual review.
- Add evidence-bounded PDF, text, transcript, and sampled-frame intake that refuses to treat opaque video bytes as understood.
- Document the pedagogy-to-implementation mapping and its limits; prevent unbounded always-loaded skill growth.
- Pin direct Python dependencies and GitHub Actions, add Dependabot, and exercise portable core validation on macOS and Windows.
- Add a machine-readable stable-release receipt; fixture adapters and schema fixtures cannot authorize a stable release.

## 0.9.0 - 2026-09-13

- Resolve the explain-first versus continuous-testing contradictions across the teaching engine, handoff, integration, and accessibility contracts.
- Pin and meta-validate ten JSON Schemas with connected positive fixtures and negative rejection tests.
- Require stable session, source, objective, lesson, assessment, claim, event, and progress identifiers where applicable.
- Add cross-artifact cycle, checkpoint, source, assessment, and active-module integrity checks.
- Replace mastery-bearing resume codes with evidence-safe `TEACH-ME:v2` locators while accepting `v1` only as an unverified legacy locator.
- Normalize 15 behavioral suites containing 88 single- and multi-turn cases and add provider-neutral response/grader execution with thresholds and critical failures.
- Add capability and cost documentation, corrected fresh-install/update/removal instructions, and deterministic release archives with checksums.
- Add a consent-gated local feedback recorder and privacy-minimized aggregation that excludes free text and suppresses small groups.
- Add a release gate requiring real Arabic and English model evaluation, end-to-end journeys, and rendered bidirectional artifact review before `v1.0.0`.
- Add a reusable bidi HTML template plus structural isolation, CSS, landmark, and link validation with positive and negative fixtures.
- Turn domain packs into a validated manifest and concept-graph system, with programming and photography pilots and six behavioral cases; both remain pending qualified review.

## 0.8.3 - Unreleased

- Define routine assessment boundaries as a complete lesson, topic, module objective, or practical skill—not a page, paragraph, isolated fact, or chat turn.
- Offer a short understanding check after each completed unit and wait for explicit learner opt-in before asking questions.
- Use three to five diagnostic items across explanation, misconception discrimination, application, and transfer as relevant.
- Continue without pressure or negative mastery inference when the learner declines.
- Preserve focused earlier checks for explicit practice requests, necessary prerequisites, consequential misconceptions, and safety.
- Add four behavioral regressions for incomplete boundaries, opt-in, refusal, and accepted checks.

## 0.8.2 - Unreleased

- Add an explain-first conversational teaching contract for beginners and substantial lessons.
- Stop appending micro-assessments and visible mastery labels to routine learner-facing turns.
- Accept an explicit zero-knowledge starting point instead of testing the learner to confirm it.
- Add immediate recovery when the learner says the experience feels like an exam.
- Keep meaningful assessment at natural checkpoints and preserve intensive testing when explicitly requested.
- Add six behavioral regressions for conversational teaching cadence.

## 0.8.1 - Unreleased

- Preserve the established teaching language across incidental code-switching.
- Add capability-aware accessibility fallbacks and an explicit hard-block path.
- Add a machine-readable portable resume-code validator without treating locators as mastery evidence.
- Add purpose, consent time, retention, deletion state, and pseudonymous group observations to learner-profile governance.
- Add six regression cases from the two-agent pressure test.

## 0.8.0 - Unreleased

- Make display direction part of teaching correctness for mixed Arabic/English output.
- Default bidirectional learning packs to semantic HTML while retaining Markdown for single-direction material.
- Require isolated left-to-right terms, identifiers, code, numbers, paths, and URLs.
- Generate requested Arabic PDF from the validated HTML source and inspect rendered pages.
- Add bidirectional curriculum and complete-pack behavioral evaluations.

## 0.7.1 - Unreleased

- Add multimodal video inspection levels, aligned timestamp provenance, and sandboxed procedure-verification rules.
- Add optional capability-provider routing with real health checks and lawful fallbacks.
- Add an external-skill adoption gate for license, provenance, security, quality, overlap, and context cost.
- Add a teaching simplicity ladder and logically separate research rigor review.
- Add ecosystem acknowledgements and seven integration behavioral evaluations.

## 0.7.0 - Unreleased


- Add adaptive retrieval, spacing, cumulative review, and retention decisions.
- Add contextual learner observations with confidence and correction rather than fixed labels.
- Add accessibility-equivalent representations and ethical engagement recovery.
- Separate a simple learner-facing pack from internal teaching and evidence artifacts.
- Add six behavioral evaluations for retention, access, engagement, pack navigation, and stale assumptions.

## 0.6.0 - Unreleased

- Add diagnostic, teaching, assessment-feedback, misconception, and Arabic-language engines.
- Add a graduated hint ladder and evidence-based mastery decisions.
- Add cognitive-load controls and material strategy changes after teaching failure.
- Add six end-to-end golden teaching evaluations across programming, children, photography, feedback, and retention.

## 0.5.0 - Unreleased

- Add capability-aware Pack, Single-file, and Chat-only delivery modes.
- Add a beginner-safe `START-HERE.md` onboarding contract and learner dashboard.
- Respect transferable expertise while assuming no unproven subject knowledge.
- Require onboarding, curriculum, first lesson, practice, and progress instead of empty scaffolding.
- End learner-facing turns with one exact action, expected time, and requested response.
- Add portable, non-sensitive `TEACH-ME:v1` resume codes and six behavioral evaluations.

## 0.4.1 - Unreleased

- Add a mandatory broad research sweep for named books, fields, courses, tools, frameworks, and standards.
- Build a role-based knowledge base across relevant paid and free source families before substantial teaching.
- Track lawful access and actual inspection without bypassing or implying access to closed material.
- Add a knowledge-base schema, template, research teaching gate, refresh rules, and six behavioral evaluations.
- Make detailed whole-book, course, curriculum, and broad-subject teaching artifact-first instead of a long chat lecture.
- Add an editable Markdown curriculum default, requested PDF delivery with Arabic RTL quality checks, stable module and lesson checkpoints, a schema, template, and six behavioral evaluations.

## 0.4.0 - Unreleased

- Reframe audience and source handling as independent routing axes.
- Add a connected learning-session contract and stable artifact identifiers.
- Add objective contracts, resumable checkpoints, capability routing, and artifact-authority rules.
- Add a claim evidence ledger with correction propagation.
- Add integration evaluations for combined educator/source use, resume, mastery evidence, and inaccessible media.

## 0.3.0 - Unreleased

- Add Source-Grounded Mode for books, documents, audio, video, playlists, courses, and websites.
- Add multimodal coverage tracking and an understanding gate before instruction.
- Add a lawful fallback that builds an independent learning path when a paid or inaccessible source cannot be inspected.
- Add source-coverage schema, template, and behavioral evaluations.

## 0.2.0 - Unreleased

- Add Educator Mode for curriculum mapping and lesson preparation.
- Add age-aware differentiation, assessment, traceability, privacy, and copyright rules.
- Add curriculum-map, lesson-plan, and minimized-feedback schemas.
- Add educator evaluation cases, reusable templates, repository validation, and a structured issue form.

## 0.1.0 - 2026-09-13

- Initial adaptive teaching loop in Arabic and English.
- Add learner model, evidence policy, safety and privacy guidance, progress schemas, and initial evaluations.
