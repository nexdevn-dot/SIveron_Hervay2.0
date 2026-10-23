# Discovery

Code checked: 2026-10-22. [Index](../INDEX.md) · [Signals](signals.md) · [Companies](companies.md)

## Purpose and workflow

Discover organizations from selected provider, business terms, locations and radius.
UI order: source → Maps options when selected → optional email lookup → separate
Search criteria section → advanced settings, preview and run controls.
Estimate/preview is distinct from starting collection. Imports are deduplicated;
subsequent profiling examines pending/stale companies in the database. Optional
email lookup checks only this run's company IDs (up to 1000), creates no contacts
and sends no email. Progress stages include location preparation, search, profiling
and optional emails. Stop is checked between work units, not an instantaneous
cancellation of every in-flight request.

## Implementation map

- [collectors/discover.py](../../harvey/collectors/discover.py): provider registry, query building, estimates, import and observations.
- [collectors/google_maps.py](../../harvey/collectors/google_maps.py): local Playwright collection, sections/checkpoints, exact radius checks.
- [pipeline.py](../../harvey/pipeline.py): discovery → profile → optional email phase.
- [discovery_progress.py](../../harvey/discovery_progress.py), [discovery_catalog.py](../../harvey/discovery_catalog.py): progress and search vocabulary.
- [dashboard.py](../../harvey/dashboard.py): `/api/discover/providers`, `/estimate`, `/run`, `/stop`, `/progress`, `/locations` under `/api/discover`; `/api/profile/run`.
- UI: [app.js](../../harvey/web/app.js), [index.html](../../harvey/web/index.html), [app.css](../../harvey/web/app.css).
- Persistence: `companies`, `company_discovery_sources`, `runs`, `observations`, `settings` (including Maps checkpoints).

## Constraints

At least one confirmed signal is required for actual discovery; signal activation
controls recorded observations rather than strict import acceptance. Listing filters
and search limits are provider-specific. Maps quick/grid modes use the local browser,
not a separate scraper service. Maps has limits of 100 sections and 200 listings per
section; no complete-coverage guarantee. Unknown exact coordinates are skipped for
radius enforcement. Login/CAPTCHA/blocking is not bypassed. Provider quotas, budget
and missing credentials can stop a run. Saved sections can be resumed or searched afresh.

## Verification and potential

Tests: `test_discover.py`, `test_google_maps.py`, `test_discovery_progress.py`,
`test_discovery_free_providers.py`, `test_pipeline.py`, `test_email_search_extensions.py`.
Next proposals: explicit signal acceptance and provider diagnostics, [roadmap](../ROADMAP.md).
Detailed topic: [Unternehmenssuche](../UNTERNEHMENSSUCHE.md).

Optional saved target profiles classify this run after import/site checks without
removing results. Counts and evidence persist as target_summary. No profile preserves
the existing unrestricted behavior. Only this run's IDs are classified, while website
profiling may still process the independent backlog. See [signals](signals.md) for
three-state semantics and source/freshness limitations.

## Shared page reads and structured suggestions

See [web extraction](web-extraction.md), implemented 2026-10-20, for the shared
bounded HTTPX reader and explicit review of extruct phone/address/contact-point
suggestions. Existing HTML extraction and contact adoption remain separate.

## Assistant search proposals (2026-10-20)

The shared assistant translates DE/EN requests into bounded terms/cities/radius and
optional public-email fields. Applying a proposal fills the regular Discover form,
preserves the selected provider, disables resuming old Maps sections, and invalidates
the estimate. Arbitrary valid 1–200 km radii are represented as a native select option.
Nothing starts until the normal Run action. Unsupported criteria require clarification;
no company rows/emails/coordinates are fabricated by the model. See
[platform assistant](platform.md#in-app-assistant-2026-10-20).

## Compact progress and details (2026-10-22)

The main Discover view shows the current phase, phase-local progress and counts.
Search details opens a native dialog with the full stages, elapsed time, ETA,
email summary, provider limits and last-report diagnostics. Closing/Escape does
not cancel work; the existing explicit Stop control remains authoritative.
A run observed running in this page becomes a compact completion/error summary.
Hide summary collapses it into Last search; an older persisted run loads collapsed.
Only the latest run is retained by the existing progress/report API, not a new
multi-run history. UI dismissal is session-only; reloading retains access to the
stored latest run. Company navigation closes the dialog. Labels support DE/EN.

The compact status uses the existing signal-row typography and spacing: status
with a small dot, one secondary phase/count line and an icon-only Search details
button with accessible label/title; completed summaries have a small dismiss icon. No outer padded card, large heading, standalone
progress bar or repeated action-button row is used. Mobile detail targets are 44px.
Company navigation and complete phase progress remain inside Search details.

## Reuse contract

Reuse interfaces inspected: 2026-10-23. See the
[detailed reuse guide](../reuse/discovery-and-research.md) for inputs/outputs,
transitive dependencies, data and side effects, failure semantics, extraction steps,
examples and relevant tests. The [catalog](../REUSABLE_COMPONENTS.md) distinguishes
small logic, adapter seams and application-coupled workflows; these modules are
not a separately versioned public SDK.

## Low-cost research guidance

Source/budget integration checked: 2026-10-23. The
[low-cost research guide](../LOW_COST_LEAD_RESEARCH.md) distinguishes company
listing data, public website evidence and optional contact enrichment. It includes
provider/account limits, dated official references and total-cost examples.
Keep source coverage, imported fields, reviewed fit and contact validation separate;
local request reservations are not a universal account billing or spend guarantee.
No quotas, source activation, campaign approvals or sending defaults are changed.
