# Campaign drafting and composer

Code checked: 2026-10-19. [Index](../INDEX.md) · [Delivery](delivery.md)

## Purpose and workflow

Choose eligible contacts, create a held draft, edit sequence steps, inspect personalized
previews, save, then prepare for approval. Saving a draft does not enqueue or send it.
Preparation produces reviewable messages in the outbox. Review/approval is a separate
step from actual scheduled delivery.

The composer supports rich content, personalization placeholders and attachments.
Content validation/sanitization and attachment validation belong to the backend, not
only the editor UI. Recipient membership and delays are part of the draft payload. Preparation snapshots
per-step spacing into the outbox; native follow-ups wait for the successful
predecessor and elapsed delay, not preparation time alone. See [delivery](delivery.md).
Company mailbox recipients need an appropriate general greeting.

AI suggestions are optional: the manual suggestion endpoint requires offer and goal
from planning fields, calls Brain for a validated draft, and returns editable text.
It currently explicitly requests a short German plain-text suggestion; DE/EN UI
localization does not imply bilingual AI generation. Suggestions do not save or
approve a draft automatically. Manual entry remains possible if the model is unavailable.
Autonomous writer behavior is a separate path in `agents/writer.py`.

## Guided manual path (R01)

The editor provides five navigable steps: contacts → draft → preview → preparation →
approval. The next-action button points to the first incomplete step. Basic client
checks are advisory; preparation still uses authoritative transactional backend
validation. Opening preview records a fingerprint of recipient and message data for
this editor session. Changed data and reload require opening preview again. “Opened”
is not evidence that every recipient was manually reviewed.

Saving persists the draft on the server. The browser stores only the last campaign
ID for “Resume last saved campaign”; unsaved input is not autosaved. A stale ID can
be discarded without modifying campaigns. External/read-only campaigns retain their
own workflow. Prepared drafts show pending, approved and sent counts and open the
Outbox scoped to that campaign. Approval remains explicit and separate from delivery.

## Repeated-outreach review (R04, implemented 2026-10-19)

`outreach_history.py` reports other campaign membership, outbox history and overlaps
between selected recipients. Evidence matches an exact contact ID, trimmed/lowercase
email (including stored outbox recipient snapshots), or the same existing linked
company ID. Equal company names without that shared established identity are labeled
uncertain; a common email domain alone is not an identity match. Company identity uses
current stored links; historical company associations cannot be reconstructed from
old messages. No fuzzy matching, remote lookup or entity merge is performed.

Campaign status and individual message statuses/counts remain separate: draft membership
is not delivery, and cancelled/failed records are not reported as sent. Current-campaign
messages are excluded, so ordinary same-sequence follow-ups and idempotent preparation
remain possible. Other selected colleagues and duplicate addresses are reviewable;
existing exact-address deduplication during preparation remains in effect.

Saved draft detail includes `outreach_history` with findings and an evidence digest.
The editor groups records under expandable evidence and an explicit checkbox. Only
saved recipients are represented; saving/preparing refreshes the evidence. Acknowledgment
is session-local and is cleared when opening a campaign. The prepare request carries
`outreach_acknowledgment`; inside the same `BEGIN IMMEDIATE` transaction as staging,
the backend recomputes the evidence and requires the matching digest. Stale/missing
acknowledgment returns `OUTREACH_REVIEW_REQUIRED` without enqueuing anything. Successful
review is recorded as a digest in campaign feedback. It is a review guard, not an auth
credential or permission to override eligibility, suppressions, opt-outs or approval.
No schema migration, new dependency or live sending is required.

Tests: `tests/test_outreach_history.py` covers company colleagues, historical recipient
snapshots, uncertain names, changed evidence, suppression, same-sequence follow-ups,
selected duplicate addresses and terminal history. Existing campaign/sequence tests
continue to cover revision checks, explicit approval and transactional preparation.

## Implementation map

- [crm.py](../../harvey/crm.py): draft payload, storage, eligibility and preparation.
- [crm_routes.py](../../harvey/crm_routes.py): POST `/api/campaign-drafts`; GET/PATCH `/{campaign_id}`; POST `/{campaign_id}/prepare`; POST `/api/campaign-drafts/suggest-text`.
- Attachments: POST `/api/campaign-attachments`, GET `/{attachment_id}`.
- [campaign_content.py](../../harvey/campaign_content.py): rich-content/attachment handling.
- [brain.py](../../harvey/brain.py), [agents/writer.py](../../harvey/agents/writer.py): model boundary and autonomous writing.
- UI: [crm.js](../../harvey/web/crm.js), [campaign-composer.js](../../harvey/web/campaign-composer.js), [campaign-workflow.js](../../harvey/web/campaign-workflow.js); bundles in `web/vendor`, build in `tools/campaign-editor`.
- Tables: `campaigns`, `campaign_attachments`, `prospects`, `outbox`.

## Constraints, verification and potential

Manual campaign eligibility can accept an unverified syntactically valid email;
this does not prove deliverability or remove suppressions, approval/configuration
and schedule gates. Model login/quota/isolation failures must not be bypassed.
Tests: `test_campaign_workflow.py`, `tools/campaign-editor/workflow.test.mjs`, `test_crm_actions.py`, `test_campaign_content.py`, `test_outbox_native.py`, `test_company_contact_sender.py`.
Potential: explicit generation-language choice; see
[roadmap](../ROADMAP.md) for prioritized proposals.

## Campaign results (R06, implemented 2026-10-19)

`campaign_results.py`: GET `/api/campaigns/{id}/results?start=YYYY-MM-DD&end=YYYY-MM-DD`.
No dates means all stored dated history. Bounds use UTC, start inclusive and end
inclusive through its day (implemented as next-day exclusive). The report is a table
of independent measured stages, not an inferred monotonic funnel/conversion rate.
Coverage is stored local records only; hosted-provider history, research attribution,
revenue and inbox delivery cannot be inferred and are labeled unavailable.

Counting contract:
- A unique participant is a stored contact ID in current campaign membership, its
  local outbox or its explicitly associated conversations. No email/company identity
  merge is guessed. Current members are a separate denominator.
- Current contactability checks current members for email syntax, trash, blocks and
  suppressions. It is a current snapshot, irrespective of event window, not proof of
  mailbox deliverability or permission to recontact an existing lifecycle.
- Approval counts use first recorded `outbox.approved_at`; new insert/update triggers
  record future approvals, including configured autoapproval. No legacy timestamps
  are backfilled. Counts include a recorded approval even if later cancelled.
- Sending counts only status=sent with readable sent_at (provider acceptance, not
  inbox delivery). Approval and send contacts and message-row counts are separate.
- Incoming replies count nonempty prospect messages, deduplicating provider receipt
  per contact across threads (fallback: timestamp+content). No outgoing/quoted-thread
  inference. Distinct replying contact IDs and incoming message counts are separate.
- Qualified/meeting outcomes are explicit current manual assessments. For each field
  the latest assessment per contact within the campaign wins across threads; its
  timestamp must fall in the selected window to count. These are not reconstructed
  historical event series. Unassessed conversation counts remain visible.
- Undated legacy approvals/sends/replies are excluded from dated counts and reported
  separately. Current participants/membership and message-status counts are not
  filtered by the event window. Historical deleted/missing contacts retain counted
  IDs; opening them may report unavailable. Unknown research is never inventory size.

The Campaigns list offers Results. The dialog links counted contacts, individual
local messages and campaign conversations, preserving exact associations. It does
not overwrite an unsaved draft, approve/send or silently qualify an interested reply.

Conversation GET `/api/conversations/{id}/review` returns latest display data, outcome
and review digest. POST `/review` requires the same digest. POST `/outcome` accepts
nullable booleans qualified/meeting, a <=2000-character note and exact revision.
Unknown is stored as NULL. First save requires revision 0; subsequent writes increment
it transactionally. Corrections are explicit; changing only a note preserves outcome
assessment dates. Existing AI intent/stage/status is independent and is not edited by
these manual fields. No opportunity, meeting invitation or calendar event is created.
Tests: `test_campaign_results.py`, `test_work_items.py`.

## Templates and sales continuation

See [sales workflows](sales-workflows.md) for implemented template reuse, explicit
opportunities, exact conversation links and due tasks in Today (checked 2026-10-19).

## Connected preparation stepper

The guide uses connected icon nodes with explicit complete/current/upcoming labels,
`aria-current="step"` only for an unfinished current step, native keyboard buttons,
and vertical connectors below 700px. When approval is complete there is no current
preparation step. Outbox message counts are displayed separately: sent, awaiting
approval and approved. All sent requires every counted local message to be sent;
failed/rejected/cancelled records request review. This is neither a time estimate nor
an inbox-delivery guarantee. No percentage or automatic advancement sends mail.
Independent styling follows the existing tokens; Chakra Steps was a visual reference,
not an imported React dependency. Tests: `tools/campaign-editor/workflow.test.mjs`.

## Reuse contract

Reuse interfaces inspected: 2026-10-23. See the
[detailed reuse guide](../reuse/campaigns-and-delivery.md) for inputs/outputs,
transitive dependencies, data and side effects, failure semantics, extraction steps,
examples and relevant tests. The [catalog](../REUSABLE_COMPONENTS.md) distinguishes
small logic, adapter seams and application-coupled workflows; these modules are
not a separately versioned public SDK.
