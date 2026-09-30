# Governance shadow fixture

`covered-v2.json` contains synthetic intent, work references, two narrowing
delegations, policy/usage/evidence observations and one technical action. No
principal, grant, task, result or evidence here is a real project record.

The fixture is source-only and never emitted into a generated project. Its fixed
year-2030 evaluation time is hypothetical. Even its covered result sets execution
authority, permission grant and reservation creation to false.

`covered.json` is the retained v1 input; `covered-v1-result.json` records the exact
old result reproduced by the reader, schema and dependencies at `360a8db`.
The v1 schema/input/result bytes remain unchanged and cannot qualify v2. Default
evaluation rejects v1 and mixed versions; no automatic converter is provided.
Intent/delegation/action definitions remain v1. The source-only v2 control
observations explicitly declare occupancy, coherent same-run accounting and
period interval/inclusion facts; they do not change active grant contracts.

`scripts/test_governance_shadow.py` derives adverse cases without changing the
fixture bytes. Tests include binding/lineage errors, narrowing in every
scope dimension, revocation, stale observations, shared/cumulative run budgets,
qualified-human obligations, unknown facts, malformed input, read-only behavior
exact-run occupancy, component-wise ancestor inclusion, incomparable period
refusal, and legacy/generation compatibility. They qualify declared coverage semantics,
not issuer authentication, sandboxing, atomic reservation or live authority.
