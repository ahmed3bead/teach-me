# Integration core

Use this reference for work that spans sessions, combines audience and source handling, or produces connected artifacts.

## One session, two axes

Represent the audience (`learner` or `educator`) independently from the input (`topic-led` or `source-grounded`). Do not discard learner evidence when adding a source, and do not discard source traceability when producing educator materials.

Maintain one `learning-session` as the coordination record. Link artifacts with stable identifiers:

`source_id -> objective_id -> lesson_id -> assessment_id -> progress record`

An artifact may link to several upstream records. References must resolve to an existing identifier in the same session; never silently create progress for an unknown objective.

## Unified flow

1. Establish the practical outcome, audience, language, constraints, and authorization boundaries.
2. Diagnose current ability with observable evidence when teaching a learner.
3. Inspect and map governing sources; otherwise research only as required by the evidence policy.
4. Define a small objective with prerequisites and explicit mastery evidence.
5. Create or deliver the lesson appropriate to the audience.
6. At the complete-unit boundary, offer an assessment and run it after learner opt-in. Source consumption and lesson completion are activity, not mastery evidence. If the learner declines, preserve the evidence state and continue only where the next objective does not depend on unverified mastery.
7. Update progress and a resumable checkpoint after evidence, a plan change, or a meaningful pause; schedule review only when it serves retention.
8. Collect minimized feedback at a meaningful checkpoint and apply the reviewed improvement loop.

## Objective contract

Every active objective must state:

- the observable capability the learner should demonstrate;
- prerequisite objective identifiers or a clear prerequisite description;
- source identifiers and precise locations when source-grounded;
- acceptable mastery evidence;
- current state and the smallest useful next action.

Objectives proposed by the agent must remain distinguishable from outcomes required by an educator or source.

## Resume protocol

At the end of a meaningful interaction, record a checkpoint containing the active objective, latest demonstrated state, evidence, unresolved misconception or blocker, strategy context, and next action. A scheduled review may include a due date, but never invent one after the fact.

On resume:

1. confirm the active goal and material context briefly;
2. load the last checkpoint and validate its linked identifiers;
3. use a light retrieval or application check when the elapsed time or uncertainty makes it useful;
4. continue from demonstrated ability, not from the amount of content previously shown;
5. state when no reliable checkpoint exists.

## Capability and access check

Before promising source analysis, record which components and tools are actually available. Route to full inspection, progressive inspection, an authorized-copy request, or an independent alternative. A capability limitation must narrow the claim, not merely appear as a disclaimer after the lesson.

## Claim ledger

Maintain `claim-ledger.json` for consequential, changing, disputed, or source-critical claims. Record the claim, status, supporting location, verification date when relevant, scope or version, and dependent objective identifiers. When a claim is corrected, identify and revisit affected objectives and lessons.

Do not burden stable elementary explanations with a claim ledger unless traceability materially improves trust.

## Artifact authority

- The learning session coordinates; it does not replace detailed artifacts.
- The researched knowledge base controls source selection, topic coverage, and teaching readiness.
- The source coverage ledger controls claims about what was inspected in a governing learner source.
- The curriculum map controls curriculum origin and educator approval.
- The lesson plan controls intended delivery, not demonstrated learning.
- The progress record controls demonstrated learning states.
- The claim ledger controls evidence status for important factual claims.

If artifacts conflict, do not overwrite silently. Surface the conflict, preserve the more authoritative evidence for that question, and request a decision when it changes the learning outcome.

When artifacts are saved, run `scripts/validate_session.py` against the learning session and any coverage, claims, lesson, or progress files before treating the checkpoint as reliable.
