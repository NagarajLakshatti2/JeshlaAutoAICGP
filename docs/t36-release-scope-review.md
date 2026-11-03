# T36 — release scope decision, 3 November 2026

## Accepted T36 scope — 3 November 2026

**Y — the user-approved limited local browser/Python release.** The user explicitly chose option B and requested T36 closure. The accepted trusted local milestone is complete. Existing P/X tasks keep their statuses; no public/native-installer/general production or multi-agent release is certified. Earlier pending/full-release/scope-choice text below is dated history and is superseded for T36 by this explicit limited-scope decision. Do not rerun already accepted checks or add gates to this closed milestone. Completion evidence: outputs/acceptance/t36-local-release-completion-20261103/completion.md/json. Counts: **Y 11 | P 20 | X 6 — total 37.**

**Review complete. T36 remains P until the existing scope decision is made.** No requirements, task IDs or acceptance gates were added. No source edit, tests, installation, model request, Git operation or policy change ran during this review.

## Already accepted

The trusted local-user development preview was already accepted; it does not need the same approval again. Existing core setup, selected pinned CI/fresh-clone/Python-module launch evidence, and scoped feature acceptances retain Y. Current task scopes accepted Y: T01/T03/T04/T08/T09/T14/T17/T21/T22/T23. T20 also has accepted text/verified-PNG/ZIP implementation and user-confirmed ZIP delivery, with other binary formats still P.

These records have specific dates/revisions and limits. In particular, the 23 October ead9aa8 CI/clone records do not certify the latest 3 November working source as a new full release. Focused recent checks remain separate, not summed into a new all-feature regression claim. This review does not order repeated tests or a new install.

## Existing full-release dependencies — no new gates

| Existing group | Existing boundary |
| --- | --- |
| T32 / WS2 | User-parked local Ollama acceptance, if retained in the agreed full scope. Do not resume automatically. |
| T06/T07/T34 | Overlapping semantic/hybrid/optional-profile native runtime and broader quality acceptance. One shared runtime cause must not be treated as repeated separate fixes. Applies to included profiles. |
| T05 / WS4 | Wider factual/source-coverage quality acceptance, already parked. Conservative guards are implemented; universal answer correctness is not established. |
| T33 | Native Windows installed launcher requires an approved signing/build route. The accepted Python-module/browser startup is not reopened. |
| T35 | Historical repository privacy/publication decision. No publication, history rewrite or visibility change is authorized here. |

T26 is the separate existing WS9 release gate, with its own repair/mobile scope. Deferred UI redesign/naming, T31 multi-agent development and optional capabilities are not newly added to T36 by this review.

## The decision

**A — Keep full release as the finish line.** Keep T36 P, preserve current local-preview acceptance, and resume only the existing prerequisites when their blockers/parked scope change. No extra development is created by this choice.

**B — Use the bounded local development release as T36's finish line.** Explicitly change T36's completion scope to the trusted single-user local browser/Python-module release and its already accepted feature scopes. This permits closing T36 for that limited milestone only. It does not certify a public/enterprise/native-installer release, every model/browser/device, arbitrary binary generation, semantic/hybrid quality or general autonomous/multi-agent completion. All other unfinished T-number statuses stay unchanged; they are not deleted or relabelled done.

Recommendation: choose B only if closing the usable local milestone is the intended goal; choose A if full release certification is required. **Neither choice is applied automatically.** This asks for the T36 definition, not repeat approval of the already accepted preview. A decision for B would need an explicit final status update; it has not happened yet.

## Evidence reviewed

- docs/core-release-review.md — existing dated scope/CI/clone/dependency audit.
- docs/workstream-8-release.md — existing preview acceptance and full-release limits.
- docs/agentic-ai-roadmap.md — current 37-task register, scoped Y/P/X and parked requirements.
- Current T14/T17/T20/T21/T22/T23 saved acceptance records are referenced by that register; no new live acceptance is claimed.

**Counts unchanged: Y 10 | P 21 | X 6 — total 37.**
