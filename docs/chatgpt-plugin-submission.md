# ChatGPT plugin submission checklist

This checklist separates repository readiness from actions that require the publisher's ChatGPT account and marketplace review.

## Repository-ready evidence

- [x] Skills-only plugin package under `plugins/teach-me/`.
- [x] Valid plugin manifest and repository marketplace entry.
- [x] Consumer-facing name, descriptions, category, starter prompts, and icon.
- [x] No MCP server, external app, backend, API key, payment, or sign-in dependency.
- [x] Generated skill and knowledge bundle share the reviewed teaching sources used by the private ChatGPT Edition.
- [x] Public privacy policy and terms of use.
- [x] Automated checks for version alignment, generated outputs, metadata, links, and bundled assets.
- [x] Manual consumer acceptance-test plan for Arabic, English, source-grounded learning, privacy, and phone or tablet use.

## Publisher-account steps

1. Open the current ChatGPT plugin publishing or review surface using the intended publisher account.
2. Import or select the exact `plugins/teach-me/` candidate from the reviewed repository commit.
3. Confirm the publisher identity shown to users is **Ahmed Ebead** and that all policy links open from the immutable reviewed commit or the merged public branch.
4. Install the candidate privately and run every [consumer acceptance test](../plugins/teach-me/ACCEPTANCE_TESTS.md) on desktop and on at least one phone or tablet.
5. Capture genuine screenshots from the installed candidate; do not use mockups as evidence of product behavior.
6. Confirm the listing says **beta**, does not promise perfect accuracy or learning outcomes, and does not claim unavailable tools or memory.
7. Submit for marketplace review. Record the submitted commit SHA and do not change the reviewed package while that submission is pending.
8. After approval, verify the public listing and installation from a separate ordinary learner account before announcing availability.

## Publication boundary

Passing repository validation makes the package review-ready; it does not publish or approve the plugin. Until the marketplace listing is visible and independently installable, documentation must say **ready for review**, not **available to everyone**.
