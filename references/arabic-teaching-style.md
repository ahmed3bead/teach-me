# Simplified Modern Standard Arabic teaching style

Teach every Arabic-speaking learner in clear simplified Modern Standard Arabic (`ar-MSA`), regardless of the dialect used in the learner's message. Do not mirror Egyptian or another colloquial dialect. Use English only when the learner explicitly requests it. Treat a legacy `ar-EG` locale value as `ar-MSA`.

## Language continuity

Keep the established teaching language unless the learner explicitly asks to switch. An English technical term, code sample, pasted quotation, source title, or one code-switched sentence does not request an English lesson. Arabic dialect in learner input is a signal to simplify the register, not to imitate the dialect.

## Terminology

- Keep foreign and technical terms in their original language and script: `API`, `Replication`, `Contract Test`, `Prompt`, and `Database` remain recognizable in Latin letters.
- On first use when needed, explain the term in Arabic without replacing it, for example: `Replication` (الاحتفاظ بنسخ متزامنة من البيانات).
- Never write the pronunciation of a foreign term in Arabic letters.
- Do not translate product names, code, commands, identifiers, or established acronyms.
- Use each chosen form consistently and keep a small glossary for long journeys.

## Simplified Modern Standard Arabic

Use contemporary words, short sentences, and direct syntax. Avoid ornate vocabulary, long nested sentences, bureaucratic phrasing, and colloquial expressions. For children, use familiar concrete examples without distorting the concept. Read the explanation aloud mentally and fix awkward inflection, unclear pronouns, invented words, and unstable example names before delivery.

## Mixed-direction content

Direction is part of correctness. For saved Arabic material containing English terms, code, paths, numbers, formulas, or URLs, read [bidirectional-output.md](bidirectional-output.md). In HTML, isolate every left-to-right run with `<bdi dir="ltr">...</bdi>` or an element carrying `dir="ltr"`. Generate PDF from that validated HTML, use an Arabic-capable font, and inspect the rendered pages. Markdown backticks alone are not sufficient isolation.

## Quality check

Before delivery, verify that the explanation is simplified Modern Standard Arabic, contains no colloquial dialect, preserves every foreign technical term in its original script, defines new terms when needed, uses clear referents, and gives the learner one unmistakable next action.
