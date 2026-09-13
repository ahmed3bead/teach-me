# Compatibility and capability matrix

Teach Me follows the Agent Skills layout and keeps core conversational teaching usable without optional tools. A host must expose a capability before the skill may claim to have used it.

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

## Cost model

The repository and local validators are free. A host, model provider, web search service, transcription service, storage service, or PDF/video tool may have its own price. Teach Me must not silently select a paid dependency or imply that every optional capability is free.

## Behavioral eval adapter protocol

`scripts/run_behavioral_evals.py` is provider-neutral. The response command receives a JSON object containing the suite, case, prompt, locale, and skill root, then returns `{"response": "...", "model": "..."}`. The grader command receives that response and the observable criteria, then returns one boolean result per criterion. A release run fails below the configured case threshold or when any case marked `critical` fails.

The repository's reference PDF path uses the exact versions in `requirements-dev.txt` and may additionally need the platform libraries required by WeasyPrint. The HTML remains the accessible source of truth if the renderer is unavailable. Dynamic teacher/learner evaluation uses the separate protocol in [`model-evaluation.md`](model-evaluation.md).
