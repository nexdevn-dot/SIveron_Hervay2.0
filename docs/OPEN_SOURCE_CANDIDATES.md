# Open-source candidates for the roadmap

Research date: 2026-10-18. Scope: repository READMEs, published feature descriptions
and repository license labels; not a source/security audit, benchmark or verified
integration. Candidates are not installed or adopted. [Roadmap](ROADMAP.md).
Integration effort below is an architectural estimate for Python/FastAPI/SQLite
and ordinary JavaScript, not a project claim. No separate services are proposed.
Pin a concrete revision and inspect its actual license/dependencies before adoption.

| Roadmap | Project / published capability | Proposed reuse here | Assessment |
| --- | --- | --- | --- |
| R01 | [Driver.js](https://github.com/nilbuild/driver.js): product tours, highlights and keyboard controls; MIT | Optional guided hints for existing screens | Small frontend component. Does not implement workflow state, persistence or readiness; those remain local services. |
| R01, R02 | [transitions](https://github.com/pytransitions/transitions): Python state machines with conditional transitions; MIT | Model allowed steps and guards | Medium adaptation. Existing database state stays authoritative; persistence, transactions and blocker explanations still need our code. For simple gates a local rule table may be cheaper. |
| R03 | [json-logic-js](https://github.com/jwadhams/json-logic-js): JSON-serialized rule evaluation; MIT | Portable representation of required/excluded rules | Medium adaptation. Backend validation/evaluation must be authoritative. Unknown evidence needs explicit three-state semantics; generic truthiness is insufficient. No arbitrary operators. |
| R04, R11 | [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz): fuzzy string similarity; MIT | Candidate matches for company/contact names | Small/medium Python component. Exact email/domain/phone checks first; similarity is not proof and must not auto-merge identities. Cross-campaign checks still need SQL. |
| R05, R09 | [Frappe CRM](https://github.com/frappe/crm): leads/deals with activities, notes and tasks; AGPL-3.0 | Independently implement a compact next-action/deal workflow using existing records | Workflow reference, not drop-in code. Different framework/data model; no second CRM service. Actual code reuse requires license/architecture review. |
| R06 | [listmonk](https://github.com/knadh/listmonk), [features](https://listmonk.app/): campaigns, templates and analytics; AGPL-3.0 | Reference campaign status/report and template workflows | Workflow reference. Go/PostgreSQL/Vue application, not an embeddable Python module. Newsletter engagement does not define qualified sales replies or meetings. |
| R06, R10 | [Apache ECharts](https://github.com/apache/echarts): browser data visualization; Apache-2.0 | Funnel and trend presentation from our aggregate endpoints | Small/medium frontend component. Does not supply metrics, qualification definitions or cost attribution. Load only needed charts. |
| R07 | [Tenacity](https://github.com/jd/tenacity): Python retry policies; Apache-2.0 | Bounded retries/backoff for transient lookup failures | Small component if needed. Existing time budgets, stop and quota logic win. Not for CAPTCHA/auth failures or non-idempotent sends; no retry amplification. |
| R08 | [Jinja](https://github.com/pallets/jinja): template rendering, inheritance and autoescape; BSD-3-Clause | Optional future controlled rendering component | Defer: template storage/reuse can initially keep current placeholders and rich-content validation. Not a ready-made campaign template manager; unrestricted template execution is not needed. |
| R09 | [SortableJS](https://github.com/SortableJS/Sortable): framework-free drag-and-drop lists; MIT | Reorder opportunity cards/steps | Small frontend component; stages and persistence are custom. Provide keyboard/buttons as an alternative and validate moves server-side. |
| R12 | [Pydantic AI](https://github.com/pydantic/pydantic-ai): typed agent inputs/outputs; MIT | Reference typed suggestion/evidence contracts | Do not replace Brain or add an agent tool loop. Reuse the contract idea through current validation and restricted model boundary; full SDK adoption is not recommended for this scope. |
| R13 | [RESPX](https://github.com/lundberg/respx): HTTPX mocking; BSD-3-Clause | Reproduce provider HTTP errors/timeouts in tests | Test-only candidate, matches HTTPX usage. Maps browser DOM/checkpoints require separate page fixtures; RESPX does not cover that layer. |
| R14 | [Playwright](https://github.com/microsoft/playwright): browser testing across engines; Apache-2.0 | Isolated dashboard flow, locale and viewport regression tests | Already relevant to local browser collection; assess test tooling separately. Temporary DB and mocked providers, no live sending. |
| R15 | No external product required | Incremental FastAPI router/service/client extraction | Prefer existing framework and tests. A new framework would increase migration cost. |

## Recommended first slice

R01/R02: derive a deterministic readiness/next-step response from existing records;
render it in the current UI. Driver.js can provide optional hints after the workflow
is usable without a tour. A state-machine dependency is optional, not prerequisite.
Then R04/R11 matching candidates, R06/R10 charts after metric definitions, and
R07/R13/R14 reliability checks alongside the affected work.

## License and adoption boundaries

License labels describe the inspected repositories, not a legal compatibility verdict.
Retain required notices for adopted components and record pinned versions in
THIRD_PARTY.md. Modified/copied code retains its license obligations. Frappe/listmonk
are proposed as behavioral references, not copied implementation. Do not translate
copied code into Python and assume its original license stops applying.

Other screened options: Viewflow requires Django and has AGPL terms; React Query
Builder adds a React-oriented UI layer. Neither is the first choice for the current
small JavaScript/FastAPI surface. Twenty is a larger CRM/framework reference, not
an embeddable module; its package-specific license boundaries need separate review
before any code reuse. No maintenance or production-readiness ranking was inferred
from repository stars.

## Follow-up: web extraction and validation (2026-10-20)

[Four-library review](WEB_EXTRACTION_REVIEW_2026-10-20.md) distinguishes already-used
HTTPX, extruct and email-validator from the new Trafilatura candidate. It proposes a
shared page reader, structured evidence adapter, DNS cache/validation consistency and
an isolated clean-text pilot. These follow-up improvements are proposals, not shipped
behavior; the introduction's non-adoption statement refers to the original candidate
list, not the three libraries already found in this checkout.

## Assistant selection (2026-10-20)

- Adopted: [Deep Chat](https://github.com/OvidijusParsiunas/deep-chat), MIT,
  pinned 2.5.1, locally shipped Web Component compatible with the existing plain-JS UI.
- Adapted pattern: [TypeChat](https://github.com/microsoft/TypeChat), MIT, typed
  interpretation/validation; independently implemented using existing Brain/Pydantic,
  no TypeChat dependency or copied implementation.
- Deferred: [assistant-ui](https://github.com/assistant-ui/assistant-ui) (React),
  [CopilotKit](https://github.com/CopilotKit/CopilotKit) (larger integration and
  package-specific license review), [Vanna](https://github.com/vanna-ai/vanna)
  (general text-to-SQL exceeds the initial bounded query scope).
- Native queries reuse existing target-profile three-state semantics, no model SQL.
  Reassess deferred candidates for later roadmap scopes rather than replacing Brain.

## OpenOutreach / OpenOutFind decision-maker adaptation (2026-10-20)

References: https://github.com/eracle/OpenOutreach and https://github.com/eracle/OpenOutFind.
Their GPLv3 workflow inspired an independent target-role → evidenced fit reason →
explicit CRM handoff implementation. Siveron reuses its own official-site extraction,
local durable jobs and contact transactions; no GPL source/dependency was copied.
OpenOutFind's external lead database, paid email enrichment and experimental embedding/
Gaussian-process selection are not implemented. A licensed people-data adapter remains
future work requiring an explicit provider contract, credentials and budget policy.


## Contact email research adaptation (2026-10-20)

[PyHunter](https://github.com/VonStruddle/PyHunter) and
[theHarvester](https://github.com/laramies/theHarvester) inform the independent
multi-source adapter/evidence pattern only. No code, dependency or license change
is introduced. Native contact research now reuses existing website/person extraction,
SerpApi/Serper, bounded public reads and explicit contact edits. Optional Hunter uses
its published-only Finder endpoint; it is disabled by default. Username matching and
email-account enumeration (Sherlock/holehe-style tasks) are not contact email research
and were not adopted. See [Contacts](modules/contacts.md).


## Company reporting references (2026-10-21)

[GPT Researcher](https://github.com/assafelovic/gpt-researcher) (Apache-2.0) and
[Evidence](https://github.com/evidence-dev/evidence) (MIT) informed evidence-linked
report structure and data-driven presentation. Siveron's first implementation is
independent, using existing signals, SQLite, Brain and native HTML/Markdown/print;
no source or dependency was imported. [Lighthouse](https://github.com/GoogleChrome/lighthouse)
(Apache-2.0) and [axe-core](https://github.com/dequelabs/axe-core) (MPL-2.0) remain
optional future measured-audit candidates, not current report data sources.
