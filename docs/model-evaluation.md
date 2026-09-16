# Model evaluation protocol

Repository validation proves structure and runner behavior. It does not prove that a real model teaches well. A release claim about model quality requires both static behavioral cases and closed-book teacher/learner simulations.

## Zero-cost local evaluation with Ollama

Use a local Ollama model while the product is being validated. This creates real named-model evidence without sending evaluation content to a paid API. The bundled adapter rejects non-loopback hosts unless `--allow-remote` is supplied explicitly.

Install and start Ollama, then pull the models:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:8b
ollama pull gemma3:4b
ollama pull qwen3:4b
```

Use the larger model as the teacher, a different family as the zero-knowledge learner, and a separate smaller model as the grader. On lower-memory machines, replace `qwen3:8b` with `qwen3:4b` for the first smoke run.

Start with one Arabic teaching case:

```bash
python3 scripts/run_behavioral_evals.py \
  --case golden-teaching/primary-school-concept \
  --response-command "python3 scripts/ollama_eval_adapter.py --role response --model qwen3:8b --num-ctx 8192 --num-predict 768" \
  --grader-command "python3 scripts/ollama_eval_adapter.py --role grader --model gemma3:4b --num-ctx 8192 --num-predict 768" \
  --output reports/local-smoke.json \
  --timeout 600
```

Then run the critical zero-knowledge simulation:

```bash
python3 scripts/run_agent_simulations.py \
  --simulation zero-knowledge-fictional/luma-routing-ar-msa \
  --teacher-command "python3 scripts/ollama_eval_adapter.py --role teacher --model qwen3:8b" \
  --learner-command "python3 scripts/ollama_eval_adapter.py --role learner --model gemma3:4b" \
  --grader-command "python3 scripts/ollama_eval_adapter.py --role grader --model qwen3:4b" \
  --output reports/local-simulation.json \
  --timeout 600
```

Only after both smoke commands pass, remove `--case` to run all static suites and remove `--simulation` to run all simulations. Record `ollama list`, the model tags, model settings, repository commit, reports, duration, and failed cases in the release receipt. A mutable model tag is not enough for long-term reproduction; retain the digest shown by Ollama as well.

Local results prove behavior only for the recorded local models. Before claiming compatibility with a hosted provider, run a small representative compatibility sample on that provider. Save a full paid run for the release candidate rather than every commit.

## Paid evaluation with the official OpenAI API

Install the exact dependencies from `requirements-dev.txt`, export `OPENAI_API_KEY` in the parent process, and pass only its environment-variable name. The adapter refuses a literal key or any alternative credential variable. The runner excludes the key from every adapter environment unless the matching per-role option is present.

Confirm model access without making a Responses API generation:

```bash
python3 scripts/openai_api_eval_adapter.py \
  --role response \
  --model gpt-5.6-sol \
  --api-key-env OPENAI_API_KEY \
  --check-access
```

For the single complete release-candidate run, use:

```bash
python3 scripts/run_behavioral_evals.py \
  --response-command "python3 scripts/openai_api_eval_adapter.py --role response --model gpt-5.6-sol --api-key-env OPENAI_API_KEY --max-output-tokens 2048 --long-artifact-max-output-tokens 4096 --reasoning-effort none --temperature 0 --timeout 600" \
  --grader-command "python3 scripts/openai_api_eval_adapter.py --role grader --model gpt-5.6-sol --api-key-env OPENAI_API_KEY --max-output-tokens 2048 --reasoning-effort none --temperature 0 --timeout 600" \
  --response-api-key-env OPENAI_API_KEY \
  --grader-api-key-env OPENAI_API_KEY \
  --expected-response-model openai/gpt-5.6-sol \
  --expected-grader-model openai/gpt-5.6-sol \
  --release-evidence \
  --candidate-commit FULL_FINAL_SHA \
  --pass-threshold 0.90 \
  --protocol-retries 0 \
  --pricing-file evals/pricing/openai-gpt-5.6-sol-standard.json \
  --authorized-cost-usd 18.912125 \
  --conservative-max-cost-usd 18.912125 \
  --hard-spend-cap-usd 7.00 \
  --output reports/openai-api-behavioral-evals-FULL_FINAL_SHA-fresh-UNIQUE_UTC.json \
  --timeout 660
```

The adapter uses Standard processing (`service_tier=default`), `store=false`, strict JSON Schema output, no tools, no SDK retries, controlled fixtures only, `reasoning.effort=none`, and `temperature=0`. Ordinary response and all grader requests retain a 2,048-token output bound. A response receives the targeted 4,096-token bound only when committed metadata classifies it as a `substantial` or `journey` file-backed deliverable of type `markdown`, `html`, `pdf`, `curriculum`, or `learning-pack`, with `capabilities.file=executable_temp`. This is capability-based and never keyed to a case ID. The response and grader are separate stateless requests. Invocation evidence records only the credential environment-variable name.

Before the run, calculate a conservative ceiling for all 95 response requests and 90 grader requests. Sum each request's actual configured maximum rather than multiplying every request by one global bound. Include the rendered prompt and strict schema, every earlier model response copied into multi-turn history, each response or artifact copied into its grader packet, the final response's additional `raw_final_response` copy, JSON escaping/re-tokenization headroom, and fixed request metadata. Use the larger count from the provider encoding and a conservative comparison encoding. At the current [GPT-5.6 Sol Standard prices](https://developers.openai.com/api/docs/models/gpt-5.6-sol), bill uncached input at $4.00/M tokens, cached input at $0.40/M, cache writes at $5.00/M, and output at $20.00/M. Aggregate input is the total of three mutually exclusive categories: cached reads, cache writes, and the uncached remainder. Never add the aggregate input charge to its cached or cache-write subcategories. Reasoning tokens are included in output tokens and must be reported separately without double-counting.

For the current 90-case suite, 19 of the 95 response requests qualify for the 4,096-token long-artifact bound. The response maximum is `76 × 2,048 + 19 × 4,096 = 233,472` tokens. The 90 grader requests add `90 × 2,048 = 184,320`, producing the 417,792-token output ceiling. Protocol retries are zero, so there is exactly one permitted attempt per request. Using the larger of `o200k_base` and `cl100k_base` for each complete rendered prompt-plus-schema request, twice each embedded output maximum for escaping/re-tokenization, and 100 metadata tokens per request gave the earlier aggregate input ceiling of 1,776,572 tokens. The preceding policy changes added at most 133,855 input tokens. This remediation adds at most another 200,830 input tokens under the same stricter byte-for-token bound, charging every positive UTF-8 byte increase in each changed routed policy to all 95 response requests even when a reference is not routed. The resulting aggregate input ceiling is 2,111,257 tokens.

Because any input token can be a cache write and cache writes are the most expensive input category, the conservative input charge is `2,111,257 × $5/M = $10.556285`. The output charge is `417,792 × $20/M = $8.355840`. The corrected total is therefore **$18.912125**. The source-bound calculation also records a 200,000-token maximum planned input per request, below the model's 272,000-token high-context pricing threshold. Obtain at least **$18.912125 of new authorization** before a future fresh run.

Pass the source-bound pricing policy, full prospective authorization, calculated conservative maximum, and independent operational spend cap through `--pricing-file`, `--authorized-cost-usd`, `--conservative-max-cost-usd`, and `--hard-spend-cap-usd`. The theoretical full-run ceiling is **$18.912125** even when the operator selects the separate **$7.00** hard cap. Release-evidence mode verifies the policy's official source, exact model and Standard tier, four independent rates, cost-sensitive source hashes, request counts, output limits, retry count, token ceilings, and calculated price before it creates a paid request. It refuses to start if pricing is missing or stale, token categories cannot reconcile, the declared calculation differs, or the full ceiling exceeds authorization. Authorization is not a running balance: money spent on any earlier attempt—including an interrupted or failed attempt—is sunk and excluded from the additional authorization for a new attempt. Every new report therefore needs authorization for its full prospective ceiling, not the earlier attempt's unused remainder. Recalculate after any prompt, schema, case, routing, output bound, model, or price change. A case-local failure does not create permission for an extra request. Do not add a paid smoke test, use Batch, enable retries, resume a completed educational case, or reuse an existing report filename.

Reports price realized usage by subtracting cached reads and cache writes from aggregate input to obtain the uncached remainder, then applying the four rates independently. Before every response or grader dispatch, the runner renders that exact payload and strict schema, counts every submitted UTF-8 byte as a token plus the committed 100-token metadata allowance, rejects bounds above the committed 200,000-token planned limit, assumes every input token could be a `$5/M` cache write, and adds the request's exact output-token limit at the applicable output price. It never falls back to the provider-global `$9.281440` reservation when a request-specific bound cannot be calculated.

The dispatch gate is `recorded cost + unresolved reservations + next-request maximum <= hard spend cap`. Each successful request replaces its reservation with independently priced provider usage. A request interrupted after dispatch without usable provider usage keeps its entire reservation as `unresolved-spent`. If the next request cannot fit, the runner writes a `stopped-hard-spend-cap` partial report before dispatch and exits without making that request. Cost accounting separately reports the `$18.912125` theoretical ceiling, `$7.00` hard cap, recorded cost, unresolved reservations, and remaining spendable budget. A hard-cap-stopped report is explicitly marked ineligible for release evidence.


Behavioral cases must declare the canonical locale `ar-MSA` or `en`; missing, ambiguous, invalid, and legacy `ar-EG` case locales fail validation before adapter execution. Inputs written in an Arabic dialect still use `ar-MSA`. The runner independently checks script dominance, colloquial markers, preserved technical terms, response completeness, and premature assessment; model-grader approval alone is never sufficient.

## Static behavioral evaluation

The response adapter receives JSON with `type: generate`, chronological history, explicit locale, case identifiers, and an immutable `prompt_packet`. The packet contains the complete content and SHA-256 of `SKILL.md` and every conditionally routed reference, routing axes, an explicit capability-state manifest, and controlled synthetic inputs resolved from stable fixture IDs. It returns complete invocation evidence and a structured artifact array (empty when no file is requested):

```json
{"response":"...","artifacts":[],"model":"provider/model-version","settings":{},"adapter_version":"...","raw_result":{},"invocation_id":"...","timing":{"started_at":"...","completed_at":"...","duration_seconds":0.0}}
```

The independent grader receives `type: grade`, the ordered numbered transcript, structured assessment events, relevant case context, controlled results, actual artifact validation, raw final response, criteria, and evidence rule. It returns one evidence-bearing verdict per criterion with the same invocation metadata:

```json
{"model":"provider/grader-version","settings":{},"adapter_version":"...","raw_result":{},"invocation_id":"...","timing":{},"results":[{"verdict":"pass","evidence":{"source":"response","turn":2,"quote":"exact excerpt"},"reason":"why the excerpt satisfies the criterion"}]}
```

Deterministic educational, language, terminology, completeness, text-quality, and consent failures are fail-closed and are never regenerated. A structurally valid `PASS` whose reasoning says behavior required by the criterion is absent, implicit, deferred, or unperformed is conservatively downgraded to `FAIL`; criteria that explicitly require prohibited behavior to be absent remain eligible to pass when exact evidence proves that absence. The report records every downgrade's original verdict and evidence as a grader-protocol adjustment, and the run continues without another paid request. A later deterministic success cannot erase a grader failure, a protocol failure, or an earlier selected-turn rejection.

Every grader `PASS` quote must occur exactly in its identified assistant turn or generated artifact. If any verdict cites absent text or otherwise violates the grader protocol after the configured retry count, none of that grader's verdicts are accepted: the case fails, all criteria receive fail-closed protocol evidence, and the run continues. The report retains the invalid verdicts and evidence, their hash, model identity, settings, timing, request/API metadata, usage, and protocol error. With `--protocol-retries 0`, the grader is not retried. Contradictory-`PASS` downgrade remains separate: it converts the individual verdict conservatively and increments the adjustment count without making an additional request.

If the OpenAI API returns a non-completed response, the adapter does not parse, expose, accept, or grade partial output. It returns auditable model identity, timing, usage, API identifiers, response status, and `incomplete_details.reason`. The runner records that invocation as `model-protocol-error`, fails the case with absent evidence, skips its grader request, and continues with the remaining cases. The final summary separately counts skipped graders, model-protocol case failures, grader-protocol case failures, malformed grader attempts, infrastructure failures, adjustments, and aggregate usage.

The runner applies the following explicit taxonomy after a case begins:

| Scope | Failure paths | Required behavior |
| --- | --- | --- |
| Case-local | Educational failure; deterministic-guard rejection or guard execution failure; completed-but-incomplete response; response schema/protocol failure with auditable usage; artifact extraction/schema failure; artifact validation failure; grader schema or evidence failure; contradictory `PASS`; response or grader command error/timeout whose usage is auditable or provably zero-cost | Finalize that case as failed, preserve the available raw result, hashes, timing, model/API metadata, and usage, skip the grader when the response or artifact is invalid, checkpoint atomically, and continue. Invalid artifacts remain failures even though the run continues. |
| Global | Candidate/`origin/main`/merge-base or tracked-tree drift; credential-boundary or report-exposure risk; requested/returned release-model mismatch; missing or inconsistent usage after a credential-bound invocation; conservative cost above authorization; report collision, stale/corrupt resume evidence, invalid global configuration, serialization failure, or inability to persist evidence atomically; operator interruption | Fail the run immediately. Continuing would compromise release integrity, credential safety, spending accountability, or evidence durability. |

A credential-bound command error, timeout, or malformed stdout is case-local only when the adapter still returned a valid usage record; without that evidence the runner cannot safely account for spending and aborts globally. Zero-credential deterministic fixtures are provably zero-cost and may continue. `NonRetryableEvaluationError` represents completed case-local content or artifact rejection and never implies a whole-run abort by itself. A generated artifact that fails extraction or validation is never accepted or graded: the report retains its rejected response and raw-result reference plus non-accepting artifact path/media-type/hash/byte evidence, marks the grader skipped, finalizes the failed case, and advances.

The report is atomically initialized as `running`, checkpointed through turns, guards, and grading, and finalized as `complete` or `failed`. A fresh release run refuses to overwrite an existing report. Resume accepts only a matching Git and run-configuration fingerprint and does not rerun completed educational responses. The runner re-verifies release Git evidence before every response and grader request. It preserves immutable prompt packets, raw responses, invocation evidence, accepted and rejected artifact hashes and validation, deterministic guards, grader evidence, timestamps, duration, and internally consistent request/failure/skipped/adjustment/usage counts. Before any write it serializes the complete report and refuses persistence if the credential value is present. Instruction bodies are stored once by content hash; prompt packets and journal entries use lossless hash references instead of repeating those bodies.

Reference routing uses independent metadata for audience, mode, source type, locale, artifact type, capability state, session state, accessibility, instructional scope, assessment state, safety level, and domain pack. `supplied_result` requires an authorized, simulated, provenance-bearing registry record with a verified content hash. `unavailable` is graded on the safe fallback. The Codex adapter permits subscription model transport but gives the response agent a read-only sandbox and only controlled external-source observations; it does not claim a generic network switch it cannot prove.

Release evidence additionally requires `--release-evidence --candidate-commit FULL_SHA`. Before either adapter runs, the runner proves that the full SHA equals `HEAD`, `origin/main`, and their merge base and that the tracked worktree is clean. Non-release fixture runs cannot provide a candidate SHA.

Run:

```bash
python3 scripts/run_behavioral_evals.py \
  --response-command "YOUR_RESPONSE_ADAPTER" \
  --grader-command "YOUR_GRADER_ADAPTER" \
  --output reports/behavioral-evals.json
```

## Dynamic zero-knowledge simulation

The learner adapter never receives hidden fictional teaching material. This makes leakage visible and lets the runner measure baseline-to-transfer gain. The saved transcript includes the learner's closing message even when it ends the dialogue.

- `type: baseline`: return `{"answer":"...","model":"..."}` from persona and baseline task only.
- `type: dialogue`: return `{"utterance":"...","assessment_intent":"none|accept|decline","done":false,"model":"..."}`. All three protocol fields are required. `done` must be a JSON Boolean and may become true only after every required learner behavior has been exercised.
- `type: transfer`: return `{"answer":"...","model":"..."}` from the transcript and fresh task.
- The teacher adapter receives `type: teach`, the governing material, transcript, current learner message, and `skill_root`; return `{"response":"...","model":"..."}`.
- The grader receives `type: simulation-grade`; return `baseline_score` and `transfer_score` from 0 to 1 plus one criterion result per expected item.

Run:

```bash
python3 scripts/run_agent_simulations.py \
  --teacher-command "YOUR_TEACHER_ADAPTER" \
  --learner-command "YOUR_LEARNER_ADAPTER" \
  --grader-command "YOUR_GRADER_ADAPTER" \
  --output reports/agent-simulations.json
```

The run fails when pass rate is below 90%, any critical simulation fails, transfer is below its scenario threshold, learning gain is below its threshold, or an authoritative deterministic guard fails. Dynamic reports record hard checks for the closed-book learner payload boundary, Arabic/English output language, Unicode text quality, assessment opt-in, teacher-response completeness, and unsupported mastery claims. The model grader cannot override them. Fixture adapters only test plumbing and must never be reported as model-quality evidence.

The structured dialogue contract is the only supported live-adapter protocol before v1; live adapters that return the old `message` field or omit `assessment_intent` are rejected. Stored transcripts and reports that predate the structured event remain readable through conservative text classification, but that compatibility does not relax validation for a new live run.

## Release evidence

Record candidate commit, previous release, exact model identifiers, model settings, runner commands, date, result files, costs, failed cases, and a manual Arabic/English grader sample. Do not commit raw real-user transcripts. Synthetic scenarios may be committed; private evaluation data should be minimized and retained only with authorization.
