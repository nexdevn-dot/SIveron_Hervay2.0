# Workflow templates and sales opportunities

Code checked: 2026-10-19. [Index](../INDEX.md)

## Reuse a campaign

Campaigns → Save draft as template saves the current campaign first when editable
and dirty. A template stores a normalized sequence (subject, body, rich document,
delay), audience/offer/goal brief, an optional target-profile reference and optional
current Discover criteria. Text is copied literally: remove personal details before
reuse. Sender identity/signature, attachments, recipients, approvals, delivery state,
credentials and spending settings are excluded.

Campaign templates → Create empty draft creates a new manual_draft with zero
recipients and no outbox messages. Select recipients and review each message before
preparation and approval. Apply search criteria is a separate explicit action: it
sets the provider, terms, locations, radius and supported search options, disables
resume and automatic email enrichment, invalidates the preview and starts no search.
A missing target profile is reported; it is not recreated or activated. Deleting a
template leaves campaigns intact. No unrestricted Jinja execution is introduced.

## Continue an interested reply

Open a conversation → Create or link opportunity. An incoming reply and explicit
interest confirmation are required. A conversation can belong to one opportunity;
repeated creation returns its existing association. Additional conversations may be
linked only for the same exact contact, preserving each source campaign and the
opportunity's original campaign. Names/company resemblance never join contacts.

Stages: new, qualified, proposal, negotiation, won, lost. Open stages require a next
task and valid UTC calendar date. Owner is optional free text, not an account or
permission. Title, stage, owner, next task/date and note can be corrected with
revision-checked updates; stale writes return 409. Won/lost allow empty next tasks.
Due open opportunities appear in Today; a future date or closed stage removes that
reminder. Reopening with a due date makes it actionable again.

Saving creates no mail, approval, invitation, qualification assessment or suppression
change. Opportunity stages remain distinct from manually recorded conversation
outcomes. No revenue, calendar integration, drag-and-drop board or automatic sales
qualification is implied.

## Entry points and storage

- [sales_workflows.py](../../harvey/sales_workflows.py): recipe/field validation and
  /api/workflow-templates, /{id}/instantiate, /api/opportunities,
  /api/conversations/{id}/opportunity routes.
- [sales-workflows.js](../../harvey/web/sales-workflows.js): explicit reuse and
  opportunity dialogs, pagination, DE/EN labels and missing-profile warnings.
- [work_items.py](../../harvey/work_items.py): derived due opportunity reminders.
- [state.py](../../harvey/state.py): append-only migration for workflow_templates,
  opportunities and opportunity_conversations.
- [test_sales_workflows.py](../../tests/test_sales_workflows.py): exclusion boundaries,
  stale revisions, explicit interest, idempotency, exact-contact linking and task dates.

List opportunities is paginated (30 rows). Search recipes are whitelisted; existing
provider preflight remains authoritative. Templates are local snapshots, not shared
accounts or a deployment of listmonk/Frappe CRM; those are workflow references only.

## Reuse contract

Reuse interfaces inspected: 2026-10-23. See the
[detailed reuse guide](../reuse/campaigns-and-delivery.md) for inputs/outputs,
transitive dependencies, data and side effects, failure semantics, extraction steps,
examples and relevant tests. The [catalog](../REUSABLE_COMPONENTS.md) distinguishes
small logic, adapter seams and application-coupled workflows; these modules are
not a separately versioned public SDK.
