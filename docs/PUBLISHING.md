# Publishing Siveron

Prepared: 2026-10-23. Target: `nexdevn-dot/SIveron_Hervay2.0`.

## Public content

Publish application code, neutral configuration templates, tests, manuals,
engineering documentation and license/attribution files. README.md is the main
GitHub description. A short repository About description is supplied in
[GITHUB_ABOUT.md](GITHUB_ABOUT.md).

## Private content

Never publish .env variants (except the empty .env.example template),
harvey.local.yaml, SQLite databases/sidecars, local authentication tokens,
mailbox credentials, LinkedIn cookies, product training, customer exports,
runtime caches, dependency installations or private session logs.
Ignore rules do not remove already tracked content or historical blobs.

Run `.venv/bin/python tools/release/check_private_data.py --history` before
staging and again before pushing. It checks local credential/account values and
selected recognizable credential formats, emitting file names/object IDs only.
It does not prove the absence of every possible secret or customer datum.
Review new files and binary assets independently. Private local files need not
be erased to publish safely; they must remain excluded from Git.

## Connection and publishing

Keep the original repository as upstream, with the owner's repository as origin.
Check `git remote -v`. Never force-push or overwrite remote branches without an
explicit migration decision. Initial publication requires a GitHub account with
write access to the target repository. An authenticated read-only connector is
insufficient. GitHub CLI authentication is global; the owner should choose the
correct account interactively with `gh auth login` if required.

Do not embed a token in a remote URL, source file or command. Preserve upstream
MIT attribution and third-party notices. Publish only after the owner-authorized
content and history pass review. If a secret was ever published, rotate it at
its provider and separately plan history cleanup.

## Preparation result (2026-10-23)

- Local origin points to the requested target; upstream preserves Ethan Rogers' repository.
- Public README, About text and stronger private-file exclusions are prepared locally.
- The private-data guard checked 277 candidate files and 660 historical blobs with
  no matches for local credential/account values or the selected key patterns.
- Write permission was verified on 2026-10-23. The target initially contains a
  README and MIT license. Publication uses a dedicated branch and pull request,
  preserving both the upstream history and target initialization commit. Commit
  authorship uses a GitHub no-reply address. The target license attribution is
  retained alongside Ethan Rogers and Bao Dang.
- Private .env, local configuration and runtime data were not erased or uploaded.
