import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
  type CallToolResult,
  type Tool,
} from "@modelcontextprotocol/sdk/types.js";
import type { jsonSchemaValidator } from "@modelcontextprotocol/sdk/validation/types.js";
import * as z from "zod";

import { loadTeachMe } from "./adapter.js";
import type { LoadTeachMeFailure, LoadTeachMeResult, LoadTeachMeSuccess } from "./types.js";

export const SERVER_NAME = "teach-me-mcp";
export const TOOL_NAME = "load_teach_me";

export const SERVER_INSTRUCTIONS = [
  "You are the teacher; call load_teach_me once before teaching or lesson preparation and follow the returned canonical guidance.",
  "Use audience educator for teacher preparation, age_band for young learners, and source-grounded when a chosen source governs the work.",
  "Aliases are prompt text, not native commands; /kids without an age uses teen.",
  "Keep sources, transcripts, credentials, and personal data in the host; send selectors only.",
  "Teach Me is read-only, stateless, and does not call a model.",
].join(" ");

const inputSchema = z
  .strictObject({
    age_band: z
      .enum(["early-childhood", "primary-younger", "primary-older", "teen", "adult", "unspecified"])
      .optional()
      .describe("Broad learner band: ages 3–5 early-childhood, 6–8 primary-younger, 9–12 primary-older, 13–17 teen. Keep exact age in the host; never send identifying data."),
    audience: z
      .enum(["learner", "educator"])
      .optional()
      .describe("Use `learner` for direct teaching and `educator` for lesson preparation or teacher notes."),
    input_mode: z
      .enum(["topic-led", "source-grounded"])
      .optional()
      .describe("Use `topic-led` for a named topic or `source-grounded` when a source governs the lesson."),
    locale: z
      .enum(["en", "ar-MSA", "ar-EG"])
      .optional()
      .describe("Learner language. Omit to let the host infer it. `ar-EG` is accepted and normalized to `ar-MSA`."),
    guidance_modules: z
      .array(z.enum(["topic-led-conversational", "educator-guidance", "child-guidance", "source-grounded"]))
      .min(1)
      .max(8)
      .optional()
      .describe("Optional exact module set. Omit to select the safe defaults for input_mode."),
    source_type: z
      .enum(["document", "book", "webpage", "video", "playlist", "course", "recording", "curriculum", "mixed"])
      .optional()
      .describe("Type of learner-chosen source. Use only with `source-grounded`; never include source content."),
  })
  .describe("Optional selectors for the Teach Me guidance. Do not include learner content.");

const errorSchema = z.object({
  code: z.string(),
  message: z.string(),
  field: z.string().optional(),
});

const outputSchema = z
  .object({
    ok: z.boolean().describe("true when guidance was loaded; false when the request was rejected"),
    teach_me_version: z.string().optional(),
    bundle_digest: z.string().optional(),
    bundle_schema_version: z.string().optional(),
    normalized_request: z
      .object({
        age_band: z.string(),
        audience: z.string(),
        guidance_modules: z.array(z.string()),
        input_mode: z.string(),
        locale_strategy: z.enum(["host-inferred", "explicit"]),
        requested_locale: z.string().nullable(),
        source_type: z.string().nullable(),
      })
      .optional(),
    educator_format_contract: z
      .object({
        timed_flow: z.literal("numbered-time-blocks"),
        arabic_markdown_tables: z.literal(false),
        arrow_dependent_diagrams: z.literal(false),
      })
      .nullable()
      .optional(),
    capabilities: z
      .object({
        age_bands: z.array(z.string()),
        audiences: z.array(z.string()),
        guidance_modules: z.array(z.string()),
        input_modes: z.array(z.string()),
        locales: z.array(z.string()),
        source_types: z.array(z.string()),
      })
      .optional(),
    host_contract: z
      .object({
        teacher: z.string(),
        server_calls_llm: z.boolean(),
        server_side_learner_persistence: z.boolean(),
        learner_transcript_required: z.boolean(),
        source_access: z.string(),
      })
      .optional(),
    loaded_module_ids: z.array(z.string()).optional(),
    error: errorSchema.optional().describe("Present only when ok is false"),
  })
  .describe("The Teach Me adapter result");

function toToolJsonSchema(schema: z.ZodType, io: "input" | "output"): Tool["inputSchema"] {
  const { $schema: _dialect, ...json } = z.toJSONSchema(schema, { io }) as Record<string, unknown>;
  return json as Tool["inputSchema"];
}

export const LOAD_TEACH_ME_TOOL: Tool = {
  name: TOOL_NAME,
  title: "Load Teach Me guidance",
  description:
    "Load the versioned Teach Me guidance that you, the connected host model, should follow for direct teaching, teacher preparation, young learners, or an accessible user-chosen source. " +
    "Call it before teaching, then follow the returned canonical modules and any explicit format contract. Arabic teacher briefs use numbered blocks, never Markdown tables or arrow-dependent diagrams. Returns public, reviewed instructions only; " +
    "send no source content, learner transcripts, files, or personal data.",
  inputSchema: toToolJsonSchema(inputSchema, "input"),
  outputSchema: toToolJsonSchema(outputSchema, "output") as NonNullable<Tool["outputSchema"]>,
  annotations: {
    title: "Load Teach Me guidance",
    readOnlyHint: true,
    destructiveHint: false,
    idempotentHint: true,
    openWorldHint: false,
  },
};

const hostResponsibilities = [
  "You are the teacher: the Teach Me server never calls a model and never sees the conversation.",
  "Follow the modules below in order; they are the canonical, reviewed guidance for this version.",
  "Keep learner transcripts, files, and personal data in the host conversation; never send them to this server.",
  "Sources stay under host control. Inspect only components the host can actually access and state coverage limits.",
];

function successText(result: LoadTeachMeSuccess): string {
  const header = [
    `# Teach Me guidance ${result.teach_me_version}`,
    "",
    `- locale_strategy: ${result.normalized_request.locale_strategy}`,
    `- audience: ${result.normalized_request.audience}`,
    `- age_band: ${result.normalized_request.age_band}`,
    `- requested_locale: ${result.normalized_request.requested_locale ?? "host-inferred"}`,
    `- guidance_modules: ${result.normalized_request.guidance_modules.join(", ")}`,
    `- source_type: ${result.normalized_request.source_type ?? "none"}`,
  ];
  const formatContract = result.educator_format_contract === null
    ? []
    : [
        "",
        "## Mandatory educator format contract",
        "",
        "- timed_flow: numbered-time-blocks",
        "- arabic_markdown_tables: forbidden",
        "- arrow_dependent_diagrams: forbidden",
        "- Revise the response before sending if any rule is violated.",
      ];
  const responsibilities = [
    "",
    "## Host responsibilities",
    "",
    ...hostResponsibilities.map((line) => `- ${line}`),
  ];
  const modules = result.selected_modules.map((module) =>
    [
      "",
      `## Module ${module.order}: ${module.id}`,
      "",
      module.content.trimEnd(),
    ].join("\n"),
  );
  return [...header, ...formatContract, ...responsibilities, ...modules].join("\n") + "\n";
}

function failureText(result: LoadTeachMeFailure): string {
  const field = result.error.field === undefined ? "" : ` (field: ${result.error.field})`;
  return `Teach Me request rejected: ${result.error.code}${field}. ${result.error.message}`;
}

export function toCallToolResult(result: LoadTeachMeResult): CallToolResult {
  if (result.ok) {
    const structuredContent = {
      ok: true,
      teach_me_version: result.teach_me_version,
      normalized_request: result.normalized_request,
      educator_format_contract: result.educator_format_contract,
      capabilities: result.capabilities,
      host_contract: result.host_contract,
      loaded_module_ids: result.selected_modules.map((module) => module.id),
    };
    const _meta = {
      bundle_digest: result.bundle_digest,
      bundle_schema_version: result.bundle_schema_version,
      provenance: result.provenance,
      selected_modules: result.selected_modules.map(({ content: _content, ...module }) => module),
    };
    return { content: [{ type: "text", text: successText(result) }], structuredContent, _meta };
  }
  const structuredContent = result as unknown as Record<string, unknown>;
  return { content: [{ type: "text", text: failureText(result) }], structuredContent, isError: true };
}

const internalFailure: LoadTeachMeFailure = {
  ok: false,
  error: { code: "invalid_input", message: "the request could not be processed" },
};

// Elicitation is never used, so JSON Schema validation must never be requested.
// Supplying this avoids the SDK's default Ajv provider, which relies on runtime code generation.
const noSchemaValidation: jsonSchemaValidator = {
  getValidator() {
    return () => ({ valid: false, data: undefined, errorMessage: "schema validation is not supported" });
  },
};

export function createTeachMeServer(version: string): Server {
  const server = new Server(
    { name: SERVER_NAME, title: "Teach Me", version },
    {
      capabilities: { tools: {} },
      instructions: SERVER_INSTRUCTIONS,
      jsonSchemaValidator: noSchemaValidation,
    },
  );

  server.setRequestHandler(ListToolsRequestSchema, () => ({ tools: [LOAD_TEACH_ME_TOOL] }));

  server.setRequestHandler(CallToolRequestSchema, (request) => {
    if (request.params.name !== TOOL_NAME) {
      throw new McpError(ErrorCode.InvalidParams, "Unknown tool");
    }
    let result: LoadTeachMeResult;
    try {
      result = loadTeachMe(request.params.arguments ?? {});
    } catch {
      result = internalFailure;
    }
    return toCallToolResult(result);
  });

  return server;
}
