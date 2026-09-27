# ChatGPT beta manual tests - 2026-09-27

This report records observed behavior from the isolated personal beta connection at `https://teach-me-mcp-next.ahmedm3bead.workers.dev/mcp`. It does not describe the production endpoint currently under review, and it is not evidence of marketplace approval.

## Automated baseline

- MCP TypeScript typecheck and build passed.
- MCP adapter and Worker tests passed: 33/33.
- The runtime bundle contains six compact ChatGPT-specific assets.
- Topic-led adapter output is approximately 6.2 KB before MCP presentation.
- A test prevents model-visible tool output from exceeding 16 KB across topic, document, video, book, and playlist selectors.
- Module content appears once in model-visible output. Bundle provenance and module digests are returned in hidden MCP `_meta`.

## Manual host observations

| Case | Selector | Host access observed | Result |
|---|---|---|---|
| Topic-led Excel lesson | `topic-led` | No external source | Practical first lesson succeeded; follow-up refinements prevent unsupported learning claims and unsolicited roadmaps. |
| GitHub repository webpage | `source-grounded` + `webpage` | Repository metadata, tree, and README | Correctly separated inspected files from architectural inference. |
| Controlled four-page PDF | `source-grounded` + `document` | Extracted text plus rendered page images | Recovered raster-only values, detected a table conflict, applied the final scenario, and rejected embedded prompt injection. |
| YouTube demo video | `source-grounded` + `video` | Title, channel, and description only | Correctly disclosed that transcript, audio, and frames were unavailable and taught only from verified metadata plus labelled explanation. |
| CS50x YouTube playlist | `source-grounded` + `playlist` | Direct YouTube fetch throttled; official Harvard index accessible | Reconstructed the eight-item map from the official external source and did not claim video or transcript coverage. |
| Project Gutenberg book | `source-grounded` + `book` | Metadata, table of contents, full web text, and chapter 1 | Mapped 12 chapters, inspected only the first unit, and separated original text, the site's automatic summary, and teaching additions. |
| PDF plus GitHub repository | `source-grounded` + `mixed` | Both sources inspected independently | Verified that the PDF was absent from the complete current `main` tree, kept fictional PDF rules separate from repository facts, and labelled their relationship as inference. |

## Confirmed capability boundary

Source behavior depends on what ChatGPT can access in that conversation. The Teach Me Worker does not receive source files, URLs, transcripts, page contents, credentials, or learner messages. In the observed host session:

- PDFs exposed both text and page visuals.
- GitHub exposed useful repository metadata and content.
- Project Gutenberg exposed book structure and readable text.
- YouTube did not expose transcript, audio, or video frames.
- YouTube playlist enumeration required a separate official index when the direct page was throttled.

Release copy must not say that Teach Me automatically watches videos, reads every transcript, or enumerates every playlist. It may say that Teach Me teaches from source components ChatGPT can inspect and states coverage limits when components are unavailable.

## Refinements made from testing

- Prohibit claims such as "you learned" or `تعلمنا` without learner evidence.
- Require one final current action and avoid unsolicited multi-topic roadmaps.
- Hide internal routing, connector retries, and recovered tool errors unless they materially affect coverage.
- For Arabic responses with English terms, use numbered lists or prose instead of Markdown tables, ASCII diagrams, or vertical arrow maps.

## Release decision

The tested source types cover every runtime routing group: core only; core plus source; source plus video; source plus curriculum; and mixed-source curriculum. Course and curriculum share the tested long-source module; recording shares the tested video module. Repeat a small smoke test after any change to tool schemas, module routing, source privacy boundaries, or the compact runtime assets.

On 2026-09-27, a live beta smoke test confirmed that `tools/list` advertises the complete age-band, educator, source-mode, and source-type schema. Direct `tools/call` tests also confirmed the expected selective modules for Arabic educator guidance, younger-primary learner guidance, and source-grounded video guidance.
