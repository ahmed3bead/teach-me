# Learner model

Maintain a provisional model, not a permanent profile. Every inference must be correctable.

## Useful fields

- desired outcome and motivation;
- current demonstrated abilities and missing prerequisites;
- time, tools, budget, and accessibility constraints;
- preferred language: `ar-MSA`, `ar-EG`, `en`, or a natural mix;
- terminology already introduced;
- strategies that helped or failed, with context;
- confidence compared with observed performance;
- mastery evidence and scheduled review;
- next smallest useful action.

## Update rules

- Base ability estimates on observable work, not self-rating alone.
- Store the evidence behind each mastery state.
- Downgrade confidence when later performance contradicts it.
- Do not infer protected or sensitive attributes.
- Do not store full conversations when structured progress is sufficient.
- Let the learner view, correct, export, or delete the profile.
- Record why a persistent profile exists, when consent was captured, its retention deadline or review point, and deletion state. Expired or deletion-requested profiles must not be used for adaptation.
- When execution is available, run `scripts/profile_lifecycle.py status` before loading a persistent profile. Renewal requires fresh purpose-specific consent. A deletion request blocks use immediately; permanent deletion requires the exact profile identifier and removes the profile file.
- Use `scripts/session_manager.py record-evidence` where available so progress state is derived from evidence type, support, outcome, task identity, and time. A `retained` state requires a different successful unsupported retrieval at least 24 hours after prior independent evidence; hosts may choose a longer interval.
- Use pseudonymous identifiers for group observations and never use a group record to infer a sensitive trait about an individual.

## Continuity

At a new session, briefly confirm the active goal and resume from the last demonstrated state. Do not repeat onboarding unless the goal or context materially changed. If no reliable record exists, say that and perform a light re-check.
