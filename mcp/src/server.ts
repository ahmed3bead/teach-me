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
  "Teach Me provides versioned, reviewed teaching guidance; you, the connected model, are the teacher.",
  "Before teaching any topic, call load_teach_me once (pass locale when the learner's language is known)",
  "and follow the returned canonical guidance for the rest of the conversation.",
  "Never send learner transcripts, files, credentials, or personal data to this server; it needs none.",
  "The server is read-only, stateless, and does not call any model.",
].join(" ");

const inputSchema = z
  .strictObject({
    audience: z.enum(["learner"]).optional().describe("Who is being taught. Only `learner` is supported."),
    input_mode: z
      .enum(["topic-led"])
      .optional()
      .describe("How the learning is driven. Only `topic-led` (the learner names a topic) is supported."),
    locale: z
      .enum(["en", "ar-MSA", "ar-EG"])
      .optional()
      .describe("Learner language. Omit to let the host infer it. `ar-EG` is accepted and normalized to `ar-MSA`."),
    guidance_modules: z
      .array(z.enum(["topic-led-conversational"]))
      .min(1)
      .max(8)
      .optional()
      .describe("Guidance modules to load. Defaults to `topic-led-conversational`."),
  })
  .describe("Optional selectors for the Teach Me guidance. Do not include learner content.");

const errorSchema = z.object({
  code: z.string(),
  message: z.string(),
  field: z.string().optional(),
});

const selectedModuleSchema = z.object({
  id: z.string(),
  path: z.string(),
  order: z.number().int(),
  classification: z.string(),
  module_categories: z.array(z.string()),
  required: z.boolean(),
  sha256: z.string(),
  content_bytes: z.number().int(),
  content: z.string(),
});

const outputSchema = z
  .object({
    ok: z.boolean().describe("true when guidance was loaded; false when the request was rejected"),
    teach_me_version: z.string().optional(),
    bundle_digest: z.string().optional(),
    bundle_schema_version: z.string().optional(),
    normalized_request: z
      .object({
        audience: z.string(),
        guidance_modules: z.array(z.string()),
        input_mode: z.string(),
        locale_strategy: z.enum(["host-inferred", "explicit"]),
        requested_locale: z.string().nullable(),
      })
      .optional(),
    capabilities: z
      .object({
        audiences: z.array(z.string()),
        guidance_modules: z.array(z.string()),
        input_modes: z.array(z.string()),
        locales: z.array(z.string()),
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
    provenance: z
      .object({
        manifest_version: z.string(),
        path: z.string(),
        schema_version: z.string(),
        selection_model: z.string(),
        sha256: z.string(),
      })
      .optional(),
    selected_modules: z.array(selectedModuleSchema).optional(),
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
    "Load the versioned Teach Me guidance that you, the connected host model, should follow when teaching an ordinary learner a topic. " +
    "Call it before teaching, then follow the returned canonical modules. Returns public, reviewed instructions only; " +
    "send no learner transcripts, files, or personal data.",
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
  "Any sources the learner provides stay under host control (source_access: host-provided).",
];

function successText(result: LoadTeachMeSuccess): string {
  const header = [
    `# Teach Me guidance ${result.teach_me_version}`,
    "",
    `- bundle_digest: ${result.bundle_digest}`,
    `- locale_strategy: ${result.normalized_request.locale_strategy}`,
    `- requested_locale: ${result.normalized_request.requested_locale ?? "host-inferred"}`,
    `- guidance_modules: ${result.normalized_request.guidance_modules.join(", ")}`,
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
      `<!-- path: ${module.path}; sha256: ${module.sha256} -->`,
      "",
      module.content.trimEnd(),
    ].join("\n"),
  );
  return [...header, ...modules].join("\n") + "\n";
}

function failureText(result: LoadTeachMeFailure): string {
  const field = result.error.field === undefined ? "" : ` (field: ${result.error.field})`;
  return `Teach Me request rejected: ${result.error.code}${field}. ${result.error.message}`;
}

export function toCallToolResult(result: LoadTeachMeResult): CallToolResult {
  const structuredContent = result as unknown as Record<string, unknown>;
  if (result.ok) {
    return { content: [{ type: "text", text: successText(result) }], structuredContent };
  }
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
