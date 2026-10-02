# Durable protected controller-container fixture

This source-only successor extends the [protected fixture](PROTECTED_FIXTURE_QUALIFICATION.md)
to actual committer-container destruction and replacement. It admits one exact
existing-task handoff under the user's disposable qualification invocation. It
issues no real grant, activates no consumer, and changes neither the unpublished
5.0 identity boundary nor kernel 4.2 behavior. Current principal reservations,
qualified-human obligations and repository/consumer contracts remain applicable.
This is partial fixture evidence, not completion of IMP-1/IMP-2.

## Owners, versions and selection

The existing disposable qualifier owns packaging. Its explicit
`--durable-fixture-qualification` also requires `--disposable-qualification`,
`--admission-qualification` and `--protected-fixture-qualification`. Ordinary
generation stays inactive. The closed `durable-fixture-inventory.json` registers
the durable facet, non-secret standalone producing client and schema. The parent
installation stays v2 and the protected facet stays v1. The additive
`octon.durable-fixture-profile.v2` binds that entire parent, three assets, four
exact source inputs, source revision and retained dependencies. The selector
refreshes/checks the complete overlay before placement. Existing/symlinked
inputs/outputs, missing assets and mixed/unsupported profiles refuse.

`durable_fixture.py` extends the existing authorization and transaction/evidence
owners; `governance_shadow.py` remains the sole coverage evaluator. Currentness
requests use v3; producing-peer, consumption and publication references have
explicit separate schemas. Historical readers, schemas, bytes and grant meanings
remain retained. The continuity index contains canonical record references,
challenges and fence/time continuity; it owns no task purpose, grant copy or
reservation ledger. No accepted decision ID is allocated.

## Supported replacement and custody

The supported profile is `linux-durable-controller-replacement-v2`, on the
existing Docker engine with this immutable image index:

```text
python@sha256:4d1caded1f729ae443eb803f26ffde7b61e696aeaef62f099abb6dd6b14257c7
```

Actual controller/committer containers and PID namespaces are destroyed/replaced.
The **original independently current keeper process/container, original trusted
launch handle, owned named volumes, stable fence and same engine kernel boot
remain dependencies**. Keeper replacement, engine restart, host reboot, power
loss, complete trusted-anchor rollback and launch-handle loss/rollback are not
qualified. Missing currentness retires affected execution; saved keys/signatures,
self-consistent hashes or fresh epochs cannot bootstrap it. Initial-launch
credential bytes travel through the once-consumed live channel, never saved or
exported. Fresh keys/areas cannot reset an existing stopped fixture after marker
loss. Restoring the index against its live tip or stale controls refuses.

| Custody | Actual owner/mount boundary |
|---|---|
| Canonical project/transactions | Root-private `/state/target`, owned kernel named volume; committer RW and keeper verifies actual record bytes. Controller keys stay outside the project in root-private `/state/controllers`. |
| Issuers/enrollment/controls | `/authority` named volume, keeper only; absent from controller mounts. |
| Current reference tip/keeper key | `/continuity` named volume, keeper only; live current tip/incarnation retained outside restored files. |
| Serialization/channel | `/ipc` named volume, keeper RW/committer RO; protected socket and stable fence inode, no private key. |
| Worker | Own tmpfs proposals/workspace, UID/GID65534, no groups/capabilities, no-new-privileges, separate session, clean exec, closed inherited descriptors/stdio and no surviving signing key. |
| Verifier/baseline | Protected copied runtime/manifest and enrolled complete durable profile; worker policy cannot replace them. |

Named-volume kernel DAC is tested on existing files before/after actual
replacement. Writable host binds remain disqualified: actual probes permitted
writes despite reported root ownership/mode. There is no writable host bind,
network, Docker socket, host PID namespace, privileged container or extra host
access. Trusted root has only CHOWN, SETUID, SETGID, SETPCAP and KILL. Opt-in markers
are misuse guards, not host attestation. Trusted root/Docker/host administrators
and verifier compromise are excluded. Separately observed Linux arm64/amd64
evidence supplies no macOS/Windows enforcement parity.

The peer uses actual socket credentials and exact immutable fixture
actor/action/intent/plan. It cannot select issuer, policy, scope or recovery. This
is fixture identity, not production principal authentication. A root-owned
immutable non-secret tmpfs client permits clean exec without exposing canonical
code; copied producer operation is tested with `/source` absent. Controller
identity/generation/key and actual PID namespace are launch-pinned. Copied launch
files in fresh unenrolled containers refuse; old processes cannot load new authority.

The original keeper retains actual kernel PID namespace descriptors, including
superseded enrollments. A narrow original-pin keeper helper signs the exact fresh
enrollment/CAS subject; the already-ready intended controller forwards its own
`/proc/self/ns/pid` via the existing protected Unix channel. Exactly one SCM_RIGHTS
descriptor, NS_GET_NSTYPE and fstat/link identity must match the signed launch.
Retained non-inheritable handles prevent object disappearance/inode reuse during
the keeper lifetime. JSON namespace numbers alone never establish enrollment.
Missing/truncated/extra/wrong-type/identity descriptors and lost retained handles
refuse; no setns, SYS_ADMIN, new witness or key export is used. Keeper teardown
closes descriptors; keeper/all-anchor loss remains outside supported recovery.

## Ordering and publication

One stable cross-container EX flock covers the transaction. Control/replacement
handlers wait for flock before the keeper mutex; holder currentness/publication/ACK
handlers use the short mutex without recursively waiting on flock. Explicit
contention barriers queue control before the holder's next RPC. A control change
acknowledged after release orders after that transaction; it cannot instantly
reverse a committed effect.

Every protected primitive performs current signed keeper evaluation and exact
binding/generation/storage checks, then a minimal trusted-time dispatch gate
immediately before rename, exclusive publication, unlink or permitted directory
operation. No callback, RPC, signing or fsync intervenes between that final gate
and the primitive. This is dispatch linearization, not kernel-atomic wall-clock
expiry or hard real-time enforcement during arbitrary trusted suspension.
Multi-file writes are journaled, not one filesystem-atomic commit.

| Window | Observable boundary |
|---|---|
| Before admission/effect | Current stop/revocation/expiry, policy, state, enrollment or dependency mismatch refuses. |
| Prepared but record missing/truncated | Durable intention quarantines the identity; no fabricated record or retry as a new action. |
| Published, directory/ACK incomplete | Current replacement verifies actual exact bytes/schema/signatures/lineage/postimages and syncs file/directory ancestry before reference ACK. |
| Confirmed, response lost | Reconcile original identity/unchanged receipt; no effect replay or provenance rewrite. |
| Partial local writes | Current-authority recovery accepts only original before/postimages; changed/expanded paths retain uncertainty/journal. |
| Journal unlink/tombstone interrupted | Exact terminal proof and exact retained journal archive are required; confirm actual absence and sync ancestry. Missing/corrupt archives refuse. |
| Bounded mock attempt, unknown response | Original attempt observation and one actual mock invocation stay unknown. Replacement never invokes again; original reconciliation is still necessary. Local rollback is not external compensation. |

Consumption and journal ACK precede task mutation. File data and directory
ancestry are synchronized. Immutable exact-byte journal/receipt/recovery archives
remain under the transaction owner with append-only causal references, including
lawful rollback status transitions. Historical archives authenticate provenance;
they are never execution tokens and do not require old postimages to remain live.
Consumption and terminal/history deletion are forbidden.

Time uses UTC plus the original monotonic origin and nondecreasing floor; new
controllers cannot choose a new origin. Actual expiry progresses against unchanged
grant/control bytes. Backward-time, unavailable-time and new-boot faults are
modeled refusal; actual clock administration/reboot/power loss are unqualified.
Successful fsync/container replacement proves only the declared retained-engine
scenario.

## Qualification and remaining gates

`test_durable_fixture.py --qualify-owned-durable-fixture` owns disposable resources
and emits only public evidence. Subsets are `targeted_passed`, never a qualified
complete profile. Complete qualification binds exact unchanged source, all cases
and verified cleanup. Failures, aborts or unknown engine/resource outcomes prevent
qualification. Actual SIGKILL targets committer containers; an owned driver SIGTERM
tests registry/finally cleanup. Driver SIGKILL/lost engine/host cleanup are not
claimed. Non-production keys stay protected in owned stores until exact-resource
removal is verified; no global prune or secure-erasure claim is made.

The qualifier compiles an immutable keyless seed once per suite through the
existing packaging owner. Only rendered source runtime/templates/schemas and
empty initial generation metadata are reused. The launch handle independently
pins the exact source, actual image and full file/mode inventory; self-consistent
seed metadata is insufficient. Seed custody is a read-only owned kernel volume,
with confinement/corruption/project-record refusals. Every case still creates
four fresh stores, new project facts/start receipt/plan/context, trusted ticket,
current keeper, keys, clocks, controls and actual namespace-FD enrollment.
Authority/evaluator/verifier/fence/postimage/recovery checks are never cached.

An internal monotonic40-minute deadline starts before seed/case preparation,
reserving bounded cleanup and public-export time before the unchanged45-minute
hosted job cap. Cleanup commands have bounded waits and a120-second total margin;
unavailable observations remain UNKNOWN. Completed case/owned-cleanup checkpoints
are append-only public partial evidence, always incomplete/nonqualified and never
containing tickets, keys or signed enrollment envelopes. Only the final complete
source-bound all-case report may qualify. A prior hard-cancelled job with no final
cleanup proof remains a failed/unknown historical attempt even after later success.

Local gates, independent review and fresh hosted evidence remain separate. The
existing 24 cross-platform matrix jobs and retained protected fixture are mandatory.
The durable job runs on PR/manual qualification; required PR always explicitly
rejects either fixture's failed/skipped/cancelled result. No failed check is waived.

See the [assessment projection](AGENT_FIRST_ASSESSMENT_REGISTER.md) and
[sole sequencing/IMP owner](OEP1_IMPLEMENTATION_PLAN.md). A concrete exact PR,
qualification report/integration brief and final independent assessment precede
separate merge authorization. Live grants/adoption, consumer conversions,
multi-run accounting, broader profiles, ChangeSets, releases and deployments stay
outside this sequence.
