# FAQ and troubleshooting

## Do I need accounts to start developing?

No service credentials are needed for the local dashboard, code changes or the
standard mocked tests. Setup needs internet access to download dependencies.
AI and optional external services require your own access when you choose to use them.

## Why does the interface say Siveron but commands say harvey?

Siveron is the visible product name. Python package names and CLI paths retain
`harvey` for compatibility with the original application.

## Why is business setup incomplete?

The public template intentionally has placeholder business details and no trained
product or mailbox. An incomplete business-setup indicator is expected during
neutral development; do not invent an identity to make it disappear.

## Why is nothing being sent?

Email and LinkedIn are disabled, the daily cap is zero and the initial database
sending switch is paused. Opening the dashboard does not start the sales agent.
These are intentional development defaults, not faults to bypass.

## AI access is unavailable. Is installation broken?

Not necessarily. `scripts/harvey status` and `scripts/harvey status --check` help
distinguish runtime status and provider preflight. Use the pinned repository
wrappers, check your own CLI authentication and supported model availability.
Do not remove guards or copy another person's authentication files.

## The virtual environment fails after moving the folder

Virtual environments contain absolute paths. Recreate `.venv` and rerun
`bash scripts/setup.sh`. Preserve private configuration and database files;
do not reset them as a generic troubleshooting step.

## Port 5555 is already occupied

Run `HARVEY_PORT=5556 bash scripts/dashboard.sh` and open
http://127.0.0.1:5556 instead.

## Chromium reports missing Linux libraries

Read Playwright's diagnostic output and install the reported system dependencies
using the appropriate administrator permissions. A Python dependency installation
alone does not supply every operating-system browser library.

## Does Windows CI mean the complete installation works on Windows?

No. The Python suite tests Windows paths, but the documented setup uses Bash and
Codex is refused on native Windows. See [Getting started](Getting-started) for
platform boundaries. WSL onboarding has not been independently verified.

## Are missing signals or discovered emails verified facts?

No. Missing evidence is distinct from a negative finding. Research coverage is
limited by sources and access. A found address is not automatically verified.
Review provenance and applicable verification before operational use.

## Where should I report a problem?

Use [GitHub issues](https://github.com/nexdevn-dot/SIveron_Hervay2.0/issues) with reproducible steps and sanitized details.
Include your OS, runtime versions, expected behavior and actual behavior. Do not
post credentials, customer data or exploitable security details publicly.
See [contribution guidance](https://github.com/nexdevn-dot/SIveron_Hervay2.0/blob/main/CONTRIBUTING.md).
