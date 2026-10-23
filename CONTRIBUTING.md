# Contributing to Siveron

Contributions are welcome through issues and pull requests at
[nexdevn-dot/SIveron_Hervay2.0](https://github.com/nexdevn-dot/SIveron_Hervay2.0).
Application code and local modifications are MIT-licensed. Preserve the original
Harvey attribution and third-party licenses; see [AUTHORS.md](AUTHORS.md) and
[THIRD_PARTY.md](THIRD_PARTY.md).

## Set up a development environment

Follow [START_HERE_EN.md](START_HERE_EN.md) for prerequisites, installation,
platform limitations and optional service access. No credentials are needed for
the dashboard, code changes or the standard mocked test suite.

Read [AGENTS.md](AGENTS.md), then [docs/INDEX.md](docs/INDEX.md). Read the module
relevant to your change; consult [architecture](docs/ARCHITECTURE.md) for changes
across modules. Technical documentation is in English; user-facing help supports
German and English.

## Make and submit a change

1. Fork the repository and clone your fork, or create a branch if you have write access.
2. Create a focused branch, for example `git switch -c fix/contact-filter`.
3. Inspect the existing implementation and tests before editing. Keep unrelated changes out.
4. Run the relevant checks in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).
   Run `bash scripts/test.sh` for the full Python suite before submitting.
   For UI changes, check desktop/mobile layouts and both interface languages.
5. Update the affected module document for functional changes and refresh its
   code-check date after source inspection. Keep proposals in the roadmap.
   Generate user manuals from `harvey/web/help-content.js` rather than editing them directly.
6. Run `.venv/bin/python tools/release/check_private_data.py --history` and
   inspect `git diff --check`, `git diff` and `git status --short` before committing.
7. Push your branch to your fork and open a pull request against this repository's
   `main` branch. Describe the problem, changed behavior and checks actually run.

The private-data check is a supporting guard, not a guarantee. Never include
`.env`, `harvey.local.yaml`, databases, credentials, customer exports, product
training, runtime installations or private logs. See [publishing](docs/PUBLISHING.md).

## Safe verification

Keep development defaults: email/LinkedIn disabled, daily send cap zero,
approvals required and sending paused. Use temporary databases and mocked
integrations. Do not start campaigns, approve messages, contact prospects or
train a real product as an installation or test step.

Mocked tests do not prove live model access or mail delivery. Preserve pinned
Codex versions, authentication checks and capability restrictions. Additional
models or tool permissions require capability tests; do not bypass these guards.

## Report an issue

Include reproducible steps, expected and actual behavior, operating system,
Python/Node versions and a minimal sanitized example. Exclude credentials,
personal data and private logs. Do not post exploitable security details or
secrets in a public issue; arrange a private reporting channel with the maintainer.
