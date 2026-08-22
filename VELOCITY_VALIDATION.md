# Octon Mini 4.0 Velocity Validation

This report records local, content-free implementation evidence for the 4.0
velocity program. It is not target-project evidence, an adoption decision,
permission, or a readiness claim. Wall-clock results are host-specific.

## Measurement boundary

- Date: 2026-08-16
- Host: local macOS workspace, APFS, Python 3.14.0
- External effects: none
- Repository payload: disposable generated snapshots and synthetic small text
  files only
- Human elapsed-time estimates: modeled ranges, clearly separated from measured
  command time
- Profiles: Minimal, Standard, High Assurance
- Layouts: compact and separated
- Collaboration: solo, pair, tiny; concurrency tested as a separate modifier

Structural conformance, harness adoption, and target-project readiness are
reported separately throughout. No test supplies real project facts,
specialist conclusions, credentials, publication, deployment, or production
effects.

## Acceptance targets

| Measure | 4.0 target | Boundary |
|---|---:|---|
| valid compact scaffold, profile p90 | `<10 s` | structural check plus bounded fast mutations |
| read-only check at 10k synthetic files, p90 | `<2 s` | full structural check; hooks never run |
| fast mutation tier at 0–20k payload files, p90 | `<10 s` | bounded governed baseline independent of payload size |
| stale plan or evidence | deterministic refusal | no target mutation |
| interrupted transaction | write-ahead planned postimages, resumable rollback, and idempotent finalization permit exact recovery or fail closed | no force bypass |
| detector, plan, doctor, resume, check | unchanged target tree | read-only contract |
| covered refusal | stable Continuation Contract with concrete shell-free next argv | mutation outcome and preserved/invalidated proofs explicit |
| routine validation proof | hit only on exact current input/tool/config/instruction/environment/effect/freshness bindings | adoption/release gates prohibit reuse |
| local bundle | one atomic stage/receipt/rollback for compatible reversible members | overlap, authority/freshness mismatch, or external effect rejected |
| long-work context/status/resume/explain at 10k synthetic files, warm p90 | `<2 s` each | separate package benchmark; read-only, deterministic, no hooks |

Consequential guided init, adoption, upgrade, and release workflows stage the
release tier even though primitive scaffolding uses the bounded fast tier.

## Autonomous-delivery benchmark

`benchmark_autonomous_delivery.py` generates a disposable Minimal snapshot,
adds 10,000 inert payload files, and records one cold plus ten warm fresh-process
samples for delivery status, context, activation preview, resume, and
explanation. Each applicable warm p90 must remain below two seconds. The report
uses the documented nearest-rank percentile and retains every command failure,
sample, and host-specific limitation.

The benchmark executes no project hook, provider call, external effect,
standing-authority activation, or evidence mutation in the source tree. It does
not measure model quality, human usability, hosted latency, or external-effect
completion time. Existing scaffold, read-only check, bounded mutation,
long-running-work, and benchmark-v2 thresholds remain unchanged.

## Historical benchmark evidence and audit finding

The following three-sample evidence predates the version 2 benchmark method.
The final recorded run in that series passed every enforced threshold:

| Synthetic files | Refresh | Check p90 | Fast mutations p90 |
|---:|---:|---:|---:|
| 0 | 0.347 s | 0.200 s | 6.332 s |
| 2,000 | 1.057 s | 0.529 s | 6.512 s |
| 10,000 | 4.015 s | **1.876 s** | 6.982 s |
| 20,000 | 7.856 s | 3.615 s | 7.597 s |

Final compact scaffold p90:

| Profile | p90 | Target |
|---|---:|---:|
| Minimal | 6.907 s | pass (`<10 s`) |
| Standard | 7.813 s | pass (`<10 s`) |
| High Assurance | 9.624 s | pass (`<10 s`) |

The immediately preceding three-sample run identified one threshold miss
rather than being reclassified as success: High Assurance scaffold p90 was
10.442 s; Minimal was 7.526 s, Standard was 7.980 s, the 10k read-only check
was 1.952 s, and every bounded mutation sample remained below 10 s.

The post-rebrand audit then preserved two more results from identical enforced
version 1 invocations: one 10,000-file check p90 failed at approximately
**2.226 s**, and the immediate rerun passed at approximately **1.931 s**. The
failed result is not discarded and the passing result does not erase it. Their
variation is the benchmark-methodology finding that prompted version 2; neither
result is version 2 evidence or, by itself, proof that the finding is resolved.

Profiling traced the earlier High Assurance miss to repeated portable copies
of the isolated governed baseline. The mutation suite uses independent copies
that retain file contents, symlink identity, and modes without copying
timestamps or extended metadata that no harness contract consumes. It does
not use hardlinks or shared writable inodes. Full lifecycle
plan/apply/rollback and explicit adoption-verification journeys remain in the
generated release tier and the dedicated source integration suites; the
primitive scaffold gate retains structural validation and bounded mutation
tests rather than rerunning those full repository transactions for every
scaffold. This classification changes validation cost, not coverage or the
thresholds.

The bounded fast tier remained nearly flat from 0 to 20k synthetic payload
files. This replaces the prior full-tree mutation behavior observed during the
velocity audit, where a 2,071-file fixture took 28.48 s because repeated
mutation clones copied project payload.

A 10k-file routine work transaction measured 0.25 s to create its reviewed
plan and 10.59 s to stage, refresh, validate, apply, validate again, and receipt
the change. That cost is an explicit safety tradeoff of portable complete-tree
staging. It is acceptable as a current limitation, not a target for read-only
`check`; future optimization must preserve isolation and cannot use unsafe
hardlinks that could mutate the live tree through staged commands.

## Benchmark protocol version 2

`octon-mini.project.validation-benchmark.v2` separates first-observation and
steady-state behavior while preserving the existing performance thresholds.
Each independent invocation creates a fresh temporary root. For every timed
scaffold, check, and fast-mutation series, it records one first observation as
an `operational_cold_start_proxy`, followed by ten `warm_steady_state` measured
samples. The cold-start proxy describes first use in that fresh benchmark root;
it does not claim that operating-system, filesystem, interpreter, or hardware
caches were globally cold.

Every observed duration and its classification is retained in the report.
Implementations do not discard a slow value, replace a failed sample, retry a
measurement into a passing bucket, interpolate away an outlier, or report only
the aggregate. A failed subprocess fails the enforced run and remains visible
in its sample accounting.

Percentiles use the nearest-rank method: sort the applicable samples, compute
`ceil(0.90 × sample_count)`, and select that one-based rank. With ten warm
samples, `warm_p90_seconds` is the ninth ordered warm value. With the cold-start
proxy plus ten warm samples, `combined_p90_seconds` is the tenth ordered value
from all eleven observations. The cold-start proxy therefore remains visible
and participates in combined enforcement; it does not enter the warm-only
percentile. Reports state this calculation, the one-plus-ten sample
configuration, synthetic sizes, profiles, layout, thresholds, and enforcement
result.

Each report also records non-content host context needed to interpret wall-clock
evidence: operating system and release, architecture, Python implementation and
version, logical CPU count, performance-counter properties, load average when
available, and temporary-filesystem context that can be observed without
retaining project content. The report is content-free, grants no authority, and
remains host-specific rather than readiness evidence.

The enforced limits remain unchanged. Compact scaffold
`combined_p90_seconds` must be `<10 s` and its warm p90 is also reported. At
10,000 files, both combined and warm read-only-check p90 must be `<2 s`; at
every measured size, both combined and warm fast-mutation p90 must be `<10 s`.
Resolution of the audit finding requires at least three successful independent
enforced version 2 invocations, each from its own fresh temporary root. A limit
change still requires a separate recorded architecture decision and cannot be
used to conceal a regression.

## Benchmark version 2 remediation evidence

The first full version 2 run is retained as a failed result. All 129 expected
samples completed successfully, but High Assurance scaffold combined p90 was
`10.014 s` against the unchanged `<10 s` limit; its warm p90 was `9.963 s`.
The same report recorded a passing 10,000-file check combined/warm p90 of
`1.966 s`. Its complete report SHA-256 is
`d412a220c88a0cc31dbe22381381c21977b4001eec1732c7a4bf5242e2d5611d`.

Profiling showed that full lifecycle plan/apply/rollback and explicit adoption
verification dominated the primitive scaffold's fast tier even though those
whole-repository journeys already run in the generated release tier, velocity
suite, and acceptance suite. They were reclassified as full-tree integration
tests without removing them. The read-only check also computed the same source
file hashes twice for its fingerprint and manifest comparison; it now derives
both results from one identical ordered traversal. No threshold, validation
rule, package assertion, or source-fingerprint algorithm changed.

Three subsequent independent enforced invocations each created a fresh system
temporary root and passed all unchanged limits. Every run recorded exactly 129
of 129 successful samples: 11 operational cold-start proxies, 110 warm samples,
and eight preparation samples.

| Run | Minimal scaffold combined p90 | Standard scaffold combined p90 | High Assurance scaffold combined p90 | 10k check combined / warm p90 | Worst mutation combined / warm p90 | Report SHA-256 |
|---|---:|---:|---:|---:|---:|---|
| 2 | 3.855 s | 4.473 s | 5.978 s | 1.480 / 1.479 s | 4.493 / 4.493 s | `1afc21f73fb0bb01c6c6842e1c252a921057030d80bbb20b11e7c044f9f2857a` |
| 3 | 3.902 s | 4.487 s | 6.054 s | 1.543 / 1.543 s | 4.643 / 4.643 s | `bb9aa0c44425038b23a7423cd28222f8c178ff71bc16e96d48be5c64f6a9d220` |
| 4 | 3.939 s | 4.484 s | 6.202 s | 1.539 / 1.539 s | 5.172 / 5.140 s | `8b89653764ce52fd8de42328f683869531ca0bdd57f2c652693cb532ab798abc` |

These measurements ran on Darwin `25.5.0`, arm64, CPython `3.13.9`, on the
system temporary filesystem. The complete content-free JSON reports retain
every ordered sample, classification, exit status, load observation, host
context, filesystem context, configuration, accounting result, and enforcement
result. They remain host-specific local evidence and do not establish project
readiness.

## Executable validation matrix

| Boundary | Cases | Executable evidence |
|---|---|---|
| profile/layout generation | 3 profiles × compact/separated | `validate_octon_mini.py` profile builds |
| guided setup | init/adopt/upgrade, conversational/TTY/flag equivalence, immutable resume, staleness, work-completion prerequisites, target no-write | `test_guided_setup.py` |
| fail-closed continuation | typed source failures, human/JSON equivalence, no-change statements, dependency-scoped successors, decision reuse, interactive init/adopt/upgrade | `test_guided_setup.py`; cross-brand migration suite; generated mutation suite |
| guided creation | explicit Minimal, compact, solo facts, first task, plan/apply/resume | `test_velocity_workflows.py` |
| established adoption | dirty Git repository, low conflict apply, existing-byte preservation, exact collision refusal | `test_velocity_workflows.py`; `test_acceptance.py` |
| archetype detection | software/product, research, brand/non-software, operations/hybrid | `test_velocity_workflows.py` |
| collaboration | solo, pair, tiny, concurrent humans/agents, stale evidence | `test_velocity_workflows.py`; generated mutation suite |
| routine lifecycle | start, handoff, resume, direct evidence-bound close, reopen, rollback | generated release tests; `test_velocity_workflows.py` |
| concurrency safety | target-preimage conflict, instruction fingerprint, dirty tree, stable task allocation | transaction and velocity tests |
| hook configuration | shell-free argv, version probe, owner, side effects, selective routing, full adoption boundary | generated mutations; acceptance |
| evidence lifecycle | selected hook writes, immutable archive, current bounded index, stale evidence | generated mutations; acceptance |
| validation proof reuse | exact hits plus input/tool/configuration/environment/freshness misses; complete adoption gate | generated mutation suite; acceptance |
| local bundles | compatible apply/rollback; overlap, authority, freshness, external-effect refusals | `test_velocity_workflows.py`; generated transaction validation |
| registry maintenance | discovery, add, rename, combine, supersede, omission, stable-ID refusal | generated mutations; acceptance |
| packages | Git, operations/observability, security/supply-chain, sample restriction, Context Pack schema; digest/decision/receipt binding | acceptance package matrix |
| long-running work | absent-by-default routing, context, limits, progress, stuck detection, checkpoint faults, package lifecycle, adapter safety | dedicated long-running-work suites |
| live upgrade | reviewed 3.1 seed plus 4.0→4.1 three-way plan/review/apply, stale reapply refusal, rollback | migration suites |
| historical migrations | 1.0.1→2.0.0 and 2.0.0→3.0.0 valid/invalid/idempotence/rollback | migration fixture suites |
| recovery | invalid configuration, stale evidence, interrupted refresh, pending transaction, changed postimage | generated mutations; velocity and migration tests |
| scale | 0, 2k, 10k, 20k synthetic payload files | `benchmark_validation.py` |
| installer | collision-safe self-contained bundle and bundled source validation | `install_skill.py`; acceptance |

Sensitive or externally effective projects are exercised structurally through
High Assurance, conditional trigger contracts, package confinement, and
external-effect gates. Tests intentionally perform no credentialed, financial,
legal, publication, deployment, production, or destructive external action.

## Real-project evidence status

All evidence recorded above is synthetic or source-repository validation.
Human elapsed-time ranges below are modeled workflow estimates, not measured
human-study results. No completed real-project usability report is currently
recorded, and the absence of one is not converted into a pass.

`docs/REAL_PROJECT_VALIDATION.md` defines the source-only protocol and reusable
content-free report template for greenfield initialization, dirty-repository
adoption, non-software work, reviewed 3.1→4.0 migration, and an unfamiliar
operator when available. Pair and tiny exercises require actual reviewer
capacity. The protocol's presence creates no evidence, permission, adoption,
review, release disposition, or readiness claim.

## Before-and-after touchpoint model

These are workflow models, not measured human studies. A command is a user-run
invocation; a manual input is a distinct semantic value; files touched counts
hand edits, not transaction-generated files. Ranges reflect project ambiguity.

| Journey | Commands before → after | Manual inputs before → after | Project-owned decisions before → after | Files hand-edited before → after | Human elapsed estimate before → after |
|---|---:|---:|---:|---:|---:|
| new solo project through first task | 5–8 → 2 + resume | 12–20 → 11–14 | 4–7 → 3–5 | 4–8 → 0 | 15–40 min → 3–8 min review plus ~20 s machine work |
| established low-conflict adoption | 7–12 → 2 + final checks | 15–30 → 6–12 | 6–12 → 4–8 | 8–20 → 0 | 30–120 min → 5–25 min review plus staged apply |
| routine task start | 3–5 → 2 | 8–12 → 8 | 2–4 → 2–4 | 2–4 → 0 | 3–10 min → 1–3 min review plus apply |
| task close and handoff | 4–7 → 2 | 8–16 → 7–12 | 3–6 → 3–6 | 3–6 → 0 | 5–20 min → 2–6 min review plus apply |
| resume interrupted work | 3–7 → 1 | 0–6 → 0 | 0–2 → 0–1 | 0–3 → 0 | 2–15 min → under 1 s command plus reading |
| configure one project hook | 3–6 → 2 | 8–14 → 7–10 | 3–6 → 3–6 | 2–5 → 0 | 10–30 min → 3–10 min review plus apply |
| recover interrupted apply | ad hoc → 2 | unknown → journal path + reviewed action | unknown → 1 | unknown → 0 | unbounded → diagnosis plus deterministic restore/refusal |
| live upgrade | manual diff/reconcile → proposal, review, plan, apply | 20+ → conflict-dependent | unchanged substantive decisions | many → 0 automatic paths | hours/days → review-dominated, machine staging in seconds/minutes |

Automation does not reduce substantive decisions by inventing answers. The
after model removes file synchronization, ID allocation, derived-state edits,
integrity maintenance, and command discovery while retaining risk/profile,
authority, applicability, trust, review, evidence, and external-effect gates.

## Failure and fallback behavior

| Failure | Automatic behavior | Required recovery |
|---|---|---|
| explicit profile absent | refuse scripted generation | select a risk profile; interactive may propose Minimal |
| existing target content | route new-project init to adoption | run semantic adoption plan |
| functional equivalent or authority collision | emit proposal and review requirements | reconcile or disposition every current ambiguity |
| changed instruction/evidence/target after plan | emit typed no-mutation refusal | create an immutable successor plan and review its semantic delta |
| staged validation failure | restore/no target mutation | fix owned source or configuration and re-plan |
| interrupted live mutation | leave/write-ahead journal | exact recover; refuse independently changed paths |
| changed path after apply | refuse rollback | project-owned reconciliation or specialist recovery |
| stale collaboration or check evidence | withhold selection/adoption claim and refuse proof hit | gather current evidence explicitly |
| derived-only drift | doctor proposes exact repair digest | accept derived repair or run explicit refresh |
| project-owned invalid configuration | no automatic repair | owner decision and reviewed transaction |
| unknown legacy baseline | refuse seed/upgrade | supply reviewed old pristine hash or reconcile manually |

## Measurement plan

Every release candidate records JSON or table evidence for:

1. **Time to first valid scaffold:** one operational cold-start proxy plus ten
   warm steady-state samples per profile, compact default, plus
   all-profile/all-layout conformance builds.
2. **Time to first meaningful task:** guided init plan/apply with an explicit
   first task; report machine time separately from review time.
3. **Established-project adoption:** low-conflict and authority-collision
   fixtures, inspected-file bounds, unchanged pre-apply tree, and apply time.
4. **Task setup and closure:** plan and apply times on small, 2k, 10k, and 20k
   trees; transaction receipt v3 reports staging, refresh, staged validation,
   live apply, post-apply validation, and receipt preparation separately; the
   process reports receipt persistence and total time after the immutable write.
5. **Resume:** command time, bytes/lines returned, exact revision availability,
   and unchanged-tree result.
6. **Manual touchpoints:** commands, distinct semantic inputs, project-owned
   decisions, and hand-edited files for scripted usability exercises.
7. **Validation runtime/recovery:** one operational cold-start proxy plus ten
   warm steady-state samples, nearest-rank combined and warm check p90,
   fast/integration/release tiers, first actionable diagnostic, and successful
   recovery time.
8. **Automation success/fallback:** plans applied unchanged, stale plans,
   review-required proposals, automatic upgrade paths, manual conflicts, and
   rollback/recovery outcomes.
9. **Continuation recovery:** refusal-to-current-successor time, invalidated
    versus preserved input counts, repeated semantic inputs, concrete-next-argv
    execution success, and false preservation/invalidation findings.
10. **False positives:** detector candidates rejected by reviewers, invalid
   collision classifications, irrelevant diagnostics, and package triggers
   assessed non-applicable.
11. **Maintenance burden:** authoritative manifest edits per release, duplicate
    representations detected, source/derived drift, fixture update count, and
    runtime regression.
12. **Long-running work:** context/status/resume/explain cold and warm samples,
    exact limit admission, no-progress findings, checkpoint phase timings,
    resume time, storage growth, critical omissions, validation references, and
    duplicate-effect count. Benchmark-v2 remains separate and unchanged.

Content-free phase profiling may separately isolate tree traversal, hashing,
schema/semantic checks, transaction staging, staged validation, live apply,
post-apply validation, and receipt creation. Phase observations are
informational, overlap where disclosed, and do not change benchmark-v2 sample
accounting or thresholds.

Suggested release thresholds retain the current `<10 s` scaffold, `<2 s`
10k check, and `<10 s` fast mutation goals. A threshold change requires a
recorded architecture decision and must not conceal a regression.

## Risks, tradeoffs, and non-goals

- Complete portable transaction staging is slower at large file counts but
  preserves pre-write validation and rollback evidence. Unsafe shared-inode
  acceleration is explicitly rejected.
- Copy-on-write or reflink staging is a separately gated candidate, not a 4.0
  optimization. Before implementation, an Architecture Proof must establish
  write isolation, file/symlink/mode identity, unsupported-platform and
  cross-filesystem fallback, partial-clone cleanup, concurrent-mutation and
  interruption recovery, and cross-platform behavior. No such proof is
  currently recorded.
- Semantic detectors are bounded recipes, not complete project understanding;
  false negatives remain possible and candidates never self-adopt.
- Compact layout currently combines only the representation pair whose
  governance boundaries were reviewed as aligned. File-count reduction is not
  allowed to collapse semantic ownership.
- The dynamic 3.1 fixture validates migration mechanics but cannot prove every
  historical project has known pristine bytes. Real legacy baselines remain a
  review obligation.
- Human elapsed-time and unfamiliar-maintainer usability need repeated real
  project exercises; automation tests cannot establish them.
- Enterprise workflows, multi-level approvals, organization-wide governance,
  generic external-effect automation, credentials, deployment, publication,
  legal conclusions, and production readiness remain non-goals.

## Reproduction

```text
python3 -B skills/octon-mini-project-bootstrap/scripts/test_velocity_workflows.py
python3 -B skills/octon-mini-project-bootstrap/scripts/test_guided_setup.py
python3 -B skills/octon-mini-project-bootstrap/scripts/test_migration_3_1_0_to_4_0_0.py
python3 -B skills/octon-mini-project-bootstrap/scripts/validate_octon_mini.py
python3 -B skills/octon-mini-project-bootstrap/scripts/test_acceptance.py
python3 -B skills/octon-mini-project-bootstrap/scripts/profile_large_project.py \
  --sizes 0 2000 10000 20000
python3 -B skills/octon-mini-project-bootstrap/scripts/benchmark_validation.py \
  --sizes 0 2000 10000 20000 --samples 10 --enforce
python3 -B skills/octon-mini-project-bootstrap/scripts/benchmark_long_running_work.py \
  --payload-files 10000 --warm-samples 10 --enforce
```

Run the final benchmark command at least three independent times. Each
invocation creates a fresh temporary root; preserve every complete JSON report,
exit status, and stderr rather than retaining only passing aggregates.

Preserve the command, exit status, stdout/stderr, elapsed time, current source
revision, dirty-state disclosure, and host limitations for any published
release evidence.
