import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { load_teach_me } from "../dist/adapter.js";

const runtimeBundle = JSON.parse(
  await readFile(new URL("../generated/teach-me-runtime.json", import.meta.url), "utf8"),
);

function success(input = {}) {
  const result = load_teach_me(input);
  assert.equal(result.ok, true, JSON.stringify(result));
  return result;
}

function error(input, code) {
  const result = load_teach_me(input);
  assert.equal(result.ok, false);
  assert.equal(result.error.code, code);
  assert.equal(typeof result.error.message, "string");
  assert.equal("stack" in result.error, false);
  return result.error;
}

test("default request uses host-inferred topic-led learner guidance", () => {
  const result = success();
  assert.deepEqual(result.normalized_request, {
    audience: "learner",
    guidance_modules: ["topic-led-conversational"],
    input_mode: "topic-led",
    locale_strategy: "host-inferred",
    requested_locale: null,
  });
  assert.equal(result.selected_modules.length, 11);
});

test("explicit English and Arabic requests select locale-appropriate guidance", () => {
  const english = success({ locale: "en" });
  assert.equal(english.normalized_request.requested_locale, "en");
  assert.equal(english.selected_modules.some((module) => module.id === "arabic-teaching-style"), false);

  const arabic = success({ locale: "ar-MSA" });
  assert.equal(arabic.normalized_request.requested_locale, "ar-MSA");
  assert.equal(arabic.selected_modules.some((module) => module.id === "arabic-teaching-style"), true);
  assert.match(
    arabic.selected_modules.find((module) => module.id === "arabic-teaching-style").content,
    /[\u0600-\u06ff]/,
  );
});

test("legacy Arabic locale normalizes to ar-MSA", () => {
  const result = success({ locale: "ar-EG" });
  assert.equal(result.normalized_request.requested_locale, "ar-MSA");
  assert.equal(result.normalized_request.locale_strategy, "explicit");
});

test("strict validation returns predictable public errors", () => {
  error(null, "invalid_input");
  error([], "invalid_input");
  error({ audience: "educator" }, "unsupported_audience");
  error({ input_mode: "source-grounded" }, "unsupported_input_mode");
  error({ locale: "fr" }, "unsupported_locale");
  error({ guidance_modules: "topic-led-conversational" }, "invalid_field_type");
  error({ guidance_modules: [] }, "empty_guidance_modules");
  error({ guidance_modules: ["source-grounded"] }, "unsupported_guidance_module");
  error({ guidance_modules: ["topic-led-conversational", "topic-led-conversational"] }, "duplicate_guidance_module");
  error({ guidance_modules: Array(9).fill("topic-led-conversational") }, "too_many_guidance_modules");
  error({ guidance_modules: [{ id: "topic-led-conversational" }] }, "invalid_field_type");
  error({ unexpected: true }, "unknown_field");
  error({ transcript: [{ role: "user", content: "private" }] }, "unknown_field");
});

test("same input produces structurally identical output", () => {
  assert.deepEqual(load_teach_me({ locale: "ar-MSA" }), load_teach_me({ locale: "ar-MSA" }));
});

test("version, provenance, content, and digests match the generated bundle", () => {
  const result = success({ locale: "ar-MSA" });
  assert.equal(result.teach_me_version, runtimeBundle.teach_me_version);
  assert.equal(result.bundle_digest, runtimeBundle.bundle_digest);
  assert.equal(result.bundle_schema_version, runtimeBundle.bundle_schema_version);
  assert.deepEqual(result.provenance, runtimeBundle.source_manifest);
  for (const selected of result.selected_modules) {
    const source = runtimeBundle.assets.find((asset) => asset.id === selected.id);
    assert.ok(source);
    assert.equal(selected.content, source.content);
    assert.equal(selected.sha256, source.sha256);
    assert.equal(selected.path, source.path);
  }
});

test("selection exposes only the requested active logical module", () => {
  const result = success({ guidance_modules: ["topic-led-conversational"] });
  assert.ok(result.selected_modules.length > 0);
  assert.ok(
    result.selected_modules.every((module) => module.module_categories.includes("topic-led-conversational")),
  );
  assert.equal(result.selected_modules.some((module) => module.path.startsWith("evals/")), false);
});

test("adapter source has no Node, process, network, or filesystem runtime dependency", async () => {
  const source = await readFile(new URL("../src/adapter.ts", import.meta.url), "utf8");
  assert.doesNotMatch(
    source,
    /(?:from\s+|import\s*\()["'](?:node:)?(?:fs(?:\/promises)?|path|child_process|http|https|net)["']/,
  );
  assert.doesNotMatch(source, /\bprocess\b|\bfetch\s*\(/);
});

test("response sizes remain within the runtime bundle ceiling", () => {
  const englishBytes = Buffer.byteLength(JSON.stringify(success({ locale: "en" })), "utf8");
  const arabicBytes = Buffer.byteLength(JSON.stringify(success({ locale: "ar-MSA" })), "utf8");
  assert.ok(englishBytes < 524288);
  assert.ok(arabicBytes < 524288);
  console.log(`Teach Me adapter response sizes: en=${englishBytes} bytes, ar-MSA=${arabicBytes} bytes`);
});
