# Octon Mini Release-Readiness Record

## 4.2.0 completed release

Octon Mini `4.2.0` was released on 2026-08-24 after separately authorized,
receipt-backed source delivery under accepted `SRC-DEC-0019`, `SRC-DEC-0020`,
and confirmed subscription-mode `SAC-02`.

| Field | Observed value |
|---|---|
| Record state | `completed_with_known_limitations` |
| Implementation / correction PRs | #21 / #22 |
| Final corrective candidate | `96d79099e5e84077565b0a9e91866084c62d50b0` |
| Exact released `main` | `22c1c142e42caa91edbf6550315c3938ff747c6f` |
| Tag | annotated `v4.2.0`; object `d5d67efea6105d9ec51eab3022420a49b3cf875c` |
| GitHub Release | `https://github.com/cooperonlineenterprises/octon-mini/releases/tag/v4.2.0` |
| Evidence policy | accepted `SRC-DEC-0020` disclosed-absence treatment |
| Package channel | `none`; GitHub-generated source archives only |
| Independent field maturity | `not_established` |

### Technical gate evidence

| Gate | Exact evidence | Result |
|---|---|---|
| Complete local validation | external manifest `f8d6f9ea…` | passed |
| Benchmark-v2 | 3 × 129 samples | 387/387 passed |
| Long-work benchmark | three 10k runs | all warm p90 <2s |
| Required PR check | run `32703858216` | passed on final candidate |
| Candidate matrix | run `32707378408` | 24/24 passed |
| Automatic integrated-main smoke | run `32714926981` | passed on released main |
| Integrated-main matrix | run `32715261752` | 24/24 passed |
| Migration / snapshot independence | source and installed-snapshot suites | passed |
| Tag / Release read-back | immutable effect receipts | exact target; final Release |

Worst local p90 was 9.019s scaffold, 1.397s for the 10k read-only
check, and 9.958s for bounded mutation. The mutation result passed the
unchanged 10s threshold with narrow headroom and remains disclosed.

Failed predecessor run `32681230721`, the post-merge evaluator-ordering stop,
the initially absent integrated-main dispatch route, monotonic read-back
continuations, and the GitHub API rate-limit pause remain retained. Every
reproducible implementation defect became a bounded regression fixture.

Unavailable unfamiliar-operator, independent-reviewer, independent external-
project, and human-usability evidence remains disclosed. This release does not
establish target-project adoption, independent maturity, usability, project
readiness, production readiness, or efficacy.

## 4.1.0 completed release

## Status and authority boundary

This source-only record is subordinate to the release gate in `RELEASE.md`.
It did not create release authority, permission, package adoption, a readiness
claim, or a target-project result. It records the observed 4.1.0 release after
separately authorized external actions.

Octon Mini `4.1.0` was released on 2026-08-22. Feature-branch evidence was not
substituted for final integrated-main evidence.

| Field | Observed value |
|---|---|
| Record state | `completed_with_known_limitations` |
| Accepted architecture | `SRC-DEC-0018` |
| Implementation / correction PRs | #18 / #19 |
| Final corrective candidate | `242ef4c496cc8fc95a7b550371beeb01bb4a6513` |
| Exact released `main` | `6d1cfb0f13d300b9d4b78bf7078cf07daa7febd6` |
| Tag | annotated `v4.1.0`; object `1df893ec42ac2c49e5944268cafec30757d06430` |
| GitHub Release | `https://github.com/cooperonlineenterprises/octon-mini/releases/tag/v4.1.0` |
| Evidence policy | `accept_disclosed_absence` |
| Package channel | `none`; GitHub-generated source archives only |
| Independent real-project maturity | `not_established` |

## Technical gate evidence

| Gate | Exact evidence | Result |
|---|---|---|
| Complete local validation | exact candidate manifest outside source tree | passed |
| Long-work benchmark | three sequential 10k runs | passed; all warm p90 <2s |
| Benchmark-v2 | three sequential runs × 129 samples | 387/387 passed |
| Required PR check | run `32536899162`, job `96939428330` | passed on exact candidate |
| Candidate hosted matrices | run `32536929040` | 12/12 source + 12/12 acceptance passed |
| Automatic integrated-main smoke | run `32540532990`, job `96949540754` | passed on exact released main |
| Integrated-main hosted matrices | run `32540555019` | 12/12 source + 12/12 acceptance passed |
| Released 4.0→4.1 migration | exact released-tag fixture | passed; dormant and unadopted |
| Generated-snapshot independence | source/profile/install/migration tests | passed |
| Ambiguous-effect fixture | local read-back work-completion case | passed; no duplicate effect |

## Performance evidence

| Measurement | Worst p90 | Unchanged threshold | Result |
|---|---:|---:|---|
| High Assurance compact scaffold | 9.028s | <10s | pass |
| 10k read-only check combined/warm | 1.616s | <2s | pass |
| Fast mutation combined/warm | 7.788s | <10s | pass |
| Long-work context | 1.787s | <2s | pass |
| Long-work status | 0.129s | <2s | pass |
| Long-work resume | 0.647s | <2s | pass |
| Long-work explain | 0.136s | <2s | pass |

## Retained failed evidence and corrections

1. Required run `32493638662` failed because shallow checkout lacked published
   tag `v4.0.0`; tag-aware checkout and its regression assertion followed.
2. Automatic main run `32514424886` was cancelled at the former 15-minute
   smoke ceiling; bounded smoke was corrected to 45 minutes and final run
   `32540532990` passed in about 15 minutes.
3. Candidate matrix `32523125576` passed eleven jobs and cancelled
   Windows/Python 3.13 when sequential source plus acceptance exceeded the
   unchanged 90-minute whole-job bound. Final CI preserves the same checks and
   combinations as separate source and acceptance matrices; no limit was
   raised. Candidate and integrated runs then passed all 24 jobs.

Every available failed log is retained in an external SHA/run-named evidence
directory. No failed hosted run was retried on the same SHA to obtain a pass,
and no failed sample or threshold was discarded.

## Real-project and human evidence

Disposable greenfield software, dirty adoption, non-software context pressure,
migration, interruption, changed authority, repeated failure, no-progress,
budget, orphan/corrupt-state, package lifecycle, and safe local
ambiguous-effect exercises passed.

The following remain `not_run` or unavailable:

- unfamiliar operator and human usability timing;
- eligible independent reviewer or genuine human pair/tiny team;
- independently authorized external real project;
- actual historical project supplied by an owner; and
- real provider/credential effect.

The owner selected `accept_disclosed_absence`. This preserves the limitations;
it does not convert them to passing evidence or establish field maturity.

## Published distribution

| External action | Observed result | Boundary |
|---|---|---|
| Annotated tag | `v4.1.0` targets exact `6d1cfb0f…` | never move the published tag |
| GitHub Release | published 2026-08-22; latest, final, no uploaded assets | source archives only |
| Separate package | none | no registry/channel exists |
| Deployment | none | not part of this release |

Structural validation, implementation, merge, tag, and Release publication do
not establish target-project adoption, worker authority, project readiness,
production readiness, legal conclusions, or efficacy.
