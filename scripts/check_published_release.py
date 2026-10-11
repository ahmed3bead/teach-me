#!/usr/bin/env python3
"""Check published listing copy, reviewer fixtures, and installation links offline."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main():
    record = read("docs/published-release.json")
    submission = read("chatgpt-app-submission.json")
    manifest = read("plugins/teach-me/.codex-plugin/plugin.json")
    interface = manifest["interface"]
    info = submission["app_info"]
    errors = []
    for field, expected in {
        "displayName": info["display_name"],
        "shortDescription": info["subtitle"],
        "longDescription": info["description"],
        "defaultPrompt": record["starter_prompts"],
    }.items():
        if interface[field] != expected:
            errors.append(f"Local listing copy differs: {field}")
    if len(submission["test_cases"]) != 5 or len(submission["negative_test_cases"]) != 3:
        errors.append("Submission requires five positive and three negative trigger cases")
    if any(case["tools_triggered"] is not None for case in submission["negative_test_cases"]):
        errors.append("Negative trigger cases must not invoke Teach Me")
    fixture = record["pdf_fixture"]
    fixture_path = ROOT / fixture["path"]
    if not fixture_path.is_file() or hashlib.sha256(fixture_path.read_bytes()).hexdigest() != fixture["sha256"]:
        errors.append("PDF fixture is missing or its recorded checksum is stale")
    expected_url = "https://raw.githubusercontent.com/ahmed3bead/teach-me/main/" + fixture["path"]
    if submission["test_cases"][4]["file_attachment_urls"] != [expected_url]:
        errors.append("Source-grounded PDF case lacks the public fixture attachment")
    for path in ("site/dist/index.html", "site/dist/en/index.html"):
        html = (ROOT / path).read_text(encoding="utf-8")
        for button in ("install-button", "launch-button"):
            if f'id="{button}" href="{record["listing_url"]}"' not in html:
                errors.append(f"{path}: {button} must work without JavaScript")
        if f'const PLUGIN_DIRECTORY_URL = "{record["listing_url"]}";' not in html:
            errors.append(f"{path}: scripted installation link differs")
        for stale in ("under OpenAI review", "Under OpenAI review", "قيد مراجعة OpenAI", "قيد المراجعة الآن"):
            if stale in html:
                errors.append(f"{path}: outdated publication text: {stale}")
    if record["listing_url"] not in (ROOT / "site/dist/llms.txt").read_text(encoding="utf-8"):
        errors.append("AI discovery summary lacks the published install URL")
    if errors:
        print("\n".join(errors))
        return 1
    print("Published listing copy, reviewer fixture, and installation-link checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
