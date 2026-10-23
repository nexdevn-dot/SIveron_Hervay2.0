# Siveron development status compared with original Harvey

Snapshot: **2026-10-20**. Local product direction and development: **Bao Dang**.
Original Harvey: **Ethan Rogers**, [upstream repository](https://github.com/ethanplusai/harvey).
Application/local-modification license: **MIT**; original and local notices are
preserved in [LICENSE](../LICENSE). See [attribution](../AUTHORS.md) and
[third-party notices](../THIRD_PARTY.md).

## Baseline and interpretation

The verified starting point is Harvey v0.3.0, commit
`e2632eb20ee2d4fb6fe04ae715a52f578acf9a37` (local Git HEAD). Its README, dashboard
routes and persistence definitions were inspected with `git show`. This is not a
comparison against the latest upstream branch or the first-ever Harvey release.
Local working-tree changes are included; they are not a published upstream release.

Harvey already provided the core autonomous sales loop, Claude/Codex model providers,
company discovery and website profiling, signals/cohorts, campaigns, approval/native
outbox, replies, usage and dashboard controls. Those foundations must not be credited
to the local extensions as newly invented functions.

## Functional comparison

| Area | Original starting point | Local Siveron development under Bao Dang |
| --- | --- | --- |
| Product/interface | Harvey dashboard and existing workflow screens | Siveron branding, sidebar workspace, responsive refinements, DE/EN UI and detailed bilingual help |
| Discovery | Provider-based discovery, estimates, runs and website profiling | Local Maps collection, quick/grid search, checkpoints, exact-radius handling, progress stages and optional run-scoped public email lookup |
| Signals/targeting | Signal confirmation, observations and cohort queries | Saved target profiles, evidence freshness, match/no-match/unknown results and optional post-import classification |
| Company workspace | Company list and contact drill-down | Pagination, contextual multi-value facets, saved views, compact Actions, shared profile dialog, reversible selected removal and cleanup |
| Public contact research | Existing profiling/scouting foundation | Explicit public email and people jobs, source review, quick/thorough lookup, diagnostics and bounded manual retry |
| Website extraction | Existing HTTPX requests and HTML detectors | Shared bounded page reader, guarded redirects, job-local caching and extruct phone/address/contact-point suggestions with explicit adoption |
| Contacts | Prospect records and existing pipeline states | Manual person/company contacts, reviewed person candidates, notes, edit, blocking and recoverable trash |
| Campaign preparation | Model-written campaigns and outbox workflow | Held manual drafts, rich editor, placeholders, attachments, preview, guided icon steps and saved-draft resume |
| Outreach overlap | Existing deduplication and suppression protections | Cross-campaign/contact/company evidence and explicit overlap acknowledgment before preparation |
| Delivery | Approval, scheduling, native sending and delivery rules already existed | Shared readiness reasons, runtime evidence, snapshotted follow-up spacing and predecessor-success checks; clearer separated progress/status |
| Conversations/results | Stored conversations and reply handling | Campaign grouping/dialogs, digest-bound reply review, explicit qualification/meeting assessments and local campaign result counts |
| Sales continuation | Existing sales-agent lifecycle | Reusable workflow templates and explicit opportunities with stage, owner, next task/date and source conversations; due tasks in Today |
| Usage | Usage events and subscription quota display | Reading timestamp, explicit cache-bypassing refresh, explanation of account quota versus Siveron-only calls |
| Email checks | Existing verification and sender rules | Shared syntax/transport checks, API/UI consistency and TTL-aware bounded DNS cache; no mailbox-existence claim or SMTPUTF8 expansion |
| Maintainability | Upstream source and release documentation | Engineering index/module maps, roadmap, owner-facing ChatGPT brief and isolated regression fixtures |

## What is implemented versus proposed

Implemented items above are described in [module documents](INDEX.md). In particular,
R01–R09 have scoped deliveries; this does not mean every possible expansion of each
roadmap item is complete. The [roadmap](ROADMAP.md) separates delivered slices from
future work.

Still proposed/deferred: Trafilatura pilot, complex structured Person/employer
relationships, comprehensive revenue/cost attribution, broader identity review and
further optional evidence-linked AI assistance. No production-readiness, complete
search coverage, verified social identity or guaranteed inbox delivery is claimed.

## Verification evidence and limits

The most recent complete Python suite at this snapshot reported **768 passed,
22 skipped**. Help content checks and campaign-workflow Node tests also passed.
Browser checks used isolated demo data for new interactions. These are development
checks, not live service SLAs or proof of real mailbox delivery. No new test run is
claimed by this documentation-only update.

Private runtime configuration, authentication and customer/contact content are not
included. No current operational business setup is inferred from development defaults.

## Ownership and licensing scope

Bao Dang's attribution identifies local Siveron development, with AI-assisted work;
it does not replace Ethan Rogers's original credit. The MIT permission/disclaimer
text remains unchanged. Third-party libraries/assets retain their respective terms;
this document does not claim their code is authored by Bao Dang or wholly MIT.

## Navigation

- [Authors and attribution](../AUTHORS.md)
- [Local workflow, German](../START_HERE_DE.md)
- [Changelog](../CHANGELOG.md)
- [Engineering index](INDEX.md)
- [Product brief for ChatGPT, German](CHATGPT_PRODUKTBRIEF_DE.md)
