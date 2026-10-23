# Signals and cohorts

Code checked: 2026-10-21. [Index](../INDEX.md) · [Discovery](discovery.md)

## Purpose and workflow

Signal definitions have proposed/confirmed/rejected states. Only confirmed codes
are recorded by the discovery/profile collectors. Confirmation is permission to
collect that supported characteristic; it is not a condition that every imported
company must satisfy. Without any confirmed signals, actual discovery stops and
profiling records nothing.

Discovery records available listing/search observations, for example no website,
review rating/count or rank. Website profiling checks supported confirmed signals.
Unavailable provider data cannot establish a positive finding. Activation alone
also does not implement a new detector or prove historical companies were rechecked.
The confirmed-code set is loaded at collector/run entry, not per UI toggle; do not
promise that changing a signal changes an already-running batch immediately.

The cohort builder queries companies with all required signals and none of the
excluded signals. This is separate from discovery's import filters. Example:
activating NO_WEBSITE does not prevent companies with websites from being imported;
the Maps listing filter can restrict imports independently.

## Implementation map

- [signals.py](../../harvey/signals.py): catalog/seeding.
- [state.py](../../harvey/state.py): `confirmed_signal_codes`, observations and `cohort` SQL.
- [collectors/discover.py](../../harvey/collectors/discover.py): `_observations` confirmation gate.
- [collectors/profile.py](../../harvey/collectors/profile.py): supported website detectors and confirmation gate.
- [dashboard.py](../../harvey/dashboard.py): GET `/api/signals`, POST `/api/signals/status`, POST `/api/cohort`, GET `/api/runs`.
- UI: [app.js](../../harvey/web/app.js); tables `signal_codes`, `observations`, `runs`.

## Constraints, verification and potential

Missing evidence is different from an explicitly negative result. Cohorts operate
on recorded evidence, not universal truth about an organization. Signal activation
does not start a campaign or approve email.
Tests: `test_dashboard_signals.py`, `test_signals_export.py`, `test_collectors_profile.py`, `test_discover.py`.
## Saved target profiles (R03, implemented 2026-10-19)

[target_profiles.py](../../harvey/target_profiles.py) persists named required/excluded
signal sets and an evidence age of 1–365 days (default 90). Profiles never confirm
signals automatically. The existing cohort builder remains its historical positive
observation query; the new profile evaluator deliberately uses different, conservative
three-state semantics. Saved profile results can be filtered to match/no match/unknown.

For each company/rule the latest observation is considered. Inactive signals, missing,
stale/future/invalid-date, low-confidence or unusable values yield unknown. Explicit
boolean 1/0 establishes true/false. Text or numeric recorded values establish presence,
not a numeric threshold. An excluded signal requires explicit false evidence to satisfy
a boolean exclusion; absent evidence is not evidence of absence. Any disproven rule
makes no_match; otherwise any unknown makes unknown; all satisfied rules make match.
Collectors that record positives only cannot establish an unobserved negative.

Results include rule, reason, value, timestamp, confidence, source and collection stage.
Listing evidence is labeled separately from website/later evidence. Inventory counts
cover all nonremoved companies, not a capped sample; results paginate 30/page. The UI
stores and evaluates profiles under Signals. APIs: GET/POST `/api/target-profiles`,
DELETE `/{id}`, GET `/{id}/evaluate?page=1&verdict=all` (match/no_match/unknown filters).
Deleting a profile retains companies/observations and does not alter an in-flight
profile snapshot.

Discover offers an optional profile; default is unrestricted. Classification occurs
**after import and the configured website checks**, scoped to that run's company IDs,
not the profiling backlog. Snapshot criteria and counts/evidence appear in persisted
progress/report `target_summary`; fresh inventory evaluation can differ later. All
imported results are retained, including no_match and unknown. This first policy is
review/filtering, not pre-import deletion, automatic contact acceptance or permission
to contact. No new detectors, collection permissions or model calls are introduced.

Tests: `test_target_profiles.py`, the scoped optional-profile case in `test_pipeline.py`.
See [roadmap](../ROADMAP.md) for later numeric predicates/import policy changes.

## Company profile dialog (2026-10-19)

Company-name buttons in cohort results and the company list open the same native
dialog. GET `/api/companies/{id}/profile` reads the exact nonremoved company and
known email/phone/social details plus nontrashed contacts. Opening is read-only:
no research, selection changes, navigation or sending. Loading/error states, Escape,
close-button focus restoration and DE/EN labels use the existing dialog shell.
The separate Contacts button retains the existing company contact workspace.

## Assistant evidence queries (2026-10-20)

Assistant reports reuse the saved-target-profile evaluator for a selected known signal,
evidence age and optional literal company/location/industry filter. Confirmed signal
with usable latest evidence is required; missing, inactive and stale evidence remain
unknown. Summary rows show per-signal counts in a selected category (or all categories),
not additive unique-company category totals. No signals are activated, observations
collected or target profiles saved by a query. See [platform](platform.md).


Company report snapshots (2026-10-21) reuse the latest-observation evaluator and add
source usability checks. They never activate signals or infer negative/positive facts
from missing records. Conditional recommendations are distinct from measurements.
See [Companies](companies.md#signal-based-company-reports-2026-10-21).
