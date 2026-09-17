# Compatibility and capability matrix

Teach Me supports four product surfaces through several delivery styles. **ChatGPT** prioritizes a skills-only plugin for ordinary learners, with a private configured GPT retained for owner testing until marketplace publication. **Claude** uploads a verified Teach Me ZIP as a custom skill. **Codex** and **Claude Code** install the Agent Skill and add the repository's local tooling, controlled artifacts, and validation workflows. The hosts are not technically identical, and output can differ with model, tool, context, and execution environment.

The ChatGPT plugin package is ready for marketplace review but must not be described as listed until approval and publication finish. It has no MCP server, external app, sign-in flow, or developer-operated backend. The separate ChatGPT Edition package remains a private owner configuration; when the signed-in web editor exposes **Create**, the owner can follow [`../chatgpt-edition/README.md`](../chatgpt-edition/README.md). Claude and Claude Code setup is documented in [`../claude-edition/README.md`](../claude-edition/README.md). A host must expose a capability before the skill may claim to have used it.

| Capability | Without it | With it |
|---|---|---|
| Read `SKILL.md` and references | The skill cannot be installed | Core Arabic and English teaching works |
| File read/write | Teach in chat and emit a `TEACH-ME:v2` locator | Maintain connected curricula, lessons, and evidence files after permission |
| Web research | Disclose the limit and narrow current or specialized claims | Run the evidence and broad-research workflows |
| PDF/document extraction | Ask for accessible text or teach an independently researched scope | Inspect the supplied document and record actual coverage |
| Audio/transcript access | Never claim audiovisual coverage | Inspect spoken content and cite timestamps |
| Video-frame or screenshot access | Never claim on-screen details | Inspect relevant visual demonstrations and record sampling limits |
| HTML/PDF rendering | Provide structured chat or source HTML | Produce and visually verify bidirectional learner artifacts |
| Persistent scheduler | Give a portable next-review plan | Schedule evidence-based review when the user authorizes it |
| Python 3.10+ | Teaching still works | Bundled schemas, integrity checks, eval runner, and packaging tools work |

## Language compatibility

The canonical locales are `ar-MSA` and `en`. Arabic input in any dialect defaults to simplified Modern Standard Arabic. The retired `ar-EG` value is accepted only at compatibility boundaries and is normalized immediately to `ar-MSA`; it never requests Egyptian Arabic. New files and eval cases must write only canonical locale values.

## Cost model

The repository and local validators are free. A host, model provider, web search service, transcription service, storage service, or PDF/video tool may have its own price. Teach Me must not silently select a paid dependency or imply that every optional capability is free.

## Behavioral eval adapter protocol

`scripts/run_behavioral_evals.py` is provider-neutral. Every case declares canonical routing metadata, a seven-capability state manifest, and stable references into the typed, content-addressed synthetic fixture registry. `supplied_result` is an observation only. `executable_temp` file output is accepted only as structured artifact content, materialized without overwrite in a disposable workspace, hashed, and—when requested—rendered from that actual artifact. The response and isolated grader must return model identity, settings, adapter version, raw result, invocation ID, and timing. Grader PASS evidence names the exact assistant turn or generated artifact containing its quote; FAIL may identify an absent requirement. Deterministic guards remain authoritative. Guard failures never trigger response regeneration; only bounded transport or malformed-protocol retries are allowed and recorded.

The repository's reference PDF path uses the exact versions in `requirements-dev.txt` and may additionally need the platform libraries required by WeasyPrint. The HTML remains the accessible source of truth if the renderer is unavailable. Dynamic teacher/learner evaluation uses the separate protocol in [`model-evaluation.md`](model-evaluation.md).
