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

Arabic model runs use canonical `ar-MSA`. Inputs written in an Arabic dialect and legacy `ar-EG` payloads are normalized to simplified Modern Standard Arabic. The runner independently checks script dominance, colloquial markers, preserved technical terms, response completeness, and premature assessment; model-grader approval alone is never sufficient.

## Static behavioral evaluation

The response adapter receives JSON with `type: generate`, prompt/history, locale, case identifiers, and `skill_root`. It returns:

```json
{"response": "...", "model": "provider/model-version"}
```

The independent grader receives `type: grade`, the transcript, expected observable criteria, and grading rule. It returns one boolean result per criterion:

```json
{"model": "provider/grader-version", "results": [{"passed": true, "reason": "observable evidence"}]}
```

Each case report records `response_attempts`, `selected_attempts` (one per turn), the final-turn `selected_attempt`, `deterministic_preflight_passed`, and an `attempt_log` containing the model, seed, acceptance state, and deterministic rejection reasons for every generation attempt. A later successful turn cannot erase a deterministic rejection in an earlier selected turn.

Run:

```bash
python3 scripts/run_behavioral_evals.py \
  --response-command "YOUR_RESPONSE_ADAPTER" \
  --grader-command "YOUR_GRADER_ADAPTER" \
  --output reports/behavioral-evals.json
```

## Dynamic zero-knowledge simulation

The learner adapter never receives hidden fictional teaching material. This makes leakage visible and lets the runner measure baseline-to-transfer gain.

- `type: baseline`: return `{"answer":"...","model":"..."}` from persona and baseline task only.
- `type: dialogue`: return `{"message":"...","done":false,"model":"..."}`. Set `done` true only after the scripted learner behavior has reached a natural endpoint.
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

The run fails when pass rate is below 90%, any critical simulation fails, transfer is below its scenario threshold, or learning gain is below its threshold. Fixture adapters only test plumbing and must never be reported as model-quality evidence.

## Release evidence

Record candidate commit, previous release, exact model identifiers, model settings, runner commands, date, result files, costs, failed cases, and a manual Arabic/English grader sample. Do not commit raw real-user transcripts. Synthetic scenarios may be committed; private evaluation data should be minimized and retained only with authorization.
