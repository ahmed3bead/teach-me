# Teach Me MCP foundation and behavior contract

## Purpose

Teach Me MCP makes the canonical Teach Me teaching behavior available to remote MCP clients without moving the teaching engine into the server. It is a production-shaped integration boundary for ordinary ChatGPT and Claude conversations, with Codex and Claude Code continuing to use their existing editions.

The first activated vertical slice is topic-led conversational teaching. The architecture remains capable of routing future learner, educator, source-grounded, persistent-session, artifact, and domain-pack modes, but this contract does not implement or claim those capabilities.

## Architectural principles

1. Teach Me remains the source of truth. The root `SKILL.md`, canonical references, schemas, templates, and reviewed domain packs define behavior.
2. The remote server is an adapter, not a teacher. ChatGPT or Claude performs the explanation, adaptation, assessment, and feedback.
3. Runtime teaching assets are derived deterministically from an explicit allowlist of canonical repository files. Teaching instructions are never maintained manually in Worker source.
4. Every deployed asset set is versioned, content-addressed, reproducible, and traceable to its canonical inputs.
5. The MCP transport and Cloudflare deployment remain outside the canonical teaching layer.
6. The initial server is stateless. Persistence, authentication, and additional Cloudflare services require a concrete user-facing feature and threat model.
7. No LLM API runs inside the MCP server.
8. Capability absence narrows the promise. The remote edition must not claim local files, source inspection, rendering, persistence, or memory that the host does not provide.
9. Existing ChatGPT, Claude, Codex, and Claude Code packages remain independently usable and must not acquire an accidental MCP dependency.
10. Behavioral success is measured by observable teaching behavior, not by a successful connection or tool call alone.

## Responsibility boundaries

### Teach Me canonical assets

The canonical layer owns:

- the cross-edition contract in `references/core-teaching-policy.md`;
- the full orchestration and routing in `SKILL.md` and routed `references/`;
- language, assessment-consent, evidence, safety, privacy, accessibility, and source rules;
- schemas and templates that define structured artifacts when a capable host uses them;
- optional domain-pack teaching specializations; and
- the behavioral expectations already represented by the repository evaluation suites.

Canonical assets do not import MCP, Cloudflare, transport, authentication, or storage code.

### Build layer

The build layer owns:

- an explicit runtime-asset allowlist;
- deterministic reading and normalization of canonical inputs;
- Teach Me version and per-asset SHA-256 digests;
- a reproducible runtime manifest and bundle;
- rejection of unsafe paths, missing inputs, duplicate identifiers, stale generated output, and prohibited development or learner data; and
- checks that generated ChatGPT artifacts and other editions remain current.

The build layer may transform or package canonical content, but it must not rewrite the teaching contract or become a second source of truth.

The concrete remote asset boundary is the machine-readable manifest at `mcp/teach-me-assets.json`. It uses an explicit allowlist: canonical roots identify where a reviewed asset may come from, but only an asset individually listed in the manifest is remotely selectable. Reserved module categories describe extension points without selecting their files.

```text
canonical repository assets
        ↓
explicit manifest allowlist
        ↓
validated remote asset boundary
        ↓
deterministic runtime bundle
        ↓
pure `load_teach_me` adapter
        ↓
MCP Streamable HTTP server (`mcp/src/server.ts`)
        ↓
Cloudflare Worker (`mcp/src/worker.ts`)
```

`scripts/validate_mcp_assets.py` enforces the boundary, path safety, deterministic order, identity uniqueness, prohibited locations, and conservative count and byte ceilings. The manifest remains the sole machine-readable deployment-selection source.

`scripts/build_mcp_bundle.py` validates that boundary and writes `mcp/generated/teach-me-runtime.json`. The generated JSON contains the ordered selected assets, canonical repository provenance, normalized UTF-8 content, versions, classifications, categories, required status, and per-asset SHA-256 digests. It contains no learner state, evaluation data, timestamps, Git identity, or machine paths.

Rebuild and check the committed artifact with:

```bash
python3 scripts/build_mcp_bundle.py
python3 scripts/build_mcp_bundle.py --check
```

Source CRLF and lone-CR newlines normalize to LF. JSON keys are sorted, assets retain validated manifest order, Unicode is emitted directly as UTF-8, output uses two-space indentation, and the file ends with one LF. The overall `bundle_digest` is SHA-256 of compact, sorted-key, UTF-8 JSON for every top-level field except `bundle_digest`; attaching the digest afterward avoids self-reference. The source-manifest digest uses the same canonical JSON encoding, so formatting-only manifest edits do not change content identity.

The initial ceilings are 64 assets, 128 KiB for one asset, and 512 KiB total. The selected topic-led graph is currently about 50 KiB, so these limits leave substantial reviewed growth for later modules while preventing an accidental directory inclusion or large content file from approaching infrastructure limits unnoticed. Raising a ceiling requires an explicit manifest change and remains bounded by stricter validator-policy maxima.

### Pure runtime adapter

The pure adapter in `mcp/src/adapter.ts` owns:

- strict input validation and bounded canonical-module selection;
- version, digest, provenance, and capability metadata in results;
- a transport-neutral `load_teach_me` result; and
- structured client-neutral errors for unsupported inputs.

It will not explain a topic, grade a learner, decide mastery, generate a curriculum, fetch arbitrary sources, call an LLM, or retain learner state.

`load_teach_me({})` defaults to the `learner` audience, `topic-led` input mode, the `topic-led-conversational` logical guidance module, and a host-inferred locale. Explicit `en` and `ar-MSA` locales are supported; legacy `ar-EG` normalizes to `ar-MSA`. The adapter rejects unknown fields, unsupported enum values, malformed or empty module arrays, duplicates, and excessive module requests.

Successful results include the normalized request, selected canonical modules, Teach Me and bundle versions, bundle and module digests, repository-relative provenance, supported capabilities, and the host contract. Failures use `{ ok: false, error: { code, message, field? } }`, with no stack or machine details. The adapter imports the generated JSON statically and has no filesystem, process, network, persistence, or LLM runtime dependency. The connected host model remains the teacher.

The only public guidance module in v1 is `topic-led-conversational`; it is a logical identifier rather than a filename. Explicit English omits the Arabic-only style asset. Arabic and host-inferred requests include it so the host can preserve the canonical language behavior. Selection remains deterministic and is limited to assets tagged for the requested active module.

### Cloudflare Worker

The Worker in `mcp/src/worker.ts` owns:

- the public HTTPS and Streamable HTTP boundary;
- protocol dispatch to the adapter;
- request method, content type, protocol version, schema, and size validation;
- deployment configuration, operational limits, and security telemetry that excludes learner content; and
- serving one immutable runtime asset version per deployment.

It does not use a runtime filesystem, execute repository Python scripts, keep correctness-relevant in-memory state, or add KV, D1, R2, Durable Objects, Queues, authentication, or outbound APIs without a demonstrated requirement.

### Host model

ChatGPT or Claude remains the teacher. The host model owns:

- interpreting the learner's request and choosing the supported route;
- using the Teach Me guidance supplied through the integration;
- identifying or safely inferring the learner's goal and starting point;
- explaining progressively with an example;
- changing strategy after confusion;
- offering assessment only at a meaningful unit boundary and waiting for consent;
- keeping progress claims evidence-bounded;
- using only file, web, source, or artifact capabilities actually available in that host; and
- maintaining conversational context for the current chat.

## Explicit non-goals

This foundation does not:

- replace the existing platform editions;
- put the teaching loop behind remote procedure calls;
- call an LLM from the server;
- store profiles, transcripts, progress, quizzes, feedback, or uploaded material;
- provide cross-chat memory or persistence;
- ingest files, PDFs, books, video, audio, or arbitrary URLs;
- perform web research or source verification server-side;
- render HTML or PDF learning packs;
- implement educator, source-grounded, artifact, resume, or domain-pack execution;
- add authentication, accounts, billing, or user-specific authorization; or
- treat generic good teaching or an MCP tool invocation as proof of Teach Me behavior.

## V1 state model

The initial architecture is stateless at the MCP boundary.

| Information | V1 authority | Persistence |
|---|---|---|
| Canonical teaching policy | Versioned deployed runtime assets | Immutable for one deployment |
| Topic and desired outcome | Host conversation | Conversation only |
| Starting-point evidence | Host conversation | Conversation only |
| Current objective and lesson position | Host conversation | Conversation only |
| Confusion and strategy history | Host conversation | Conversation only |
| Assessment offer, consent, questions, and answers | Host conversation | Conversation only |
| Progress or mastery evidence | Host conversation, evidence-bounded | Not stored by MCP |
| Uploaded or retrieved source content | Host capability, outside this first slice | Never stored by MCP |
| MCP request/session transport data | Protocol handling only | Not learner state |

An isolate cache may optimize immutable public assets, but correctness must not depend on a previous request reaching the same isolate. A new request must be answerable from its input and the deployed runtime bundle alone.

Cross-chat continuity is not a v1 promise. If it becomes a product requirement, it requires a separate authenticated design covering consent, minimization, retention, correction, export, deletion, and evidence integrity before storage is selected.

## V1 security boundary

The initial trust boundary contains public, read-only Teach Me product content only.

- The server accepts bounded routing metadata, not full learner transcripts, credentials, source documents, or arbitrary URLs.
- Runtime assets come only from an explicit build-time allowlist inside the repository.
- Retrieved pages, uploaded documents, and learner-provided text remain untrusted host context and never become server instructions.
- The server performs no outbound network fetches and has no secret-bearing backend dependency.
- Requests and outputs have explicit size bounds.
- Unknown methods, unknown fields, invalid enums, unsafe paths, unsupported modes, and malformed protocol messages fail closed.
- Logs contain operational metadata only. Learner prompts, model answers, and returned policy bodies are not intentionally logged.
- The initial anonymous endpoint exposes no private or user-specific data and performs no write action. Authentication must be added before either condition changes.
- Public release still requires abuse controls, dependency review, rate-limit policy, privacy disclosure, and separate compatibility testing for each host.

## Remote MCP Worker (public beta)

The first remote slice is a Cloudflare Worker named `teach-me-mcp` that exposes one read-only tool over MCP Streamable HTTP.

| Item | Value |
|---|---|
| MCP endpoint | `https://teach-me-mcp.ahmedm3bead.workers.dev/mcp` |
| Status endpoint | `GET https://teach-me-mcp.ahmedm3bead.workers.dev/` |
| Transport | Streamable HTTP, stateless, JSON responses (no SSE stream, no `Mcp-Session-Id`) |
| Tool | `load_teach_me` (`readOnlyHint: true`, `destructiveHint: false`, `idempotentHint: true`, `openWorldHint: false`) |
| Authentication | None (public, read-only guidance only) |
| Bindings | None: no KV, D1, R2, Durable Objects, Queues, AI, secrets, or variables |
| Logging | Workers observability disabled; the Worker writes no logs |

The Worker also reserves `GET /.well-known/openai-apps-challenge` for OpenAI directory domain verification. It returns `404` until the publisher configures the exact portal-issued token in the `OPENAI_APPS_CHALLENGE` Worker secret, then returns that token as plain text with no newline. It is not an MCP route and exposes no learner data.

### Protocol and HTTP behavior

- `POST /mcp` handles JSON-RPC requests. Each request builds a fresh SDK `Server` and `WebStandardStreamableHTTPServerTransport`, so correctness never depends on isolate state.
- `GET /mcp` and `DELETE /mcp` return `405` with `Allow: POST, OPTIONS`. The specification permits `405` instead of a standalone SSE stream, and there are no sessions to terminate.
- `OPTIONS /mcp` answers CORS preflight for the allowed origins below.
- `GET /` returns service name, public-beta status, endpoint, Teach Me version, bundle digest, and the privacy statement. Other routes return `404`; other methods return `405` with `Allow`.
- Request bodies are capped at 64 KiB, checked against `Content-Length` and again while streaming, before JSON parsing.
- `Content-Type` must be `application/json` (`415` otherwise). `Accept` must list `application/json` and `text/event-stream` (`406`), and `MCP-Protocol-Version`, when sent after initialization, must be supported (`400`).
- Malformed JSON returns JSON-RPC `-32700`; valid JSON that is not a JSON-RPC 2.0 message returns `-32600`. Unknown tools return `-32602` without echoing the requested name. Error bodies never include stacks, paths, or input values.
- Requests carrying an `Origin` header are accepted only from `https://chatgpt.com`, `https://chat.openai.com`, `https://claude.ai`, or loopback development origins; others receive `403`. Server-to-server requests without `Origin` are accepted.
- Every response sets `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, a deny-all `Permissions-Policy`, `Content-Security-Policy: default-src 'none'`, `X-Frame-Options: DENY`, and `Cache-Control: no-store`. No response sets cookies.

The initialization instructions tell the host to call `load_teach_me` before teaching and follow the returned canonical guidance, and fit within 512 characters. They do not restate teaching policy; all guidance comes from the generated bundle through the pure adapter.

### Tool contract

`load_teach_me` accepts bounded optional selectors: `audience` (`learner` or `educator`), `age_band` (`early-childhood`, `primary-younger`, `primary-older`, `teen`, `adult`, or `unspecified`), `input_mode` (`topic-led` or `source-grounded`), `source_type`, `locale` (`en`, `ar-MSA`, or legacy `ar-EG`), and an exact `guidance_modules` set when a host needs explicit validation. The adapter always includes the compact core, then composes educator, young-learner, source, video, and curriculum guidance only when the selectors require it. The advertised input schema rejects additional properties. The Worker passes arguments unchanged to the pure adapter, which owns all validation, normalization, and selection.

A success returns compact selectors and loaded module identifiers in `structuredContent`, plus one text block containing the model-readable guidance. It does not duplicate module content across both model-visible fields. Bundle digests, paths, classifications, sizes, and per-module hashes are returned in hidden MCP `_meta`. A rejection returns `isError: true` with `structuredContent` `{ ok: false, error: { code, message, field? } }`. The output schema is one flat object with required `ok`, which both result shapes satisfy, for compatibility with ChatGPT and Claude.

### Local development and MCP Inspector

```bash
npm --prefix ./mcp ci
npm --prefix ./mcp run check          # typecheck, build, adapter and protocol tests
npm --prefix ./mcp run dev            # wrangler dev on http://127.0.0.1:8787
```

With the dev server running, test with the MCP Inspector CLI:

```bash
npx @modelcontextprotocol/inspector --cli http://127.0.0.1:8787/mcp --transport http --method tools/list
npx @modelcontextprotocol/inspector --cli http://127.0.0.1:8787/mcp --transport http \
  --method tools/call --tool-name load_teach_me --tool-arg locale=ar-MSA
```

Or run `npx @modelcontextprotocol/inspector`, choose **Streamable HTTP**, and connect to `http://127.0.0.1:8787/mcp` (or the production URL).

### Deployment

Build the production bundle without deploying:

```bash
npm --prefix ./mcp run build:production   # wrangler deploy --dry-run --outdir dist/production
```

Deploy from a clean, validated checkout with Cloudflare credentials for the owning account:

```bash
npm --prefix ./mcp run deploy             # wrangler deploy
```

After deploying, confirm that `GET /` reports the expected `teach_me_version` and `bundle_digest` and that `tools/list` works through MCP Inspector against the production URL.

When the OpenAI submission portal issues a domain-verification token, configure it without committing the value:

```bash
npx wrangler secret put OPENAI_APPS_CHALLENGE --config mcp/wrangler.jsonc
```

Then verify that `https://teach-me-mcp.ahmedm3bead.workers.dev/.well-known/openai-apps-challenge` returns exactly the issued token before selecting **Verify Domain** in the portal.

### Connecting hosts

- ChatGPT (developer mode or plugin connection): `https://teach-me-mcp.ahmedm3bead.workers.dev/mcp`, authentication **None**.
- Claude custom connector: `https://teach-me-mcp.ahmedm3bead.workers.dev/mcp`, no OAuth client ID or secret.

Repository readiness means the Worker is implemented and tested. It does not mean the connector is listed in, reviewed by, or approved for the ChatGPT app directory, the Claude connector directory, or any other marketplace; those reviews are separate.

### Why there is no authentication, and when OAuth becomes mandatory

The endpoint serves only public, versioned, read-only guidance, stores nothing, and performs no user-specific reads or writes, so authentication would protect nothing. OAuth (MCP authorization with protected-resource metadata) becomes mandatory before the service:

- reads or writes any user-specific data, such as profiles, progress, memory, or history;
- accepts learner content, files, or source material for server-side processing;
- performs any write, side effect, or paid operation on a user's behalf;
- exposes non-public, licensed, or tenant-specific content; or
- needs per-user quotas or abuse controls that cannot be keyed anonymously.

## Supported compact slices

The default slice remains learner-facing, topic-led, conversational teaching in English and simplified Modern Standard Arabic:

```text
audience: learner
mode: topic-led
source type: none
artifact type: chat
server state: none
teacher: connected ChatGPT or Claude model
```

The same plugin and the same MCP tool also compose:

- educator guidance when `audience: educator`;
- child- or teen-friendly guidance when a young `age_band` is supplied;
- both together for a teacher preparing child-facing material; and
- source-grounded guidance alongside any of those modes.

The prompt aliases `/learn`, `/teacher`, and `/kids` are convenience text interpreted by the host instructions. They are not native ChatGPT commands and do not create separate plugins or tools.

The slice must preserve the canonical behavior rather than define a reduced teaching method:

1. Accept an explicitly stated beginner starting point and respect transferable expertise.
2. Establish or safely infer a practical outcome and state uncertain assumptions.
3. Ask no more than three high-value questions, and do not delay useful teaching when the request already determines a safe first objective.
4. Teach one manageable objective progressively with a relevant example.
5. Do not turn the interaction into a chain of micro-quizzes.
6. When confusion persists, diagnose a likely barrier and change representation or prerequisite intervention materially.
7. Finish a meaningful unit before offering a routine check.
8. Ask whether the learner wants the check and wait for explicit consent; an explicit request to verify understanding is already consent.
9. Accept a declined check without pressure, penalty language, or a negative progress inference.
10. Do not claim mastery, transfer, or retention without suitable observed evidence.
11. Preserve the teaching language and use simplified Modern Standard Arabic for Arabic input unless English is explicitly requested.
12. End with one clear current action.

The cases in `evals/mcp-poc-cases.yaml` bind this slice back to the canonical skill and routed references through the existing immutable prompt-packet and evaluation machinery.

## Future-compatible modes

The architecture must be able to add independently versioned routes for:

- educator audiences;
- source-grounded teaching;
- source coverage and evidence resources;
- multi-session and resumable journeys;
- learner-authorized structured persistence;
- curricula, learning packs, HTML, and PDF artifacts;
- accessibility-specific delivery;
- high-stakes boundaries;
- reviewed domain packs; and
- consented, minimized feedback.

These are routing and capability extensions around the same canonical assets. They must not become separate teaching engines. Listing them here does not advertise them as implemented by the first remote release.

## Success criteria for the first real MCP journey

A journey succeeds only when all of the following are evidenced:

### Integration evidence

- The intended remote connector is enabled for the conversation.
- A trace shows that the host invoked the Teach Me MCP capability before relying on it.
- The result identifies the expected Teach Me version and runtime bundle digest.
- The returned modules trace to canonical repository assets and their expected digests.
- No LLM API, user database, source fetch, or learner-state write occurs in the MCP service.

### Behavioral evidence

- The response passes the relevant case in `evals/mcp-poc-cases.yaml`.
- English and Arabic behavior are tested independently.
- A beginner receives useful explanation and an example before routine assessment.
- Confusion produces a materially different teaching strategy.
- Assessment questions do not appear before a completed-unit boundary and explicit opt-in.
- Declining assessment produces no pressure, penalty, or unsupported mastery inference.
- The response ends with one clear current action.

### Operational evidence

- The same deployed version returns the same asset digests across fresh requests.
- Fresh and concurrent conversations do not share learner state.
- Malformed, oversized, unknown, and unsupported requests fail safely.
- Existing ChatGPT, Claude, Codex, and Claude Code validation remains green.

A successful MCP handshake or tool call without the behavioral evidence is an integration pass, not a Teach Me product pass.

## Enabled-versus-disabled connector control test

Run paired tests to distinguish Teach Me behavior from generic host teaching.

### Test controls

For each case:

1. Use fresh conversations with the same host product, model, model settings, locale, user turns, and available host capabilities.
2. In the enabled run, enable only the candidate Teach Me remote connector and remove any separately installed Teach Me skill, plugin, custom instructions, memory, or project context.
3. In the disabled run, disable the connector and likewise remove all other Teach Me instruction paths.
4. Do not paste Teach Me policy language into either user prompt.
5. Record the complete user-visible transcript and structured tool trace separately.
6. Grade both runs against the same canonical criteria and deterministic guards. Do not compare exact wording or require the disabled control to fail.

### Enabled-run requirements

- The expected MCP invocation is present before Teach Me-specific behavior is attributed to the connector.
- The returned version and digest match the deployed manifest.
- Every case-specific behavioral criterion passes.
- No response claims capabilities or persistence unavailable in the host.

### Disabled-run interpretation

The disabled run is a control, not a deliberately degraded product. A capable generic model may satisfy some or all criteria. Record which criteria pass, fail, or are not exercised. The control establishes a baseline and helps detect prompts whose success is too generic to demonstrate integration value.

### Attribution rule

Claim only that the enabled journey executed the versioned Teach Me contract when both the MCP trace and observable behavior pass. Do not claim that MCP caused a quality improvement from a single pair. Comparative quality claims require repeated runs, predefined sampling, and aggregated results.
