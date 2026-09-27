# Source-grounded MCP v1.1 candidate

This document tracks the next Teach Me MCP release. It is intentionally separate from the exact `v1.0` candidate currently under OpenAI review. Do not deploy these changes to the reviewed production endpoint until that review finishes or a deliberate resubmission is chosen.

## Implemented foundation

- `load_teach_me` remains backward compatible for ordinary topic-led teaching.
- `input_mode: source-grounded` activates the reviewed source workflow.
- `source_type` distinguishes `document`, `book`, `webpage`, `video`, `playlist`, `course`, `recording`, `curriculum`, and `mixed` inputs.
- Source mode loads a compact ChatGPT teaching contract plus source inspection guidance. Video guidance is loaded only for videos, playlists, and recordings; curriculum guidance is loaded only for books, playlists, courses, curricula, and mixed collections.
- Model-visible module content is returned once. Digests, paths, byte counts, classifications, and bundle provenance are kept in MCP `_meta` so they do not consume the model context.
- Only bounded selectors reach the Teach Me server. Source content, files, URLs, transcripts, credentials, and learner data remain in the host conversation.

## What this enables

When ChatGPT can inspect a user upload or retrieve a public source, Teach Me can:

1. distinguish inspected content from metadata and inaccessible material;
2. teach progressively from a document or book;
3. map a course or playlist before teaching its units;
4. distinguish transcript evidence from visual-frame evidence;
5. cite pages, sections, timestamps, or URLs that were actually available;
6. build an independent, clearly labelled learning path when a closed source cannot be inspected.

## Host capability boundary

This release does not send learner source material to the Teach Me Worker and does not make the Worker an unrestricted crawler. Actual extraction depends on capabilities available in the ChatGPT conversation. If the host cannot inspect a PDF, webpage, transcript, audio track, or video frame, Teach Me must disclose the limitation and request an accessible alternative.

Direct enumeration of a public YouTube playlist through the official YouTube Data API requires an application API key and quota. That optional server-backed connector is a later capability, not part of this privacy-preserving foundation.

## Required before release

- Test uploaded text, PDF, and document inputs in ChatGPT developer mode.
- Test a public webpage, a YouTube video with accessible transcript, and a playlist.
- Record which components ChatGPT actually exposes on desktop and mobile.
- Add v1.1 submission cases and update the listing copy without overstating source access.
- Run the complete repository and MCP test suites.
- Redeploy and verify the separate beta Worker before updating production. Bump the public version only when the release candidate is frozen.
