export type Audience = "learner";
export type InputMode = "topic-led";
export type RequestedLocale = "en" | "ar-MSA";
export type InputLocale = RequestedLocale | "ar-EG";
export type GuidanceModule = "topic-led-conversational";

export interface LoadTeachMeInput {
  audience?: Audience;
  input_mode?: InputMode;
  locale?: InputLocale;
  guidance_modules?: GuidanceModule[];
}

export type AdapterErrorCode =
  | "invalid_input"
  | "unknown_field"
  | "invalid_field_type"
  | "unsupported_audience"
  | "unsupported_input_mode"
  | "unsupported_locale"
  | "unsupported_guidance_module"
  | "empty_guidance_modules"
  | "duplicate_guidance_module"
  | "too_many_guidance_modules";

export interface AdapterError {
  code: AdapterErrorCode;
  message: string;
  field?: keyof LoadTeachMeInput | string;
}

export interface NormalizedRequest {
  audience: Audience;
  guidance_modules: GuidanceModule[];
  input_mode: InputMode;
  locale_strategy: "host-inferred" | "explicit";
  requested_locale: RequestedLocale | null;
}

export interface SelectedModule {
  classification: string;
  content: string;
  content_bytes: number;
  id: string;
  module_categories: string[];
  order: number;
  path: string;
  required: boolean;
  sha256: string;
}

export interface RuntimeBundleAsset extends SelectedModule {}

export interface RuntimeBundle {
  asset_count: number;
  assets: RuntimeBundleAsset[];
  bundle_digest: string;
  bundle_schema_version: string;
  content_bytes: number;
  source_manifest: {
    manifest_version: string;
    path: string;
    schema_version: string;
    selection_model: string;
    sha256: string;
  };
  teach_me_version: string;
}

export interface LoadTeachMeSuccess {
  ok: true;
  teach_me_version: string;
  bundle_digest: string;
  bundle_schema_version: string;
  normalized_request: NormalizedRequest;
  capabilities: {
    audiences: Audience[];
    guidance_modules: GuidanceModule[];
    input_modes: InputMode[];
    locales: RequestedLocale[];
  };
  host_contract: {
    teacher: "connected-host-model";
    server_calls_llm: false;
    server_side_learner_persistence: false;
    learner_transcript_required: false;
    source_access: "host-provided";
  };
  provenance: RuntimeBundle["source_manifest"];
  selected_modules: SelectedModule[];
}

export interface LoadTeachMeFailure {
  ok: false;
  error: AdapterError;
}

export type LoadTeachMeResult = LoadTeachMeSuccess | LoadTeachMeFailure;
