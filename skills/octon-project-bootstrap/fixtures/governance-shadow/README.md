# Governance shadow fixture

`covered.json` contains synthetic intent, work references, two narrowing
delegations, policy/usage/evidence observations and one technical action. No
principal, grant, task, result or evidence here is a real project record.

The fixture is source-only and never emitted into a generated project. Its fixed
year-2030 evaluation time is hypothetical. Even its covered result sets execution
authority, permission grant and reservation creation to false.

`scripts/test_governance_shadow.py` derives adverse cases without changing these
canonical fixture bytes. Tests include binding/lineage errors, narrowing in every
scope dimension, revocation, stale observations, shared/cumulative run budgets,
qualified-human obligations, unknown facts, malformed input, read-only behavior
and legacy/generation compatibility. They qualify declared coverage semantics,
not issuer authentication, sandboxing, atomic reservation or live authority.
