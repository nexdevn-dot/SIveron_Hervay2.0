# Getting started

## Requirements

Use macOS or Linux for the documented Bash setup and Codex integration. You need
Git, Bash, Node.js with npm (CI uses Node.js 20), an existing Python 3 with pip,
and internet access for the first installation. Linux may need additional Chromium
system libraries. Follow Playwright's missing-library diagnostics if installation
reports them.

Native Windows is not a verified path for these setup scripts, and Codex is
explicitly refused on native Windows. A separate Linux environment such as WSL is
an alternative, but WSL onboarding has not been independently verified.

## Install

```bash
git clone https://github.com/nexdevn-dot/SIveron_Hervay2.0.git
cd SIveron_Hervay2.0
bash scripts/setup.sh
bash scripts/doctor.sh
bash scripts/dashboard.sh
```

Open **http://127.0.0.1:5555/**. Stop the dashboard with **Ctrl+C**.
For another port, use `HARVEY_PORT=5556 bash scripts/dashboard.sh`.

Setup installs Python **3.12.15**, Codex CLI **0.159.3**, dependencies and Chromium
inside the checkout. It creates private configuration and a local database without
overwriting existing private settings. It does not require a global Codex install.
Some setup/diagnostic messages are currently in German.

## Verify your environment

```bash
bash scripts/test.sh -q
scripts/harvey status
scripts/codex --version
```

The dashboard and standard mocked tests do not require model or mailbox credentials.
Use `.venv/bin/python` for Python commands and the repository's CLI wrappers.
Keep global Codex configuration unchanged.

A fresh public checkout was installed and checked on macOS on **2026-10-23**:
setup and doctor succeeded, the dashboard returned HTTP 200, and the standard
suite reported **851 passed, 22 skipped**. This is a dated check, not evidence
of live AI access, mail delivery or successful Linux/Windows installation.

Next: [Features and workflow](Features-and-workflow) or
[Development and contributions](Development-and-contributions).

Detailed reference: [English setup guide](https://github.com/nexdevn-dot/SIveron_Hervay2.0/blob/main/START_HERE_EN.md).
