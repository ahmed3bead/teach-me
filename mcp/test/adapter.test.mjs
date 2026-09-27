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
    age_band: "unspecified",
    audience: "learner",
    guidance_modules: ["topic-led-conversational"],
    input_mode: "topic-led",
    locale_strategy: "host-inferred",
    requested_locale: null,
    source_type: null,
  });
  assert.deepEqual(result.selected_modules.map((module) => module.id), ["chatgpt-runtime-core"]);
});

test("source-grounded requests load core and source guidance without receiving source content", () => {
  const result = success({ input_mode: "source-grounded", source_type: "playlist", locale: "en" });
  assert.deepEqual(result.normalized_request, {
    age_band: "unspecified",
    audience: "learner",
    guidance_modules: ["topic-led-conversational", "source-grounded"],
    input_mode: "source-grounded",
    locale_strategy: "explicit",
    requested_locale: "en",
    source_type: "playlist",
  });
  assert.equal(result.host_contract.source_access, "host-provided-or-host-retrieved");
  assert.deepEqual(result.selected_modules.map((module) => module.id), [
    "chatgpt-runtime-core",
    "chatgpt-runtime-source",
    "chatgpt-runtime-video",
    "chatgpt-runtime-curriculum",
  ]);
});

test("explicit English and Arabic requests select locale-appropriate guidance", () => {
  const english = success({ locale: "en" });
  assert.equal(english.normalized_request.requested_locale, "en");
  assert.deepEqual(english.selected_modules.map((module) => module.id), ["chatgpt-runtime-core"]);

  const arabic = success({ locale: "ar-MSA" });
  assert.equal(arabic.normalized_request.requested_locale, "ar-MSA");
  assert.deepEqual(arabic.selected_modules.map((module) => module.id), ["chatgpt-runtime-core"]);
  assert.match(arabic.selected_modules[0].content, /Modern Standard Arabic/);
});

test("legacy Arabic locale normalizes to ar-MSA", () => {
  const result = success({ locale: "ar-EG" });
  assert.equal(result.normalized_request.requested_locale, "ar-MSA");
  assert.equal(result.normalized_request.locale_strategy, "explicit");
});

test("educator requests load a teacher brief module without changing the default plugin", () => {
  const result = success({ audience: "educator", locale: "ar-MSA" });
  assert.deepEqual(result.educator_format_contract, {
    timed_flow: "numbered-time-blocks",
    arabic_markdown_tables: false,
    arrow_dependent_diagrams: false,
  });
  assert.deepEqual(result.normalized_request.guidance_modules, [
    "topic-led-conversational",
    "educator-guidance",
  ]);
  assert.deepEqual(result.selected_modules.map((module) => module.id), [
    "chatgpt-runtime-core",
    "chatgpt-runtime-educator",
  ]);
  assert.equal(success().educator_format_contract, null);
});

test("young learner requests load only the compact child guidance needed for the age band", () => {
  const result = success({ age_band: "primary-younger" });
  assert.deepEqual(result.normalized_request.guidance_modules, [
    "topic-led-conversational",
    "child-guidance",
  ]);
  assert.deepEqual(result.selected_modules.map((module) => module.id), [
    "chatgpt-runtime-core",
    "chatgpt-runtime-child",
  ]);
  const child = result.selected_modules.find((module) => module.id === "chatgpt-runtime-child");
  assert.match(child.content, /40–80 words/);
  assert.match(child.content, /Do not end the first explanation with a question/);

  const adult = success({ age_band: "adult" });
  assert.deepEqual(adult.selected_modules.map((module) => module.id), ["chatgpt-runtime-core"]);
});

test("teacher preparation for children and a source composes the relevant modules", () => {
  const result = success({
    audience: "educator",
    age_band: "primary-older",
    input_mode: "source-grounded",
    source_type: "document",
  });
  assert.deepEqual(result.normalized_request.guidance_modules, [
    "topic-led-conversational",
    "educator-guidance",
    "child-guidance",
    "source-grounded",
  ]);
  assert.deepEqual(result.selected_modules.map((module) => module.id), [
    "chatgpt-runtime-core",
    "chatgpt-runtime-educator",
    "chatgpt-runtime-child",
    "chatgpt-runtime-source",
  ]);
});

test("strict validation returns predictable public errors", () => {
  error(null, "invalid_input");
  error([], "invalid_input");
  error({ audience: "student" }, "unsupported_audience");
  error({ age_band: "8" }, "unsupported_age_band");
  error({ input_mode: "unsupported" }, "unsupported_input_mode");
  error({ locale: "fr" }, "unsupported_locale");
  error({ source_type: "book" }, "source_type_requires_source_grounded");
  error({ input_mode: "source-grounded", source_type: "unknown" }, "unsupported_source_type");
  error({ guidance_modules: "topic-led-conversational" }, "invalid_field_type");
  error({ guidance_modules: [] }, "empty_guidance_modules");
  error({ guidance_modules: ["source-grounded"] }, "incompatible_guidance_modules");
  error(
    { input_mode: "source-grounded", guidance_modules: ["topic-led-conversational"] },
    "incompatible_guidance_modules",
  );
  error({ guidance_modules: ["unsupported"] }, "unsupported_guidance_module");
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

test("source-grounded selection loads only modules relevant to the source type", () => {
  const expected = {
    document: ["chatgpt-runtime-core", "chatgpt-runtime-source"],
    webpage: ["chatgpt-runtime-core", "chatgpt-runtime-source"],
    video: ["chatgpt-runtime-core", "chatgpt-runtime-source", "chatgpt-runtime-video"],
    recording: ["chatgpt-runtime-core", "chatgpt-runtime-source", "chatgpt-runtime-video"],
    book: ["chatgpt-runtime-core", "chatgpt-runtime-source", "chatgpt-runtime-curriculum"],
    course: ["chatgpt-runtime-core", "chatgpt-runtime-source", "chatgpt-runtime-curriculum"],
    curriculum: ["chatgpt-runtime-core", "chatgpt-runtime-source", "chatgpt-runtime-curriculum"],
    playlist: [
      "chatgpt-runtime-core",
      "chatgpt-runtime-source",
      "chatgpt-runtime-video",
      "chatgpt-runtime-curriculum",
    ],
    mixed: ["chatgpt-runtime-core", "chatgpt-runtime-source", "chatgpt-runtime-curriculum"],
  };
  for (const [source_type, identifiers] of Object.entries(expected)) {
    const result = success({ input_mode: "source-grounded", source_type });
    assert.deepEqual(result.selected_modules.map((module) => module.id), identifiers, source_type);
  }
});

test("adapter source has no Node, process, network, or filesystem runtime dependency", async () => {
  const source = await readFile(new URL("../src/adapter.ts", import.meta.url), "utf8");
  assert.doesNotMatch(
    source,
    /(?:from\s+|import\s*\()["'](?:node:)?(?:fs(?:\/promises)?|path|child_process|http|https|net)["']/,
  );
  assert.doesNotMatch(source, /\bprocess\b|\bfetch\s*\(/);
});

test("adapter response sizes remain within the compact runtime budget", () => {
  const englishBytes = Buffer.byteLength(JSON.stringify(success({ locale: "en" })), "utf8");
  const arabicBytes = Buffer.byteLength(JSON.stringify(success({ locale: "ar-MSA" })), "utf8");
  assert.ok(englishBytes < 20_000);
  assert.ok(arabicBytes < 20_000);
  console.log(`Teach Me adapter response sizes: en=${englishBytes} bytes, ar-MSA=${arabicBytes} bytes`);
});
