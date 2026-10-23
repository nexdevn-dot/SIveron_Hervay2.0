# SIveron: local development

This checkout is a neutral development environment, not a configured business.
Respond to the owner in German unless requested otherwise.

## Commands and runtime

- Setup/rebuild: `bash scripts/setup.sh`
- Dashboard: `bash scripts/dashboard.sh` (127.0.0.1:5555)
- Tests: `bash scripts/test.sh`
- Check local installation: `bash scripts/doctor.sh`
- SIveron CLI: `scripts/harvey status` (or other upstream commands)
- Pinned Codex CLI: `scripts/codex --version`
- Python: `.venv/bin/python`; do not use macOS system Python 3.9.

Python 3.12.15 and Codex CLI 0.159.3 are installed inside this checkout.
Keep the global Codex CLI and user-level configuration unchanged. SIveron's
upstream Codex lockdown requires its pinned version. Following the owner's
request to use another available model, this checkout also supports
`gpt-6-luna` (or the verified fallback `gpt-6.1-sol`) with
`brain.codex_restricted_text: true`. This local extension
permits only the separately verified intrinsic computation tools, with no
host capabilities; any tool-call event still aborts the turn. The normal
upstream tool-less mode remains available for compatible models.
Do not remove version or auth checks, grant file/shell/network/MCP access,
accept tool calls, or expand the supported model list without capability tests.

## Configuration

`config/development.yaml` is the neutral template. `harvey.local.yaml` is the
gitignored active configuration; `.env` holds integrations, initially empty.
Do not invent a product, sender identity, business, target group or credentials.
Product training and mailbox setup are intentionally incomplete.
Do not treat the older setup suggestions in CLAUDE.md as overriding this setup.

Email and LinkedIn are disabled, the daily send cap is zero, approvals are
required, and the initial database sending switch is paused. Preserve these
development defaults unless the user requests enabling live operation.
Do not start campaigns, contact prospects or approve mail as a setup/test step.
Leave all prospecting signals unconfirmed until the user chooses them.

## Development

Keep upstream application code unchanged for environment-only tasks. Make
focused changes and run relevant tests; run the existing full suite before
reporting a completed environment setup. The upstream tests use mocks; a
passing suite does not prove live model access or mailbox delivery.

Secrets, authentication files, SQLite state, personal product knowledge,
runtime installations and exports stay out of Git. Never display tokens or
copy credential contents into documentation or a chat. No automatic pushes.

Source: https://github.com/ethanplusai/harvey
Read START_HERE_DE.md for the local workflow and remaining live-use steps.

## Engineering documentation

Start with `docs/INDEX.md`, then read only the module relevant to the task.
Use `docs/ARCHITECTURE.md` for cross-module changes and `docs/DEVELOPMENT.md`
for verification commands. Documentation is a navigation aid; verify the cited
code before changing behavior. Existing runtime and safety rules above still apply.

For functional changes, update the affected `docs/modules/` document in the same
change and refresh its code-check date after inspection. Keep implemented facts
separate from proposals in `docs/ROADMAP.md`. Link sources rather than copying
large code blocks. Do not read every module for a narrow task or store secrets,
private runtime configuration, customer data or authentication contents in docs.
Technical docs use English; user-facing help stays DE/EN. Older dated assessments
are historical snapshots. Generate user manuals from `harvey/web/help-content.js`.
