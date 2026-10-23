# Project status and roadmap

Siveron builds on Harvey v0.3.0 (`e2632eb`) with local product development and
extensions by Bao Dang. This page distinguishes implemented foundations from
future proposals; it is not a promise of delivery dates or live-service reliability.

## Implemented foundations

- Company discovery with configurable sources and bounded search flows.
- Company filters, saved views, profiles and reviewed public-email research.
- Explicit signal activation, stored observations and target-profile evaluation.
- Decision-maker and contact-specific email research with reviewed adoption.
- Company reports based on stored signal evidence, source links and open checks.
- Optional in-app assistant with constrained proposals and supported data analysis.
- Campaign drafts, templates, guided preparation, approval and delivery readiness.
- Campaign conversations, explicit outcomes, opportunities and next tasks.
- German/English help, local integration settings and usage reporting.

Details and implementation entry points are in the
[module documentation](https://github.com/nexdevn-dot/SIveron_Hervay2.0/blob/main/docs/INDEX.md) and the
[baseline comparison](https://github.com/nexdevn-dot/SIveron_Hervay2.0/blob/main/docs/DEVELOPMENT_STATUS_2026-10-20.md).

## Limitations and later work

Examples of deferred work include broader evidence-backed assistant queries,
evaluated real-world research quality, additional licensed source adapters,
uncertain identity review and richer cost attribution. Calendar booking remains
a placeholder. Company reports do not include fresh Lighthouse/axe measurements
or proven revenue impact. Automatic AI qualification and arbitrary model/tool
access are not established capabilities.

The [versioned roadmap](https://github.com/nexdevn-dot/SIveron_Hervay2.0/blob/main/docs/ROADMAP.md) is the detailed reference for scope,
dependencies and acceptance criteria. Some earlier roadmap slices have shipped;
read each item's implementation notes instead of treating the entire document
as either all planned or all complete.

## Validation boundaries

Passing mocked tests does not prove live model access, complete market coverage,
mailbox delivery or effectiveness of a campaign. Dated checks apply to their
stated platform and snapshot. Avoid unsupported maturity percentages, commercial
promises and inferred business outcomes.
