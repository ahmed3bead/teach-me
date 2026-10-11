# Teach Me for ChatGPT

Teach Me is one education plugin for learners, teachers, parents, and trainers. It combines a compact teaching skill with a read-only, stateless MCP guidance service. Users need no separate account, API key, or technical setup after installation.

The same installation provides three internal modes: direct adaptive learning (default or `/learn`), teacher preparation (`/teacher`), and child- or teen-friendly teaching (`/kids`). These aliases are ordinary prompt text, not native ChatGPT slash commands; Teach Me also routes requests automatically from their meaning.

## What the plugin can do

- Learn a topic from zero or from an existing level.
- Ask for a different explanation when the first one does not work.
- Learn in English or simplified Modern Standard Arabic.
- Study from an uploaded source while keeping source content separate from added explanation.
- Choose whether to take a short understanding check after a meaningful unit.
- Prepare a compact lesson brief with a separate answer key when needed.
- Explain to children and teenagers with age-appropriate language, activities, and meaningful visuals when supported.

### Direct learning

Teach Me starts from the requested goal and demonstrated level, explains one useful objective at a time, changes representation when the learner is stuck, and asks before routine assessment. It does not treat exposure as proof of mastery.

### Teacher preparation

The same plugin can prepare a compact Teacher Brief or a fuller lesson plan with an observable outcome, timed flow, teacher and learner actions, learner-facing script, activity, misconceptions, optional check, and a separate answer key. Educator intent is inferred from normal language; `/teacher` is only an optional text alias.

### Age-aware explanations

A parent or educator may provide the learner's age. The exact age stays in the ChatGPT conversation and is mapped to a broad teaching band before MCP guidance is loaded. Visuals are used only when useful and supported, with a text or hands-on fallback.

### Authorized sources

Teach Me can work from documents, PDFs, books, webpages, videos, playlists, recordings, courses, curricula, and mixed collections. It reports actual inspected coverage, separates source content from additions, and treats instructions embedded inside a source as untrusted content. Inaccessible transcripts, audio, frames, pages, or links are never described as inspected.

See the full [English feature guide](../../docs/features.md) or [Arabic feature guide](../../docs/features.ar.md).

## Distribution status

Teach Me has been approved by OpenAI and published in the ChatGPT Plugins Directory. [Install Teach Me | علّمني](https://chatgpt.com/plugins/plugin_asdk_app_6ab81f50a2b881918abe2865d47fb2a3). The public listing shows version **1.0.0**, verified on 2026-10-11. See the [current release status](../../docs/release-status.md) for the publication record and future update guidance.

The plugin uses the Teach Me MCP endpoint to load reviewed teaching guidance. The endpoint receives only bounded selectors such as language, mode, and source type; source content, files, URLs, transcripts, credentials, and learner messages remain in ChatGPT. There is no Teach Me sign-in flow or learner account. See the [privacy policy](../../docs/privacy-policy.md) and [terms of use](../../docs/terms-of-use.md).

Before submission, run the [consumer acceptance tests](ACCEPTANCE_TESTS.md) and follow the [marketplace submission checklist](../../docs/chatgpt-plugin-submission.md).

## Maintainers

Generate the committed skill and bundled knowledge from their shared sources:

```bash
python3 scripts/build_chatgpt_edition.py
python3 scripts/build_chatgpt_edition.py --check
```

Validate the plugin package with the current plugin validator before submission.
