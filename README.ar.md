# Teach Me

**معلّم متكيّف يبدأ من هدفك، ويشرح خطوة بخطوة، ويغيّر طريقة الشرح عندما تواجه صعوبة.**

[English](README.md) · [العربية](README.ar.md)

[![CI](https://github.com/ahmed3bead/teach-me/actions/workflows/validate.yml/badge.svg)](https://github.com/ahmed3bead/teach-me/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/ahmed3bead/teach-me?include_prereleases&label=release)](https://github.com/ahmed3bead/teach-me/releases/tag/v1.0.0-beta.2)
[![License: MIT](https://img.shields.io/github/license/ahmed3bead/teach-me)](LICENSE)

> **نسخة تجريبية:** الإصدار العام الحالي هو `v1.0.0-beta.2`. يمكن تجربته الآن، لكن إصدار `v1.0.0` المستقر ما زال يحتاج إلى الاختبار المصحح المكوّن من 90 حالة والمراجعة البشرية.

## لماذا Teach Me؟

- يبدأ من هدف المتعلم وما يعرفه بالفعل.
- يقسّم الموضوعات الصعبة إلى خطوات مناسبة.
- يغيّر طريقة الشرح بدل تكرار الكلام نفسه عند استمرار الالتباس.
- يدعم الإنجليزية والعربية الفصحى المبسطة.
- يستطيع التعليم من الملفات المصرّح باستخدامها، ويميّز بين المصدر والشرح المضاف.
- لا يدّعي إتقان المتعلم دون دليل، ولا يبدأ اختبارًا اعتياديًا دون موافقته.

## اختر النسخة المناسبة

| النسخة | الأنسب لها | الإعداد |
|---|---|---|
| **إضافة ChatGPT** | أسهل مسار للمستخدم العادي من المتصفح أو الهاتف أو الجهاز اللوحي | التثبيت من ChatGPT بعد قبولها في المتجر؛ [حالة الإضافة](plugins/teach-me/README.md) |
| **GPT مخصص** | اختبار خاص بواسطة المالك قبل إتاحة الإضافة العامة | [إعداد المالك](chatgpt-edition/README.md) |
| **Claude** | التعلم داخل محادثة Claude عادية | [إعداد Claude](claude-edition/README.md) |
| **Codex** | التعلم المنظم مع الملفات المحلية والتقارير والتحقق | [إعداد Codex](docs/codex-installation.md) |
| **Claude Code** | تشغيل المسار الكامل داخل Claude Code | [إعداد Claude Code](claude-edition/README.md#claude-code-marketplace-setup) |

إذا كنت غير متأكد، ابدأ بإضافة ChatGPT أو Claude. استخدم Codex أو Claude Code فقط عندما تحتاج إلى ملفات محلية أو خطوات قابلة للتكرار أو مخرجات تقنية.

## بداية سريعة

أعطِ Teach Me هدفًا عمليًا واحدًا:

```text
علّمني Docker من الصفر. أنا مطور Laravel وأريد تشغيل مشروع Laravel حقيقي محليًا باستخدام Docker.
```

حزمة إضافة ChatGPT العامة جاهزة للمراجعة في المتجر. تعتمد على تعليمات مرفقة فقط، ولذلك لا يحتاج المتعلم إلى حساب إضافي أو مفتاح API أو خادم أو أوامر Terminal. وجود الحزمة في المستودع لا يعني أنها قُبلت أو أُدرجت في المتجر بعد.

على Claude Code:

```text
/plugin marketplace add ahmed3bead/teach-me
/plugin install teach-me@teach-me
/teach-me:teach-me
```

على Codex في Linux أو macOS:

```bash
sh installers/install.sh install --version 1.0.0-beta.2
```

على Windows PowerShell:

```powershell
.\installers\install.ps1 -Action install -Version "1.0.0-beta.2"
```

راجع [دليل البداية](docs/getting-started.md) لمعرفة خطوات أول جلسة وطريقة التحديث.

## كيف يعلّمك؟

يتبع Teach Me دورة بسيطة:

1. يفهم الهدف ونقطة البداية.
2. يختار أصغر خطوة مفيدة تالية.
3. يشرح باستخدام مثال مناسب.
4. يغيّر الاستراتيجية عندما يواجه المتعلم صعوبة.
5. يعرض اختبارًا قصيرًا بعد اكتمال وحدة مفيدة وبعد موافقة المتعلم.

راجع [كيف يعمل Teach Me](docs/how-it-works.md) لمعرفة مسارات المتعلم والمعلّم والتعليم المعتمد على المصادر.

## الأدلة

| الدليل | المحتوى |
|---|---|
| [البداية](docs/getting-started.md) | اختيار النسخة والإعداد والتحديث وأول جلسة |
| [طريقة العمل](docs/how-it-works.md) | أسلوب التعليم ومسارات الاستخدام |
| [أمثلة جاهزة](docs/examples.md) | طلبات جاهزة بالعربية والإنجليزية |
| [القيود الحالية](docs/limitations.md) | حدود النسخة التجريبية واختلاف المنصات |
| [التطوير](docs/development.md) | اختبارات المشروع وأوامر المساهمة |
| [التوافق](docs/compatibility.md) | مقارنة تفصيلية لإمكانات المنصات |
| [تقديم إضافة ChatGPT](docs/chatgpt-plugin-submission.md) | حدود المراجعة العامة وخطوات حساب الناشر |
| [تقييم النماذج](docs/model-evaluation.md) | بروتوكول الاختبارات السلوكية والمحاكاة |
| [قائمة الإصدار](docs/release-checklist.md) | شروط الانتقال إلى الإصدار المستقر |

أدلة كل منصة:

- [نسخة ChatGPT](chatgpt-edition/README.md)
- [Claude وClaude Code](claude-edition/README.md)
- [تثبيت Codex](docs/codex-installation.md)

## الحالة والقيود

لا يضمن Teach Me دقة كاملة أو إتقانًا أو احتفاظًا بالمعلومة أو نتيجة تعليمية محددة. كما تختلف النماذج والأدوات والملفات المتاحة بين المنصات. الادعاءات المهمة أو المتغيرة أو عالية الخطورة تحتاج إلى مصادر موثوقة مناسبة.

راجع [القيود](docs/limitations.md) و[ملاحظات الإصدار](RELEASE_NOTES.md) قبل الاستخدام الإنتاجي أو عالي الخطورة.

## المساهمة

المساهمات مرحب بها. ابدأ من [CONTRIBUTING.md](CONTRIBUTING.md)، ولا تضف بيانات شخصية أو مفاتيح وصول أو محادثات خاصة أو مناهج محمية أو تقارير مولدة أو مخرجات نماذج.

## الأمان

أبلغ عن الثغرات من خلال [GitHub Private Vulnerability Reporting](https://github.com/ahmed3bead/teach-me/security/advisories/new). راجع [SECURITY.md](SECURITY.md).

## الترخيص

المشروع متاح تحت [رخصة MIT](LICENSE).
