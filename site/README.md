# Teach Me landing page

Static bilingual landing and usage guide for ordinary ChatGPT users.

- Arabic page: `dist/index.html`
- English page: `dist/en/index.html`
- Social preview: `dist/og.png`
- Search metadata: canonical URLs, language alternatives, JSON-LD, `robots.txt`, and `sitemap.xml`
- AI discovery: explicit `OAI-SearchBot` access and a concise `llms.txt` capability summary
- Platform hardening: security and cache rules in `dist/_headers`, plus a branded `404.html`
- Privacy: no analytics, cookies, forms, or external runtime dependencies

The primary install button stays in a pre-launch state until the approved public Plugins Directory URL is available. After approval, set `PLUGIN_DIRECTORY_URL` near the end of both HTML pages.

The current Cloudflare Pages project uses Direct Upload:

```powershell
node ..\mcp\node_modules\wrangler\bin\wrangler.js pages deploy dist --project-name teach-me-guide --branch main --commit-dirty=true
```
