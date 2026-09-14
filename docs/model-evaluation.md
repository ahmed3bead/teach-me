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

Deterministic educational, language, terminology, completeness, text-quality, and consent failures are fail-closed and are never regenerated. A retry is permitted only for a recorded transport or malformed-protocol failure, defaults to one, and is capped at two. The report preserves every protocol attempt and retry cause. A later turn cannot erase an earlier selected-turn rejection.

The report is atomically initialized as `running`, checkpointed through turns, guards, and grading, and finalized as `complete` or `failed`. Resume accepts only a matching Git and run-configuration fingerprint and does not rerun completed educational responses. It preserves immutable prompt packets, raw responses, invocation evidence, artifact hashes and validation, deterministic guards, grader evidence, timestamps, and duration. Instruction bodies are stored once by content hash; prompt packets and journal entries use lossless hash references instead of repeating those bodies.

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
