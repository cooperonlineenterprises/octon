# Decision-governance fixtures

These fixtures are domain-neutral and non-authorizing.

- `valid/empty-register.json` is the valid generated baseline. It proves only
  that an empty register can be represented without fabricating a decision.
- `invalid/mutations.json` is the negative mutation pack. Each named mutation
  is instantiated against a populated valid register by
  `.agent/tests/test_validate.py`; the generated validator must emit the
  recorded diagnostic fragment.

The suite covers dashboard/sheet mismatch, owner selection presented as
accepted, accepted state without authority, evidence-first work without a stop
condition, decision cycles, a gate failure hidden by scoring, duplicated
balanced attributes, a missing trade-off review, absent dependencies, material
unknowns not preserved as evidence-first, and completed closure without
evidence. Additional tests cover handoff contradictions, maturity overclaims,
exact references, and no-write review behavior.

Fixtures contain no project fact, owner selection, accepted authority, or
readiness conclusion.
