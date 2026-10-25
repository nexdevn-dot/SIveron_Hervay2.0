# Development roadmap

Local Siveron product direction and development: **Bao Dang**, based on Harvey by
**Ethan Rogers**. Application/local modifications: **MIT**.
[Attribution](../AUTHORS.md) · [Delivered baseline comparison](DEVELOPMENT_STATUS_2026-10-20.md).

Reviewed: 2026-10-19. Reconciled with the startup workflow recommendations and
the subsequent code-based delivery-sequence review. All items below are proposals, not implemented behavior or release
commitments. Priorities are recommendations; implementation needs a concrete task.
Current feature maps: [index](INDEX.md). Technical documentation remains in English.

## Product objective and target workflow

Help the owner turn suitable companies into qualified conversations with a clear
next action, visible evidence and understandable delivery status.

**Target customer profile → discover companies → enrich contact data → review selection
→ prepare campaign → approve messages → handle replies → track sales opportunities.**

Build on existing discovery, contacts, held drafts, outbox, Today and conversations.
Prefer connecting these surfaces over creating parallel lists or another CRM workflow.
AI is optional assistance, not a prerequisite for completing the manual workflow.

## Reconciliation with the previous roadmap

| Recommendation | Previous coverage | Decision |
| --- | --- | --- |
| Guided campaign start | Implemented 2026-10-19 | R01: five-step navigation, saved draft resume and campaign-scoped review |
| Target customer profile and signal rules | Signal-based discovery acceptance | Expand into R03; preserve tri-state evidence and unrestricted search |
| Campaign results funnel | Campaign outcome overview | Expand R06 with consistent counts and qualified-conversation outcomes |
| Central action queue | Existing Today UI, no explicit roadmap item | Add R05 to extend Today instead of a duplicate inbox |
| Explain blocked/waiting delivery | Delivery readiness explanation | Expand R02 into sequence assurance (R02a) and shared readiness (R02b), before R01 |
| Sales pipeline after replies | Missing | Add R09 after reply/outcome semantics are defined |
| Prevent repeated outreach | Existing deduplication and suppressions provide partial protection | Add R04 for cross-campaign/company visibility; keep suppressions authoritative |
| Reusable workflow templates | Existing saved company filters cover only one part | Add R08 for target profile, search and sequence templates |
| Effort, costs and outcomes | Usage reporting exists, campaign attribution not covered | Add R10 with measured costs and sample-size context |
| Evidence-based AI assistance | Optional text generation already exists | Add R12 for optional fit/response assistance; do not imply autonomous approval |

Existing lookup diagnostics, identity review, Maps resilience, frontend regression
coverage and modularization remain in scope as R07, R11, R13, R14 and R15.

## Open-source research

The candidates below are part of the roadmap evaluation, not adopted dependencies.
Research basis: repository documentation and license labels reviewed on 2026-10-18;
no integration or source/security audit has been completed. The
[detailed candidate matrix](OPEN_SOURCE_CANDIDATES.md) retains research context.
Effort is a qualitative estimate for this checkout, not a delivery commitment.

| Roadmap | Candidate / license label | Proposed reuse and decision | Adaptation |
| --- | --- | --- | --- |
| R01 | [Driver.js](https://github.com/nilbuild/driver.js) · MIT | Optional contextual hints on existing screens. Recommended after the guided workflow works without a tour; does not provide saved progress. | Small frontend integration |
| R01, R02 | [transitions](https://github.com/pytransitions/transitions) · MIT | Optional Python guards/state transitions. First assess a smaller local readiness rule table; keep SQLite transactions and lifecycle authoritative. | Medium; no persistence supplied |
| R03 | [json-logic-js](https://github.com/jwadhams/json-logic-js) · MIT | Candidate JSON rule representation. Validate/evaluate server-side; explicitly implement unknown evidence semantics and operator allowlists. Do not add React solely for rule editing. | Medium; Python/backend parity required |
| R04, R11 | [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) · MIT | Later candidate for possible company/name matches; first deliver exact email/domain/phone checks without fuzzy matching. Review uncertain matches; never auto-merge on similarity. Cross-campaign checks remain local SQL. | Small/medium Python integration |
| R05, R09 | [Frappe CRM](https://github.com/frappe/crm) · AGPL-3.0 | Reference for lead/deal activities, tasks and next actions. Independently implement the applicable workflow using existing contacts/conversations; no second CRM deployment. | Workflow reference; high cost for direct code integration |
| R06, R08 | [listmonk](https://github.com/knadh/listmonk) · AGPL-3.0 | Reference campaign reports and template workflows. No Go/PostgreSQL/Vue service integration. Newsletter engagement does not define qualified sales outcomes. | Workflow reference |
| R06, R10 | [Apache ECharts](https://github.com/apache/echarts) · Apache-2.0 | Recommended for funnel/trend presentation once local metric definitions and aggregate endpoints exist. Does not calculate attribution or supply missing data. | Small/medium frontend integration |
| R07 | [Tenacity](https://github.com/jd/tenacity) · Apache-2.0 | Candidate bounded retries for transient lookup failures. Preserve stop/time/quota budgets; avoid nested retry amplification. Not for automatic non-idempotent mail retries or auth/CAPTCHA bypass. | Small if existing retry logic is insufficient |
| R08 | [Jinja](https://github.com/pallets/jinja) · BSD-3-Clause | Deferred rendering candidate. Start with current placeholders/rich-content validation and add template storage; no unrestricted user template execution. | Medium if adopted; unnecessary for first slice |
| R09 | [SortableJS](https://github.com/SortableJS/Sortable) · MIT | Candidate opportunity-card reordering. Add server-validated transitions and keyboard/button alternatives; storage/stages remain local. | Small frontend integration plus workflow logic |
| R12 | [Pydantic AI](https://github.com/pydantic/pydantic-ai) · MIT | Reference typed suggestion/evidence contracts only. Use current validation and restricted Brain boundary; do not adopt another agent/tool loop or change Codex isolation. | Contract pattern; full SDK not recommended |
| R13 | [RESPX](https://github.com/lundberg/respx) · BSD-3-Clause | Candidate test-only HTTPX failures/timeouts and responses. Maps DOM/checkpoints need separate browser fixtures. | Small test integration |
| R14 | [Playwright](https://github.com/microsoft/playwright) · Apache-2.0 | Recommended isolated UI regression coverage; reuse relevant existing browser tooling. Temporary DB, mocked integrations and no live sends. | Medium test setup |
| R15 | Existing FastAPI/Python/JavaScript structure | No new library: incremental router/service/client extraction with existing tests. | Incremental maintenance |

### Adoption constraints

All proposals integrate into the current application or its development tests;
no separate CRM/scraper service and no framework replacement are planned. Pin a
specific revision/version, verify its actual license and dependencies, and retain
required notices in THIRD_PARTY.md before adoption. License labels are not a legal
compatibility verdict. Copied, modified or translated code retains applicable
license obligations. Frappe/listmonk are behavioral references, not approved code
copies. Do not replace working local components just to add a candidate library.

## Prioritized backlog

Implemented slices: **R02a, R02b, R01, R04 (exact review), R03/R07 (first delivery), R05, R06 and R08/R09 (first delivery)**. Other entries remain proposals. IDs stay stable as priorities change.
R02a/R02b below are delivery slices of R02, not new independent backlog IDs.
The delivery order below is authoritative; ID order is not implementation order.

| ID | Priority | Proposal | Acceptance criteria / scope boundary |
| --- | --- | --- | --- |
| R01 | P1 | Guided campaign start | **Implemented 2026-10-19:** saved-only resume, five steps and scoped review; see campaigns module. After R02a/R02b, connect contacts → draft → preview → preparation → approval using existing screens. Show completed, missing and blocked steps; preserve saved work and resume after reload. Cover empty/error states and DE/EN without requiring a tour library. No implicit contact acceptance, message approval or live sending. |
| R02 | P1 | Sequence assurance and shared delivery readiness | **R02a implemented 2026-10-19:** spacing snapshots, predecessor-success guard, deferred next schedules and conservative legacy migration; see delivery module. **R02b implemented 2026-10-19:** shared assessment, stable reasons/actions, runtime evidence and DE/EN outbox display. **R02b:** explain each waiting/blocked message with concrete blockers and next action using the same business rules as Sender. Distinguish dashboard, agent, model availability and delivery states; never bypass gates. See first two delivery slices below. |
| R03 | P1 | Target customer profiles and optional signal-based acceptance | **Implemented 2026-10-19:** saved required/excluded presence rules, freshness, three-state evidence/counts and optional post-import run classification; all imported results retained. Numeric predicates and destructive pre-import acceptance are not implemented. Save reusable required/excluded criteria. Classify match, no match and unknown with evidence and counts. Keep unrestricted search. Define when evidence is available before import versus after profiling; do not discard unknown results silently. |
| R04 | P1 | Repeated-outreach prevention | **Exact review slice implemented 2026-10-19:** campaign/message evidence, selected colleagues, uncertain-name labels and transaction-bound explicit acknowledgment; see campaigns module. First cover exact address and established company identity without a fuzzy-matching dependency. Before preparation, show existing campaign membership and previous outreach for the contact and company, including another person at the same company. Separate exact matches from uncertain company identity. Suppressions/opt-outs remain hard constraints; avoid blocking legitimate follow-ups within the same sequence. |
| R05 | P2 | Central next-action queue | **Implemented 2026-10-19:** derived/paginated reply, approval and blocked/unknown delivery tasks; fresh record navigation and digest-bound reply review. Extend Today with actionable replies, draft approvals and blocked delivery. Each item links to the relevant record and explains the next step. Avoid duplicate notifications and distinguish stale/resolved work. |
| R06 | P2 | Campaign results funnel | **Implemented 2026-10-19:** independent local stage counts with UTC periods, distinct contacts/messages, explicit revisioned qualification/meeting records and unknown attribution/legacy dates. No inferred conversion rates or chart dependency. Per campaign show researched, contactable, approved, sent, replied and qualified/meeting outcomes with linked records. Define entity, denominator, time window and unique versus message counts. Show unavailable stages as unknown rather than zero; preparation/approval is not delivery. |
| R07 | P1 | Lookup failure diagnostics | **Public email slice implemented 2026-10-19:** persisted stage/reason/source/attempts, DE/EN result display and manual transient retry (60-second cooldown, three total attempts/job). People lookup remains unchanged. Show stage/reason, source evidence and safe retry for unsuccessful public contact lookup. Preserve quick/thorough budgets; distinguish no data from unreachable/failed pages. |
| R08 | P2 | Reusable campaign workflow templates | Save target-profile references, search criteria and message sequence as a reusable template. Do not copy recipient membership, approvals, sent status, credentials or private sender configuration. Review recipients/content before preparation. |
| R09 | P2 | Sales opportunities after replies | Explicitly create/link an opportunity with stage, owner, next task and date from an interested contact. Preserve campaign/conversation links. Replies are not automatically qualified opportunities; allow manual correction. |
| R10 | P2 | Campaign effort/cost and outcome attribution | Attribute measurable provider/model costs and processed-contact counts to campaigns/runs without counting shared discovery costs twice. Keep estimates, actual and unavailable values distinct. Show qualified-conversation/meeting counts and small-sample context; do not claim ROI without revenue data. |
| R11 | P2 | Contact/profile identity review | Later phase: review public source evidence and uncertain matches before accepting a person/profile association. No automatic identity merge; linked social profiles alone do not prove identity. |
| R12 | P2 | Optional AI fit and reply assistance | Later phase: propose evidence-linked fit explanations and editable reply drafts, with uncertainty visible. Keep user-provided facts separate from inferences and treat website/reply instructions as untrusted. Allow manual completion when AI is unavailable; never auto-approve, qualify or send on a suggestion alone. |
| R13 | P2 | Maps fixtures and provider resilience | Versioned fixtures, parser failure categories and checkpoint recovery tests. Preserve radius enforcement and limits; no anti-bot bypass or completeness claims. |
| R14 | P2 | Frontend flow regression checks | Isolated DE/EN/mobile flows for selection, menus, drafts, review and guided navigation. Include blocked/empty/error states. No live sending or production-data mutation. |
| R15 | P3 | Split large API/client files by feature | Extract boundaries from `dashboard.py`, `state.py` and `app.js` incrementally. Preserve routes, migrations, JS hooks and lifecycle behavior; avoid a framework rewrite as a prerequisite. |

## Evidence behind the revised order

**Implemented foundations:** manual preparation uses a transaction, revision checks
and repeat-preparation protection in [crm.py](../harvey/crm.py)
(`prepare_campaign_review`). Existing sender checks cover suppression and stop-on-reply.
The previous targeted check reported **47 passing tests** across CRM actions, native
outbox and sending settings. That result is historical evidence from the review,
not a new test run or proof of live delivery.

**R02a implemented (2026-10-19):** the earlier risk was reproduced with a fake
provider and isolated DB: delayed approval could release overdue steps together,
and unsuccessful predecessors did not hold follow-ups. New regression tests first
failed, then passed after adding snapshotted `delay_days`, exact predecessor-success
checks, delayed next schedules, and readiness selection before the batch limit.
An appended migration preserves approval/sent states and infers legacy spacing only
from readable whole-day adjacent snapshots; unknown intervals remain held.
See [delivery module](modules/delivery.md) and
[sequence tests](../tests/test_sequence_schedule.py). These findings concern native
SMTP/Gmail sending; no live sending error or inbox delivery was asserted.
Validation on 2026-10-19: 17 sequence regression tests; full Python suite
696 passed / 22 skipped; 3 bilingual help-content checks passed. Existing
heartbeat fixtures now include successful predecessors so their safety checks
remain exercised. No live mail or live database migration was performed.

**Partial readiness already exists:** `/api/campaign-readiness` in
[dashboard.py](../harvey/dashboard.py) explains global setup such as channel,
provider, daily-limit configuration and pause. R02b now extends this with the shared per-message assessment; the global endpoint remains a setup summary. [main.py](../harvey/main.py) also distinguishes a failed
Brain preflight from exhausted AI quota: the former holds the cycle, while the
latter has a guarded native approved-mail path. Explain these existing distinctions;
do not weaken isolation/auth checks or reply-safety requirements.

**R02b implemented (2026-10-19):** see [delivery module](modules/delivery.md)
and [readiness tests](../tests/test_delivery_readiness.py). Unknown or stale runtime
checks are explicitly unconfirmed. Sender shares deterministic checks with the API;
heartbeat observation remains conservative and never performs a fresh external check
on a dashboard read. Provider configuration is not a live connectivity guarantee.
Validation: 9 readiness tests, full Python suite 705 passed / 22 skipped,
3 help checks and isolated desktop/mobile DE/EN preview (2026-10-19).

## Suggested delivery order and dependencies

| Order / slice | Work and dependency | Verifiable completion criteria |
| --- | --- | --- |
| **1 — R02a: sequence assurance (implemented)** | Implemented 2026-10-19 before R01 without a new dependency. Existing waiting queues migrate conservatively on normal DB initialization; no live agent was started. | Tests cover approval after several scheduled dates, predecessor rejection/failure, cap deferral and legitimate follow-ups. A follow-up respects the intended successful predecessor and defined elapsed delay; no unintended catch-up burst. Legacy readable whole-day intervals are snapshotted; unknown intervals remain held, without new approvals. Per-item explanations are provided by R02b; ambiguous legacy intervals are not automatically rewritten. Preserve approval, suppression and stop-on-reply. |
| **2 — R02b: one readiness assessment (implemented)** | Implemented 2026-10-19: shared native message rules, read-only per-message reasons/actions, timestamped runtime observations and desktop/mobile DE/EN display. No new dependency or live send. | Each waiting/blocked item has concrete reason codes, readable explanations and next actions. Sender and display use the same business rules. Cover future due time, actual remaining daily capacity, pause, provider/setup failure, contact restrictions, predecessor state and relevant runtime/model/reply-safety blockers. Unknown runtime state is not shown as ready. Assessment itself sends/approves nothing. |
| **3 — R01: small guided campaign path (implemented 2026-10-19)** | Five-step next-action navigation, saved-only resume and campaign-scoped Outbox/approval implemented without a new dependency. Consume R02b; connect existing contacts, draft, preview, preparation and approval. No Driver.js, transitions or other new library is a prerequisite. | User can complete the manual path, resume saved work after reload, understand missing/blocked steps and handle empty/error states in DE/EN. Repeated preparation does not duplicate queued messages. Approval stays explicit. Optional tours are a later enhancement. |
| **4 — R04: exact repeated-outreach checks (implemented 2026-10-19)** | Local indexed evidence matching and explicit review, no fuzzy dependency or separate service. Reuse contact/campaign/outbox history and authoritative suppressions. Start with exact identity, not RapidFuzz. | Before preparation, expose other campaign membership and previous outreach to the same address or established company, including another known person there. Give reviewable reasons and distinguish active versus historical campaigns. Legitimate follow-ups within a sequence remain possible; opt-outs cannot be overridden. |
| **5 — R03 + R07: target profiles and research explanations (implemented first delivery 2026-10-19)** | Saved presence-based profiles, optional retain-all post-import classification and bounded public-email diagnostics/retry. No new dependency, automatic rejection or live sending. Build on the usable completion path and established identity checks. | Reusable required/excluded signals yield match/no match/unknown with evidence and counts. Preserve unrestricted search; distinguish pre-import evidence from later profiling. Lookup failures identify stage/reason and support bounded safe retry without silently treating unavailable data as a negative finding. |
| **6 — R05 + R06: tasks and campaign results (implemented 2026-10-19)** | Derived tasks, exact record links, explicit outcome assessment and independent local campaign stage counts. Extend Today; agree outcome vocabulary and attribution before charts. | Every actionable item links to the right record and resolves when done. Count unique contacts, messages and replies separately with time windows and unavailable values. Explicitly record qualified conversations/meetings; do not infer them from any reply. ECharts is optional presentation after aggregate definitions exist. |
| **7 — R08 + R09: reuse and sales continuation — implemented 2026-10-19** | Templates reuse R03 profiles; opportunities reuse R06 outcome definitions and conversation links. | Save/reuse profile, search and sequence templates without recipients, prior approvals or delivery state. Explicit opportunities have a stage, next task and date, with ownership where applicable. Preserve manual correction. Keep existing placeholders initially; defer Jinja and optional SortableJS until needed. |

### Deliberately later

- **R11 and fuzzy matching:** uncertain identity/profile review and RapidFuzz follow
  exact checks; similarity alone never establishes identity or permits automatic merging.
- **R12:** AI fit/response assistance follows evidence/review foundations. Preserve
  manual operation and the restricted Brain boundary; no second agent loop is required.
- **R10:** detailed cost attribution follows explicit run/campaign/outcome links;
  distinguish measured, estimated and unavailable costs without double counting.
- **New research providers:** no additional provider is required for these first
  slices. Validate a specific coverage gap before expanding the provider set.

R13/R14 accompany the changes they protect rather than wait for a separate late phase:
HTTPX fixtures cover network failure modes, browser fixtures cover Maps DOM/checkpoints,
and isolated DE/EN/mobile flow checks protect touched UI paths. RESPX covers HTTP only;
reuse existing test tooling before adding dependencies. R15 remains incremental
maintenance, not a prerequisite rewrite. P1 means importance, not a request to ship
all P1 items together. Retain every candidate above as an evaluation option, not an
installation commitment.

## Affected implementation areas

| Work | Start with |
| --- | --- |
| R01, R05 | [Platform](modules/platform.md), [campaigns](modules/campaigns.md), [contacts](modules/contacts.md) |
| R02, R04 | [Delivery](modules/delivery.md), [contacts](modules/contacts.md) |
| R03, R07, R11, R13 | [Signals](modules/signals.md), [discovery](modules/discovery.md), [companies](modules/companies.md) |
| R06, R08, R09, R10, R12 | [Campaigns](modules/campaigns.md), [delivery](modules/delivery.md), [platform](modules/platform.md) |
| R14, R15 | [Development](DEVELOPMENT.md), [architecture](ARCHITECTURE.md) |

## Evidence and maintenance

Use module tests, failure handling, recovery, user feedback and separately authorized
live validation before maturity claims. Do not assign unsupported completion percentages
or count mocked provider checks as live validation. Use the same definitions for
metrics in UI, APIs and help; track unknowns and avoid double counting.

When an item ships, record its implemented scope, date, validation and module link;
retain any unfinished acceptance criteria rather than marking the entire proposal
complete. Update the affected module and user help in the same functional change.
Do not store private customer data or actual campaign results in this roadmap.

Implemented foundations (not new proposals): company filter views and facets;
compact action popover; quick/thorough email lookup; local Maps checkpoints;
contact actions/trash; held campaign composer and optional AI text suggestions;
approvals, visual outbox status, campaign-grouped conversations, Today and usage.
Their existence does not establish the extended workflows above. See [index](INDEX.md).

### Slice 7 delivered: local templates and explicit opportunities

See [sales workflows](modules/sales-workflows.md). Templates snapshot validated
sequence/brief, optional profile reference and search criteria; fresh drafts have
no recipients, attachments, private sender settings or approval/delivery state.
Applying criteria never starts discovery. Opportunities require an incoming reply
and explicit interest confirmation, retain exact contact/conversation/campaign links,
and expose editable stage/owner/next task/date with revision checks. Due open tasks
appear in Today. Conversation qualification/meeting outcomes remain independent.
Frappe CRM and listmonk informed workflows only; no code or service was imported.
Jinja, SortableJS, revenue forecasting and automatic qualification remain deferred.

### R07/R13/R15 extraction foundation delivered (2026-10-20)

Public email, people and website profiling use a shared bounded HTTPX reader.
extruct phone/postal-address/contact-point suggestions can be reviewed in the company
profile with source and current value; transactional adoption is explicit. See
[web extraction](modules/web-extraction.md). No new dependencies or live contact
creation were added. Complex Person relationships, cross-job reuse, generalized
HTTP retry policy and Trafilatura remain future work.

### R07 email validation consistency delivered (2026-10-20)

A bounded TTL-aware DNS resolver cache now serves explicit domain checks. Shared
syntax/transport checks connect contact input, API flags, campaign selection and
Sender/Gate without new verification statuses, SMTP probes or automatic approvals.
Temporary DNS failure stays unknown. Existing lowercase keys/.test fixture policy
remain compatible; normalization migrations and SMTPUTF8 support are not included.

## Implemented assistant foundation (2026-10-20)

The in-app side-panel assistant ships with locally bundled Deep Chat, a TypeChat-inspired
Pydantic plan boundary on the existing restricted Brain, configurable DE/EN settings,
authored-help retrieval, explicit Discover proposals, literal inventory lookup and
single-signal/category evidence reports. Data pagination uses no extra model call.
See [platform](modules/platform.md#in-app-assistant-2026-10-20).

Later proposals remain separate: combined signal predicates, numeric employee/revenue
filters backed by real evidence, unique category aggregates/charts, campaign comparisons,
evaluated grounded-answer fixtures and optional durable chat history. Vanna/CopilotKit/
assistant-ui are research references, not installed services or current functionality.

## Decision-maker research foundation (implemented 2026-10-20)

Official-company-site search now supports explicit target roles, explained deterministic
role fit, per-run evidence snapshots, paginated review and selected contact adoption.
See [Contacts](modules/contacts.md#b2b-decision-maker-research-2026-10-20).
OpenOutreach/OpenOutFind serve as workflow references; application code remains independently
implemented under MIT. Licensed people-database search, paid enrichment, product-aware AI
qualification and calibrated learning remain proposals, not shipped capabilities.


## Contact email research foundation (implemented 2026-10-20)

Contacts now exposes an evidence-first per-contact research dialog, bounded website/
public-web/profile-hint adapters, optional Hunter published-only Finder, DE/EN settings
and explicit revision-safe contact adoption. No separate service or new dependency is
required. See [Contacts](modules/contacts.md#contact-specific-email-research-2026-10-20).
Paid provider requests require configured credentials and source selection; this does
not implement social login scraping, account enumeration, inferred addresses or automatic
sending. Future work: evaluated real-world precision/recall fixtures and additional
licensed source adapters with explicit provenance and budget policies.


## Company optimization reports (implemented 2026-10-21)

Companies now offers selected-company reports using existing signal evidence,
DE/EN categories/age selection, persisted snapshots/history, source-linked review
advice, contextual facts, open checks, Markdown and browser PDF print output.
Optional existing-Brain explanations are separately labelled and cached. See
[Companies](modules/companies.md#signal-based-company-reports-2026-10-21).
GPT Researcher/Evidence supplied workflow references only, no new runtime service.
Lighthouse/axe measurements, quantified impact and fresh audit collection remain
proposals and must not be inferred from this reporting feature.

## Local OpenAI-compatible model adapter — proposal (2026-10-25)

A colleague uses llama.cpp with 16 GB VRAM. The
[endpoint preparation guide](local-llm/README.md) supplies a synthetic API smoke
test and an explicit implementation gap. Pending: exact server/model/platform
identification, text/JSON capability tests, validated HTTP provider settings,
timeout/cancellation/status handling, no cloud fallback, rejection of tool calls
and regression coverage of existing provider boundaries. No provider or model
support is implemented by this documentation. Docker packaging remains unverified.
