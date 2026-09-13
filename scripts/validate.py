#!/usr/bin/env python3
"""Dependency-free structural checks for the Teach Me skill repository."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from validate_resume import validate as validate_resume_code


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ORIGINS = {"curriculum", "educator", "inferred", "external", "adaptation"}


def fail(message: str) -> None:
    raise AssertionError(message)


def check_json() -> None:
    for path in sorted((ROOT / "schemas").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            fail(f"{path}: unexpected or missing JSON Schema dialect")
        if not data.get("$id"):
            fail(f"{path}: missing stable $id")
        if data.get("properties", {}).get("version", {}).get("const") != "1.0.0":
            fail(f"{path}: schema version must be pinned to 1.0.0")
        if data.get("type") != "object" or not data.get("required"):
            fail(f"{path}: expected an object schema with required fields")


def check_skill() -> None:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail("SKILL.md: missing YAML frontmatter")
    for required in ("name: teach-me", "Learner Mode", "Educator Mode", "Source-Grounded", "references/educator-mode.md", "references/source-grounded-mode.md", "references/integration-core.md", "references/research-sweep.md", "references/curriculum-delivery.md", "references/guided-learning-pack.md", "references/diagnostic-engine.md", "references/teaching-engine.md", "references/assessment-feedback-engine.md", "references/conversational-teaching.md", "references/arabic-teaching-style.md", "references/bidirectional-output.md", "references/retention-adaptation.md", "references/accessibility-engagement.md", "references/learning-pack-structure.md", "references/integration-foundation.md", "references/multimodal-video.md"):
        if required not in text:
            fail(f"SKILL.md: missing {required!r}")
    for match in re.findall(r"\]\(([^)]+)\)", text):
        if "://" not in match and not (ROOT / match).exists():
            fail(f"SKILL.md: broken local reference {match}")


def check_evals() -> None:
    # Avoid a runtime YAML dependency: these invariants cover the committed format.
    for path in sorted((ROOT / "evals").glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        ids = re.findall(r"^  - id: (\S+)$", text, flags=re.MULTILINE)
        if not ids or len(ids) != len(set(ids)):
            fail(f"{path}: missing or duplicate case IDs")
        if "    expected:\n" not in text:
            fail(f"{path}: cases need observable expectations")


def check_templates() -> None:
    curriculum = (ROOT / "templates" / "curriculum-map.md").read_text(encoding="utf-8")
    lesson = (ROOT / "templates" / "lesson-plan.md").read_text(encoding="utf-8")
    for word in ("Origin", "Source references", "Approval"):
        if word not in curriculum:
            fail(f"curriculum-map.md: missing {word}")
    for word in ("Demonstrable outcomes", "Assessment", "Traceability"):
        if word not in lesson:
            fail(f"lesson-plan.md: missing {word}")
    if not ALLOWED_ORIGINS.issubset(set(lesson.replace("/", " ").split())):
        fail("lesson-plan.md: origin labels are incomplete")
    coverage = (ROOT / "templates" / "source-coverage.md").read_text(encoding="utf-8")
    for word in ("Session ID", "Source ID", "Actually inspected", "Understanding gate", "Safe teaching scope"):
        if word not in coverage:
            fail(f"source-coverage.md: missing {word}")
    session = (ROOT / "templates" / "learning-session.md").read_text(encoding="utf-8")
    for word in ("Session ID", "Active objective", "Mastery evidence", "Resume checkpoint"):
        if word not in session:
            fail(f"learning-session.md: missing {word}")
    knowledge = (ROOT / "templates" / "knowledge-base.md").read_text(encoding="utf-8")
    for word in ("Source matrix", "Actually inspected", "Topic map", "Teaching readiness"):
        if word not in knowledge:
            fail(f"knowledge-base.md: missing {word}")
    curriculum = (ROOT / "templates" / "study-curriculum.md").read_text(encoding="utf-8")
    for word in ("Curriculum ID", "Learning path", "Demonstrable outcome", "Source references", "Progress and resume checkpoint"):
        if word not in curriculum:
            fail(f"study-curriculum.md: missing {word}")
    start_here = (ROOT / "templates" / "start-here.md").read_text(encoding="utf-8")
    for word in ("لوحة رحلتك", "ماذا ستستفيد", "كيف تدرس كل درس", "كيف أتوقف وأكمل لاحقًا", "ابدأ الآن"):
        if word not in start_here:
            fail(f"start-here.md: missing {word}")
    misconception = (ROOT / "templates" / "misconception-map.md").read_text(encoding="utf-8")
    for word in ("Tempting wrong model", "Diagnostic prompt", "Counterexample", "Verification task"):
        if word not in misconception:
            fail(f"misconception-map.md: missing {word}")
    progress = (ROOT / "templates" / "progress.md").read_text(encoding="utf-8")
    for word in ("Session ID", "Record ID", "Objective ID", "Observable evidence", "not mastery evidence"):
        if word not in progress:
            fail(f"progress.md: missing {word}")
    bidi = (ROOT / "templates" / "bidi-learning-pack.html").read_text(encoding="utf-8")
    for word in ('lang="ar"', 'dir="rtl"', 'unicode-bidi: isolate', 'dir="ltr"', '<main>'):
        if word not in bidi:
            fail(f"bidi-learning-pack.html: missing {word}")


def check_integration() -> None:
    session = json.loads((ROOT / "schemas" / "learning-session.schema.json").read_text(encoding="utf-8"))
    claim = json.loads((ROOT / "schemas" / "claim-ledger.schema.json").read_text(encoding="utf-8"))
    for field in ("session_id", "audience", "input_mode", "objectives", "checkpoint"):
        if field not in session["required"]:
            fail(f"learning-session.schema.json: {field} must be required")
    objective = session["properties"]["objectives"]["items"]
    for field in ("objective_id", "mastery_evidence", "state", "next_action"):
        if field not in objective["required"]:
            fail(f"learning-session.schema.json: objective {field} must be required")
    if "session_id" not in claim["required"] or "claims" not in claim["required"]:
        fail("claim-ledger.schema.json: missing connected required fields")
    integration_eval = (ROOT / "evals" / "integration-cases.yaml").read_text(encoding="utf-8")
    for invariant in ("reading or lesson completion is not recorded as mastery", "educator and source-grounded handling are combined", "dependent objectives and lessons are identified"):
        if invariant not in integration_eval:
            fail(f"integration-cases.yaml: missing invariant {invariant!r}")
    validator = ROOT / "scripts" / "validate_session.py"
    if not validator.exists():
        fail("missing session referential-integrity validator")


def check_research_sweep() -> None:
    schema = json.loads((ROOT / "schemas" / "knowledge-base.schema.json").read_text(encoding="utf-8"))
    for field in ("session_id", "subject", "researched_at", "sources", "topic_map", "teaching_readiness"):
        if field not in schema["required"]:
            fail(f"knowledge-base.schema.json: {field} must be required")
    source = schema["properties"]["sources"]["items"]
    for field in ("source_id", "source_family", "access", "inspected", "role", "limitations"):
        if field not in source["required"]:
            fail(f"knowledge-base.schema.json: source {field} must be required")
    cases = (ROOT / "evals" / "research-sweep-cases.yaml").read_text(encoding="utf-8")
    for invariant in ("access controls are not bypassed", "popularity is not treated as an accuracy signal", "prior knowledge is not presented as a completed sweep"):
        if invariant not in cases:
            fail(f"research-sweep-cases.yaml: missing invariant {invariant!r}")


def check_curriculum_delivery() -> None:
    schema = json.loads((ROOT / "schemas" / "study-curriculum.schema.json").read_text(encoding="utf-8"))
    for field in ("curriculum_id", "session_id", "subject", "language", "target_capability", "scope", "modules", "completion_criteria"):
        if field not in schema["required"]:
            fail(f"study-curriculum.schema.json: {field} must be required")
    module = schema["properties"]["modules"]["items"]
    for field in ("module_id", "title", "outcome", "lessons"):
        if field not in module["required"]:
            fail(f"study-curriculum.schema.json: module {field} must be required")
    lesson = module["properties"]["lessons"]["items"]
    for field in ("lesson_id", "objective_ids", "demonstrable_outcome", "activity", "assessment", "source_refs"):
        if field not in lesson["required"]:
            fail(f"study-curriculum.schema.json: lesson {field} must be required")
    cases = (ROOT / "evals" / "curriculum-delivery-cases.yaml").read_text(encoding="utf-8")
    for invariant in ("an editable Markdown curriculum is the default artifact", "the rendered pages are inspected before delivery", "structured Markdown is provided in chat as a disclosed fallback"):
        if invariant not in cases:
            fail(f"curriculum-delivery-cases.yaml: missing invariant {invariant!r}")


def check_guided_learning_pack() -> None:
    cases = (ROOT / "evals" / "guided-learning-pack-cases.yaml").read_text(encoding="utf-8")
    for invariant in ("the learner is not asked to design the course", "empty module scaffolding is not created", "a valid non-sensitive TEACH-ME v2 resume code with a session identifier is included", "one exact action and expected time", "a requested reply appears only when the action genuinely requires learner input", "START-HERE begins with explanation rather than a subject-matter test"):
        if invariant not in cases:
            fail(f"guided-learning-pack-cases.yaml: missing invariant {invariant!r}")


def check_teaching_engine() -> None:
    cases = (ROOT / "evals" / "golden-teaching-cases.yaml").read_text(encoding="utf-8")
    for invariant in ("worked example, guided attempt, and independent evidence", "materially different representation or prerequisite intervention", "retention requires successful retrieval after a meaningful delay"):
        if invariant not in cases:
            fail(f"golden-teaching-cases.yaml: missing invariant {invariant!r}")


def check_retention_accessibility() -> None:
    cases = (ROOT / "evals" / "retention-accessibility-cases.yaml").read_text(encoding="utf-8")
    for invariant in ("retrieval is attempted before restudy", "one smaller purposeful action is offered without guilt or pressure", "internal ledgers are not presented as learner tasks", "corrected rather than treated as a fixed learning style"):
        if invariant not in cases:
            fail(f"retention-accessibility-cases.yaml: missing invariant {invariant!r}")


def check_integration_foundation() -> None:
    cases = (ROOT / "evals" / "integration-foundation-cases.yaml").read_text(encoding="utf-8")
    for invariant in ("inspection is labeled transcript rather than fully watched", "the catalog license is not assumed to cover every linked skill", "the simplicity ladder avoids generating a full learning pack", "source count alone is not treated as research readiness"):
        if invariant not in cases:
            fail(f"integration-foundation-cases.yaml: missing invariant {invariant!r}")
    if not (ROOT / "ACKNOWLEDGEMENTS.md").exists():
        fail("missing ecosystem acknowledgements")


def check_hardening() -> None:
    profile = json.loads((ROOT / "schemas" / "learner-profile.schema.json").read_text(encoding="utf-8"))
    if "data_governance" not in profile["required"]:
        fail("learner-profile.schema.json: data_governance must be required")
    governance = profile["properties"]["data_governance"]
    for field in ("purpose", "consent_recorded_at", "retention_until", "deletion_status"):
        if field not in governance["required"]:
            fail(f"learner-profile.schema.json: data_governance {field} must be required")
    cases = (ROOT / "evals" / "hardening-cases.yaml").read_text(encoding="utf-8")
    for invariant in ("English sentence is not treated by itself as a language-switch request", "text is not mislabeled as audio", "an access block and resume checkpoint", "expired profile is not used"):
        if invariant not in cases:
            fail(f"hardening-cases.yaml: missing invariant {invariant!r}")
    valid = validate_resume_code("TEACH-ME:v2:S001:k8s:ar-EG:M02:L03")
    legacy = validate_resume_code("TEACH-ME:v1:k8s:ar-EG:M02:L03:retained")
    partial = validate_resume_code("TEACH-ME:v2:S001:k8s:ar-EG:M02")
    future = validate_resume_code("TEACH-ME:v3:S001:k8s:ar-EG:M02:L03")
    if valid["status"] != "valid" or valid["mastery_evidence"] is not False:
        fail("resume validator: valid locator must not become mastery evidence")
    if legacy["status"] != "legacy-valid" or legacy.get("legacy_claimed_state") != "retained":
        fail("resume validator: legacy state must be isolated from evidence")
    if partial["status"] != "partial" or future["status"] != "unsupported-version":
        fail("resume validator: partial/version classification failed")


def check_conversational_teaching() -> None:
    cases = (ROOT / "evals" / "conversational-teaching-cases.yaml").read_text(encoding="utf-8")
    for invariant in ("accepted without a subject-matter placement test", "without appending a quiz to each part", "does not end with another diagnostic question", "routine evidence classification remains internal", "one authentic low-pressure application", "unfinished page slice is not treated as a completed learning-unit boundary", "no assessment question is asked until the learner explicitly opts in", "accepted without pressure, penalty language, or a negative mastery inference", "three to five concise items sample explanation, misconception discrimination, and application", "unverified mastery is not assumed for a dependent objective"):
        if invariant not in cases:
            fail(f"conversational-teaching-cases.yaml: missing invariant {invariant!r}")


def main() -> int:
    check_json()
    check_skill()
    check_evals()
    check_templates()
    check_integration()
    check_research_sweep()
    check_curriculum_delivery()
    check_guided_learning_pack()
    check_teaching_engine()
    check_retention_accessibility()
    check_integration_foundation()
    check_hardening()
    check_conversational_teaching()
    print("Teach Me validation passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, json.JSONDecodeError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
