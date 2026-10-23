# Companies and public contact lookup

Code checked: 2026-10-21. [Index](../INDEX.md) · [Contacts](contacts.md)

## Purpose and workflow

Organizations retain public email, phone, website and source evidence. The list uses
30 rows/page with server-side filtering. Multi-value locations/industries use OR;
different filter fields use AND. Facet counts cover the inventory and respect other
filters. Additional fields include phone, named people, linked social profiles and
source. Saved filter views persist in SQLite; they do not save selection or email mode.

Select rows through checkboxes. The left-aligned Actions popover contains lookup,
mode, cleanup and available results. The separate selection toolbar and selection
instruction paragraph are hidden. Selection survives paging and clears on filter changes.
Search results/review are opened on demand rather than permanently occupying the list.

Quick email mode stops after a matching email and checks fewer subpages. Thorough
also checks about/team pages. Structured data, mail links, validation and constrained
browser fallback support extraction. Source evidence and validation metadata remain
separate from confirmed mailbox deliverability. Explicit social links may be stored;
this does not establish a person's identity or crawl social accounts. Cleanup removes
companies with no known valid email, phone or website across the entire inventory;
restoration is supported. Finding public emails does not create contacts automatically.

## Implementation map

- [company_filtering.py](../../harvey/company_filtering.py): validated filters, parameterized SQL, pagination and contextual facets.
- [collectors/company_contacts.py](../../harvey/collectors/company_contacts.py): extraction, modes, validation and profile links.
- [collectors/contact_jobs.py](../../harvey/collectors/contact_jobs.py): durable bulk lookup jobs.
- [dashboard.py](../../harvey/dashboard.py): `/api/companies/page`, `/api/company-filter-views` (GET/POST; DELETE `/{view_id}`), `/api/companies/cleanup`, restore `/{batch_id}/restore`;
  `/api/company-email-jobs` and latest/stop; `/api/companies/{company_id}/lookup-contacts`.
- UI: [company-filters.js](../../harvey/web/company-filters.js), `app.js`, `app.css`, `index.html` in `harvey/web`.
- Tables: `companies`, `company_public_emails`, `company_social_profiles`, `company_filter_views`, `company_email_jobs`, `company_email_job_items`; cleanup state is managed through StateManager.

## Constraints, verification and potential

Website availability, redirects, obfuscation and extraction limits affect results.
Format/DNS checks do not prove a mailbox exists. No SMTP probing is implied.
Tests: `test_company_filters.py`, `test_company_pagination.py`, `test_company_cleanup.py`,
`test_company_contacts.py`, `test_company_contacts_browser.py`, `test_email_search_extensions.py`.
Potential: clearer lookup diagnostics and reviewed identity matching; [roadmap](../ROADMAP.md).
Detail: [Öffentliche E-Mail-Suche](../OEFFENTLICHE_EMAIL_SUCHE.md).

## Public email lookup diagnostics (R07, implemented 2026-10-19)

`lookup_diagnostics.py` provides stable stage/reason codes and sanitized source URLs
(no userinfo/query/fragment or raw exception messages). Email lookup distinguishes
HTTP status, timeout/network failure, host-guard block, unsupported content/size,
browser fallback failure, no website, found and no email in the checked pages.
Not found describes only the bounded pages, never proof of no mailbox. Partial
failures remain visible even when another page was readable or an email was found.
DNS/domain evidence remains optional and does not verify mailbox deliverability.

Durable email job items store diagnostic_json and attempts. The existing result dialog
shows per-company evidence, reason/stage, HTTP status, sanitized source and attempt
count, including an explicit unknown diagnostic for legacy items. Single explicit
company lookups also expose diagnostics in the dialog (not a new durable job).

POST `/api/company-email-jobs/{id}/retry` only requeues transient failed or incomplete
not_found items from a completed job. It requires no other active email job, a
60-second cooldown and fewer than three total attempts per company/job. Successful,
no-website, permanent guard/content errors and stopped jobs are not retried. Existing
two-worker concurrency, quick/thorough per-lookup budgets and stop behavior remain.
Restart recovery also respects the three-attempt ceiling; no anti-bot bypass or new
mail sending/contact creation is added. A fresh manually requested job is a separate
operation, not an automatic retry loop. People lookup retains its existing behavior.

Tests: `test_lookup_diagnostics.py`, `test_contact_jobs.py`, `test_company_contacts.py`.

## Company profile dialog (2026-10-19)

Company-name buttons in cohort results and the company list open the same native
dialog. GET `/api/companies/{id}/profile` reads the exact nonremoved company and
known email/phone/social details plus nontrashed contacts. Opening is read-only:
no research, selection changes, navigation or sending. Loading/error states, Escape,
close-button focus restoration and DE/EN labels use the existing dialog shell.
The separate Contacts button retains the existing company contact workspace.

## Delete selected companies (2026-10-20)

Actions → Delete selected companies requires a nonempty selection and confirmation
with the selected count. POST `/api/companies/remove-selected` validates 1–1000
explicit IDs, deduplicates and transactionally soft-removes only active matching
companies using removed_at/cleanup_batch. Active email/people jobs block the action.
No contacts, campaigns, messages or evidence are deleted; contact suppression and
sending state are unchanged. Existing batch undo restores the last removal/cleanup,
including after reload in the same browser session. This is list removal, not a
cascade delete or outreach stop. Filters remain intact; selection clears on success.

## Shared page reads and structured suggestions

See [web extraction](web-extraction.md), implemented 2026-10-20, for the shared
bounded HTTPX reader and explicit review of extruct phone/address/contact-point
suggestions. Existing HTML extraction and contact adoption remain separate.

Company contact adoption now includes a dropdown of the current known email addresses;
see [contacts](contacts.md). Different addresses may become separate company contacts,
while repeated adoption of the same address remains deduplicated.


## Signal-based company reports (2026-10-21)

Companies → select 1–20 companies → Actions → Create optimization report opens the
native report dialog. Choose discovery/profile/people/verification, DE/EN and maximum
evidence age 1–365 days (90 default). Reports use saved data only; creation performs
no collection, does not activate signals, and creates no contacts/campaigns/outbox.
A separate immutable JSON snapshot per company is stored in `company_reports`, with
latest 20 per-company history available in the dialog. Removed companies are hidden.

`company_reports.py` reuses target-profile latest-observation semantics: inactive,
missing, stale/future/invalid timestamps, low confidence and unusable values remain
unknown. A missing/unusable HTTP(S) source also prevents an optimization finding.
Explicit negatives are context, not defects. Boolean positives for no-website listing,
unclaimed listing, missing schema, missing booking and crawler restriction produce
conditional review advice, in that fixed review order; they are not business-impact
scores or a financial prioritization. Other measurements remain contextual facts.
A listing missing a website is not proof that no website exists; crawler restrictions
may be deliberate; a booking feature may be irrelevant to the business model.

The overview's segmented bar counts opportunity/context/unknown records and includes
textual counts; it is not a health score. Every finding retains value, source,
observation timestamp and collection confidence. Snapshot timestamps are UTC.
HTML previews escape source content. Markdown is a direct attachment; PDF / Print
opens an independent, self-contained A4 print view for the browser's Save as PDF.
No new PDF service/dependency is installed.

Optional AI explanation uses existing Brain/configuration with tool restrictions
unchanged, bounded evidence-only input and 90-second timeout. It excludes unknown
facts, validates output length and referenced codes, labels prose for human review,
and stores it separately from the immutable facts. A successful explanation is reused;
failed output leaves the factual report intact. Generated prose may still be wrong
and is not an additional measurement. No provider credentials are added by this feature.

Routes: POST `/api/company-reports`; GET `/history?company_id=`, `/{id}`,
`/{id}/preview`, `/{id}/markdown`; POST `/{id}/explain`. Preview query
`printing=true` invokes the browser print dialog. Entry points: `company_reports.py`,
`web/company-reports.js`, `company-reports.css`. Tests: `test_company_reports.py`.
GPT Researcher and Evidence informed the report/evidence separation and presentation
pattern only; no source/dependency was copied. Lighthouse/axe audits remain future work.


Mobile report discoverability (2026-10-21): report creation is the first action
below the company menu heading, before email-mode controls. Its contextual hint
explains the empty-selection and 20-company limit states, refreshed on selection
and language changes. The main company toolbar remains unchanged.


### AI signal relevance extension (2026-10-21)

Explanation version 2 covers up to six usable findings, in snapshot order. Each
signal has explicit visibility, AI-search, potential acquisition, next-step and
inference-limit fields. General context (Google Search Central AI features and
OpenAI crawler documentation, reviewed 2026-10-21) is linked separately from actual
company evidence. The prompt distinguishes search from training crawlers, avoids
special-AI-schema/ranking promises, retains explicit negatives and permits indirect/
no established relevance for contact or technology signals. Neither citations nor
business outcomes are measured by this prose.

All fields, lengths, exact known-code coverage and uniqueness are validated. Version-2
output is cached; legacy prose remains readable and exposes Extend AI analysis.
Upgrading requires an explicit click; failure retains the previous explanation.
No new crawl/model permissions or migrations are introduced. Markdown/print preview
include the additional fields and background links in DE/EN. Generated text still
requires human review; schema validation does not establish factual accuracy.


### Scoped row actions and compact bulk menu (2026-10-21)

The final company column is Actions: an icon dropdown with profile, contact count,
add contact, report, public email search, decision-maker research, people search,
scoped cleanup and reversible removal. Keyboard arrows/Home/End/Escape/Tab and
outside-click dismissal are supported. Row commands pass explicit company IDs and
do not replace the current bulk selection; report callbacks retain row focus.
Single-company cleanup posts `company_ids` to the existing cleanup route, applying
all existing contact-channel/active-job checks only inside that scope. Invalid or
empty explicit scope is rejected rather than falling back to inventory. Omitted
body retains the original global cleanup behavior; undo batches remain exact.
Email jobs and removal likewise accept explicit row IDs; bulk removal now serializes
Map keys rather than entries. Busy-state guards are preserved.

Persistent explanations are removed from the bulk menu. Native titles and accessible
hover/focus tooltips expose source-mode, report availability and action scope. Row
menu items have labels/icons only. Global cleanup remains inventory-wide and is
identified as such in its tooltip. No sending/approval/identity logic changes.
Entry point: `web/company-actions.js`; cleanup scope covered in
`tests/test_company_cleanup.py`.
