# Contacts and people review

Code checked: 2026-10-22. [Index](../INDEX.md) · [Campaigns](campaigns.md)

## Purpose and workflow

Create a known person manually, accept a reviewed public person suggestion, or create
a company mailbox contact. Organizations and contacts are separate entities; a company
mailbox is not converted into a fictitious named person. Review names, roles and sources
before accepting candidates. Contacts can be selected for campaign drafting when they
have a valid email and are not blocked; technical verification is optional for the
manual campaign path. Other sending paths retain their own eligibility checks.

The contact Actions popover provides notes, edit, blocking and recoverable deletion.
Blocking cancels pending/approved local mail and queues remote campaign pauses where
applicable. Opt-out restrictions cannot be removed through ordinary manual unblocking.
Deleting uses trash; restoration preserves blocks and does not restart cancelled mail.

## Implementation map

- [contacts.py](../../harvey/contacts.py): contact creation/edit validation.
- [collectors/people.py](../../harvey/collectors/people.py): public person extraction.
- [collectors/contact_jobs.py](../../harvey/collectors/contact_jobs.py): durable people search.
- [crm.py](../../harvey/crm.py), [crm_routes.py](../../harvey/crm_routes.py): paging, status, notes, block and trash actions.
- [dashboard.py](../../harvey/dashboard.py): `/api/contacts` creation, `/api/person-candidates`, accept/dismiss `/{candidate_id}/accept` or `/dismiss`, `/api/company-people-jobs` and latest/stop.
- CRM routes: `/api/contacts/page`, `/api/contacts/status`, PATCH `/api/contacts/{contact_id}`; `/{contact_id}/notes`, `/block`, `/trash` under `/api/contacts`.
- UI: [contacts.js](../../harvey/web/contacts.js), [crm.js](../../harvey/web/crm.js).
- Tables: `prospects`, `person_candidates`, `company_people_jobs`, `company_people_job_items`, `feedback`, `contact_trash`, `contact_suppressions`, `campaign_pause_requests`.

## Constraints, verification and potential

Public suggestions may be absent or wrong; acceptance is explicit. A profile link is
not verified identity. Do not equate email syntax validity with delivery assurance.
Tests: `test_people_contacts.py`, `test_contact_jobs.py`, `test_crm_actions.py`, `test_company_contact_sender.py`.
Potential: evidence-based profile matching and clearer review diagnostics; [roadmap](../ROADMAP.md).
Detail: [Ansprechpersonen und Kontakte](../ANSPRECHPERSONEN_UND_KONTAKTE.md).

## Shared page reads and structured suggestions

See [web extraction](web-extraction.md), implemented 2026-10-20, for the shared
bounded HTTPX reader and explicit review of extruct phone/address/contact-point
suggestions. Existing HTML extraction and contact adoption remain separate.

## Shared email format results

Contact and campaign APIs expose deterministic email_checks for consistent selection
and transport-format warnings. See [web extraction](web-extraction.md). Reads perform
no DNS queries and do not change verification, suppression or approval states.

## Choose a company email on adoption (2026-10-20)

The company contact editor fetches the selected company's current profile and offers
all known email addresses in a native dropdown. Multiple addresses require an explicit
choice; a single address prefills only an empty input. Manual entry remains available.
Changing company/type resets the picker; stale requests cannot overwrite a new dialog.
Selection copies the address only, not verification or personal identity. Editing an
existing contact and adopting a Person candidate retain their existing behavior.

Different company mailboxes can now create separate company contacts even with the
same company phone. Re-adopting the same address stays idempotent. Cross-contact email
collisions (including named people), trash and suppression rules remain protected;
existing records are not silently overwritten or converted. No mail is prepared/sent.

## B2B decision-maker research (2026-10-20)

Contacts → Research decision makers (also Companies → Actions) opens the target-role
research dialog. Choose explicit existing companies and one or more supported roles:
management/owner, sales, marketing, IT/engineering, HR, finance, purchasing, operations.
This independently adapts OpenOutFind's target → qualify with reason → contact handoff
workflow; no GPL source or OpenOutreach runtime dependency is incorporated.

The first source is public official company websites, reusing the bounded shared page
reader and person collector. No paid data service, social-account scraper, guessing
of email addresses or new model calls are introduced. No website means no website-based
result. This is not equivalent in coverage to OpenOutFind's licensed people database.
A published role is a hint for human review, not proof of identity or purchasing authority.

`company_people_jobs.criteria_json` stores this run's roles; empty retains the existing
unrestricted people search. Only candidates actually returned by this collection are
qualified and associated through `decision_maker_results`. Missing/generic/unmatched
roles are unknown, explicit former/support/training roles are no_match, and known
published title vocabulary yields match. Roles are OR within the selected role set.
There is no probabilistic or uncalibrated fit score. Categories do not confirm prospecting
signals. Legacy/accepted/dismissed people are not reopened by collection.

Per-run candidate/fit/evidence snapshots remain distinct from later research. The result
filter provides match/unknown/no_match/all, uncapped inventory counts and 20/page. Names,
source URL, discovery date, published role and personal channels accompany each result.
Changed snapshots cannot be bulk-adopted: an evidence fingerprint is checked again inside
create_contact's existing BEGIN IMMEDIATE transaction. Review and edit fetches current
candidate fields. Removed companies are excluded. Contact adoption requires explicit
selection and source-review acknowledgment; per-person created/duplicate/unavailable/
review_required results make partial completion visible. Missing email is allowed;
email validity/verification, duplicate/trash/suppression and campaign rules are unchanged.
No outbox entry is created, no contact is approved or mailed automatically.

Entry points: `decision_makers.py`, `web/decision-makers.js`, `decision-makers.css`;
GET `/api/decision-makers/roles`, `/latest`, `/jobs/{id}`, `/results?job_id=&verdict=&page=`;
POST `/api/company-people-jobs` with `decision_makers.roles`; POST
`/api/decision-makers/adopt` with exact job/candidate IDs and reviewed=true.
Tests: `test_decision_makers.py`, `test_people_contacts.py`, `test_contact_jobs.py`.


## Contact-specific email research (2026-10-20)

Contacts → row Actions → Research email opens a native dialog with source selection,
quick/thorough mode, persisted findings and explicit one-address adoption. Settings →
Contact research configures enabled sources, SerpApi/Serper, page/query ceilings,
UTC-month request reservations and optional Hunter. Hunter is off by default.
Keys use the existing environment settings endpoint; only presence flags are returned.

`contact_research.py` reuses the public reader, company contact links, person entity
extraction, email normalization and existing discovery adapters. It makes no model calls.
Website pages and actual organic result pages are read; snippets are not email evidence.
Targeted searches and observed public links cover LinkedIn/Facebook/TikTok hints without
login automation or bypasses. Unreadable pages retain links for manual review.
Hunter uses `/v2/email-finder/found` (published results only) with a header credential;
its verification/confidence is not imported. PyHunter and theHarvester inform the adapter
pattern only; no new package or GPL code is incorporated.

Findings distinguish explicit person entity in company context, company mailbox,
provider suggestion and unclear association. These labels are evidence heuristics, not
identity or deliverability proof. A run stores criteria/contact snapshot in
`contact_email_research`; findings live separately in `contact_email_findings`.
Quick stops after explicit personal evidence; thorough stays within the configured caps.
One active contact run is allowed per database, total timeout 150 seconds. Stop/disable
is checked between operations. A process restart marks orphaned runs interrupted and
never resumes paid calls automatically. Source settings are snapshotted per run; the
master switch and reduced monthly limits are reread during execution.

Adoption requires a selected finding, explicit review, replacement acknowledgment for
an existing address and additional acknowledgment for nonpersonal findings on a person.
It reuses `contacts.create_contact` with a second evidence/snapshot/suppression check
inside BEGIN IMMEDIATE. Stale contact revisions, cross-contact findings, trash, removed
companies, duplicates and suppressed destinations are rejected. Source notes and
adopted_at commit atomically with the normal edit, verification reset and queued-mail
cancellation. Contact source attribution is retained; no outbox item is created.

Entry points: `contact_research.py`, `web/contact-research.js`, `contact-research.css`.
API: GET/POST `/api/settings/contact-research`; POST
`/api/contacts/{id}/email-research`; GET `/latest` or `/{job}` under that path;
POST `/{job}/stop`, `/{job}/adopt`. Tests: `tests/test_contact_research.py` plus
existing contact edit/queue/suppression tests. User help: `contact-email-research`.


## Wrapped person cards (2026-10-21)

The person parser now recognizes a name wrapped in its own paragraph followed by
role and plaintext email paragraphs in the same small card, as used by WordPress.
It inspects at most three ancestor blocks, each limited to 600 characters and one
name heading/strong element, and reuses public email normalization. Multiple distinct
mailboxes remain ambiguous; role mailboxes are not attached to named people.
No emails are inferred from naming patterns. Regression tests cover adjacent cards
and prevent borrowing another person's role or email.

### Contact research preference switches (2026-10-22)

The five boolean research settings (enabled, website, web, profiles, Hunter) use
shared preference-switch styles in app.css, matching the assistant/Signals green
track and white thumb. Native checked inputs with role=switch retain form
serialization, label/keyboard activation and the existing explicit Save action.
This UI change neither enables Hunter nor starts a research job. DE/EN and
existing values are preserved. Selection checkboxes inside research workflows
are unchanged.
