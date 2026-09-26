import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

import worker from "../dist/worker.js";

const BASE = "https://teach-me-mcp.example.test";
const MCP = `${BASE}/mcp`;
const PROTOCOL_VERSION = "2025-11-25";
const MAX_BODY_BYTES = 64 * 1024;
const runtimeBundle = JSON.parse(
  await readFile(new URL("../generated/teach-me-runtime.json", import.meta.url), "utf8"),
);

const env = new Proxy(
  {},
  {
    get(_target, property) {
      throw new Error(`worker accessed env binding ${String(property)}`);
    },
  },
);

function call(request) {
  return worker.fetch(request, env, { waitUntil() {}, passThroughOnException() {} });
}

function mcpHeaders(extra = {}) {
  return {
    "Content-Type": "application/json",
    Accept: "application/json, text/event-stream",
    "MCP-Protocol-Version": PROTOCOL_VERSION,
    ...extra,
  };
}

function post(body, headers = {}) {
  return call(
    new Request(MCP, {
      method: "POST",
      headers: mcpHeaders(headers),
      body: typeof body === "string" || body instanceof Uint8Array ? body : JSON.stringify(body),
    }),
  );
}

function initializeMessage(id = 1) {
  return {
    jsonrpc: "2.0",
    id,
    method: "initialize",
    params: { protocolVersion: PROTOCOL_VERSION, capabilities: {}, clientInfo: { name: "test", version: "0.0.0" } },
  };
}

function toolCall(args, id = 7, name = "load_teach_me") {
  return { jsonrpc: "2.0", id, method: "tools/call", params: { name, arguments: args } };
}

function assertSecurityHeaders(response) {
  assert.equal(response.headers.get("X-Content-Type-Options"), "nosniff");
  assert.equal(response.headers.get("Referrer-Policy"), "no-referrer");
  assert.equal(response.headers.get("Cache-Control"), "no-store");
  assert.equal(response.headers.get("Cross-Origin-Resource-Policy"), "cross-origin");
  assert.match(response.headers.get("Permissions-Policy"), /camera=\(\)/);
  assert.match(response.headers.get("Content-Security-Policy"), /default-src 'none'/);
  assert.equal(response.headers.get("Set-Cookie"), null);
}

async function assertJsonRpcError(response, status, code) {
  assert.equal(response.status, status);
  assertSecurityHeaders(response);
  const body = await response.json();
  assert.equal(body.jsonrpc, "2.0");
  assert.equal(body.error.code, code);
  assertNoDebugDetails(JSON.stringify(body));
  return body;
}

function assertNoDebugDetails(text) {
  assert.doesNotMatch(text, /\bat [\w.<>]+ \(|stack|node_modules|[A-Za-z]:\\|\/home\/|\/sessions\/|\/Users\//);
}

async function connectedClient() {
  const client = new Client({ name: "teach-me-protocol-test", version: "0.0.0" });
  const transport = new StreamableHTTPClientTransport(new URL(MCP), {
    fetch: (input, init) => call(new Request(input, init)),
  });
  await client.connect(transport);
  return client;
}

test("GET / returns public status without learner data", async () => {
  const response = await call(new Request(`${BASE}/`));
  assert.equal(response.status, 200);
  assertSecurityHeaders(response);
  const body = await response.json();
  assert.deepEqual(body, {
    service: "teach-me-mcp",
    status: "public-beta",
    mcp_endpoint: "/mcp",
    transport: "streamable-http",
    teach_me_version: runtimeBundle.teach_me_version,
    bundle_digest: runtimeBundle.bundle_digest,
    privacy: "No learner data is stored. The server is read-only, stateless, and never calls a model.",
  });
});

test("unknown routes return 404 and unsupported methods return 405 with Allow", async () => {
  for (const path of ["/favicon.ico", "/mcp/", "/sse", "/mcp/extra"]) {
    const response = await call(new Request(`${BASE}${path}`));
    assert.equal(response.status, 404, path);
    assertSecurityHeaders(response);
  }
  for (const method of ["POST", "PUT", "DELETE"]) {
    const response = await call(new Request(`${BASE}/`, { method }));
    assert.equal(response.status, 405, method);
    assert.equal(response.headers.get("Allow"), "GET, HEAD");
  }
  for (const method of ["GET", "DELETE", "PUT", "PATCH"]) {
    const response = await call(new Request(MCP, { method, headers: mcpHeaders() }));
    assert.equal(response.status, 405, method);
    assert.equal(response.headers.get("Allow"), "POST, OPTIONS");
    assertSecurityHeaders(response);
  }
});

test("initialize negotiates protocol and returns concise host instructions", async () => {
  const response = await post(initializeMessage());
  assert.equal(response.status, 200);
  assertSecurityHeaders(response);
  assert.equal(response.headers.get("Mcp-Session-Id"), null, "server must stay stateless");
  const body = await response.json();
  assert.equal(body.result.protocolVersion, PROTOCOL_VERSION);
  assert.deepEqual(body.result.capabilities, { tools: {} });
  assert.equal(body.result.serverInfo.name, "teach-me-mcp");
  assert.equal(body.result.serverInfo.version, runtimeBundle.teach_me_version);
  const instructions = body.result.instructions;
  assert.ok(instructions.length <= 512, `instructions are ${instructions.length} characters`);
  assert.match(instructions.slice(0, 512), /call load_teach_me/);
  assert.match(instructions.slice(0, 512), /follow the returned canonical guidance/);
});

test("SDK client connects and lists exactly one read-only tool with explicit schemas", async () => {
  const client = await connectedClient();
  const { tools } = await client.listTools();
  assert.equal(tools.length, 1);
  const [tool] = tools;
  assert.equal(tool.name, "load_teach_me");
  assert.deepEqual(tool.annotations, {
    title: "Load Teach Me guidance",
    readOnlyHint: true,
    destructiveHint: false,
    idempotentHint: true,
    openWorldHint: false,
  });
  assert.equal(tool.inputSchema.type, "object");
  assert.equal(tool.inputSchema.additionalProperties, false);
  assert.deepEqual(tool.inputSchema.required ?? [], []);
  assert.deepEqual(tool.inputSchema.properties.audience.enum, ["learner"]);
  assert.deepEqual(tool.inputSchema.properties.input_mode.enum, ["topic-led"]);
  assert.deepEqual(tool.inputSchema.properties.locale.enum, ["en", "ar-MSA", "ar-EG"]);
  assert.deepEqual(tool.inputSchema.properties.guidance_modules.items.enum, ["topic-led-conversational"]);
  assert.equal(tool.outputSchema.type, "object");
  assert.deepEqual(tool.outputSchema.required, ["ok"]);
  assert.equal("$schema" in tool.inputSchema, false);
  await client.close();
});

test("English tools/call returns adapter result and model-readable guidance", async () => {
  const client = await connectedClient();
  const result = await client.callTool({ name: "load_teach_me", arguments: { locale: "en" } });
  assert.notEqual(result.isError, true);
  const structured = result.structuredContent;
  assert.equal(structured.ok, true);
  assert.equal(structured.teach_me_version, runtimeBundle.teach_me_version);
  assert.equal(structured.bundle_digest, runtimeBundle.bundle_digest);
  assert.equal(structured.normalized_request.requested_locale, "en");
  assert.equal(structured.host_contract.server_calls_llm, false);
  assert.equal(structured.host_contract.server_side_learner_persistence, false);
  assert.equal(structured.selected_modules.some((module) => module.id === "arabic-teaching-style"), false);

  const [content] = result.content;
  assert.equal(content.type, "text");
  assert.ok(content.text.includes(runtimeBundle.teach_me_version));
  assert.ok(content.text.includes(runtimeBundle.bundle_digest));
  assert.match(content.text, /## Host responsibilities/);
  for (const module of structured.selected_modules) {
    const canonical = runtimeBundle.assets.find((asset) => asset.id === module.id);
    assert.equal(module.content, canonical.content);
    assert.ok(content.text.includes(canonical.content.trimEnd()), `text includes ${module.id}`);
    assert.ok(content.text.includes(canonical.sha256));
  }
  await client.close();
});

test("Arabic tools/call selects Arabic teaching guidance", async () => {
  const client = await connectedClient();
  const result = await client.callTool({ name: "load_teach_me", arguments: { locale: "ar-MSA" } });
  assert.equal(result.structuredContent.ok, true);
  assert.equal(result.structuredContent.normalized_request.requested_locale, "ar-MSA");
  const arabic = result.structuredContent.selected_modules.find((module) => module.id === "arabic-teaching-style");
  assert.ok(arabic);
  assert.match(arabic.content, /[؀-ۿ]/);
  assert.match(result.content[0].text, /[؀-ۿ]/);
  await client.close();
});

test("legacy ar-EG locale normalizes to ar-MSA through the adapter", async () => {
  const client = await connectedClient();
  const legacy = await client.callTool({ name: "load_teach_me", arguments: { locale: "ar-EG" } });
  const modern = await client.callTool({ name: "load_teach_me", arguments: { locale: "ar-MSA" } });
  assert.equal(legacy.structuredContent.normalized_request.requested_locale, "ar-MSA");
  assert.equal(legacy.structuredContent.normalized_request.locale_strategy, "explicit");
  assert.deepEqual(legacy.structuredContent.selected_modules, modern.structuredContent.selected_modules);
  await client.close();
});

test("invalid tool input returns safe structured adapter errors", async () => {
  const client = await connectedClient();
  const cases = [
    [{ locale: "fr" }, "unsupported_locale"],
    [{ audience: "educator" }, "unsupported_audience"],
    [{ input_mode: "source-grounded" }, "unsupported_input_mode"],
    [{ guidance_modules: [] }, "empty_guidance_modules"],
    [{ guidance_modules: "topic-led-conversational" }, "invalid_field_type"],
    [{ transcript: [{ role: "user", content: "private learner text" }] }, "unknown_field"],
  ];
  for (const [args, code] of cases) {
    const result = await client.callTool({ name: "load_teach_me", arguments: args });
    assert.equal(result.isError, true, code);
    assert.equal(result.structuredContent.ok, false);
    assert.equal(result.structuredContent.error.code, code);
    assert.match(result.content[0].text, new RegExp(code));
    assertNoDebugDetails(JSON.stringify(result));
    assert.doesNotMatch(JSON.stringify(result), /private learner text/);
  }
  await client.close();
});

test("unknown tool is a JSON-RPC invalid params error without echoing input", async () => {
  const response = await post(toolCall({}, 9, "delete_everything"));
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.id, 9);
  assert.equal(body.error.code, -32602);
  assert.equal(body.error.message.includes("delete_everything"), false);
});

test("malformed JSON, invalid JSON-RPC, and wrong headers fail safely", async () => {
  await assertJsonRpcError(await post("{not json"), 400, -32700);
  await assertJsonRpcError(await post("\"just a string\""), 400, -32600);
  await assertJsonRpcError(await post("[]"), 400, -32600);
  await assertJsonRpcError(await post({ id: 1, method: "tools/list" }), 400, -32600);
  await assertJsonRpcError(await post(new Uint8Array([0x7b, 0xff, 0x7d])), 400, -32700);
  await assertJsonRpcError(await post({ jsonrpc: "2.0", id: 1 }), 400, -32700);
  await assertJsonRpcError(await post(initializeMessage(), { "Content-Type": "text/plain" }), 415, -32000);
  await assertJsonRpcError(await post(initializeMessage(), { Accept: "application/json" }), 406, -32000);
  await assertJsonRpcError(
    await post({ jsonrpc: "2.0", id: 2, method: "tools/list" }, { "MCP-Protocol-Version": "1999-01-01" }),
    400,
    -32000,
  );
});

test("request body size limit is enforced before processing", async () => {
  const oversized = JSON.stringify({ ...initializeMessage(), padding: "x".repeat(MAX_BODY_BYTES) });
  await assertJsonRpcError(await post(oversized), 413, -32600);

  const declared = await call(
    new Request(MCP, {
      method: "POST",
      headers: mcpHeaders({ "Content-Length": String(MAX_BODY_BYTES + 1) }),
      body: "{}",
    }),
  );
  await assertJsonRpcError(declared, 413, -32600);

  const chunk = new TextEncoder().encode("x".repeat(16 * 1024));
  let sent = 0;
  const stream = new ReadableStream({
    pull(controller) {
      sent += chunk.byteLength;
      controller.enqueue(chunk);
      if (sent > MAX_BODY_BYTES * 4) {
        controller.close();
      }
    },
  });
  const streamed = await call(
    new Request(MCP, { method: "POST", headers: mcpHeaders(), body: stream, duplex: "half" }),
  );
  await assertJsonRpcError(streamed, 413, -32600);
  assert.ok(sent <= MAX_BODY_BYTES + 2 * chunk.byteLength, "reader stopped soon after the limit");
});

test("repeated calls are byte-for-byte deterministic", async () => {
  const first = await (await post(toolCall({ locale: "ar-MSA" }))).text();
  const second = await (await post(toolCall({ locale: "ar-MSA" }))).text();
  assert.equal(first, second);
  const firstDefault = await (await post(toolCall({}))).text();
  const secondDefault = await (await post(toolCall({}))).text();
  assert.equal(firstDefault, secondDefault);
});

test("every response carries security headers and origin policy is enforced", async () => {
  const responses = [
    await call(new Request(`${BASE}/`)),
    await call(new Request(`${BASE}/missing`)),
    await call(new Request(MCP, { method: "GET" })),
    await post(initializeMessage()),
    await post(toolCall({ locale: "en" })),
    await post("{bad"),
  ];
  for (const response of responses) {
    assertSecurityHeaders(response);
  }

  const forbidden = await post(initializeMessage(), { Origin: "https://attacker.example" });
  assert.equal(forbidden.status, 403);
  assertSecurityHeaders(forbidden);
  assert.equal(forbidden.headers.get("Access-Control-Allow-Origin"), null);

  const allowed = await post(initializeMessage(), { Origin: "http://localhost:6274" });
  assert.equal(allowed.status, 200);
  assert.equal(allowed.headers.get("Access-Control-Allow-Origin"), "http://localhost:6274");

  const preflight = await call(new Request(MCP, { method: "OPTIONS", headers: { Origin: "https://claude.ai" } }));
  assert.equal(preflight.status, 204);
  assert.equal(preflight.headers.get("Access-Control-Allow-Origin"), "https://claude.ai");
  assert.match(preflight.headers.get("Access-Control-Allow-Headers"), /Mcp-Protocol-Version/);
});

test("no outbound fetch, env binding access, cookies, or learner persistence", async () => {
  const originalFetch = globalThis.fetch;
  let outbound = 0;
  globalThis.fetch = () => {
    outbound += 1;
    throw new Error("outbound fetch is not allowed");
  };
  try {
    await call(new Request(`${BASE}/`));
    await post(initializeMessage());
    const privateText = "learner secret: my exam is on Monday";
    const response = await post(toolCall({ locale: "en", transcript: privateText }));
    const text = await response.text();
    assert.equal(text.includes(privateText), false);
    const after = await (await post(toolCall({ locale: "en" }))).text();
    assert.equal(after.includes(privateText), false);
  } finally {
    globalThis.fetch = originalFetch;
  }
  assert.equal(outbound, 0);

  const wrangler = await readFile(new URL("../wrangler.jsonc", import.meta.url), "utf8");
  for (const binding of [
    "kv_namespaces",
    "d1_databases",
    "r2_buckets",
    "durable_objects",
    "queues",
    "analytics_engine_datasets",
    "services",
    "vectorize",
    "hyperdrive",
    "ai",
    "vars",
  ]) {
    assert.doesNotMatch(wrangler, new RegExp(`"${binding}"`), `wrangler config declares ${binding}`);
  }
  assert.match(wrangler, /"observability":\s*\{\s*"enabled":\s*false\s*\}/);
});

test("worker sources use only Web-standard runtime APIs", async () => {
  for (const file of ["worker.ts", "server.ts", "config.ts", "adapter.ts"]) {
    const source = await readFile(new URL(`../src/${file}`, import.meta.url), "utf8");
    assert.doesNotMatch(source, /from\s+["']node:|require\(|\bprocess\.|\bBuffer\b|__dirname/, file);
    assert.doesNotMatch(source, /(?<!async )\bfetch\s*\(|\bconsole\.|caches\.|localStorage|indexedDB|express/i, file);
  }
});
