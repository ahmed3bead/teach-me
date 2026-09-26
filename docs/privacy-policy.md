# Teach Me privacy policy

Effective date: 2026-09-17

Teach Me is an open-source teaching plugin maintained by Ahmed Ebead. Its skills-only editions run entirely inside the selected host. An optional public remote MCP connector serves the same versioned teaching guidance from a Cloudflare Worker. Teach Me has no account system, advertising service, payment system, or learner API key.

## Data handling

Teach Me processes the messages and files that a learner chooses to provide through the host conversation. The skills-only package does not transmit that content to Ahmed Ebead or to a developer-operated service. The optional remote MCP connector accepts only bounded routing selectors such as language and teaching mode; it does not require or accept learner transcripts, files, credentials, or personal data. It returns public teaching instructions, stores no learner state, uses no analytics or cookies, and has application-level Worker observability disabled. Cloudflare may still process ordinary network metadata needed to deliver and protect the service under its own terms. The host platform may process and retain conversations according to its own terms, privacy policy, account settings, and product controls.

The current MCP endpoint is `https://teach-me-mcp.ahmedm3bead.workers.dev/mcp`. Do not send learner content to it. If a future version accepts user-specific data or performs actions, this policy and the connector's authentication and consent flow must be updated before that version is enabled.

Do not submit passwords, API keys, financial credentials, unnecessary personal information, private learner transcripts, or material you are not authorized to use. When age affects safety or teaching, Teach Me should ask for an age band rather than a birth date.

Teach Me does not create or claim a persistent learner record unless the learner explicitly requests one and the host clearly supports a private artifact. Availability of memory, files, browsing, and other capabilities depends on the host.

## External sources

When host-provided browsing is available, Teach Me may consult external sources to support current or specialized claims. Opening those sources is subject to the source website's own privacy practices.

## Changes and contact

Material changes will be recorded in the public repository. Report privacy or security concerns through [GitHub Private Vulnerability Reporting](https://github.com/ahmed3bead/teach-me/security/advisories/new). For other privacy questions, open a minimized public issue that contains no personal or confidential information.
