# Curriculum delivery

Use this workflow when the user asks for a detailed explanation of an entire book, course, curriculum, playlist, or broad field. The goal is a coherent teaching program that can be navigated and resumed, not a wall of chat text.

## Choose the artifact

- Default to `study-curriculum.md`: editable, searchable, diffable, and easy to improve.
- Use PDF when the user asks for a polished, fixed-layout, printable, or shareable document. Generate from the same curriculum structure; preserve headings, links, page breaks, and readable typography.
- If the environment cannot create files, provide the curriculum as structured Markdown in chat and disclose that it was not saved.
- Do not create both formats unless requested or conversion is inexpensive and clearly useful.

For Arabic, use right-to-left layout in PDF, choose a font with complete Arabic glyph support, keep English technical terms readable beside Arabic terms, and render-inspect the final pages before delivery.

## Artifact-first rule

Before substantial instruction:

1. Complete the applicable source-coverage and research-sweep gates.
2. Define the learner outcome, assumed starting point, scope, exclusions, and study constraints.
3. Map the subject into ordered modules and lessons, including prerequisites and deliberate review points.
4. Create the curriculum artifact using `templates/study-curriculum.md` or an equivalent structure and connect it to the learning session.
5. Give the learner a short orientation: what the curriculum covers, where to begin, and the next decision or diagnostic.

Do not paste the entire curriculum into chat after creating the file. Do not begin an unstructured chapter-by-chapter lecture merely because the user asked for detail.

## Required curriculum qualities

The artifact must make these visible:

- learner, outcome, level assumptions, language, estimated effort, and scope;
- module and lesson order, prerequisites, and stable identifiers;
- a demonstrable outcome for each lesson;
- source references at the lesson or claim level, including edition/version when relevant;
- explanation plan, worked example or activity, and assessment evidence;
- review schedule, completion criteria, progress states, and resume checkpoint;
- gaps, inaccessible material, disputes, uncertainty, and lawful substitute sources.

Use summaries and original teaching explanations. Do not reproduce a copyrighted source or imply that independent materials are an exact replacement for inaccessible paid content.

## Granularity

A curriculum is a map, not the complete prose of every lesson. Give enough detail to show the path and verify coverage. Put extensive instruction in separate module or lesson files when needed, linked from the curriculum. This prevents one oversized file while preserving a single table of contents and progress map.

Adapt lesson length and activity type to the learner. Avoid fixed chapter-to-lesson mapping when concepts need reordering, prerequisites, or synthesis across sources.

## Updating and resuming

Keep `curriculum_id`, `module_id`, `lesson_id`, `objective_id`, and `source_id` stable across revisions. Record the active module and lesson in the session checkpoint. Update the curriculum when diagnostics reveal a missing prerequisite or unsuitable pacing, but preserve completed evidence and explain material structural changes.
