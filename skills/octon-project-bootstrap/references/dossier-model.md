# Dossier Model

Read the first available dossier definition:

- source checkout: `../../../dossier/SPECIFICATION.md`;
- installed bundle: `../assets/octon-source/dossier/SPECIFICATION.md`.

The essential rule is semantic separation:

- canonical target answers what should exist;
- current state answers what was observed;
- conformance compares the two;
- plans describe future work;
- evidence supports bounded claims;
- provenance describes source origin;
- handoff is a compact view;
- history is never current authority.

Use `authoritative`, `observed`, `inferred`, `proposed`, `derived`,
`historical`, `superseded`, `stale`, `unknown`, and
`intentionally_omitted` as information-role descriptions, not as a universal
status enum. Aggregate-specific lifecycles remain authoritative. No role grants
action permission or readiness, and consequential evidence states what it does
not prove.

Use three explicit ID levels: conceptual artifact-type IDs, `REP-####`
physical-representation IDs, and schema-governed project record IDs. They are
unique within their typed namespace and never silently reused. Prefer
structured requirements, findings, plans, sources, and evidence when the
standard or high-assurance profile applies.

Treat plan `depends_on` edges as hard `PLAN-####` prerequisites. Derive the
ready frontier from completed predecessors, passed or validly waived gates,
resolved structured blockers, populated acceptance/evidence contracts, and
reciprocal plan/task links. Dates remain provenance, freshness, expiry, or
explicit external constraints and never determine readiness or priority.

`machine-readable/artifact-registry.json` is the authoritative project-local
metadata source, initially seeded from the Octon Mini taxonomy. Maintain
artifact types, representations, source direction, applicability, ownership,
and substantive review state there. `ARTIFACT_CATALOG.json` and
`machine-readable/path-authority.json` are generated mirrors and must cover
every dossier file. Manifests, checksums, and validation reports are derived
point-in-time evidence and never independently edited truth.

A generation date is provenance, not a review or observation. Conditional and
optional conceptual types begin `not_assessed`; physical entry-point presence
does not establish applicability. A `not_applicable` type remains in the
registry with its dated assessor/rationale even after its representation is
removed. `combined` is a representation state and requires multiple
required/applicable artifact-type IDs.

Decision governance stays inside `DEC-0001`.
`.agent/decisions/governance-register.json` owns `DREG-####` question,
recommendation, owner-selection, review, compatibility, and minimum-closure
tracking. Accepted `.agent/decisions/DEC-####*.md` records alone own durable
accepted authority, and an accepted register entry links reciprocally with its
resolving durable record. Run non-negotiable option gates before balanced
scoring; failed gates disqualify and material unknowns remain evidence-first.

Requirement and gate maturity is a scoped evidence assessment from
`Architecturally specified` through `Production-proven`, not a universal
lifecycle. No structural check promotes it or implies a higher level.
