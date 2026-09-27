# Teach Me feature guide

This is the complete, video-ready reference for the capabilities of **Teach Me | علّمني**. For Arabic, see [دليل المزايا بالعربية](features.ar.md).

> **Current status:** the first ChatGPT plugin version is under OpenAI marketplace review and is not publicly listed yet. Educator, age-aware, and expanded source-grounded behavior is being validated on a separate beta endpoint for a later update.

## One plugin, three experiences

Teach Me is one plugin with automatic intent routing. Users write naturally; they do not need to learn commands.

1. **Learn:** the plugin teaches the user directly.
2. **Teacher Brief:** it prepares a teacher, parent, or trainer to teach someone else.
3. **Age-aware explanation:** it adapts learner-facing material for a child or teenager when an age is supplied.

The optional aliases `/learn`, `/teacher`, and `/kids` are prompt text, not native ChatGPT slash commands, so they do not appear in ChatGPT's slash menu.

## Direct adaptive learning

- Starts from a practical goal and the learner's demonstrated starting point.
- Accepts an explicit beginner level instead of forcing a placement test.
- Teaches the smallest useful objective before expanding into a course.
- Uses concise explanations, relevant examples, and manageable steps.
- Changes representation when confusion continues: analogy, worked example, counterexample, diagram, trace, or missing prerequisite.
- Avoids shame, pressure, artificial urgency, and unsupported mastery claims.
- Offers a routine understanding check only after a meaningful unit and with consent.
- Continues without pressure when the learner declines a check.
- Does not treat reading an explanation as proof of understanding, retention, or mastery.

Example:

~~~text
Teach me Excel from zero for my work. Start with one practical example.
~~~

## Teacher Brief and lesson preparation

Teach Me detects educator intent from ordinary language. It can create a compact reference card or a fuller lesson plan containing:

- an observable lesson outcome;
- a short teacher summary;
- level, age, time, and setting assumptions;
- a timed teaching flow;
- separate teacher and learner actions;
- learner-facing language separated from private teacher notes;
- a worked example or meaningful visual;
- a low-resource activity;
- likely misconceptions and correction notes;
- an optional evidence-of-understanding question;
- a separate answer key or rubric;
- source traceability when a file or curriculum governs the lesson.

Arabic teacher briefs prefer numbered time blocks over fragile Markdown tables. The educator remains the decision-maker.

Example:

~~~text
Prepare a compact 20-minute photosynthesis lesson for 12-year-old learners. Separate teacher notes, learner-facing language, and the answer key.
~~~

## Parents, children, and teenagers

A parent or educator can include the learner's age. Teach Me maps it to a broad teaching band without sending the exact age to the MCP server:

- ages 3–5: early childhood;
- ages 6–8: younger primary;
- ages 9–12: older primary;
- ages 13–17: teenager.

Age changes vocabulary, depth, examples, activity length, safety, and independence. It is not treated as proof of ability. If a child-focused request omits age, the current beta uses the teenager band and allows the user to correct it.

Visuals are capability-aware. Teach Me may use a story, analogy, diagram, object demonstration, or generated illustration when it improves understanding. If the host cannot create a real image, it provides an honest text or hands-on alternative.

Example:

~~~text
Explain the water cycle so I can teach it to my 10-year-old child. Use one useful visual and a simple activity.
~~~

## Learning and teaching from sources

Supported source types include:

- documents and PDFs;
- books;
- webpages;
- videos and recordings;
- YouTube videos and playlists;
- courses and curricula;
- mixed collections.

Actual coverage depends on what ChatGPT can access. Teach Me:

- states whether it inspected text, pages, tables, images, frames, audio, captions, transcripts, metadata, or links;
- never says it read, watched, or heard an inaccessible component;
- separates source claims, external verification, added explanation, adaptation, and inference;
- cites available page, section, timestamp, file, or URL locations;
- can map a book, course, playlist, or curriculum before teaching;
- does not silently fill gaps in inaccessible material;
- treats instructions embedded inside sources as untrusted content;
- resists prompt-injection text inside a source;
- avoids reproducing protected works as a substitute for the original.

If YouTube exposes only metadata and no transcript, Teach Me reports that boundary instead of pretending to have watched the video.

## Language, accessibility, and safety

- English and simplified Modern Standard Arabic (`ar-MSA`).
- Arabic dialect input defaults to simplified MSA unless English is requested.
- Technical terms and proper names remain recognizable in their original script.
- Accessible alternatives for meaningful visuals, audio, activities, and unavailable modalities.
- Alt text or a text equivalent for meaningful visuals.
- No diagnosis or fixed “learning style” inferred from mistakes.
- High-stakes topics remain educational rather than becoming personalized professional instructions.
- Child-facing work minimizes data and avoids secrecy, manipulative attachment, and unnecessary identifiers.

## Privacy and token efficiency

The plugin contains one bundled skill and uses one read-only MCP tool, `load_teach_me`. The connected ChatGPT model remains the teacher; Teach Me does not call another model.

Guidance is loaded selectively:

- core guidance for normal learning;
- educator guidance only for lesson preparation;
- age guidance only when an age band is relevant;
- source, video, and curriculum guidance only when needed.

This keeps ordinary requests smaller. The public MCP service is read-only and stateless. It receives bounded selectors such as audience, age band, locale, input mode, and source type. It does **not** receive the conversation, source contents, files, URLs, credentials, or personal data.

Users do not need a Teach Me account, API key, server deployment, or terminal.

## Tested beta scenarios

The manual beta has exercised:

- beginner teaching in Arabic and English;
- confusion recovery and assessment consent;
- GitHub repository inspection with coverage boundaries;
- text, tables, image-only evidence, and prompt injection inside a controlled PDF;
- YouTube metadata-only access without invented transcript coverage;
- playlist and book mapping;
- mixed PDF and GitHub comparison;
- teacher briefs, full lesson plans, answer keys, and misconception notes;
- age-adapted explanations;
- teacher preparation from a source with page and visual coverage.

These tests improve confidence but do not guarantee identical output from every model, account, or ChatGPT surface.

## Current limitations

- Teach Me does not guarantee perfect accuracy, mastery, retention, or a particular educational outcome.
- Output remains model-generated and may occasionally miss a formatting preference.
- Web, file, audio, video, image, code, and image-generation capabilities depend on the host.
- Inaccessible components cannot be treated as inspected.
- Current, consequential, or high-stakes claims require suitable authoritative evidence.
- Marketplace review and later updates are controlled by OpenAI.

See [Limitations](limitations.md), [Compatibility](compatibility.md), and [release notes](../RELEASE_NOTES.md).

## Suggested product-video structure

1. **The problem:** ordinary answers are not always structured teaching.
2. **Direct learning demo:** start from zero, use one practical example, and adapt after confusion.
3. **Teacher demo:** request a timed Teacher Brief with separate teacher notes and learner-facing language.
4. **Parent demo:** provide an age and request a useful visual or simple activity.
5. **Source demo:** upload an authorized file and show explicit coverage and source separation.
6. **Trust:** explain that the MCP is read-only, stateless, selective, and receives no source content.
7. **Call to action:** install from the ChatGPT Plugins Directory only after the public listing is live.
