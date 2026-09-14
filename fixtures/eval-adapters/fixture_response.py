#!/usr/bin/env python3
"""Deterministic response adapter used only to test runner plumbing."""

import json
import sys


payload = json.load(sys.stdin)
prompt = payload["prompt"]
if "MALFORMED_PROTOCOL_THEN_OK" in prompt and not payload.get("protocol_retry"):
    sys.stdout.write("not-json")
    raise SystemExit(0)
if "TRANSPORT_THEN_OK" in prompt and not payload.get("protocol_retry"):
    raise SystemExit(3)
if "FORCE_FAIL" in prompt:
    response = "fixture-fail"
elif "ALWAYS_ENGLISH" in prompt:
    response = "This is a complete English explanation that the permissive fixture grader will incorrectly approve."
elif "ALWAYS_INCOMPLETE" in prompt:
    response = "هذا شرح عربي مبسط لكنه ينتهي في منتصف"
elif "ALWAYS_MALFORMED" in prompt:
    response = "هذا شرح عربي مكتمل ومبسّط، لكنه يقول إذا قسّّيت الشريط إلى جزأين متساويين، فتظهر فيه كلمة مشوشة يجب رفضها."
elif "PREMATURE_ASSESSMENT" in prompt:
    response = "هذا شرح عربي مبسط وواضح للكسور حتى يفهم الطفل الفكرة. ارسم دائرة ولوّن نصفها ثم أخبرني ما الكسر."
elif "UNDERSTANDING_CHECK" in prompt:
    response = "هذا شرح عربي مبسط وواضح للكسور حتى يفهم الطفل الفكرة من دون ضغط. هل فهمت؟"
elif "ALWAYS_MSA" in prompt:
    response = "سأشرح لك مفهوم الكسور بطريقة عربية واضحة. لنبدأ بفكرة أن الكسر جزء من كل مقسوم بالتساوي."
elif "ALWAYS_EGYPTIAN" in prompt:
    response = "ده شرح عربي بسيط بالمصري عشان نفهم الفكرة اللي عندنا، وهنكملها خطوة خطوة من غير ضغط."
elif "FOREIGN_SCRIPT" in prompt:
    response = "هذا شرح عربي مبسط حتى نفهم الجزء الموجود، وسنكمل الفكرة ببساطة من دون ضغط 你."
elif "OPTIONAL_INVITATION" in prompt:
    response = "هذا شرح عربي مبسط وواضح للكسور حتى يفهم الطفل الفكرة من دون ضغط. هل ترغب في سؤال قصير؟"
elif "TECHNICAL_COMPARISON_OK" in prompt:
    response = "API يعني واجهة تسمح للبرامج بالتواصل ولا تنشئ نسخًا من البيانات. أما Database Replication فهي آلية تحافظ على نسخ متزامنة من قاعدة البيانات لرفع التوفر. الأول ينظم التواصل بين البرامج، والثاني ينسخ حالة البيانات بين مواقع متعددة."
elif "CONCEPT_ORDER_OK" in prompt:
    response = "سنبدأ من الصفر بخطوة بسيطة. هذا شريط ورقي واحد، وقد قسمناه إلى قسمين متساويين. كل قسم جزء من الشريط الكامل. لأن القسمين متساويان، نسمي كل قسم نصفًا. بعد أن عرفنا معنى الأجزاء المتساوية، يمكننا كتابة النصف بالرمز 1/2. الرقم الأول يصف الجزء، والرقم الثاني يصف عدد الأقسام كلها."
elif "CONCEPT_ORDER_WRONG" in prompt:
    response = "سنبدأ من الصفر بخطوة بسيطة. الرمز 1/2 يعني النصف، والرمز 1/4 يعني الربع. هذه رموز مهمة ينبغي أن نحفظها أولًا. بعد ذلك يمكن أن نرى شريطًا من الورق مقسّمًا إلى قسمين متساويين، ثم نعود إلى الرموز السابقة ونقارن بينها في هذا الدرس القصير والواضح للطفل."
elif "TECHNICAL_TERMS_OK" in prompt:
    response = "API يعني واجهة للتواصل بين البرامج، وReplication يعني الاحتفاظ بنسخ متزامنة، وContract Test يعني اختبار اتفاق التكامل، وPrompt يعني التعليمات المقدمة للنموذج، وDatabase يعني مخزنًا منظمًا للبيانات."
elif "TECHNICAL_TERMS_TRANSLITERATED" in prompt:
    response = "هذه مصطلحات تقنية مثل إيه بي آي وريبليكيشن وكونتراكت تيست وبرومبت وداتابيز، وقد كُتبت خطأ بحروف عربية."
elif str(payload.get("locale", "")).lower().replace("_", "-") == "en":
    response = "This is a clear English teaching response that matches the learner's requested language and level."
elif str(payload.get("locale", "")).lower().replace("_", "-").startswith("ar"):
    response = "هذا شرح عربي مبسط وواضح للكسور حتى يفهم الطفل الفكرة. سنكمل خطوة خطوة من دون ضغط."
else:
    response = "fixture-pass"
json.dump({
    "response": response, "artifacts": [], "model": "fixture/response-v2",
    "settings": {"deterministic": True, "agent_sandbox": "fixture"},
    "adapter_version": "fixture-2.0.0", "invocation_id": "fixture-response-invocation",
    "timing": {"started_at": "2026-09-14T00:00:00Z", "completed_at": "2026-09-14T00:00:00Z", "duration_seconds": 0.0},
    "raw_result": {"response": response, "artifacts": []}, "artifact_evidence": []
}, sys.stdout)
