# Configuration and integrations

## Configuration files

| File | Role |
| --- | --- |
| `config/development.yaml` | Public neutral development template |
| `harvey.local.yaml` | Active private local configuration, excluded from Git |
| `.env` | Private service credentials, excluded from Git |
| `.env.example` | Public environment-variable reference with empty credential fields |
| `data/harvey.db` | Private local SQLite state |

Setup creates the private files only when absent. Do not publish authentication
files, private settings, customer data, product training, exports or runtime caches.
Legacy `.env.example` references to `harvey.yaml` do not override this checkout's
active `harvey.local.yaml` configuration.

## Optional external access

| Capability | Access needed |
| --- | --- |
| Dashboard, code changes and standard mocked tests | No service credentials |
| OpenStreetMap discovery | Network access; no provider account |
| AI assistant and AI generation | Your own supported Claude/Codex authentication and usage allowance |
| Mail delivery and replies | Your own configured Gmail OAuth, SMTP/IMAP or other supported mail integration |
| Optional search, contact lookup and verification providers | Your own provider credentials and applicable budget |
| LinkedIn | Separate account configuration; disabled and unnecessary for development |

External providers may charge for use. The application does not supply shared
accounts or guarantee plan availability, provider coverage or live model access.

## Codex runtime boundary

Use `scripts/codex` and `scripts/harvey`, not an arbitrary global CLI.
The pinned CLI is **0.159.3**. The neutral template selects **gpt-6-luna** with
`codex_restricted_text: true`; **gpt-6.1-sol** is the separately supported
restricted-mode alternative. Account availability must be checked separately.

If authentication is needed, run `scripts/codex login` yourself in your terminal.
The integration requires file-based CLI authentication; desktop-app login alone
is not sufficient evidence. `scripts/harvey status --check` performs the separate
preflight without sending a model prompt.

Preserve authentication, version and capability checks. Restricted text mode grants
no host file, shell, network or MCP access; any tool-call event aborts the turn.
The upstream tool-less mode remains available for compatible models. Do not expand
the model list or permissions without capability tests.

## Live operation is separate

Configure and review your business details, sender identity, mailbox, product
knowledge and chosen signals for your own use case. Enabling email, selecting a
positive cap and resuming sending are intentional operational changes, not
installation tasks. Keep approval requirements in place. Mock tests do not prove
mail delivery or live model operation.

References: [setup guide](https://github.com/nexdevn-dot/SIveron_Hervay2.0/blob/main/START_HERE_EN.md),
[development template](https://github.com/nexdevn-dot/SIveron_Hervay2.0/blob/main/config/development.yaml),
[publishing guide](https://github.com/nexdevn-dot/SIveron_Hervay2.0/blob/main/docs/PUBLISHING.md).

## Source and budget choices

[Low-cost lead research](Low-cost-lead-research) compares free/local discovery,
paid data and selective contact enrichment. Its detailed repository guide contains
dated provider references, imported fields, integration restrictions and practical
budget approaches. A source offering a paid plan does not mean the current adapter
supports that plan. Keep research, evidence review, adoption and outreach separate.
