import runtimeBundleJson from "../generated/teach-me-runtime.json";

import type {
  AdapterErrorCode,
  Audience,
  GuidanceModule,
  InputMode,
  LoadTeachMeFailure,
  LoadTeachMeInput,
  LoadTeachMeResult,
  LoadTeachMeSuccess,
  NormalizedRequest,
  RequestedLocale,
  RuntimeBundle,
  SelectedModule,
} from "./types.js";

const runtimeBundle = runtimeBundleJson as unknown as RuntimeBundle;
const allowedFields = new Set<keyof LoadTeachMeInput>([
  "audience",
  "input_mode",
  "locale",
  "guidance_modules",
]);
const supportedAudiences: Audience[] = ["learner"];
const supportedInputModes: InputMode[] = ["topic-led"];
const supportedLocales: RequestedLocale[] = ["en", "ar-MSA"];
const supportedGuidanceModules: GuidanceModule[] = ["topic-led-conversational"];
const maximumGuidanceModules = 8;
const arabicGuidanceAsset = "arabic-teaching-style";

function failure(code: AdapterErrorCode, message: string, field?: string): LoadTeachMeFailure {
  return {
    ok: false,
    error: field === undefined ? { code, message } : { code, field, message },
  };
}

function normalizeInput(input: unknown): NormalizedRequest | LoadTeachMeFailure {
  if (typeof input !== "object" || input === null || Array.isArray(input)) {
    return failure("invalid_input", "input must be an object");
  }
  const prototype = Object.getPrototypeOf(input);
  if (prototype !== Object.prototype && prototype !== null) {
    return failure("invalid_input", "input must be a plain object");
  }
  const value = input as Record<string, unknown>;
  const unknownFields = Object.keys(value)
    .filter((field) => !allowedFields.has(field as keyof LoadTeachMeInput))
    .sort();
  if (unknownFields.length > 0) {
    const field = unknownFields[0] as string;
    return failure("unknown_field", `unknown input field: ${field}`, field);
  }

  const audience = value.audience ?? "learner";
  if (typeof audience !== "string") {
    return failure("invalid_field_type", "audience must be a string", "audience");
  }
  if (!supportedAudiences.includes(audience as Audience)) {
    return failure("unsupported_audience", `unsupported audience: ${audience}`, "audience");
  }

  const inputMode = value.input_mode ?? "topic-led";
  if (typeof inputMode !== "string") {
    return failure("invalid_field_type", "input_mode must be a string", "input_mode");
  }
  if (!supportedInputModes.includes(inputMode as InputMode)) {
    return failure("unsupported_input_mode", `unsupported input_mode: ${inputMode}`, "input_mode");
  }

  let requestedLocale: RequestedLocale | null = null;
  if (Object.hasOwn(value, "locale")) {
    if (typeof value.locale !== "string") {
      return failure("invalid_field_type", "locale must be a string", "locale");
    }
    const normalizedLocale = value.locale === "ar-EG" ? "ar-MSA" : value.locale;
    if (!supportedLocales.includes(normalizedLocale as RequestedLocale)) {
      return failure("unsupported_locale", `unsupported locale: ${value.locale}`, "locale");
    }
    requestedLocale = normalizedLocale as RequestedLocale;
  }

  let guidanceModules: GuidanceModule[] = ["topic-led-conversational"];
  if (Object.hasOwn(value, "guidance_modules")) {
    if (!Array.isArray(value.guidance_modules)) {
      return failure("invalid_field_type", "guidance_modules must be an array", "guidance_modules");
    }
    if (value.guidance_modules.length === 0) {
      return failure("empty_guidance_modules", "guidance_modules must not be empty", "guidance_modules");
    }
    if (value.guidance_modules.length > maximumGuidanceModules) {
      return failure(
        "too_many_guidance_modules",
        `guidance_modules must contain at most ${maximumGuidanceModules} items`,
        "guidance_modules",
      );
    }
    const seen = new Set<string>();
    guidanceModules = [];
    for (const module of value.guidance_modules) {
      if (typeof module !== "string") {
        return failure(
          "invalid_field_type",
          "guidance_modules items must be strings",
          "guidance_modules",
        );
      }
      if (seen.has(module)) {
        return failure(
          "duplicate_guidance_module",
          `duplicate guidance module: ${module}`,
          "guidance_modules",
        );
      }
      if (!supportedGuidanceModules.includes(module as GuidanceModule)) {
        return failure(
          "unsupported_guidance_module",
          `unsupported guidance module: ${module}`,
          "guidance_modules",
        );
      }
      seen.add(module);
      guidanceModules.push(module as GuidanceModule);
    }
  }

  return {
    audience: audience as Audience,
    guidance_modules: guidanceModules,
    input_mode: inputMode as InputMode,
    locale_strategy: requestedLocale === null ? "host-inferred" : "explicit",
    requested_locale: requestedLocale,
  };
}

function selectedModules(request: NormalizedRequest): SelectedModule[] {
  return runtimeBundle.assets
    .filter((asset) => request.guidance_modules.some((module) => asset.module_categories.includes(module)))
    .filter((asset) => request.requested_locale !== "en" || asset.id !== arabicGuidanceAsset)
    .sort((left, right) => left.order - right.order)
    .map((asset) => ({
      classification: asset.classification,
      content: asset.content,
      content_bytes: asset.content_bytes,
      id: asset.id,
      module_categories: [...asset.module_categories],
      order: asset.order,
      path: asset.path,
      required: asset.required,
      sha256: asset.sha256,
    }));
}

export function loadTeachMe(input: unknown = {}): LoadTeachMeResult {
  const normalized = normalizeInput(input);
  if ("ok" in normalized) {
    return normalized;
  }
  const success: LoadTeachMeSuccess = {
    ok: true,
    teach_me_version: runtimeBundle.teach_me_version,
    bundle_digest: runtimeBundle.bundle_digest,
    bundle_schema_version: runtimeBundle.bundle_schema_version,
    normalized_request: normalized,
    capabilities: {
      audiences: [...supportedAudiences],
      guidance_modules: [...supportedGuidanceModules],
      input_modes: [...supportedInputModes],
      locales: [...supportedLocales],
    },
    host_contract: {
      teacher: "connected-host-model",
      server_calls_llm: false,
      server_side_learner_persistence: false,
      learner_transcript_required: false,
      source_access: "host-provided",
    },
    provenance: { ...runtimeBundle.source_manifest },
    selected_modules: selectedModules(normalized),
  };
  return success;
}

export { loadTeachMe as load_teach_me };
