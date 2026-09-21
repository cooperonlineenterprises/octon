# Octon Mini 4.0.0 to 4.1.0 disposable fixture

The executable test builds a pristine 4.0.0 snapshot from the annotated source
tag, proves that snapshot remains independently usable, then plans and applies
the reviewed 4.1.0 upgrade. It verifies dormant package routing, package absence,
explicit trigger state, stale reapply refusal, and exact rollback.

The fixture is synthetic migration evidence. It does not establish behavior
for a modified real project, package adoption, release status, or readiness.
