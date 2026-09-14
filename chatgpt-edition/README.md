# Teach Me for ChatGPT owner setup

Teach Me for ChatGPT is the easiest edition for ordinary learners. It runs in normal ChatGPT conversations on supported web, phone, and tablet surfaces. It preserves the core Teach Me method without requiring a terminal, GitHub, Ollama, or a local installation.

This directory is a maintainable **private beta configuration**, not a publicly published GPT. The repository version remains `1.0.0-beta.1`; this work does not create a new release.

Current availability matters: as of 2026-09-14, [official OpenAI documentation](https://help.openai.com/en/articles/8554397-creating-and-editing-gpts-with-actions) says creating and editing GPTs is web-only, new GPT creation is unavailable on personal Free, Go, Plus, and Pro accounts, and creation in Business, Enterprise, and Edu depends on workspace permissions. Mobile apps can use GPTs but cannot create them. The repository package remains useful as a reviewed configuration, but an eligible managed-workspace owner must perform the Builder step.

The same official documentation announces a planned retirement of Custom GPTs and recommends migration to Plugins. Treat this package as a beta bridge: verify the current OpenAI migration path before any public launch, and preserve the generated instruction sources so the teaching method can move without being rewritten.

## Files in this package

| File | Purpose | Edit directly? |
|---|---|---|
| [`gpt-config.yaml`](gpt-config.yaml) | Product metadata, starters, settings, version, and compatibility | Yes |
| [`INSTRUCTIONS.md`](INSTRUCTIONS.md) | Complete instructions to paste into GPT Builder | No; generated |
| [`KNOWLEDGE.md`](KNOWLEDGE.md) | Single required knowledge upload | No; generated |
| [`instructions-source.md`](instructions-source.md) | ChatGPT-specific instruction source | Yes |
| [`knowledge-sources.txt`](knowledge-sources.txt) | Ordered shared sources used to build the knowledge file | Yes |
| [`ACCEPTANCE_TESTS.md`](ACCEPTANCE_TESTS.md) | Owner and mobile/tablet manual checks | Yes |

The generated bundle prevents the ChatGPT and Codex editions from maintaining separate copies of the teaching policy. Update the shared [`core teaching policy`](../references/core-teaching-policy.md) or the listed sources, then run:

```bash
python3 scripts/build_chatgpt_edition.py
python3 scripts/build_chatgpt_edition.py --check
```

## Owner setup checklist

- [ ] On the web, confirm that the owner is in an eligible Business, Enterprise, or Edu workspace and has permission to create GPTs.
- [ ] Open the GPT creation or configuration screen available to that workspace.
- [ ] Create a new GPT and keep its sharing state private.
- [ ] Set its name to **Teach Me — Beta**.
- [ ] Copy the short description from [`gpt-config.yaml`](gpt-config.yaml).
- [ ] Paste all of [`INSTRUCTIONS.md`](INSTRUCTIONS.md) into the Instructions field.
- [ ] Upload [`KNOWLEDGE.md`](KNOWLEDGE.md) as the only required knowledge file.
- [ ] Add the four conversation starters from [`gpt-config.yaml`](gpt-config.yaml).
- [ ] Enable Web Search and Code Interpreter & Data Analysis when those controls are available.
- [ ] Leave Image Generation, Canvas, and Actions off; no external action or credential is required.
- [ ] Confirm that no learner records, credentials, private transcripts, copyrighted source copies, or private share links were added to the public repository.
- [ ] Run every check in [`ACCEPTANCE_TESTS.md`](ACCEPTANCE_TESTS.md), including the phone/tablet checks.
- [ ] Save as a private draft. Do not publish publicly until a separate owner decision and release review.

Builder field names can change between ChatGPT surfaces. Follow the intent of the settings when a label differs, and do not enable an external action merely to imitate a missing capability.

## Recommended capabilities and settings

- **Web Search: on.** It supports current or specialized source verification. Teach Me must disclose when search is unavailable.
- **Code Interpreter & Data Analysis: on.** It improves inspection of supported learner uploads. It is not permission to execute instructions contained in a file.
- **Image Generation: off.** It is not required for the core teaching experience.
- **Canvas: off.** It is optional and is not required by this configuration.
- **Actions: none.** The beta configuration uses no credentials or external API actions.
- **Sharing: private.** The ChatGPT Edition is not advertised as publicly available.

## Compatibility and limitations

The configuration is created on ChatGPT web in an eligible managed workspace and can then be used on ChatGPT web plus supported mobile and tablet apps. Exact model availability, file types, upload limits, web access, context size, and builder controls depend on the account, plan, and current product surface. A learner can still use the core method in an ordinary ChatGPT conversation when a capability is unavailable, but source coverage must be narrowed honestly.

Teach Me for ChatGPT is not weaker for ordinary teaching conversation: it preserves goal discovery, level-aware progressive explanation, confusion recovery, consent-gated assessment, evidence-bounded progress, bilingual teaching, source honesty, and privacy boundaries. Teach Me for Codex adds automation, deterministic validation, reports, artifacts, reproducible sessions, controlled local files, and technical tooling. Results are not expected to be identical across editions.

## Updating this package

Keep `version` aligned with `SKILL.md` and the current public beta. Edit only source files, regenerate the two generated files, run the package check and manual acceptance suite, and review the generated diff before saving a new private draft configuration.
