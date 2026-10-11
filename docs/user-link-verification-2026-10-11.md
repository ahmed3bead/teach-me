# User-link verification - 2026-10-11

Public links were checked without learner data. HTTP success establishes reachability, not successful account installation or complete product behavior.

| URL | Result |
|---|---|
| [https://github.com/ahmed3bead/teach-me](https://github.com/ahmed3bead/teach-me) | HTTP 200 |
| [https://github.com/ahmed3bead/teach-me/issues](https://github.com/ahmed3bead/teach-me/issues) | HTTP 200 |
| [https://github.com/ahmed3bead/teach-me/blob/main/docs/privacy-policy.md](https://github.com/ahmed3bead/teach-me/blob/main/docs/privacy-policy.md) | HTTP 200 |
| [https://github.com/ahmed3bead/teach-me/blob/main/docs/terms-of-use.md](https://github.com/ahmed3bead/teach-me/blob/main/docs/terms-of-use.md) | HTTP 200 |
| [https://teach-me-guide.pages.dev/](https://teach-me-guide.pages.dev/) | HTTP 200 |
| [https://teach-me-mcp.ahmedm3bead.workers.dev/](https://teach-me-mcp.ahmedm3bead.workers.dev/) | HTTP 200 |
| [https://teach-me-mcp-next.ahmedm3bead.workers.dev/](https://teach-me-mcp-next.ahmedm3bead.workers.dev/) | HTTP 200 |
| [ChatGPT listing](https://chatgpt.com/plugins/plugin_asdk_app_6ab81f50a2b881918abe2865d47fb2a3) | Browser inspection: Teach Me, version 1.0.0, Install plugin; sign-in required for installation |

## Guide correction

The Arabic guide returned HTTP 200 but still described the plugin as under review and disabled its installation links. The Arabic and English source pages now use the published listing directly in both buttons, including without JavaScript. Their publication text and `llms.txt` are updated. Direct Upload deployment completed on 2026-10-11. Post-deployment HTTP checks for the Arabic page, English page, and `llms.txt` returned 200, contained the public install URL, and contained no old pending-review text. Browser inspection of the Arabic guide confirmed both enabled install links and the available-now status.

## Test attachment

The original MIT-licensed [water-cycle PDF](../fixtures/submission/water-cycle.pdf) repairs the future submission case's missing attachment. Its public raw URL must be checked after merge; local PDF rendering and visual review succeeded.

## Limits

Independent-account installation, current ChatGPT conversation acceptance tests, and historical portal identity/domain/scan records remain unverified. No production MCP code or deployment is changed by these documentation and guide updates.
