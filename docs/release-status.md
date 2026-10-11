# Current release status | حالة الإصدار الحالية

Last updated: 2026-10-11

## Approved and published

Teach Me | علّمني has been approved by OpenAI and published in the ChatGPT Plugins Directory.

- Public listing: [Install Teach Me | علّمني](https://chatgpt.com/plugins/plugin_asdk_app_6ab81f50a2b881918abe2865d47fb2a3)
- Public listing version: **1.0.0**.
- Developer: Ahmed Ebead.
- Verification date: **2026-10-11**. This is the date the public page was checked, not a claim about the original approval or publication date.
- The listing was accessible without signing in and displayed **Install plugin**; installation requires signing in to ChatGPT. Installation from a separate learner account has not been verified in this check.

## Runtime evidence

The [release record](published-release.json) captures the observed deployment comparison:

- Runtime and repository package version: **1.0.0-beta.2**; listing version: **1.0.0**.
- Production and beta bundle digest: `sha256:efbe6e8a20891fddcafbf9eb5a5ff9469779e8df12f2b3d3f23df2a9d367d2f4`.
- Comparison repository commit: `b54b0a4f9f1ca0311508712a0d52b512f30b0a44` (approval documentation merge); this is not a claim about the original deployment commit.
- Tool schema, description, annotations, and complete responses for seven routing cases match the local implementation. The generated bundle is current with its six source assets.
- Original deployment commit, approval date, and publication date: unknown.

The repository's generated MCP bundle has since changed to the v1.0.1 candidate digest `sha256:d4b8a36f43dc09278720ff75a662b15807ff532dc9118a5f9439744dae634f32`; the earlier candidate `sha256:6dc9dc84d1866ea0af904f9d80b5013f8a969eae9befb0142872aa2a7cb0f94e` is the one described below. Beta was redeployed with this candidate on 2026-10-11 from commit `cc03b22` (Cloudflare version `5ffbbe58-9363-47f2-b205-8200edcea1e7`). Beta `GET /` reports the candidate digest; production still reports `efbe6e8a…` and has not been redeployed. Automated checks against beta passed for `initialize`, `tools/list`, security headers, and `load_teach_me` calls in English, `ar-MSA`, legacy `ar-EG`, educator, child, and source-grounded book, course, and curriculum routes; the new guidance is present where routed. Manual ChatGPT acceptance on the beta connection is still pending.

The public listing description and subtitle match `chatgpt-app-submission.json`; listing starter prompts are recorded in `docs/published-release.json`. The local skills-only manifest mirrors this copy but retains its independently versioned package metadata. The full repository also includes Codex/Claude workflows and development tools outside the compact MCP guidance bundle.

The published description includes learner, educator, parent, age-aware, and source-grounded workflows. These checks verify the observable MCP guidance and metadata; they do not prove every internal ChatGPT setting or conversation outcome. Merging changes into `main` does not automatically update the published plugin, production MCP server, or Direct Upload guide.

See [user-link verification](user-link-verification-2026-10-11.md) for the installation, guide, policy, terms, and support checks.

## Future updates

The 2026-09-27 plan to cancel the earlier review and resubmit is historical and no longer the current release instruction. For future changes, test the candidate on the beta endpoint, follow the submission checklist, and record the deployed version and any required review before updating production.

Current endpoints:

- Production MCP: `https://teach-me-mcp.ahmedm3bead.workers.dev/mcp`
- Beta MCP: `https://teach-me-mcp-next.ahmedm3bead.workers.dev/mcp`

## الملخص بالعربية

تمت الموافقة على Teach Me | علّمني من OpenAI ونشرها في دليل بلاجين ChatGPT، والنسخة المعروضة هي **1.0.0**.

[رابط التثبيت في ChatGPT](https://chatgpt.com/plugins/plugin_asdk_app_6ab81f50a2b881918abe2865d47fb2a3)

تم التحقق من ظهور الصفحة العامة وزر التثبيت في **11 أكتوبر 2026**؛ هذا تاريخ التحقق وليس تاريخ الموافقة الأصلية. التثبيت يتطلب تسجيل الدخول، ولم يُختبر هنا من حساب متعلم مستقل.

تعليمات انتظار المراجعة القديمة أو إلغائها لم تعد تمثل الحالة الحالية. أي تحديث قادم يُختبر على البيتا أولًا، ووجود تغييرات على `main` لا يعني نشرها تلقائيًا أو أن نفس نسخة الكود تعمل في الإنتاج.
