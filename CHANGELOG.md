# Changelog

Notable changes to Siveron. Dates are release dates; the format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) loosely and versions
follow [semver](https://semver.org/), with the caveat that Siveron is pre-1.0 and
minor versions can still change behaviour.

## [Unreleased] — local checkout, documented 2026-10-20

These entries summarize local development, not a published upstream release.
Local product direction and development: **Bao Dang**, extending Harvey by **Ethan Rogers**.
The application/local modifications remain **MIT**. See [attribution](AUTHORS.md)
and [the verified v0.3.0 comparison](docs/DEVELOPMENT_STATUS_2026-10-20.md).
For implementation boundaries and remaining proposals see [engineering docs](docs/INDEX.md)
and [roadmap](docs/ROADMAP.md). No new live validation is claimed by this documentation update.

### Added

- Company-row action dropdowns with explicit per-company scope, reversible scoped
  cleanup/removal, and compact bulk actions with hover/focus explanations.

- Extended report AI explanations: per-signal visibility, AI-search, potential
  acquisition, next steps and limits, with separate background sources and explicit
  upgrade of legacy explanations.

- Company-specific signal reports with saved DE/EN evidence snapshots, conditional
  recommendations, per-company history, Markdown download, PDF via browser print
  and optional separately labelled AI explanations.

- Contact-specific public email research with website, SerpApi/Serper and public profile
  hints, optional published-only Hunter results, bounded settings, persisted evidence
  and explicit reviewed contact adoption; localized DE/EN help.

- Guided campaign steps, shared delivery readiness and predecessor-based sequence spacing.
- Saved target profiles, cross-campaign outreach review, central tasks and manual outcome/result reporting.
- Workflow templates and explicit sales opportunities linked to source conversations.
- Company profile dialog, reversible selected company removal and structured field review.
- Shared bounded HTTPX page reader, extruct organization/contact-point suggestions,
  common email format checks and a TTL-aware DNS resolver cache.
- Subscription quota reading timestamp and explicit refresh bypassing the cached value.

- Native local Google Maps discovery with quick/grid sections, exact-radius checks,
  resumable checkpoints and source identities; no separate scraper service.
- Shared quick/thorough public email lookup, structured-data extraction, format/DNS
  checks and evidence; optional email phase scoped to a discovery run.
- Public person candidates with explicit review/acceptance and manual/company contacts.
- Company pagination, contextual facets, multi-value filters and persisted filter views.
- Contact notes, edit, suppression and recoverable deletion; pending-message cancellation.
- Held campaign drafts, optional AI text suggestions, rich-text composition,
  personalization, preview and native email attachments.
- Native approval/scheduled outbox workflow, sending settings and visual message status;
  conversation grouping by campaign with separate thread dialogs.
- Sidebar workspace, header agent switch, bilingual help and compact icon action popovers.
- Technical index, architecture, module maps, development workflow and separate roadmap.

### Changed

- Manual campaign paths accept valid email addresses without mandatory technical
  verification; suppression, approval and delivery gates remain applicable.
- Eligible company contacts are supported by sender checks without inventing person data.
- Company selection toolbar/help are hidden; Actions is left-aligned. Row checkboxes remain.
- Discovery source-specific options and optional email lookup precede the separate
  Search criteria section containing business terms, location and radius.
- Visible branding uses Siveron; technical `harvey` paths and CLI names remain.

### Known boundaries

- Activated signals govern recorded observations, not automatic signal-based import acceptance.
- Public email validation does not prove mailbox delivery; public profiles do not prove identity.
- Maps page structure, quotas and provider availability constrain results; complete coverage is not guaranteed.
- Model suggestions remain optional and subject to pinned CLI, login, quota and isolation checks.
- Mock tests and UI checks do not establish live provider success or unattended production readiness.

## [0.3.0] — 2026-10-13

### Added

- **Opt-in Codex brain (ChatGPT plan).** Set `brain.provider: codex` (or pick
  it in `harvey setup`, or `harvey train --provider codex`) to think with the
  Codex CLI on a ChatGPT subscription instead of Claude. Claude remains the
  default and there is no automatic fallback between providers. Each call
  runs a throwaway, isolated `codex app-server` with no tools; Siveron verifies
  the lockdown from Codex's own reports before sending any prompt, aborts on
  any attempted tool use, refuses API-key logins and custom endpoints
  (checked before your login is exposed to Codex), and never changes your own
  Codex settings or login: each call gets a private copy of the login without
  its refresh token, so an expired login must be renewed with Codex itself or
  `codex login`. Requires Codex CLI 0.159.3; other versions are refused. See
  the README section "Using a ChatGPT plan instead (Codex)".
- `brain.model` picks the model for either provider, for Siveron only. For
  Codex use `gpt-5.5` (suggested by `harvey setup`): the verified text-only
  model. Blank auto-selection only picks listed models without code-execution
  tools, and on current ChatGPT accounts there are none; code-mode models are
  refused.
- If Codex can't be used (expired or renewal-due login, unsupported CLI,
  unsafe Codex config, rejected model, plan usage limit), Siveron pauses the
  heartbeat instead of running agents that would fail: replies stay unread
  and unescalated, queued emails wait, and the reason shows in the log,
  `harvey status` and the dashboard. It resumes on its own once the cause is
  fixed. `harvey status --check` runs the same check (no prompt sent) on demand
  and exits non-zero when it fails. The Codex provider supports macOS and
  Linux; it is refused on Windows (use Claude there).

### Changed

- Each heartbeat now sends email after the agents that read and answer
  replies have finished, and native mail providers (Gmail/SMTP) read the
  mailbox every cycle, so a reply always cancels its queued follow-ups before
  that cycle's sends (previously the two could run at the same time, and a
  reply arriving with no open conversation waited for a later cycle). This
  applies to Claude and Codex alike.
- A reply is only recorded once its reply draft (if it needs one) is
  written, so a brain outage part-way never half-records it. If a working
  brain returns no usable draft, the conversation is flagged for a human
  instead of being left open with no answer.
- Usage is tracked per provider. The budget gate, `harvey usage`, `harvey
  status` and the dashboard read and label the active provider's own quota;
  existing usage history is kept and attributed to Claude.

### Fixed

- Dashboard HTML and text assets now use UTF-8 explicitly, fixing Windows
  decoding failures. Regression tests cover HTML, CSS, JavaScript and SVG.

## [0.2.1] — 2026-10-13

A security release. Update if you run Siveron.

### Security

- **Claude now runs with no tools.** Every Claude call used to run with
  `--dangerously-skip-permissions`, and prompts include text Siveron doesn't
  control: prospect email replies and scraped web pages. Instructions hidden
  in that text could make Claude run commands, read or write files, or use
  the operator's connected MCP servers. Calls now run with `--tools ""` and
  `--strict-mcp-config`; Siveron only ever needed text back, so nothing else
  changes. Reported privately by [@hackchang](https://github.com/hackchang).
  If you ran an earlier version with live replies coming in, check the
  account that ran Siveron for unexpected files or activity.

### Fixed

- `harvey run` no longer drops into the setup wizard when the trained config
  lives in `harvey.local.yaml`; the dashboard reads it too.
- A heartbeat cycle is capped at 10 minutes, so one hung agent can't freeze
  Siveron, and quiet hours are re-checked every 5 minutes so a Mac waking from
  sleep resumes on time.
- Sites that only answer on plain HTTP or `www.` are no longer marked
  unreachable.
- Profile and contact backfills rotate through every company instead of
  retrying the same few forever.
- The trainer writes full place names ("Solon, Ohio") and real job titles, so
  discovery doesn't geocode to the wrong city and found contacts aren't
  silently discarded.

### Added

- Contacts are backfilled for companies found without any, from their own team
  pages and, if a key is set, Hunter's named-people search.
- `HUNTER_MONTHLY_SEARCHES` (default 25) sets one Hunter budget shared by every
  domain search.

Thanks to [@sshaw0729-dotcom](https://github.com/sshaw0729-dotcom) for the
fixes above (#2).

## [0.2.0] — 2026-09-13

The release that made Siveron worth running. The previous version could write
and send email but could not reliably find anyone to send it to, and it needed
a paid third-party platform to send at all. Both are fixed.

### Added

- **A prospecting pipeline that works.** Four stages, each independently
  runnable and re-runnable: DISCOVER (who exists) → PROFILE (what they are) →
  ENRICH (who decides) → VERIFY (can you reach them).
- **DISCOVER, with a provider menu.** Four sources behind one adapter
  interface, shown side by side in the dashboard with what each does, what it
  costs, its free tier and which keys it needs. The default — OpenStreetMap —
  needs no account, no card and no key, so the whole pipeline can be run
  before paying anyone. `harvey discover`.
- **Cost discipline in the collector.** Every discovery run estimates before it
  spends, refuses to start over your cap, re-checks the cap between batches,
  reads a kill switch, and flushes observations per batch so a run that dies
  keeps what it learned. `harvey discover --estimate` prints the projection and
  exits.
- **PROFILE.** Free — three HTTP requests per business, no browser, no model
  call. Reads the incumbent agency out of the site footer, ad pixels, missing
  schema, abandoned blogs, open roles and named people. Chained onto DISCOVER
  and run on every heartbeat. `harvey profile`.
- **A signal catalog you confirm.** Siveron knows how to collect 23 signals and
  collects none of them until a human says so. Each shows a plain-language
  description, what it costs, and how many companies already carry it.
  `harvey signals`.
- **The cohort builder.** Pick what a prospect must have and what disqualifies
  them; see the matching companies live. A prospect list is a query you can
  explain, not a file.
- **Native mail providers.** Gmail (REST + OAuth) and any SMTP+IMAP mailbox.
- **The outbox approval ladder.** Every outgoing email waits for approval by
  default (`pending_review → approved → sent`), reviewed one at a time in a
  decisions desk with `A`/`R`/`J`/`K`. A deterministic pre-send gate — no model
  involved — rejects unrendered merge tags, banned phrases, over-length bodies,
  too many links, HTML, undeliverable addresses and recipient mismatches.
- **Bounce handling and a kill switch.** A bounce marks the address invalid,
  cancels that prospect's queued sends, and trips a global pause past a
  configured bounce rate. `harvey sending pause|resume`.
- **Claude usage tracking.** Per-call attribution by agent, task and model, plus
  live subscription-quota gauges read the same way `/usage` does, so Siveron
  throttles itself and leaves headroom for your own interactive work.
  `harvey usage`.
- **CSV export.** `harvey export` writes a sequencer-ready list. Siveron is worth
  running as a list-builder even if you never let it send.
- **A dashboard worth looking at.** Opens on Today — what needs a human — with
  an activity feed and a rail of pipeline figures, collector runs and setup.
  Light and dark are the same design re-tokenised; appearance follows your OS by
  default. Fonts are vendored so it renders with the network off.
- **A Python version guard.** `python3 -m venv` on macOS builds from the system
  3.9, which cannot run Siveron. It now fails immediately with the fix instead of
  surfacing later as an unrelated-looking ImportError.

### Changed

- **The data model.** Every fact Siveron learns is now an observation — a row in
  `observations`, never a column. A new signal needs no migration, re-observing
  over time is a free time series, and confidence and provenance travel with the
  fact. The vocabulary is governed: a database trigger rejects any signal code
  not in `signal_codes`.
- **Email finding is pattern-first.** Siveron derives the domain's address format
  and verifies one candidate rather than brute-forcing name variations, and
  grades every address honestly as `verified` / `risky` / `guess` / `invalid`.
  Only deliverable addresses are ever sent to.
- **The default mail provider** is now `gmail`. Instantly is still supported as
  a legacy option.
- **Discovery depth defaults to 30, not 100.** Google removed
  100-results-per-page in September 2025, so depth 100 is now billed as ten
  pages nearly everywhere — and below rank 30 it is mostly directories.
- **The dashboard's HTML, CSS and JS** are real files in `harvey/web/` instead
  of a 1,500-line string literal in `dashboard.py`. Still no build step.

### Fixed

- **Guessed emails were being reported as verified** whenever the domain merely
  had an MX record. The migration downgrades every legacy `email_verified=1` row
  to `guess`.
- **Cohorts counted the wrong companies.** PROFILE records a false boolean when
  it checks and finds nothing — which is correct — but `cohort()` matched on the
  row existing, so "companies running Google Ads" silently meant "companies we
  checked for Google Ads", which was all of them. Cohorts now read the newest
  observation per company and signal, and require it to be true.
- **Usage tracking counted every Claude session on the machine**, not just
  Siveron's. The transcript reconciler is gone; the ledger contains only rows
  Siveron's own Brain wrote.
- **Page titles were being extracted as people** ("Request Service", "Commercial
  Services"), and titles bled between team members.
- **Confirming a signal before anything had loaded the catalog** reported success
  while changing nothing.
- **The free OSM provider answered unmapped search terms with every registered
  office in the area** — coffee roasters and churches for a roofing query. It now
  refuses the query and names the trades it can search.

### Security

- Test fixtures no longer carry real businesses' phone numbers or street
  addresses.
- `harvey.local.yaml` (gitignored) overrides the tracked `harvey.yaml`, so a
  fork can hold real product configuration without it reaching a public repo.

## [0.1.0]

Initial release: the heartbeat loop, five sub-agents, the skills library, the
website trainer, Instantly-based sending, and the first dashboard.

### 2026-10-22 — Compact discovery progress

- Discover shows a compact live phase and completion summary. Full phases, timing,
  email results and errors are available through Search details in a native dialog.
- The latest stored run loads collapsed; hiding a completion summary preserves
  access under Last search. Closing details never stops a running search.
- DE/EN help and generated manuals updated; UI state-transition tests added.
