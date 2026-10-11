# ChatGPT publication record and future update checklist

Teach Me is approved and [publicly listed in ChatGPT](https://chatgpt.com/plugins/plugin_asdk_app_6ab81f50a2b881918abe2865d47fb2a3), with listing version **1.0.0**, verified on **2026-10-11**. See [current release status](release-status.md) and [the machine-readable evidence record](published-release.json).

## Sources of truth

- `chatgpt-app-submission.json`: public display name, subtitle, description, tool justifications, and the next submission's five positive and three out-of-scope negative cases.
- `docs/published-release.json`: observed listing version, URL, starter prompts, runtime version, bundle digest, comparison commit, and verification limits.
- `plugins/teach-me/.codex-plugin/plugin.json`: the independently installable skills-only package. Its display copy and starters mirror the listing sources above; its package version remains `1.0.0-beta.2`. It is not proof of the package imported by the ChatGPT portal.
- `site/dist/`: user guide and installation links, deployed separately through Cloudflare Pages Direct Upload.

Run `python scripts/check_published_release.py` after changing these files. Editing repository metadata does not update the ChatGPT portal.

## Published configuration

| Field | Value |
|---|---|
| Display name | Teach Me &#124; علّمني |
| Listing version | 1.0.0 |
| Runtime/package version | 1.0.0-beta.2 |
| Submission route recorded in repository | With MCP; Universal; no authentication |
| MCP server | `https://teach-me-mcp.ahmedm3bead.workers.dev/mcp` |
| Developer | Ahmed Ebead |
| Public category | Education & Research |
| Submission category enum | EDUCATION |
| Website | https://github.com/ahmed3bead/teach-me |
| Support | https://github.com/ahmed3bead/teach-me/issues |
| Privacy | https://github.com/ahmed3bead/teach-me/blob/main/docs/privacy-policy.md |
| Terms | https://github.com/ahmed3bead/teach-me/blob/main/docs/terms-of-use.md |

The public category label and submission enum are different representations. The listing's `1.0.0` and runtime's `1.0.0-beta.2` are separately observed version identifiers, not evidence of different teaching content. The runtime still reports `public-beta`; this describes its runtime release label and does not override the confirmed ChatGPT publication status. No production redeployment is needed for this documentation correction.

## Current review cases

The JSON submission file is authoritative for portal cases. It contains five positive cases: English beginner, Arabic learner, educator, parent teaching a child, and source-grounded PDF. It contains three negative trigger cases: weather lookup, sending email, and deleting files. Negative trigger cases must not call `load_teach_me`.

The PDF case now links to the [original, MIT-licensed one-page fixture](../fixtures/submission/water-cycle.pdf). Confirm the public raw URL is reachable after merge before using it in a future submission. This fixture was added after approval; it is not historical reviewer evidence.

Additional behavioral regression checks remain in [consumer acceptance tests](../plugins/teach-me/ACCEPTANCE_TESTS.md): prior-knowledge transfer, alternate explanations, assessment consent, prompt injection, and inaccessible source components. These are separate from negative tool-trigger cases.

## Evidence recorded on 2026-10-11

- [x] Publisher reports OpenAI approval; the public page displays **Install plugin** and version **1.0.0**.
- [x] Production and beta guidance bundle digests match the committed runtime bundle.
- [x] Production tool description, schemas, and annotations match the repository implementation.
- [x] Complete production tool responses match local responses for seven recorded routing cases.
- [x] The generated six-asset bundle is current with repository sources.
- [x] Documentation of approval and publication was merged in [PR #58](https://github.com/ahmed3bead/teach-me/pull/58), with Linux, Windows, and macOS CI passing.

## Remaining user acceptance

- [ ] Install from a separate ordinary learner account and record a successful first lesson.
- [ ] Record fresh ChatGPT conversation evidence for the current [consumer acceptance tests](../plugins/teach-me/ACCEPTANCE_TESTS.md).

These remain unverified. Direct MCP response comparisons do not substitute for host-conversation tests.

## Future update checklist

This is a reusable checklist for the next candidate, not unfinished tasks from the already approved submission.

- [ ] Record the candidate source commit, bundle digest, runtime version, and intended listing version.
- [ ] Run repository checks and consumer acceptance tests against the beta deployment.
- [ ] Confirm website, support, privacy, terms, and test attachment URLs are public and accurate.
- [ ] Confirm publisher identity, Apps Management permissions, and domain-verification status in the signed-in portal if required. Historical portal evidence is not stored here.
- [ ] Create the update through the recorded **With MCP** route, scan tools, and inspect imported schemas and annotations.
- [ ] Copy listing text from `chatgpt-app-submission.json` and starters from `docs/published-release.json`; verify the portal matches the intended candidate.
- [ ] Enter the five positive and three negative cases with available attachments and required genuine traces.
- [ ] Record production deployment evidence and leave the submitted build unchanged during review.
- [ ] After approval/publication, verify installation independently and update the release record, user guide, and documentation.

The original approval date, publication date, deployment commit, portal identity checks, and scan/domain verification timestamps are unknown. Do not infer them from the current listing or mark them complete without evidence. The former 2026-09-27 cancellation/resubmission plan is historical and is superseded by the published status.
