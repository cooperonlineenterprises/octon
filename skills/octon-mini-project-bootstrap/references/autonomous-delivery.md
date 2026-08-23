# Autonomous Delivery

Use this reference when discovering, drafting, activating, deactivating,
operating, recovering, or upgrading governed autonomous delivery.

## Before activation

`octon delivery research|context|assess|plan|status|explain|activation-preview`
is read-only, runs no project hook, writes no receipt, and creates no authority.
The status is `available_not_activated`; writes and external effects are locked.

## Activation

Choose `review_first`, `balanced_autonomous`, `fast_delivery`, or `custom` as a
preset. `fast_delivery` is normally recommended for solo developers but is not
selected automatically. Select exactly one compute mode: `metered_api` with
host-enforced per-run and authorization-period ceilings, or
`included_subscription` with current readable provider-enforced included
allowance only. Draft the full contract from exact repository, branch, action,
release, limits, compute, evidence, validity, revocation, and stop inputs. Show
every field and SHA-256 digest. Only an independent human exact-
digest confirmation can supply authority. Store its immutable evidence outside
the repository, then plan/apply package activation through the existing
transaction boundary and an accepted project adoption decision.

No flag can substitute for confirmation. A more-permissive contract requires a
confirmed successor. A successor uses a new stable `SAC-##` ID, binds the exact
predecessor, and cannot activate until the operator-controlled predecessor
revocation is serialized from the confirmed records. Upgrade never renews or
broadens authority.

## Effects and recovery

Use work completion for commit, push, PR, checks, merge, synchronization, and
cleanup. Use the delivery adapter only for exact workflow dispatch, annotated
tag, tag push, GitHub source Release, and read-back. Revalidate current
standing evidence and live state before each effect.

Transactions may restore exact local preimages. Public effects are monotonic:
persist attempted state, execute once, read back, receipt, reconcile, and fix
forward. Never replay `outcome_unknown`.

The external host must enforce the selected compute mode. Unknown metered cost
blocks. Unreadable, exhausted, or changed subscription allowance blocks;
separately purchased credits, API/pay-as-you-go billing, add-ons, and upgrades
are prohibited. All purchases and direct external spending remain prohibited.
