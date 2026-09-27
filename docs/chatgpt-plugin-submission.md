# ChatGPT public plugin submission kit

> **Release guard:** the plugin currently under OpenAI review uses the previously submitted production deployment. The `main` branch contains the next version and must not be deployed to production or resubmitted until the current review finishes. See [Current release status](release-status.md).

This is the source-of-truth checklist for publishing Teach Me to ordinary ChatGPT users through the universal Plugins Directory. The submission type is **With MCP**, using the public, anonymous, read-only server below. Developer mode is only for private testing and is not the distribution path.

## Production candidate

| Field | Value |
|---|---|
| Name | Teach Me |
| Submission type | With MCP |
| MCP URL type | Universal |
| MCP server URL | `https://teach-me-mcp.ahmedm3bead.workers.dev/mcp` |
| Authentication | None |
| Category | Education |
| Developer | Ahmed Ebead |
| Website | `https://github.com/ahmed3bead/teach-me` |
| Support | `https://github.com/ahmed3bead/teach-me/issues` |
| Privacy policy | `https://github.com/ahmed3bead/teach-me/blob/main/docs/privacy-policy.md` |
| Terms | `https://github.com/ahmed3bead/teach-me/blob/main/docs/terms-of-use.md` |
| Logo source | `plugins/teach-me/assets/teach-me-icon.svg` |

Use the merged public commit for all repository-backed URLs before final submission.

## Listing copy

**Short description**

> Learn any topic step by step in English or Arabic, with explanations that adapt when you get stuck.

**Long description**

> Teach Me turns ChatGPT into a patient, adaptive teacher for ordinary learners. It starts from your goal and current level, explains one manageable idea at a time, uses practical examples, and changes strategy when an explanation does not click. It supports English and simplified Modern Standard Arabic. Routine assessments are offered only after a meaningful learning unit and start only with your consent. Teach Me does not create an account, store learner state, or send your conversation to its server; its read-only connector returns public, versioned teaching guidance for ChatGPT to follow.

**Capabilities**

- Adaptive step-by-step teaching.
- English and simplified Modern Standard Arabic.
- Practical examples and alternate explanations.
- Consent-based understanding checks.
- No Teach Me account or learner-data storage.

**Starter prompts**

1. Teach me how compound interest works from zero, using a practical example.
2. Explain recursion in Arabic as if I know basic programming but keep getting stuck.
3. I understand voltage but not current. Diagnose the gap and teach me with a different analogy.
4. Teach me the basics of photography exposure, one manageable idea at a time.
5. Help me understand supply and demand, then ask before giving me a short check.

## Tool annotation justification

`load_teach_me` is read-only because it only returns immutable, public teaching guidance. It is non-destructive because it cannot mutate user, host, or third-party data. It is closed-world because it makes no outbound requests and selects only from a build-time allowlist embedded in the deployed Worker. It is idempotent because identical valid arguments against one deployed version return identical content and digests.

The server requires no authentication because it exposes no private or user-specific data and performs no action. Its input contains only optional bounded selectors for locale and the supported teaching route. Learner prompts, transcripts, files, credentials, and personal data are neither required nor accepted.

## Positive review cases

1. **English beginner** — Prompt: “Teach me compound interest from zero.” Expected: the connector is called before teaching; the answer establishes or safely infers a goal, teaches progressively, and includes a practical example without an immediate quiz.
2. **Arabic learner** — Prompt in Arabic asking to learn recursion. Expected: `locale` resolves to Arabic, the answer stays in simplified Modern Standard Arabic, and technical English is used only when useful.
3. **Transferable knowledge** — Prompt: “I know JavaScript loops; teach me recursion.” Expected: the response respects existing knowledge and bridges from loops rather than restarting from programming basics.
4. **Persistent confusion** — After one explanation, say it still does not make sense. Expected: the next explanation changes representation or addresses a prerequisite instead of paraphrasing the same explanation.
5. **Assessment consent** — Ask to learn a short unit, then decline the offered check. Expected: the check is offered only after the unit, waits for explicit consent, and a refusal is accepted without pressure or a negative progress claim.

## Negative review cases

1. **Private data sent as an argument** — Attempt to include a transcript or personal field in `load_teach_me`. Expected: the strict schema rejects the unknown field and does not echo its value.
2. **Unsupported mode** — Request `source-grounded` or `educator` routing. Expected: a safe structured error; the server does not claim an unavailable capability.
3. **Unsupported side effect** — Ask the tool to save progress, send a message, fetch a URL, or modify a file. Expected: no matching tool or side effect exists; the server remains read-only and stateless.

## Repository and deployment evidence

- [x] Public production MCP endpoint uses Streamable HTTP over HTTPS.
- [x] `initialize`, `tools/list`, and `tools/call` pass against production.
- [x] The only tool has explicit input/output schemas and `readOnlyHint`, `destructiveHint`, and `openWorldHint` annotations.
- [x] The deployed Worker has no storage, outbound model/API call, cookie, analytics binding, or learner-state persistence.
- [x] Privacy policy and terms disclose the remote connector and host-platform boundary.
- [x] Linux, Windows, and macOS validation pass for the reviewed commit.
- [x] OpenAI domain-verification route exists and is disabled until its portal-issued token is configured.
- [ ] Reviewed changes are merged to `main` and the public URLs above resolve to that commit.
- [ ] Publisher identity is verified in the OpenAI Platform organization.
- [ ] Submitter has Apps Management write permission (`api.apps.write`).
- [ ] A **With MCP** draft is created and **Scan Tools** succeeds against production.
- [ ] The portal-issued domain token is configured as the `OPENAI_APPS_CHALLENGE` Worker secret and **Verify Domain** succeeds.
- [ ] Five positive and three negative cases are entered with their expected behavior.
- [ ] The candidate is tested privately in ChatGPT with genuine traces and screenshots where the portal requests them.
- [ ] The exact production version is submitted for review and left unchanged while review is pending.
- [ ] After approval, the publisher selects **Publish** and verifies installation from a separate ordinary learner account.

## Publication boundary

A healthy public MCP endpoint is not by itself a public ChatGPT listing. Ordinary users can discover Teach Me only after OpenAI review, approval, and the publisher's explicit publication step. Until then, describe the MCP connector as a public beta ready for directory submission, not as generally available in ChatGPT.

The existing skills-only package under `plugins/teach-me/` remains independently usable for compatible plugin hosts. It must not be represented as the reviewed remote MCP listing unless that exact combined package is what the portal imports and approves.
