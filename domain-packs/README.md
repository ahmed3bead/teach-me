# Domain teaching packs

A teaching pack specializes **how to teach and assess** a domain. It is not a copied course, a list of facts, or a replacement for the core `teach-me` skill.

Each pack lives in `domain-packs/<domain>/PACK.md` and should define:

- who the pack serves and which goals it does not cover;
- a prerequisite and concept map;
- diagnostic tasks that reveal actual ability;
- suitable practice formats and authentic projects;
- common misconceptions and recovery strategies;
- observable mastery and transfer evidence;
- source hierarchy and facts that require fresh verification;
- safety, accessibility, age, language, and tooling considerations;
- bilingual terminology where useful;
- reproducible evaluation cases.

Packs inherit the teaching, evidence, privacy, and safety contracts from the core skill. They may narrow those contracts for a domain but cannot weaken them.

## Proposed layout

```text
domain-packs/
└── programming/
    ├── PACK.md
    ├── concept-map.yaml
    ├── terminology.ar-en.yaml
    └── evals.yaml
```

## Acceptance criteria

A pack is ready only when it succeeds with beginners and experienced learners, produces a real learner activity, checks transfer rather than acknowledgement, cites consequential claims correctly, and passes Arabic and English evaluation cases.
