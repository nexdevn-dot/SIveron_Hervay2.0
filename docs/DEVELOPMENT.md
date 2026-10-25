# Development workflow

Code checked: 2026-10-23. See [index](INDEX.md) and [AGENTS.md](../AGENTS.md).

New contributors: start with [CONTRIBUTING.md](../CONTRIBUTING.md) and the
[English setup guide](../START_HERE_EN.md) for prerequisites and optional access.

## Commands

Run from the repository root; examples do not depend on the checkout folder name.

```bash
bash scripts/setup.sh                 # install/rebuild local environment
bash scripts/dashboard.sh             # dashboard at 127.0.0.1:5555
bash scripts/doctor.sh                # local installation checks
bash scripts/test.sh                  # Python suite
scripts/harvey status                 # inspect runtime status
scripts/codex --version               # pinned CLI
```

Use `.venv/bin/python`, not system Python. `config/development.yaml` is the public
neutral template; `harvey.local.yaml` and `.env` are private runtime inputs.
Do not infer current sending settings from templates. Keep global Codex configuration unchanged.

## Small-change procedure

1. Read the relevant module document and its source entry points.
2. Inspect existing changes; preserve work outside scope.
3. Change the narrowest service/UI boundary. Preserve IDs used by existing JS.
4. Run relevant tests below and syntax checks for modified JavaScript.
5. For layout changes inspect desktop/mobile and DE/EN in an isolated preview.
6. Update module facts, checked date and any affected roadmap item. Report actual checks.

| Area | Typical verification |
| --- | --- |
| Discovery | `bash scripts/test.sh tests/test_discover.py tests/test_google_maps.py tests/test_discovery_progress.py tests/test_pipeline.py` |
| Companies | `bash scripts/test.sh tests/test_company_filters.py tests/test_company_contacts.py tests/test_email_search_extensions.py` |
| Contacts | `bash scripts/test.sh tests/test_people_contacts.py tests/test_contact_jobs.py tests/test_crm_actions.py` |
| Campaigns/delivery | `bash scripts/test.sh tests/test_campaign_content.py tests/test_outbox_native.py tests/test_company_contact_sender.py` |
| Frontend | `node --check harvey/web/app.js` (repeat for changed scripts); browser checks |
| Help | `node tools/help-guide/export.cjs` then `node --test tools/help-guide/content.test.cjs` |

Broaden testing for cross-module/schema/lifecycle changes. Environment setup completion
requires the full existing suite. Mock tests do not prove live mail, Maps completeness
or live model availability. Never approve/send mail or start campaigns as a test.
Use a temporary SQLite database and mocked integrations for side-effecting flows.

## Assets and documentation

Local bundle build tools: `tools/company-filters`, `tools/campaign-editor`.
Read their package/build files before rebuilding; retain pinned dependencies and licenses.
See [THIRD_PARTY.md](../THIRD_PARTY.md). User guide source is
`harvey/web/help-content.js`; do not edit generated manuals directly.

Technical docs are intentionally short: link code rather than copying implementation,
list only relevant endpoints/tests, and keep future behavior in [ROADMAP.md](ROADMAP.md).
If a task reveals stale behavior, correct that fact and date; do not claim an audit
of unrelated modules. Never add private customer data, logs containing secrets or credentials.

Schema initialization rechecks user_version under BEGIN IMMEDIATE and executes SQL
statements (including complete trigger bodies) in one transaction; it does not use
executescript's implicit commit during upgrades. Concurrent dashboard/agent initializers
serialize, and failures roll back both schema and version. Tests:
`test_migration_concurrency.py` (parallel upgrade and failed-upgrade rollback).

## Cross-platform CI diagnostics

The matrix runs Python 3.11/3.12 on Linux, macOS and Windows. Individual test names
are logged and the first failure ends that job; a 20-minute job timeout bounds
hung workers. Codex runtime remains macOS/Linux-only with the existing Windows
refusal and capability tests. UTF-8 content is tested with a simulated CP1252
locale. Contact-job concurrency uses an asyncio event barrier rather than a
10ms sleep, so the two-worker assertion is independent of SQLite/filesystem speed.

The restricted-mode configuration-preservation unit explicitly simulates a supported
platform and uses a finite scripted answer sequence. It must not endlessly select
Codex on a Windows host where the real setup correctly refuses it. The separate
Windows rejection/Claude fallback tests continue to exercise the production guard.

## Offline reuse example

Run `.venv/bin/python -m examples.reuse.offline_demo` after setup. It exercises
internal contracts with mocked HTTP, synthetic records, a fake clock and a temporary
database. It starts no model/provider research or delivery. Keep it aligned with the
[reuse catalog](REUSABLE_COMPONENTS.md) when changing documented interfaces.

## WAL startup contention (2026-10-25)

`StateManager._enable_wal` handles SQLITE_BUSY/SQLITE_LOCKED (including extended
codes) while setting journal mode before the migration transaction. Short SQLite
busy waits and asynchronous backoff share one BUSY_TIMEOUT_SECONDS startup budget.
The journal-mode cursor is consumed/closed and the resulting mode must be WAL;
normal connection busy timeout is restored on success. Other errors and cancellation
propagate. Migration locking, version recheck and rollback remain unchanged.
Tests in `test_migration_concurrency.py` cover parallel upgrades/trigger survival,
transient lock codes, a real persistent exclusive lock with no partial migration,
non-lock failure, refused mode, timeout restoration and cancellation.
