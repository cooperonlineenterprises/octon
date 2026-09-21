# 4.1.0 to 4.2.0 Migration Fixture

The executable test generates an exact snapshot from annotated `v4.1.0`, adds
bounded project evidence, plans and reviews the current three-way upgrade,
applies it, verifies dormant autonomous delivery and both offline payloads,
proves read-only status leaves the target unchanged, rejects inferred standing
authority, and rolls the exact transaction back to 4.1.0.

This fixture uses no provider, credential, external project, or runtime
authorization and establishes no readiness claim.
