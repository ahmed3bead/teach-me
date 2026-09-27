import runtimeBundleJson from "../generated/teach-me-runtime.json";

import type {
  AdapterErrorCode,
  AgeBand,
  Audience,
  EducatorFormatContract,
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
  SourceType,
} from "./types.js";

const runtimeBundle = runtimeBundleJson as unknown as RuntimeBundle;
const allowedFields = new Set<keyof LoadTeachMeInput>([
  "age_band",
  "audience",
  "input_mode",
  "locale",
  "guidance_modules",
  "source_type",
]);
const supportedAudiences: Audience[] = ["learner", "educator"];
const supportedAgeBands: AgeBand[] = [
  "early-childhood",
  "primary-younger",
  "primary-older",
  "teen",
  "adult",
  "unspecified",
];
const supportedInputModes: InputMode[] = ["topic-led", "source-grounded"];
const supportedLocales: RequestedLocale[] = ["en", "ar-MSA"];
const supportedGuidanceModules: GuidanceModule[] = [
  "topic-led-conversational",
  "educator-guidance",
  "child-guidance",
  "source-grounded",
];
const supportedSourceTypes: SourceType[] = [
  "document",
  "book",
  "webpage",
  "video",
  "playlist",
  "course",
  "recording",
  "curriculum",
  "mixed",
];
const maximumGuidanceModules = 8;
const videoSourceTypes = new Set<SourceType>(["video", "playlist", "recording"]);
const curriculumSourceTypes = new Set<SourceType>(["book", "playlist", "course", "curriculum", "mixed"]);
const youngAgeBands = new Set<AgeBand>([
  "early-childhood",
  "primary-younger",
  "primary-older",
  "teen",
]);

function requiredModulesFor(audience: Audience, ageBand: AgeBand, inputMode: InputMode): GuidanceModule[] {
  const modules: GuidanceModule[] = ["topic-led-conversational"];
  if (audience === "educator") {
    modules.push("educator-guidance");
  }
  if (youngAgeBands.has(ageBand)) {
    modules.push("child-guidance");
  }
  if (inputMode === "source-grounded") {
    modules.push("source-grounded");
  }
  return modules;
}

function educatorFormatContractFor(audience: Audience): EducatorFormatContract | null {
  if (audience !== "educator") {
    return null;
  }
  return {
    timed_flow: "numbered-time-blocks",
    arabic_markdown_tables: false,
    arrow_dependent_diagrams: false,
  };
}

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
    return failure("unsupported_audience", "audience is not supported", "audience");
  }

  const ageBand = value.age_band ?? "unspecified";
  if (typeof ageBand !== "string") {
    return failure("invalid_field_type", "age_band must be a string", "age_band");
  }
  if (!supportedAgeBands.includes(ageBand as AgeBand)) {
    return failure("unsupported_age_band", "age_band is not supported", "age_band");
  }

  const inputMode = value.input_mode ?? "topic-led";
  if (typeof inputMode !== "string") {
    return failure("invalid_field_type", "input_mode must be a string", "input_mode");
  }
  if (!supportedInputModes.includes(inputMode as InputMode)) {
    return failure("unsupported_input_mode", "input_mode is not supported", "input_mode");
  }

  let requestedLocale: RequestedLocale | null = null;
  if (Object.hasOwn(value, "locale")) {
    if (typeof value.locale !== "string") {
      return failure("invalid_field_type", "locale must be a string", "locale");
    }
    const normalizedLocale = value.locale === "ar-EG" ? "ar-MSA" : value.locale;
    if (!supportedLocales.includes(normalizedLocale as RequestedLocale)) {
      return failure("unsupported_locale", "locale is not supported", "locale");
    }
    requestedLocale = normalizedLocale as RequestedLocale;
  }

  let sourceType: SourceType | null = null;
  if (Object.hasOwn(value, "source_type")) {
    if (typeof value.source_type !== "string") {
      return failure("invalid_field_type", "source_type must be a string", "source_type");
    }
    if (!supportedSourceTypes.includes(value.source_type as SourceType)) {
      return failure("unsupported_source_type", "source_type is not supported", "source_type");
    }
    if (inputMode !== "source-grounded") {
      return failure(
        "source_type_requires_source_grounded",
        "source_type may be used only when input_mode is source-grounded",
        "source_type",
      );
    }
    sourceType = value.source_type as SourceType;
  }

  const requiredModules = requiredModulesFor(
    audience as Audience,
    ageBand as AgeBand,
    inputMode as InputMode,
  );
  let guidanceModules: GuidanceModule[] = requiredModules;
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
          "guidance_modules must not contain duplicates",
          "guidance_modules",
        );
      }
      if (!supportedGuidanceModules.includes(module as GuidanceModule)) {
        return failure(
          "unsupported_guidance_module",
          "guidance_modules contains an unsupported item",
          "guidance_modules",
        );
      }
      seen.add(module);
      guidanceModules.push(module as GuidanceModule);
    }
    if (
      guidanceModules.length !== requiredModules.length ||
      requiredModules.some((module) => !guidanceModules.includes(module))
    ) {
      return failure(
        "incompatible_guidance_modules",
        `guidance_modules must be ${requiredModules.join(", ")} for input_mode ${inputMode}`,
        "guidance_modules",
      );
    }
    guidanceModules = requiredModules;
  }

  return {
    age_band: ageBand as AgeBand,
    audience: audience as Audience,
    guidance_modules: guidanceModules,
    input_mode: inputMode as InputMode,
    locale_strategy: requestedLocale === null ? "host-inferred" : "explicit",
    requested_locale: requestedLocale,
    source_type: sourceType,
  };
}

function selectedModules(request: NormalizedRequest): SelectedModule[] {
  const includeAsset = (id: string): boolean => {
    if (id === "chatgpt-runtime-video") {
      return request.source_type !== null && videoSourceTypes.has(request.source_type);
    }
    if (id === "chatgpt-runtime-curriculum") {
      return request.source_type !== null && curriculumSourceTypes.has(request.source_type);
    }
    return true;
  };
  return runtimeBundle.assets
    .filter((asset) => request.guidance_modules.some((module) => asset.module_categories.includes(module)))
    .filter((asset) => includeAsset(asset.id))
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
    educator_format_contract: educatorFormatContractFor(normalized.audience),
    capabilities: {
      age_bands: [...supportedAgeBands],
      audiences: [...supportedAudiences],
      guidance_modules: [...supportedGuidanceModules],
      input_modes: [...supportedInputModes],
      locales: [...supportedLocales],
      source_types: [...supportedSourceTypes],
    },
    host_contract: {
      teacher: "connected-host-model",
      server_calls_llm: false,
      server_side_learner_persistence: false,
      learner_transcript_required: false,
      source_access: "host-provided-or-host-retrieved",
    },
    provenance: { ...runtimeBundle.source_manifest },
    selected_modules: selectedModules(normalized),
  };
  return success;
}

export { loadTeachMe as load_teach_me };
