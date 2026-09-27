# Current release status | حالة الإصدار الحالية

Last updated: 2026-09-27

## Important distinction

The `main` branch contains the newest Teach Me work, including the next plugin version with learner, educator, age-aware, and source-grounded workflows plus selective guidance loading for lower token usage.

The ChatGPT plugin currently under OpenAI review is an earlier submitted version. Merging code into `main` does **not** update that submission, redeploy the production MCP server, or make the new capabilities live in the Plugins Directory.

## Release decision

Decision recorded on 2026-09-27: prepare the complete next version, then cancel the current OpenAI review and resubmit the complete version before producing the public promotional video. Do not cancel the current review until the beta acceptance tests, submission metadata, and reviewer test cases are ready, so cancellation and resubmission can happen in one controlled session.

## Release guard

Until the full-version resubmission kit is ready:

1. Do not redeploy the production MCP endpoint from `main`.
2. Do not cancel or replace the plugin version currently under review prematurely.
3. Treat changes merged into `main` as the source for the **next** plugin update.
4. Use the beta MCP deployment for manual testing of the next version.

Current endpoints:

- Production submission: `https://teach-me-mcp.ahmedm3bead.workers.dev/mcp`
- Next-version beta: `https://teach-me-mcp-next.ahmedm3bead.workers.dev/mcp`

When the kit is ready, use this order: cancel the current review, deploy the tested beta build to the unchanged production origin, run **Scan Tools**, verify the imported metadata, update the reviewer cases, and submit the complete version. Update this status file in the same pull request as any production release change.

## الملخص بالعربية

فرع `main` يحتوي أحدث شغل وخصائص النسخة القادمة، لكن البلاجين الموجودة حاليًا عند OpenAI للمراجعة هي النسخة السابقة التي تم تقديمها بالفعل.

وجود الكود الجديد على `main` لا يغيّر النسخة قيد المراجعة ولا ينشر MCP جديدًا تلقائيًا. حتى تنتهي المراجعة الحالية، لا نعيد نشر رابط الإنتاج ولا نعيد تقديم البلاجين. نختبر النسخة القادمة على رابط البيتا، ثم ننشرها كتحديث مستقل بعد اتخاذ قرار واضح.

القرار الحالي هو تجهيز النسخة الكاملة أولًا، ثم إلغاء المراجعة القديمة وإعادة التقديم بالنسخة الكاملة قبل تصوير فيديو الدعاية. لا نلغي الطلب قبل اكتمال الاختبارات وبيانات التقديم حتى تتم عملية الإلغاء والنشر وإعادة التقديم في جلسة واحدة.
