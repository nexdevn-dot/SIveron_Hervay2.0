# Develop Siveron locally

Siveron is developed by **Bao Dang**, based on **Harvey by Ethan Rogers**,
v0.3.0 (`e2632eb`). Application code and local modifications remain MIT-licensed.
See [attribution](AUTHORS.md), [licenses](THIRD_PARTY.md) and the
[development comparison](docs/DEVELOPMENT_STATUS_2026-10-20.md).

This is a neutral development environment. You supply your own business details
and service accounts only if you later choose a live use case.

## Prerequisites and platforms

- Git, Bash, Node.js with npm (CI uses Node.js 20), and an existing Python 3
  with pip to bootstrap uv.
- Internet access for the initial runtime, dependency and Chromium downloads.
- macOS or Linux for the documented Bash setup and Codex integration. Linux may
  also need Chromium system libraries; if Playwright reports missing libraries,
  install them using your distribution's package manager or Playwright's
  `install-deps chromium` command with the appropriate administrator permissions.
- CI tests Python 3.11/3.12 on Linux, macOS and Windows. This does not establish
  native Windows support for the Bash setup scripts. Codex is explicitly refused
  on native Windows; use a separate Linux environment such as WSL for this setup.
  The WSL onboarding path has not been independently verified.

Setup installs Python **3.12.15**, a local virtual environment and Codex CLI
**0.159.3** inside the checkout. Use the repository wrappers; keep global Codex
configuration unchanged. There is no need to install Codex globally.

## Install and start

```bash
git clone https://github.com/nexdevn-dot/SIveron_Hervay2.0.git
cd SIveron_Hervay2.0
bash scripts/setup.sh
bash scripts/doctor.sh
bash scripts/dashboard.sh
```

For contributions, clone your own fork instead. All commands run from the
repository root; the folder may have any name.

Open http://127.0.0.1:5555 and stop the dashboard with Ctrl+C.
To use another port: `HARVEY_PORT=5556 bash scripts/dashboard.sh`.
Starting the dashboard does not start the sales agent or authorize sending.
The setup and diagnostic scripts currently print some German status messages.

Setup creates `.env` from `.env.example`, `harvey.local.yaml` from
`config/development.yaml`, and a local database with sending paused. Existing
private configuration is preserved. After moving a checkout, recreate `.venv`
by rerunning setup because virtual environments contain absolute paths.

```bash
bash scripts/test.sh -q
scripts/harvey status
scripts/codex --version
```

Use `.venv/bin/python` for Python commands. See
[CONTRIBUTING.md](CONTRIBUTING.md) and [development checks](docs/DEVELOPMENT.md).

## What works without service credentials

You can open the dashboard, inspect and modify the code, and run the standard
mocked tests without a model login or mailbox credentials. A missing AI login in
status output is expected on a fresh installation and does not prevent UI work.
OpenStreetMap discovery requires network access but no provider account; actually
running discovery is a separate user action, not part of setup.

| Optional capability | Access you provide |
| --- | --- |
| AI assistant, AI analysis and generation | A supported Claude/Codex setup with your own authentication and usage allowance |
| Codex provider | File-based Codex CLI authentication; run `scripts/codex login` yourself if needed, then `scripts/harvey status --check` |
| Email sending and replies | Your own configured Gmail OAuth, SMTP/IMAP or other supported mail provider |
| Provider-backed discovery, contact lookup and verification | Your own credentials for the selected provider; consult `.env.example` and dashboard settings |
| LinkedIn | Separate account configuration; disabled by default and unnecessary for development |

The neutral template selects `gpt-6-luna` with `codex_restricted_text: true`.
Availability depends on your account. The separately supported restricted-mode
alternative is `gpt-6.1-sol`; do not assume arbitrary models are compatible.
Keep version, authentication and capability checks intact. The restricted mode
does not grant host file, shell, network or MCP access; tool-call events still
abort the turn. The upstream tool-less mode remains available for compatible models.
A desktop-app login alone does not guarantee the required CLI authentication.
Never copy another person's authentication files.

## Private configuration and live use

Edit private settings in `harvey.local.yaml`; store integration credentials in
`.env`. These files, SQLite state, runtime directories, exports and product
knowledge must stay out of Git. `.env.example` is a reference for variable names;
its legacy references to `harvey.yaml` do not replace this checkout's active
`harvey.local.yaml` configuration.

Email and LinkedIn are disabled, the daily sending limit is zero, approvals are
required and the initial database sending switch is paused. Leave these defaults
in place for development. No business, sender identity, target audience or
confirmed prospecting signals are supplied.

Live use is a separate configuration step: supply and review your business and
product details, choose signals, connect your own mailbox and review applicable
outreach requirements. Enable sending only intentionally. Do not use real
campaigns or messages as setup tests. Mocked tests prove neither live model
access nor mail delivery. Calendar booking remains a placeholder.

## Where to go next

- [English user guide](docs/USER_GUIDE_EN.md) and [German manual](docs/HANDBUCH_DE.md)
- [Engineering index](docs/INDEX.md), [architecture](docs/ARCHITECTURE.md) and [roadmap](docs/ROADMAP.md)
- [Publishing and private-data checks](docs/PUBLISHING.md)
- [German local setup notes](START_HERE_DE.md), which include dated owner-specific history
