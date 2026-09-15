# Development and validation

This page is for contributors and release maintainers. Learners do not need these commands.

## Requirements

- Python 3.10 or newer.
- Exact development packages from `requirements-dev.txt`.
- A clean checkout for release evidence.

Installer tests use isolated temporary roots and fixture archives. Deterministic validation does not start Ollama, call paid APIs, or run behavioral model generation.

## Install development dependencies

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pip check
```

## Fast documentation check

```bash
python3 scripts/build_chatgpt_edition.py --check
python3 scripts/check_product_docs.py
python3 scripts/check_markdown_links.py
python3 scripts/test_installers.py
```

## Complete deterministic Linux validation

The Linux `validate` job in [`.github/workflows/validate.yml`](../.github/workflows/validate.yml) is authoritative:

```bash
python3 -m pip check
python3 scripts/check_dependency_pins.py
python3 scripts/check_context_budget.py
python3 scripts/build_chatgpt_edition.py --check
python3 scripts/check_product_docs.py
python3 scripts/check_markdown_links.py
python3 scripts/test_installers.py
bash -n installers/install.sh
python3 scripts/validate.py
python3 scripts/validate_schemas.py
python3 scripts/validate_evals.py
python3 scripts/validate_domain_packs.py
python3 scripts/validate_simulations.py
python3 scripts/run_behavioral_evals.py --validate-only
python3 scripts/run_agent_simulations.py --validate-only
python3 scripts/test_behavioral_eval_runner.py
python3 scripts/test_openai_api_eval_adapter.py
python3 scripts/test_agent_simulations.py
python3 scripts/test_ollama_eval_adapter.py
python3 scripts/test_package_release.py
python3 scripts/test_feedback_pipeline.py
python3 scripts/test_validate_bidi_html.py
python3 scripts/test_validate_session.py
python3 scripts/test_validate_resume.py
python3 scripts/test_session_manager.py
python3 scripts/test_profile_lifecycle.py
python3 scripts/test_render_learning_pack.py
python3 scripts/test_inspect_source.py
python3 scripts/validate_session.py fixtures/session/learning-session.json \
  --coverage fixtures/session/source-coverage.json \
  --knowledge-base fixtures/session/knowledge-base.json \
  --curriculum-map fixtures/session/curriculum-map.json \
  --curriculum fixtures/session/study-curriculum.json \
  --claims fixtures/session/claim-ledger.json \
  --lesson fixtures/session/lesson-plan.json \
  --progress fixtures/session/progress.json
```

The portable matrix runs the applicable shared checks on macOS and Windows. Dynamic simulations and paid behavioral evaluations are separate, explicitly invoked workflows.

## Before contributing

Read [CONTRIBUTING.md](../CONTRIBUTING.md). Remove personal data, credentials, private transcripts, protected curricula, generated reports, and model outputs before opening a pull request.
