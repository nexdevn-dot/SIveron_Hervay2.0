# Development and contributions

## Make your first change

1. Fork [the repository](https://github.com/nexdevn-dot/SIveron_Hervay2.0) and clone your fork.
2. Follow [Getting started](Getting-started).
3. Read [AGENTS.md](https://github.com/nexdevn-dot/SIveron_Hervay2.0/blob/main/AGENTS.md) and the [engineering index](https://github.com/nexdevn-dot/SIveron_Hervay2.0/blob/main/docs/INDEX.md).
4. Create a focused branch and inspect the relevant module and code.
5. Implement the smallest useful change and run the relevant checks.
6. Update the affected module documentation for functional changes.
7. Review the diff, run the private-data check and open a pull request against `main`.

Describe the concrete problem, resulting behavior and validation actually performed.
Preserve MIT attribution and third-party licenses.

## Verification commands

```bash
bash scripts/doctor.sh
bash scripts/test.sh -q
git diff --check
.venv/bin/python tools/release/check_private_data.py --history
```

The full Python suite is required before reporting environment setup complete.
For modified JavaScript, run syntax checks and the relevant frontend checks.
For UI changes, inspect desktop/mobile and German/English behavior.
Use temporary databases and mocked integrations for side-effecting workflows.
Do not start real campaigns, approve mail or contact prospects as a test.

## Architecture map

| Entry point | Responsibility |
| --- | --- |
| `harvey/dashboard.py` | FastAPI dashboard and HTTP routes |
| `harvey/state.py` | SQLite state and migrations |
| `harvey/collectors/` | Company, website, email and people research |
| `harvey/brain.py`, `harvey/codex.py` | Model integration and runtime boundaries |
| `harvey/web/` | Dashboard UI, localization and integrated help |
| `tests/` | Automated Python tests |
| `tools/` | Frontend tooling, help export and release checks |

Technical paths retain the name `harvey` for compatibility. The visible product
is Siveron. Follow [architecture](https://github.com/nexdevn-dot/SIveron_Hervay2.0/blob/main/docs/ARCHITECTURE.md) for cross-module changes.

## Documentation maintenance

Technical docs use English; user-facing help supports German and English.
Generate user manuals from `harvey/web/help-content.js`, rather than editing the
exported manuals directly. Keep implemented facts separate from proposals in
[the roadmap](https://github.com/nexdevn-dot/SIveron_Hervay2.0/blob/main/docs/ROADMAP.md).

The repository's `docs/wiki/` directory contains the wiki source pages. Keep
wiki introductions concise and link to versioned reference documents. The live
GitHub wiki is a separate Git repository and needs a separate publication step.
Never include secrets, customer records or private runtime configuration.

Detailed contribution policy: [CONTRIBUTING.md](https://github.com/nexdevn-dot/SIveron_Hervay2.0/blob/main/CONTRIBUTING.md).
