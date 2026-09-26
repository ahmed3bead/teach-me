import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";

import runtimeBundleJson from "../generated/teach-me-runtime.json";
import { MAX_REQUEST_BODY_BYTES, MCP_PATH } from "./config.js";
import { createTeachMeServer, SERVER_NAME } from "./server.js";

// Only the default export may be exported: workerd treats every named export as an entrypoint.

const bundle = runtimeBundleJson as unknown as { teach_me_version: string; bundle_digest: string };

interface Env {
  OPENAI_APPS_CHALLENGE?: string;
}

const allowedOrigins = new Set(["https://chatgpt.com", "https://chat.openai.com", "https://claude.ai"]);
const loopbackOrigin = /^http:\/\/(?:localhost|127\.0\.0\.1|\[::1\])(?::\d{1,5})?$/;

const securityHeaders: Record<string, string> = {
  "Cache-Control": "no-store",
  "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
  // The public MCP endpoint is intentionally called cross-origin by approved hosts.
  "Cross-Origin-Resource-Policy": "cross-origin",
  "Permissions-Policy":
    "accelerometer=(), camera=(), clipboard-read=(), clipboard-write=(), geolocation=(), gyroscope=(), microphone=(), payment=(), usb=()",
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
};

const corsAllowHeaders = "Content-Type, Accept, Mcp-Protocol-Version, Mcp-Session-Id, Last-Event-ID";

type JsonRpcErrorCode = -32700 | -32600 | -32000;

function isAllowedOrigin(origin: string): boolean {
  return allowedOrigins.has(origin) || loopbackOrigin.test(origin);
}

function withHeaders(response: Response, request: Request, extra: Record<string, string> = {}): Response {
  const headers = new Headers(response.headers);
  for (const [name, value] of Object.entries({ ...securityHeaders, ...extra })) {
    headers.set(name, value);
  }
  headers.delete("Set-Cookie");
  const origin = request.headers.get("Origin");
  if (origin !== null && isAllowedOrigin(origin)) {
    headers.set("Access-Control-Allow-Origin", origin);
    headers.set("Access-Control-Expose-Headers", "Mcp-Session-Id, Mcp-Protocol-Version");
    headers.append("Vary", "Origin");
  }
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

function json(body: unknown, status: number, extra: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...extra },
  });
}

function jsonRpcError(status: number, code: JsonRpcErrorCode, message: string, extra: Record<string, string> = {}): Response {
  return json({ jsonrpc: "2.0", error: { code, message }, id: null }, status, extra);
}

function statusResponse(): Response {
  return json(
    {
      service: SERVER_NAME,
      status: "public-beta",
      mcp_endpoint: MCP_PATH,
      transport: "streamable-http",
      teach_me_version: bundle.teach_me_version,
      bundle_digest: bundle.bundle_digest,
      privacy: "No learner data is stored. The server is read-only, stateless, and never calls a model.",
    },
    200,
  );
}

type BodyResult = { ok: true; value: unknown } | { ok: false; response: Response };

async function readJsonBody(request: Request): Promise<BodyResult> {
  const declared = request.headers.get("Content-Length");
  if (declared !== null) {
    const length = Number(declared);
    if (!Number.isSafeInteger(length) || length < 0) {
      return { ok: false, response: jsonRpcError(400, -32600, "Invalid Content-Length") };
    }
    if (length > MAX_REQUEST_BODY_BYTES) {
      return { ok: false, response: jsonRpcError(413, -32600, "Request body too large") };
    }
  }
  if (request.body === null) {
    return { ok: false, response: jsonRpcError(400, -32700, "Parse error") };
  }

  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let received = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    received += value.byteLength;
    if (received > MAX_REQUEST_BODY_BYTES) {
      await reader.cancel();
      return { ok: false, response: jsonRpcError(413, -32600, "Request body too large") };
    }
    chunks.push(value);
  }
  const bytes = new Uint8Array(received);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }

  try {
    const text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: false }).decode(bytes);
    return { ok: true, value: JSON.parse(text) as unknown };
  } catch {
    return { ok: false, response: jsonRpcError(400, -32700, "Parse error") };
  }
}

function isJsonMediaType(contentType: string | null): boolean {
  if (contentType === null) {
    return false;
  }
  const mediaType = contentType.split(";", 1)[0]?.trim().toLowerCase();
  return mediaType === "application/json";
}

function isJsonRpcMessage(value: unknown): boolean {
  const messages = Array.isArray(value) ? value : [value];
  return (
    messages.length > 0 &&
    messages.every(
      (message) =>
        typeof message === "object" &&
        message !== null &&
        !Array.isArray(message) &&
        (message as Record<string, unknown>).jsonrpc === "2.0",
    )
  );
}

async function handleMcpPost(request: Request): Promise<Response> {
  if (!isJsonMediaType(request.headers.get("Content-Type"))) {
    return jsonRpcError(415, -32000, "Unsupported Media Type: Content-Type must be application/json");
  }
  const body = await readJsonBody(request);
  if (!body.ok) {
    return body.response;
  }
  if (!isJsonRpcMessage(body.value)) {
    return jsonRpcError(400, -32600, "Invalid Request");
  }

  const server = createTeachMeServer(bundle.teach_me_version);
  // No sessionIdGenerator: stateless mode, one server and transport per request.
  const transport = new WebStandardStreamableHTTPServerTransport({ enableJsonResponse: true });
  try {
    await server.connect(transport);
    return await transport.handleRequest(request, { parsedBody: body.value });
  } catch {
    return jsonRpcError(500, -32000, "Internal error");
  } finally {
    await server.close().catch(() => undefined);
  }
}

async function route(request: Request, env: Env): Promise<Response> {
  const { pathname } = new URL(request.url);
  const origin = request.headers.get("Origin");
  if (origin !== null && !isAllowedOrigin(origin)) {
    return json({ error: "forbidden_origin" }, 403);
  }

  if (pathname === "/.well-known/openai-apps-challenge") {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return json({ error: "method_not_allowed" }, 405, { Allow: "GET, HEAD" });
    }
    const token = env.OPENAI_APPS_CHALLENGE;
    if (typeof token !== "string" || token.length === 0 || token.length > 512) {
      return json({ error: "not_found" }, 404);
    }
    return new Response(request.method === "HEAD" ? null : token, {
      status: 200,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }

  if (pathname === "/") {
    if (request.method === "GET" || request.method === "HEAD") {
      const response = statusResponse();
      return request.method === "HEAD" ? new Response(null, response) : response;
    }
    return json({ error: "method_not_allowed" }, 405, { Allow: "GET, HEAD" });
  }

  if (pathname === MCP_PATH) {
    switch (request.method) {
      case "POST":
        return handleMcpPost(request);
      case "OPTIONS":
        return new Response(null, {
          status: 204,
          headers: {
            Allow: "POST, OPTIONS",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": corsAllowHeaders,
            "Access-Control-Max-Age": "600",
          },
        });
      default:
        // Stateless server: no standalone SSE stream (GET) and no sessions to terminate (DELETE).
        return jsonRpcError(405, -32000, "Method not allowed", { Allow: "POST, OPTIONS" });
    }
  }

  return json({ error: "not_found" }, 404);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    let response: Response;
    try {
      response = await route(request, env);
    } catch {
      response = jsonRpcError(500, -32000, "Internal error");
    }
    return withHeaders(response, request);
  },
} satisfies ExportedHandler<Env>;
