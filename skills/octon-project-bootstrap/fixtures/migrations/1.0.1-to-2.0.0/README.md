# 1.0.1 to 2.0.0 executable migration fixtures

These fixtures exercise the breaking task, plan, lifecycle, project-command,
validator, and origin contracts introduced by Project Blueprint 2.0.0. They
are reference migration evidence, not target-project facts, authority,
approval, project-check evidence, or readiness.

`valid/v1-standard.json` is a closed representative 1.0.1 live-state bundle.
It deliberately contains legacy mixed-purpose relationship arrays. The
`classification` section explicitly separates hard prerequisites from
reciprocal task/plan links and advisory relationships before any v2 record is
created. `valid/expectations.json` records the stable IDs and semantic results
asserted by the isolated tests. The project-command classifications also show
three distinct outcomes: preservation as unassessed, an explicitly supplied
argv-style configured assessment, and a justified not-applicable assessment.
The migrator never derives argv from a legacy string and never runs project
commands. A configured v1 command string therefore fails closed.

Files under `invalid/` are mutation descriptors. Each names the valid base,
one or more deterministic mutations, and the failure text expected from the
fail-closed migrator. They cover unclassified relationships, v1/v2 live-state
mixing, category confusion, nonreciprocal links, cycles, and non-external
migration authority. They also cover mixed project/validator authority,
legacy configured command strings, and unsafe inline-shell argv assessments.
They also reject a version probe that names an executable different from the
configured command, so unrelated tool output cannot be cited as its version.
An adopted v1 project without current v2 check evidence also fails closed;
the migrator neither demotes nor carries forward that readiness claim.

Run from the repository root:

```text
python3 -B skills/project-bootstrap/scripts/test_migration_1_0_1_to_2_0_0.py
```

Read-only validation of the valid fixture:

```text
python3 -B skills/project-bootstrap/scripts/migrate_1_0_1_to_2_0_0.py \
  --input skills/project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/valid/v1-standard.json \
  --check
```

Writing a migrated result always requires a new explicit destination. The
migrator refuses in-place changes and existing output paths. Its embedded
rollback material retains the exact input bytes and parsed v1 live state as
noncurrent evidence. Restoring those bytes remains a separately authorized
project action and must restore all v1 live contracts together.
Because the output contains an exact copy of its input, it inherits the
input's sensitivity, access, and retention requirements. New output files are
created with owner-only permissions where the operating system honors POSIX
file modes.
