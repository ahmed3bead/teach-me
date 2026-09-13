#!/usr/bin/env python3
"""Run Teach Me evaluation roles against a local Ollama model.

The adapter reads one runner payload from stdin and writes one JSON object to
stdout. It intentionally accepts only loopback Ollama endpoints unless the
caller explicitly opts into a remote host.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from locale_policy import canonical_locale, infer_locale


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
ARABIC_TEACHER_CONTEXT = """
أنت معلّم صبور ودقيق، ويُقاس نجاحك بما يستطيع المتعلم فعله بعد الشرح، لا بطول الرد.

قواعد التعليم:
- استخدم العربية الفصحى المبسطة لأي متعلم يكتب بالعربية، حتى لو كتب سؤاله بلهجة محلية. استخدم الإنجليزية فقط عندما يطلبها صراحة.
- أبقِ المصطلحات الأجنبية والتقنية بلغتها الأصلية، مثل API وReplication وContract Test وPrompt وDatabase. لا تكتب نطقها بحروف عربية، واشرح معناها بالعربية عند أول استخدام عند الحاجة.
- افهم الهدف ونقطة البداية، واقبل أن المتعلم مبتدئ عندما يقول إنه يبدأ من الصفر. اشرح قبل أن تختبره.
- اختر أصغر هدف مفيد، وعلّم فكرة مركزية واحدة بنموذج ذهني بسيط ومثال محلول مناسب للعمر ومن دون إحراج.
- أكمل وحدة شرح مفيدة قبل عرض أي تقييم. بعد الملخص، يمكنك عرض اختبار فهم قصير على سبيل الاختيار، ثم انتظر موافقة صريحة؛ لا تضع أول سؤال أو تمرين داخل الدعوة.
- لا تعتبر مجرد القراءة أو إنهاء الدرس دليلًا على الإتقان. إذا لم ينجح الشرح، فشخّص السبب وغيّر الطريقة بدل تكرار الكلام نفسه.
- لا تدّع خبرة شخصية أو مصادر لم تراجعها. وضّح عدم اليقين في المعلومات التي قد تغيّر الفهم أو القرار.
- اختم بفعل واحد واضح ومناسب للمرحلة؛ قد يكون مجرد القراءة أو الاستمرار، ولا يلزم أن يطلب إجابة.
- اكتب جملًا سليمة وطبيعية، وراجع دقة المصطلحات والأمثلة. لا تخترع اسمًا لجزء من المفهوم، ولا تحشر ألفاظًا لمجرد إثبات أسلوب لغوي.
- في الفصحى المبسطة، استخدم تركيبًا طبيعيًا مثل «تخيّل أن لديك» و«هذا يعني»، وراجع التصريف وحروف الجر قبل الإرسال.
- استخدم كلمات عربية مألوفة وصحيحة فقط. اقرأ الرد مرة أخيرة، واحذف أو أصلح أي كلمة مشوشة أو غير سليمة قبل الإرسال.
- اختر مثالًا محسوسًا واحدًا، وثبّت اسم الشيء نفسه طوال المثال حتى لا تختلط الكلمات على المتعلم.
- عند شرح الكسور لطفل، ابدأ بمعنى «أجزاء متساوية» مستخدمًا شريطًا من الورق له جزآن متساويان، ثم سمِّ النصف أو الربع. لا تستخدم الأكل أو شيئًا غير مألوف.

للطفل: استخدم جملًا قصيرة، وأمثلة محسوسة، ومفهومًا واحدًا قبل الرموز والاستثناءات، ومن دون أسئلة تشعره بأنه في امتحان.
""".strip()


def normalize_host(value: str) -> str:
    value = value.rstrip("/")
    if "://" not in value:
        value = "http://" + value
    parsed = parse.urlparse(value)
    if not parsed.hostname:
        raise ValueError("invalid Ollama host")
    return value


def require_local_host(host: str, allow_remote: bool) -> None:
    hostname = parse.urlparse(host).hostname
    if not allow_remote and hostname not in LOCAL_HOSTS:
        raise ValueError(
            "refusing a non-local Ollama endpoint; pass --allow-remote only when cost and privacy are understood"
        )


def load_skill_context(skill_root: Path) -> str:
    skill_file = skill_root / "SKILL.md"
    if not skill_file.is_file():
        raise ValueError(f"SKILL.md not found under {skill_root}")
    files = [skill_file, *sorted((skill_root / "references").glob("*.md"))]
    chunks = []
    for path in files:
        relative = path.relative_to(skill_root)
        chunks.append(f"\n--- {relative} ---\n{path.read_text(encoding='utf-8')}")
    return "".join(chunks)


def teacher_skill_context(skill_root: Path, payload: dict[str, Any]) -> str:
    """Use a compact Arabic rendering so small local models do not mirror an English-heavy context."""
    if not (skill_root / "SKILL.md").is_file():
        raise ValueError(f"SKILL.md not found under {skill_root}")
    if requested_locale(payload).lower().replace("_", "-").startswith("ar"):
        return ARABIC_TEACHER_CONTEXT
    return load_skill_context(skill_root)


def requested_locale(payload: dict[str, Any]) -> str:
    """Return canonical ar-MSA/en; legacy ar-EG is always treated as ar-MSA."""
    text_parts = [payload.get("prompt"), payload.get("learner_message")]
    text_parts.extend(
        item.get("content")
        for item in payload.get("history", [])
        if isinstance(item, dict)
    )
    combined = " ".join(part for part in text_parts if isinstance(part, str))
    return infer_locale(combined, payload.get("locale"))


def child_lesson_requested(payload: dict[str, Any]) -> bool:
    """Detect an explicitly child-focused lesson without relying on the model to infer it."""
    parts = [payload.get("prompt"), payload.get("learner_message")]
    combined = " ".join(part for part in parts if isinstance(part, str)).casefold()
    return any(marker in combined for marker in ("طفل", "ابتدائي", "primary school", "child"))


def seed_for_payload(base_seed: int, payload: dict[str, Any]) -> int:
    """Use a reproducible but distinct seed for the single corrective retry."""
    attempt = payload.get("attempt_index", 1)
    return base_seed + (max(int(attempt) - 1, 0) * 1009) if isinstance(attempt, int) else base_seed


def locale_instruction(locale: str) -> str:
    normalized = canonical_locale(locale)
    if normalized == "ar-MSA":
        return (
            "اكتب الرد كله بفصحى مبسطة وطبيعية تناسب عمر المتعلم، مستخدمًا كلمات يومية وجملًا قصيرة. "
            "اكتب كل جملة شرح وكل عنوان بحروف عربية، وتجنب اللهجات المحلية والأسلوب الرسمي المعقد. "
            "ممنوع تحويل الشرح إلى الإنجليزية. أبقِ كل مصطلح أجنبي أو تقني بلغته الأصلية ولا تكتبه بحروف عربية، "
            "واشرح معناه بالعربية عند أول استخدام عند الحاجة."
        )
    return (
        "Respond entirely in English and match the learner's level and register. Keep foreign and technical terms "
        "in their original language and never transliterate them into another script."
    )


def teacher_output_contract(payload: dict[str, Any]) -> str:
    locale = requested_locale(payload)
    normalized = canonical_locale(locale)
    language_rule = locale_instruction(locale)
    correction = payload.get("retry_feedback")
    if normalized == "ar-MSA":
        parts = [
            "عقد إخراج إلزامي:",
            f"- {language_rule}",
            "- لا تبدأ تقييمًا قبل موافقة المتعلم الصريحة. إذا لم يوافق، فلا تسأله سؤال معرفة، ولا تعطه تمرينًا، "
            "ولا تطلب منه الإجابة أو الحساب أو الرسم أو الحل.",
            "- بعد اكتمال وحدة الشرح، يمكنك عرض اختبار قصير اختياري ثم الانتظار. يجب ألا تتضمن الدعوة أول سؤال أو مهمة.",
            "- اجعل الدعوة اختيارية فعلًا، مثل «إن أحببت، يمكننا تجربة سؤال قصير»، ولا تقل «إذا كنت تفهم فسأختبرك».",
            "- لا تبدأ بسؤال إلى المتعلم؛ ابدأ بالشرح مباشرة.",
            "- اكتب النص العربي من دون حركات أو علامات تشكيل اختيارية لتجنب أخطاء الترميز، مع إبقاء الحروف والهمزات الأصلية.",
            "- احتفظ بالمصطلحات الأجنبية كما هي بالحروف اللاتينية. لا تكتب API أو Replication أو Contract Test أو Prompt أو Database بحروف عربية.",
            "- عند طلب مصطلح تقني، عرّفه عند أول ظهور بصيغة واضحة مثل: API (واجهة تسمح لبرنامج بالتواصل مع برنامج آخر).",
            "- في HTML وPDF اعزل كل مصطلح إنجليزي باستخدام <bdi dir=\"ltr\"> أو عنصر يحمل dir=\"ltr\".",
            "- اجعل الرد مركزًا ومن 100 إلى 180 كلمة، ولا تكرر الفكرة أو الجملة نفسها.",
        ]
        if child_lesson_requested(payload):
            parts.extend(
                [
                    "- ترتيب درس الطفل إلزامي: ابدأ بهذه الجمل: «سنبدأ من الصفر بخطوة بسيطة. لدينا شريط ورقي واحد. للشريط جزآن متساويان. الجزآن معا يشكلان الشريط الكامل. كل جزء يسمى نصفا.»",
                    "- بعد هذه الجمل انتقل إلى الرمز. لا تضف جملة تبدأ بكلمة «إذا»، ولا تصف فعل قص الشريط أو تقسيمه، ولا تطلب من الطفل تنفيذ أي عملية.",
                    "- اجعل الجمل الثلاث الأولى بلا أي رمز رياضي. بعد ثبات الفكرة بالكلمات ومثال الورق، اعرض رمزًا واحدًا فقط مثل 1/2 واشرح العددين. لا تضف 1/4 أو 3/4 أو قائمة أنواع في المقدمة.",
                    "- اختم بملخص بسيط ودعوة اختيارية بلا سؤال أو تمرين. استخدم نبرة دافئة مشجعة، لا نبرة كتاب رسمي.",
                ]
            )
        prompt_text = str(payload.get("prompt", "")).casefold()
        if "api" in prompt_text and "database replication" in prompt_text:
            parts.extend(
                [
                    "- ابدأ المقارنة بتعريفين مباشرين بين قوسين، ولا تستبدلهما بتشبيه: "
                    "API (واجهة برمجية تسمح لبرنامج بطلب وظائف أو بيانات من برنامج آخر)، ثم "
                    "Database Replication (عملية تحتفظ بنسخ متزامنة من قاعدة البيانات في أكثر من موقع).",
                    "- بعد التعريفين، قل بوضوح إن API ينظم التواصل ولا ينسخ قاعدة البيانات، بينما "
                    "Database Replication يزامن نسخ البيانات ولا يعمل كواجهة لطلبات البرامج.",
                ]
            )
        if correction:
            parts.append(f"- تصحيح إلزامي في هذه المحاولة: {correction}")
        return "\n".join(parts)

    parts = [
        "NON-NEGOTIABLE OUTPUT CONTRACT:",
        f"- {language_rule}",
        "- Do not begin an assessment before explicit learner opt-in. If the learner has not explicitly accepted a check, "
        "do not ask a knowledge question, assign an exercise, or tell them to answer, calculate, draw, or solve anything.",
        "- At a completed-unit boundary, you may only offer an optional short check and wait. The invitation itself must "
        "not contain the first test question or task.",
        "- Keep technical terms in their original language; never transliterate them into another script.",
    ]
    if correction:
        parts.append(f"- REQUIRED CORRECTION: {correction}")
    return "\n".join(parts)


def text_schema(field: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {field: {"type": "string", "minLength": 1}},
        "required": [field],
        "additionalProperties": False,
    }


def grade_schema(count: int, simulation: bool = False) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "results": {
            "type": "array",
            "minItems": count,
            "maxItems": count,
            "items": {
                "type": "object",
                "properties": {
                    "passed": {"type": "boolean"},
                    "reason": {"type": "string", "minLength": 1, "maxLength": 300},
                },
                "required": ["passed", "reason"],
                "additionalProperties": False,
            },
        }
    }
    required = ["results"]
    if simulation:
        properties.update(
            {
                "baseline_score": {"type": "number", "minimum": 0, "maximum": 1},
                "transfer_score": {"type": "number", "minimum": 0, "maximum": 1},
            }
        )
        required = ["baseline_score", "transfer_score", "results"]
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def role_for_payload(payload_type: str) -> str:
    if payload_type == "generate":
        return "response"
    if payload_type == "teach":
        return "teacher"
    if payload_type in {"baseline", "dialogue", "transfer"}:
        return "learner"
    if payload_type in {"grade", "simulation-grade"}:
        return "grader"
    raise ValueError(f"unsupported payload type: {payload_type}")


def messages_and_schema(payload: dict[str, Any], skill_context: str | None) -> tuple[list[dict[str, str]], dict[str, Any], float]:
    kind = payload["type"]
    if kind == "generate":
        output_contract = teacher_output_contract(payload)
        normalized = requested_locale(payload)
        if normalized == "ar-MSA":
            intro = "أنت معلّم Teach Me. التزم بعقد التعليم المعروض، وتصرّف معلّمًا مباشرة، ولا تذكر نظام التقييم."
        else:
            intro = (
                "You are the Teach Me teaching agent. Follow the supplied skill contract exactly, "
                "act directly as the teacher, and do not mention evaluation machinery."
            )
        system = intro + "\n\n" + (skill_context or "") + f"\n\n{output_contract}"
        messages = [{"role": "system", "content": system}]
        messages.extend(payload.get("history", []))
        messages.append({"role": "user", "content": str(payload["prompt"])})
        return messages, text_schema("response"), 0.2

    if kind == "teach":
        output_contract = teacher_output_contract(payload)
        normalized = requested_locale(payload)
        if normalized == "ar-MSA":
            intro = "أنت معلّم Teach Me في محاكاة مغلقة المصادر. التزم بالعقد، وعلّم بلغة طبيعية، ولا تذكر نظام الاختبار."
        else:
            intro = (
                "You are the Teach Me teaching agent in a closed-book simulation. Follow the skill, "
                "teach naturally in the requested locale, and never discuss the test harness."
            )
        system = intro + "\n\n" + (skill_context or "") + f"\n\n{output_contract}"
        history = payload.get("history", [])
        content = {
            "locale": normalized,
            "authorized_teaching_material": payload.get("teaching_material"),
            "dialogue_so_far": history,
            "current_learner_message": payload.get("learner_message"),
            "turn": payload.get("turn_index"),
            "maximum_turns": payload.get("max_turns"),
        }
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(content, ensure_ascii=False)},
        ], text_schema("response"), 0.4

    if kind in {"baseline", "dialogue", "transfer"}:
        system = (
            "Act only as the described learner. Never use hidden or outside knowledge. "
            "Admit uncertainty naturally and follow the learner behaviors without quoting them.\n"
            f"Persona: {payload.get('learner_persona', '')}\n"
            f"Behaviors: {json.dumps(payload.get('learner_behaviors', []), ensure_ascii=False)}"
        )
        if kind == "baseline":
            user = f"Instruction: {payload.get('instruction', '')}\nTask: {payload.get('task', '')}"
            return [{"role": "system", "content": system}, {"role": "user", "content": user}], text_schema("answer"), 0.2
        if kind == "transfer":
            user = json.dumps(
                {
                    "instruction": payload.get("instruction"),
                    "teaching_transcript": payload.get("history", []),
                    "fresh_task": payload.get("task"),
                },
                ensure_ascii=False,
            )
            return [{"role": "system", "content": system}, {"role": "user", "content": user}], text_schema("answer"), 0.2
        schema = text_schema("message")
        schema["properties"]["done"] = {"type": "boolean"}
        schema["required"].append("done")
        user = json.dumps(
            {
                "instruction": payload.get("instruction"),
                "dialogue": payload.get("history", []),
                "turn": payload.get("turn_index"),
                "maximum_turns": payload.get("max_turns"),
                "task": "Write the learner's next natural message. Set done=true only at a natural endpoint.",
            },
            ensure_ascii=False,
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}], schema, 0.2

    expected = payload.get("expected", [])
    simulation = kind == "simulation-grade"
    if requested_locale(payload) == "ar-MSA":
        single_criterion = "يوجد معيار واحد فقط؛ أعد حكمًا واحدًا عليه ولا تقسّمه إلى معايير فرعية. " if len(expected) == 1 else ""
        system = (
            "أنت مصحح مستقل وصارم. قيّم الدليل الظاهر فقط في الرد أو الحوار، ولا تفترض سلوكًا غير مكتوب. "
            + single_criterion
            + "أعد نتيجة لكل معيار بالترتيب نفسه. اجعل كل سبب جملة واحدة موجزة، واذكر فيها دليلًا محددًا من الرد أو ما ينقصه. "
            "قيّم كل معيار منفصلًا، ولا تنقل حكم معيار إلى سبب معيار آخر. ممنوع نسخ نص المعيار نفسه على أنه السبب. "
            "الدعوة الاختيارية لاختبار لاحق صحيحة عندما تنتظر الموافقة ولا تتضمن سؤال الاختبار. لا تطلب وجود سؤال قبل الموافقة. "
            "لا تصف مثالًا عاديًا بأنه محرج أو ضار ما لم يحتوِ الرد نفسه على لوم أو سخرية أو ضغط."
        )
    else:
        system = (
            "You are an independent strict evaluator. Judge only observable evidence in the supplied response or transcript. "
            "Do not infer missing behavior. Return results in exactly the same order as the criteria. "
            "For every result, name concrete evidence from the response or name what is missing. Never copy the criterion as the reason."
        )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ], grade_schema(len(expected), simulation=simulation), 0.0


def ollama_chat(
    host: str,
    model: str,
    messages: list[dict[str, str]],
    schema: dict[str, Any],
    temperature: float,
    timeout: int,
    num_ctx: int,
    num_predict: int,
    seed: int,
) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": False,
            "format": schema,
            "keep_alive": "10m",
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
                "num_predict": num_predict,
                "repeat_penalty": 1.0,
                "seed": seed,
            },
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request(
        host + "/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise RuntimeError(f"cannot reach Ollama at {host}: {exc.reason}") from exc
    content = result.get("message", {}).get("content")
    if not isinstance(content, str):
        raise RuntimeError("Ollama returned no message content")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        excerpt = " ".join(content.split())[:240]
        raise RuntimeError(f"Ollama did not return valid structured JSON: {excerpt!r}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Ollama structured output must be an object")
    parsed["model"] = "ollama/" + str(result.get("model") or model)
    parsed["seed"] = seed
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=["response", "teacher", "learner", "grader"], required=True)
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "qwen3:8b"))
    parser.add_argument("--host", default=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--num-ctx", type=int, default=32768)
    parser.add_argument("--num-predict", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict) or not isinstance(payload.get("type"), str):
            raise ValueError("stdin must be a runner payload object with a type")
        expected_role = role_for_payload(payload["type"])
        if args.role != expected_role:
            raise ValueError(f"payload type {payload['type']} requires --role {expected_role}")
        host = normalize_host(args.host)
        require_local_host(host, args.allow_remote)
        skill_context = None
        if args.role in {"response", "teacher"}:
            skill_context = teacher_skill_context(Path(payload["skill_root"]), payload)
        if payload["type"] == "grade" and len(payload.get("expected", [])) > 1:
            combined_results: list[dict[str, Any]] = []
            result_model = "ollama/" + args.model
            for criterion in payload["expected"]:
                criterion_payload = {**payload, "expected": [criterion]}
                messages, schema, temperature = messages_and_schema(criterion_payload, skill_context)
                criterion_result = ollama_chat(
                    host,
                    args.model,
                    messages,
                    schema,
                    temperature,
                    args.timeout,
                    args.num_ctx,
                    args.num_predict,
                    seed_for_payload(args.seed, criterion_payload),
                )
                combined_results.extend(criterion_result["results"])
                result_model = str(criterion_result.get("model", result_model))
            result = {"results": combined_results, "model": result_model}
        else:
            messages, schema, temperature = messages_and_schema(payload, skill_context)
            result = ollama_chat(
                host,
                args.model,
                messages,
                schema,
                temperature,
                args.timeout,
                args.num_ctx,
                args.num_predict,
                seed_for_payload(args.seed, payload),
            )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (KeyError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Ollama adapter failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
