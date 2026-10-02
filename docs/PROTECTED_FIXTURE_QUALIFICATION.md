# Protected Linux fixture, effect fencing and controller recovery

This source-only successor qualifies one explicitly invoked disposable fixture.
It admits one existing `TASK-0001` handoff through the existing authorization
evaluator and transaction engine. It creates no production grant, consumer
adoption, source decision, runtime release or autonomous integration authority.
Current accepted decisions, genuine human obligations, kernel 4.2 and the
identity-only unpublished 5.0 boundary still govern ordinary consumers.

## Canonical owners and versions

The existing disposable qualifier owns packaging. Its new opt-in
`--protected-fixture-qualification` requires `--admission-qualification` and
`--disposable-qualification`. Ordinary profile generation remains inactive for
these semantics. The additional closed source inventory is
`shared/source-contracts/protected-fixture-inventory.json`; it pins the protected
facet and schema. The parent manifest remains disposable-installation **v2**.
The additional `octon.protected-fixture-profile.v1` binds that entire parent
manifest, every extra asset and source input. This is an explicit additive
fixture successor, rather than a v3 installation or a legacy grant conversion.
The selector refreshes and checks the complete staged overlay before placement;
its immediate copied `octon check` must pass. Existing or symlinked facet inputs
and outputs refuse before copying.

`protected_fixture.py` is a facet of the existing admission and transaction
owners. It delegates staging, plan checks, exact local paths, rollback and
recovery to the existing copied transaction engine. `governance_shadow.py`
remains the sole coverage evaluator. Existing v1 signed observations retain
their historical meaning. The separate closed protected request/effect **v2**
records bind fencing generation, control generation/digest, protected profile,
exact original action and transaction lineage. No old signed response is an
execution token. Historical admission/installation readers and schemas remain
available, with unchanged meanings.

The canonical task/DEC/evidence owners retain their original records. New
protected transaction observations and consumed identities live under the
existing `.octon/agent/transactions/` concern. The authority anchor retains
hashes of those records as recovery high-water evidence; it does not create a
second editable task graph, authorization ledger or accounting/reservation
service. No source decision ID is allocated.

## Supported host and worker threat boundary

The supported profile is `linux-disposable-container-distinct-uid-v1`, using an
existing Docker engine and the immutable official Python image index:

```text
python@sha256:4d1caded1f729ae443eb803f26ffde7b61e696aeaef62f099abb6dd6b14257c7
```

The container has no network, a read-only root and source mount, no Docker socket,
and an explicitly owned `nosuid,nodev,exec` temporary filesystem. Its trusted
fixture supervisor has only CHOWN, SETUID, SETGID, SETPCAP and KILL. The worker starts
a separate session, clears all supplemental groups and environment, closes
every inherited nonstdio descriptor, drops the complete capability bounding
set, becomes UID/GID 65534 and sets no-new-privileges. Qualification requires all
five capability fields to be zero and probes existing protected files, process
memory/environment/descriptors, ptrace, process signals including SIGCONT,
clock setting and privilege escalation. The trusted process is nondumpable.

All writable canonical, authority, worker and evidence custody uses kernel tmpfs.
An actual Docker Desktop writable host-bind probe allowed the worker to modify
a result file despite apparent root ownership/mode; that route is unqualified
and the profile refuses it. The final profile has no writable host mount. Worker
stdio is disconnected to `/dev/null`. After every owned worker/controller has
terminated, the trusted qualifier exports only sanitized public evidence through
Docker stdout; this report transport never accepts an authorization command.
The private PID namespace belongs to this one qualification invocation. Scoped
CAP_KILL and a process subreaper terminate and reap all UID65534 descendants,
including a tested forked, detached, nondumpable orphan, before export. Cleanup
uses kernel status UID fields; proc inode ownership can differ for nondumpable
processes. A bounded cleanup failure refuses export. Docker removal closes the
ephemeral environment afterward. No host PID namespace or additional host access
is supplied to the container.
The top-level qualifier, namespace cleanup and enrollment require the dedicated
PID1 supervisor; child controllers retain the enrolled PID namespace identity
and cannot invoke namespace-wide cleanup or replace their own enrollment.

Worker proposals and its own actor key are confined to its writable workspace.
Canonical state, issuer keys, controls, verifier/evaluator and acceptance
baseline are in root-owned directories with private traversal permissions.
Trusted code is copied from the protected inventory, never imported from a
producer-selected working directory or PYTHONPATH. A Unix socket checks the
actual connecting UID with SO_PEERCRED and verifies the enrolled actor's
Ed25519 signature. A newly generated worker key cannot enroll itself. The socket
accepts only an exact original action and the immutable trusted command allowlist;
it exposes no issuer enrollment, policy replacement or control update operation.

The marker and `/.dockerenv` check prevent accidental ordinary execution; they
are not cryptographic host attestation. This boundary excludes a malicious host,
Docker/CI administrator, root supervisor or trusted executor. Issuer secrets are
written directly by OpenSSL to protected ephemeral files, never loaded into the
fork parent's Python values or handed to worker descriptors. UID separation is
not a general guarantee against secrets already copied into a forked parent's
address space. No macOS/Windows security parity is claimed. Native macOS
sandbox-exec remained unavailable in the qualification environment.

## Effect ordering and expiry

A stable protected flock inode serializes control updates, controller enrollment
and the entire trusted local transaction. The lock is never replaced during
controller recovery. An updater demonstrably contending with an admitted
transaction waits until that transaction releases the fence. Its completed
revocation/stop therefore orders after those earlier effects; it cannot promise
instantaneous reversal or interruption. A separate trusted termination can kill
the controller, releasing the fence and leaving its journal for reconciliation.

At each canonical mutation, the executor checks current generation, controls,
the unchanged full action/plan/source/task/expected-state/policy/installation/
intent/delegation/footprint bindings and required coverage. Staged bytes and
fsync finish before the final current time check. The effect dispatch
linearization point is that final check immediately followed by the protected
primitive, with no producer callback, barrier, transport or disk write between
them. Replace/delete paths use the existing primitives; new JSON metadata is
staged privately and atomically published with Linux `renameat2(NOREPLACE)` to
preserve the existing owner's exclusive-create semantics. Journals, receipts,
authority observations, restoration and cleanup share the same fence.

Trusted time is the maximum of current host wall time and the enrollment wall
time plus elapsed kernel monotonic time, with a retained nondecreasing floor and
kernel boot identity. Backward wall-clock adjustment cannot extend the modeled
lease. A new boot or missing continuity refuses execution. Expiry is evaluated
at every effect dispatch; expiry before admission or between writes refuses the
next mutation. If implicit restoration is then unauthorized, the pending journal
and consumed identity remain. This dispatch semantics belongs only to the new
fixture; it does not reinterpret historical grant deadlines. Physical clock
advance and rename are not a single kernel operation: hard real-time deadlines
under arbitrary trusted-process suspension and privileged clock manipulation
remain unqualified.

Policy/state/ownership changes before the fence are re-evaluated. Control changes
arriving after admission wait for the held fence. A stale controller cannot act
after its replacement is enrolled. Local writes during a transaction are not an
atomic multi-file filesystem operation; their protected serialization and
journal enable exact bounded recovery. Already committed effects are recorded
and never represented as instantaneously reversed by a later stop.

## Restart, restoration and uncertainty

Only the trusted fixture authority path may enroll a replacement controller and
issuer. It CAS-checks the current control digest and generations, increments the
ownership generation, retains all prior issuer public keys for historical
verification, and preserves current revocation/stop/grant bytes. Generating a
new key itself supplies no authority. A still-present old controller is rejected.
Bootstrap first claims an exclusive canonical authority-owner binding under the
existing protected transaction concern. It binds the root, retained authority
area, profile and PID namespace, and stays outside every transaction rollback
footprint. A fresh area/key cannot re-enroll a stopped root, even if its anchor
is missing. Incomplete bootstrap and a missing owner binding preserve uncertainty;
the supervisor's refusal cache prevents recreating a lost claim within this
qualification lifetime. Full supervisor/storage restoration remains unsupported.

The retained authority store includes the lock identity, boot/time continuity,
current enrollment and transaction history hashes. An independently retained
supervisor checkpoint binds the complete current anchor. Restorable controller
snapshots exclude that checkpoint and the fence. Actually copying an older
controller/control anchor back while retaining the checkpoint refuses, including
same-boot restoration. Stale control CAS and attempts to remove a stop/revocation
also refuse. A receipt restored with old matching postimages cannot replace the
retained terminal record high-water after rollback. A mismatch never reconstructs
or narrows history from an older snapshot.

Consumed identities are written before canonical effects and survive controller
restart. A lost response reconciles the existing receipt and its exact postimages;
apply cannot reuse the identity. SIGKILL after journal creation, after a partial
local write and after all local effects but before receipt publication leaves
the original pending journal. Under current authority, the existing owner restores
only the original before/after footprint and records `recovered_to_preimage`.
An exact persisted receipt can instead be finalized. Forged footprints, altered
postimages, unsigned/altered historical evidence, stale controllers and missing
journals refuse. Revoked, expired or stopped recovery retains uncertainty and
does not restore grant validity.

This qualifies controlled process replacement within one retained disposable
container/boot. Full authority-store/checkpoint restoration, arbitrary kill
between checkpoint writes, storage loss, container destruction and power-loss
durability remain unqualified and fail closed when continuity is unavailable.
Ephemeral tmpfs keys are removed when the disposable container is removed;
SIGKILL alone does not establish secure key erasure. External providers remain
mocked. Local restoration is not external compensation, and an unknown external
outcome has no replay path here. Accounting remains synthetic single-fixture
coverage; unknown usage or mandatory obligations refuse. No multi-run reservation
or live accounting implementation is supplied.

## Qualification and integration boundary

```text
docker run --rm --network none --cap-drop ALL \
  --cap-add CHOWN --cap-add SETUID --cap-add SETGID --cap-add SETPCAP --cap-add KILL \
  --security-opt no-new-privileges --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,exec,size=512m \
  --tmpfs /evidence:rw,nosuid,nodev,size=64m \
  -e OCTON_OWNED_EPHEMERAL_CONTAINER=protected-fixture-v1 \
  -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0=/source \
  -v /absolute/candidate:/source:ro -w /source \
  python@sha256:4d1caded1f729ae443eb803f26ffde7b61e696aeaef62f099abb6dd6b14257c7 \
  python -B skills/octon-project-bootstrap/scripts/test_protected_fixture.py \
  --qualify-linux-container --output /evidence/qualification.json --emit-evidence
```

The explicit test runs real UID exclusion, signed narrow requests and denials,
nonblocking lock-contention proof, pipe barriers, actual SIGKILL, real clock
crossing at admission and between canonical writes, copied executor operation
under `-I`, history preservation, snapshot restoration, version/dependency and
path refusal. Synthetic historical TASK/DEC/EVD records are fixture seeds, not
new accepted source decisions. Summary output retains their hashes and canonical
journal/receipt/evidence hashes without private keys. Portable invocation without
the explicit container flag reports consequential execution disabled.

The existing validate workflow adds `protected Linux fixture` for PR and dispatch;
the required PR gate depends on it. All 24 existing cross-platform matrix jobs
remain mandatory for the unchanged ordinary contracts. Local protocol, local
Linux host enforcement, hosted Linux execution and independent review are
separate evidence subjects. A source PR still needs current base/composition,
trusted check issuers, all mandatory checks and independent exact-candidate
assessment. Merge requires separate user authorization; this fixture does not
activate real grants, broader consumers, IMP-1/IMP-2, Plectarium or general autonomy.
