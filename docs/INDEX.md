# Engineering documentation

Local Siveron product direction and development: **Bao Dang**; original Harvey by
**Ethan Rogers**. MIT remains in effect for application/local modifications.
[Attribution](../AUTHORS.md) · [Baseline comparison](DEVELOPMENT_STATUS_2026-10-20.md).

Code checked: 2026-10-19. Scope: this local checkout, not upstream Harvey generally.
Technical documentation uses English; owner communication and user help retain DE/EN support.

## Read only what the task needs

1. Read repository [working rules](../AGENTS.md).
2. Choose one module below. Follow its source links before changing behavior.
3. Read [architecture](ARCHITECTURE.md) only for cross-module changes; use
   [development](DEVELOPMENT.md) for commands and validation.
4. Update the affected document with the code. Read [roadmap](ROADMAP.md) for planned work.

| Task | Start here |
| --- | --- |
| Find businesses, providers, radius, progress | [Discovery](modules/discovery.md) |
| Public page downloads, structured field suggestions | [Web extraction](modules/web-extraction.md) |
| Company list, filters, email lookup, cleanup | [Companies](modules/companies.md) |
| Decision-maker research, people suggestions, contact adoption, blocking/deletion | [Contacts](modules/contacts.md) |
| Signal activation, observations, cohorts | [Signals](modules/signals.md) |
| Drafts, editor, AI suggestions, attachments | [Campaigns](modules/campaigns.md) |
| Reusable templates, opportunities, next sales tasks | [Sales workflows](modules/sales-workflows.md) |
| Approval, scheduling, delivery, replies | [Delivery and conversations](modules/delivery.md) |
| Settings, agent controls, usage, languages, help | [Platform](modules/platform.md) |

## Research

[Open-source candidates](OPEN_SOURCE_CANDIDATES.md) maps reusable components and workflow references to roadmap IDs. Research is not adoption.

## Documentation boundaries

- These files describe implemented behavior, not a complete API reference or a copy of code.
- Each module lists representative entry points, tables and tests; consult implementation for all fields.
- Checked dates mean source inspection, not proof of live external-service operation.
- Development defaults do not describe the owner's current private configuration. Never copy it here.
- Older dated assessments (for example `ENTWICKLUNGSSTAND_2026-10-16.md` and
  `KAMPAGNEN_REIFEGRAD_2026-10-16.md`) are historical snapshots, not current specifications.
- Existing topic documents provide deeper context; resolve conflicts against current code and AGENTS.md.
- User manuals: [Deutsch](HANDBUCH_DE.md), [English](USER_GUIDE_EN.md).
  Their source is `harvey/web/help-content.js`; regenerate rather than hand-edit.

## Product discussion brief

[German ChatGPT product brief](CHATGPT_PRODUKTBRIEF_DE.md) is a standalone,
owner-facing snapshot with workflows, boundaries, roadmap context and a reusable
critical-review prompt. It contains no private runtime or customer data.

## Publishing

[GitHub publication guide](PUBLISHING.md) covers repository remotes, credential
exclusions and the local pre-publication check. [GitHub About text](GITHUB_ABOUT.md)
contains the prepared short description/topics. README.md is the public project overview.
