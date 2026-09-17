# Teach Me for ChatGPT

Teach Me is a skills-only education plugin for ordinary learners. It needs no separate account, API key, server, or technical setup after installation.

## What learners can do

- Learn a topic from zero or from an existing level.
- Ask for a different explanation when the first one does not work.
- Learn in English or simplified Modern Standard Arabic.
- Study from an uploaded source while keeping source content separate from added explanation.
- Choose whether to take a short understanding check after a meaningful unit.

## Distribution status

This directory is the review-ready public plugin package. Repository inclusion does not by itself mean the plugin is already listed in ChatGPT. Until marketplace review and publication finish, use it only in an authorized development or review environment.

The plugin has no MCP server, external app, sign-in flow, or developer-operated backend. See the [privacy policy](../../docs/privacy-policy.md) and [terms of use](../../docs/terms-of-use.md).

Before submission, run the [consumer acceptance tests](ACCEPTANCE_TESTS.md) and follow the [marketplace submission checklist](../../docs/chatgpt-plugin-submission.md).

## Maintainers

Generate the committed skill and bundled knowledge from their shared sources:

```bash
python3 scripts/build_chatgpt_edition.py
python3 scripts/build_chatgpt_edition.py --check
```

Validate the plugin package with the current plugin validator before submission.
