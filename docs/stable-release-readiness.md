# Stable v1.0.0 readiness

Updated: 2026-10-11. The complete multi-host package remains `1.0.0-beta.2`. The separately published ChatGPT listing is `1.0.0`; its approval does not authorize a stable multi-host release.

## Preflight work

- Codex subscription transport was tested with CLI 0.159.0 and the recorded `codex/gpt-5.6-sol` model.
- Windows adapter subprocesses use UTF-8 and retain `SystemRoot` without forwarding API keys, proxy credentials, or unrelated secrets.
- Child routing loads `children-mode.md`; natural from-zero explanations and familiar object examples are recognized by the onboarding guard.
- The shared policy acknowledges an explicit beginner starting point. Child guidance separates observing an example from requesting an application answer before consent.
- A closed-book subscription simulation adapter rejects privileged learner inputs and uses independent ephemeral roles. Its leakage/role/protocol regression tests pass.
- A failed authoritative criterion is counted as a deterministic failure even when the model grader passes it.
- An explicit subscription release route rejects alternate adapters and paid API options while retaining exact-SHA and full-suite checks. The paid API pricing policy remains stale and must not be reused.

## Gates still required

- [ ] Final candidate metadata and generated artifacts are prepared and merged, with `HEAD`, `origin/main`, and merge base matching the candidate SHA.
- [ ] Full real-model behavioral run: currently 95 committed cases, at least 90% passing, zero critical failures, no fixture evidence substitution.
- [ ] Previous-release comparison using recorded response and independent grader sessions.
- [ ] Both closed-book learner simulations pass their transfer/gain and safety/consent checks.
- [x] The repository owner confirmed completion of the human-review requirement in this chat on 2026-10-11 (Arabic and English review scope discussed above). This is owner-attested completion; the assistant did not independently observe the review. See `human-review-attestation-2026-10-11.md`.
- [ ] A complete learner journey and an educator/source-grounded journey are reviewed.
- [ ] A mixed Arabic/English HTML learning pack and its PDF pages, links, and code readability are inspected.
- [ ] A genuine `real-release` receipt bound to the final candidate SHA passes `verify_release_evidence.py`.
- [ ] Reproducible archives and adjacent checksums are built, then the stable tag and GitHub release are published.

## Diagnostic evidence

Preflight reports remain under ignored `reports/`. Early runs contained Windows encoding/transport failures; later runs reached the real response and grader. Child teaching diagnostics exposed both evaluator false negatives and actual starting-point/assessment issues. The corrected Arabic primary-school smoke case passed all criteria, with no infrastructure, protocol, guard, or educational failure. This is one case only. These smoke reports are not full-suite pass evidence and must never be used as the stable release receipt.

Use [the model evaluation protocol](model-evaluation.md) and [release checklist](release-checklist.md). Keep human reviews pending until a person actually completes them. This preflight record does not establish that stable quality gates have passed. It does not record a production MCP redeployment or a paid API evaluation.
