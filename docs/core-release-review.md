# Core agent release review

Prepared 18 October 2026. Decision: keep the full core release pending. The current implementation supports a useful trusted local-user development preview; this report does not declare a release or waive the parked acceptance gates.

## Evidence baseline

The full Workstream 7 offline suite passed 343 tests in 45.360 seconds (outputs/acceptance/workstream-7-offline-final.log). The subsequent synthetic backup rehearsal passed one additional scenario independently; a full 344-test run is not claimed. Installed pip check found no broken requirements. A no-index install probe could not resolve langchain; fresh-install acceptance is unverified, not proven incompatible.

## Acceptance review

The broad acceptance checklist remains P wherever its full scenario exceeds the evidence. Verified components keep their Y credit in the workstream checklists.

| Release gate | Verified evidence | Remaining acceptance |
|---|---|---|
| Conversation and clarification | Offline conversation/clarification tests; sampled live answers and missing-detail clarification | Broader factual accuracy and adversarial cases; no universal no-hallucination guarantee |
| Named chats and scope | Catalog/session tests, observed browser exports and browser-to-console recall after restart | Complete live summary-content isolation acceptance remains parked |
| Memory and conflicting facts | Save/update/forget, provenance, revision and suggestion tests; scoped retrieval | Paraphrase semantic recall and broader contradiction quality parked |
| Long conversation retention | Durable new-turn archive, summary validation/failure cooldown, caught save-failure checks | Actual-history summary quality and Ollama summary attribution parked; archive/checkpoint saves are not atomic together |
| Combined evidence sources | Local source tools, structured tables, mixed-source fixtures and sampled live grounding | Broader corpus/hybrid relevance and entailment quality parked; optional format dependencies not fully audited |
| Citations and search failures | Citation guards, page deadlines, source-reference fixtures and sampled authority/snippet disclosures | Structural citations do not prove every claim is entailed by a source |
| Multi-step completion | Workstream 5 bounded planning/recovery and complete/partial/blocked outcomes | Long-horizon and universal semantic task completion are outside measured scope |
| Arguments paths permissions | Tool registries, validated arguments/root boundaries and permission matrix tests | Application boundary is not an OS sandbox or public-user security boundary |
| Both-interface approval | Live browser approval/decline, console controls and offline all-action dispatch tests | Arbitrary command effects and all provider-generated plans are not certified |
| Restart cancellation replay | Durable receipt tests, fresh-process crashes and synthetic restored receipt checks | No automatic uncertain-outcome clearing, external rollback or relocated-root approval reuse |
| Provider and context failures | Four-label/six-category console/browser simulations, transport retry checks and configured budget preflight | Not every provider fault tested live; token estimates approximate and hosted limits operator supplied |
| Setup backup regression | 343-test full baseline, installed pip check, stopped-writer synthetic core-store restoration | Fresh install, optional format/index stores and actual user-data restoration unverified |

## Proposed preview scope for later agreement

Trusted local-user Windows use through console and loopback Streamlit, configurable existing providers, explicit memory commands, scoped saved chats, read-only evidence tools and exact approved local actions with durable receipts. Treat source and model output as evidence requiring review. Use the existing configured environment; a clean distributable installation is not yet accepted.

Exclude public hosting/multi-user authentication, OS command sandboxing, guaranteed semantic recall or conflict resolution, universal citation entailment, unattended long-running tasks, unlimited hosted API access, automatic provider switching, uncertain-action replay and new automation-framework development.

This is a proposed scope, not user agreement. Existing Jira uncertain receipts remain intact and must not be cleared to pass a release check. Parked quality items remain P unless independently verified or explicitly excluded through a concrete agreed release scope.

## Next actions

1. Complete the optional-dependency audit and a bounded connected clean-install rehearsal when packages/network resources are available. Do not treat an installed-environment check as clean setup.
2. Prepare explicit startup, installation and state-store smoke acceptance in the fresh environment.
3. Decide whether to continue the full core gate or agree a narrower development-preview scope after reviewing this report. Even a preview does not change unfinished quality gates to Y.
4. Synchronize the Word roadmap after the release evidence and scope are settled. UI changes remain a separate proposed milestone before Workstream 9.

## Evidence references

- docs/workstream-2-summaries.md and outputs/acceptance/summary-actual-groq.json
- docs/workstream-3-memory.md and outputs/acceptance/semantic-memory-bounded-retry.json
- docs/workstream-4-grounding.md and outputs/acceptance/source-authority-summary.json
- outputs/acceptance/workstream-5-summary.json and workstream-6-summary.json
- docs/workstream-7-reliability.md and outputs/acceptance/workstream-7-offline-final.log
- tests/test_backup_recovery.py and outputs/acceptance/workstream-8-offline-install-probe.log

## Updated core preview evidence

Fresh core-profile installation and 71 selected offline end-to-end checks passed on 18 October 2026. Installation plus run took 117.7 seconds; tests took 12.872 seconds. Source-only isolated data and mocked provider calls were used. This closes the scoped core setup/rehearsal concern for a development preview, not every broad release acceptance item. Full-profile/RAG install, model/index behavior and parked quality remain P. User agreement to preview scope remains pending.

Proposed decision for the user: accept the current trusted local-user core as a development preview and proceed to UI improvements, while retaining full release and Workstream 9 as pending. This is not approval to perform new external writes or clear uncertain receipts.
