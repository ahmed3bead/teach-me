# Teach Me landing page

Static bilingual landing and usage guide for ordinary ChatGPT users.

- Arabic page: `dist/index.html`
- English page: `dist/en/index.html`
- Social preview: `dist/og.png`
- Search metadata: canonical URLs, language alternatives, JSON-LD, `robots.txt`, and `sitemap.xml`
- AI discovery: explicit `OAI-SearchBot` access and a concise `llms.txt` capability summary
- Platform hardening: security and cache rules in `dist/_headers`, plus a branded `404.html`
- Privacy: no analytics, cookies, forms, or external runtime dependencies

The Arabic and English install buttons point to the approved public ChatGPT listing, including without JavaScript. Keep the links and `PLUGIN_DIRECTORY_URL` aligned with `docs/published-release.json`. Deploy changes to this Direct Upload site explicitly; merging Git does not update the hosted guide.

The current Cloudflare Pages project uses Direct Upload:

```powershell
node ..\mcp\node_modules\wrangler\bin\wrangler.js pages deploy dist --project-name teach-me-guide --branch main --commit-dirty=true
```
