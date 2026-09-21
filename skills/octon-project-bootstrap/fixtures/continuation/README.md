# Continuation Contract Fixtures

These source-only fixtures exercise the non-authorizing
`octon-mini.continuation.v1` contract. They are not generated project facts,
permission, accepted decisions, evidence, adoption, or readiness.

- `valid/blocked-operation.json` is a complete no-mutation refusal with one
  shell-free continuation and one safe read-only action.
- `invalid/mutations.json` identifies closed-contract mutations that must fail
  schema validation.
