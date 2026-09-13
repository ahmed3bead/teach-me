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

Packs inherit the teaching, evidence, privacy, and safety contracts from the core skill. They may narrow those contracts for a domain but cannot weaken them. Validate manifests, concept dependencies, guides, and pack evals with `python3 scripts/validate_domain_packs.py`.

## Implemented pilots

- `programming`: executable prediction, debugging, testing, and project evidence.
- `photography`: available-equipment visual practice, cause-specific critique, and safe capture.

Both pilots are marked `needs-qualified-review`; they demonstrate and test the pack contract but must not be presented as fully reviewed curricula.

## Layout

```text
domain-packs/
└── programming/
    ├── PACK.md
    ├── pack.yaml
    └── evals.yaml
```

## Acceptance criteria

A pack is ready only when it succeeds with beginners and experienced learners, produces a real learner activity, checks transfer rather than acknowledgement, cites consequential claims correctly, and passes Arabic and English evaluation cases.
