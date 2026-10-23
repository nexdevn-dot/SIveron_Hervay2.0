# Web extraction library review

Reviewed: 2026-10-20. Scope: upstream READMEs, metadata/license/dependency files and
selected local call sites. No dependency installation, benchmark, complete security
audit or implementation change was performed. Effort estimates below are local
engineering judgments, not upstream guarantees.

## Existing adoption verified in code

| Library | Declared local version range / lock | Current use |
| --- | --- | --- |
| HTTPX | >=0.27,<1 / 0.28.1 | Async requests throughout the app; streamed and bounded contact/people HTML downloads. |
| extruct | >=0.18,<0.19 / 0.18.0 | JSON-LD and Microdata extraction of email properties and Person candidates. |
| email-validator | >=2.3,<3 / 2.3.0 | Contact/email normalization, syntax validation and bounded explicit DNS checks. |
| Trafilatura | Not declared in inspected dependency manifests | New candidate for content extraction from already downloaded HTML. |

Local sources: [requirements](../requirements.txt), [lock](../requirements-dev.lock),
[company contacts](../harvey/collectors/company_contacts.py),
[people](../harvey/collectors/people.py), [profile](../harvey/collectors/profile.py),
[contact creation](../harvey/contacts.py).

## 1. Trafilatura: clean content for summaries and evidence snippets

[Repository](https://github.com/adbar/trafilatura), Apache-2.0 for versions >=1.8.0;
older versions were GPLv3+. Supports main text, metadata and multiple output formats,
including processing already downloaded HTML. Its dependency graph includes HTML/date
and URL-processing libraries; assess a pinned release against our lock before adoption.
[Dependency declaration](https://github.com/adbar/trafilatura/blob/master/pyproject.toml).

Proposed small slice: extract bounded clean text/title/language where available from
public HTML fetched by our controlled reader. Keep source URL, collection time and
extraction method; fall back to existing text handling if extraction is empty. Feed
only selected evidence excerpts into future optional R12 suggestions. Measure actual
prompt size and quality; reduced tokens are an objective, not a proven result.

Do not replace raw HTML for contact lookup, agency credit detection, forms, technical
signals or Person extraction. Removing boilerplate can remove footer email/imprint
information. Do not adopt a second unrestricted network crawler. This library neither
verifies organizations nor makes web instructions trustworthy. Medium effort.

## 2. extruct: broaden structured evidence, not just email strings

[Repository](https://github.com/scrapinghub/extruct), BSD-3-Clause. Supports JSON-LD,
Microdata, Microformats, Open Graph, RDFa (experimental) and Dublin Core. Installed
parser dependencies include lxml, rdflib, pyrdfa3, mf2py and w3lib; these are not all
new costs because the library is already declared here.
[Dependency declaration](https://github.com/scrapinghub/extruct/blob/master/setup.py).

Current local extraction uses JSON-LD/Microdata. Proposed shared entity adapter:
Organization/LocalBusiness/Person/ContactPoint, telephone, postal address, sameAs,
jobTitle and explicitly linked organization/person relationships. Resolve bounded
in-document @id references and @graph relationships; this relationship resolution
and source selection are our code, not an extruct feature to assume.

Store field-level source URL/entity identity and compare conflicts with stored data.
A page can contain its publisher, web agency, unrelated authors, branches and multiple
companies. Propose rather than overwrite ambiguous associations. Social sameAs links
remain unverified. Add other syntaxes only against representative failing fixtures;
not every syntax provides reliable contact fields. Medium effort; high functional fit.
Roadmap R03/R07/R11.

## 3. email-validator: improve repeated checks and consistency

[Repository](https://github.com/JoshData/python-email-validator), Unlicense. Syntax,
normalization/internationalized domains and optional domain DNS checks already serve
our manual contacts and public email lookup. Domain checks do not prove a mailbox
exists or that a message will reach its inbox. Current code correctly returns unknown
when no usable MX result is available.

Proposed slice: reuse a bounded caching resolver across lookup checks, preserving DNS
expiry and temporary-error semantics. The upstream helper explicitly supports this:
[DNS cache guidance](https://github.com/JoshData/python-email-validator#dns-timeout-and-cache).
Use stable application error codes with DE/EN messages rather than displaying only
raw English exceptions. Audit remaining regex-based UI/backend eligibility checks
for consistency without broadening Sender rules.

Local details worth regression tests: normalize_email currently uses
`test_environment=True` for fixture support and lowercases the entire address. Separate
fixture acceptance from normal public input; consider retaining normalized local-part
case and a distinct dedup key. Any normalization change needs duplicate/history
compatibility tests, not a silent rewrite of stored addresses. Small/medium effort.
No new external verification service or SMTP probing is needed. R07/R14.

## 4. HTTPX: consolidate the reader already in use

[Repository](https://github.com/encode/httpx), BSD-3-Clause
([license](https://github.com/encode/httpx/blob/master/LICENSE.md)). Supports async,
connection pooling, streaming, timeouts and test transports.

Contact and people readers already stream with size limits and validate redirect
hops. ProfileCollector currently uses a separate AsyncClient, follows redirects and
reads response.text without the same explicit streamed size cap. Consolidate these
policies in an injectable public-page reader: approved host checks on every hop,
connect/read/pool limits plus whole-operation budget, decoded-size limits, bounded
concurrency, cancellation and diagnostic codes. Keep external API clients separate
where their auth and host policy differ. Pool clients within a run/job, not globally
across unrelated authenticated sessions.

Transport retries only cover connection errors/timeouts; 429/503 and Retry-After
need explicit bounded policy. Avoid adding another retry layer on top of durable job
attempt limits. Never add automatic retries for mail sending or other non-idempotent
side effects. Use MockTransport/ASGITransport for fixtures without live research.
[Transport documentation](https://www.python-httpx.org/advanced/transports/).
Medium effort; highest foundation priority. R07/R13/R14/R15.

## Recommended sequence and acceptance evidence

1. **Shared HTTPX page reader:** one fixture suite for valid pages, redirects, size
   limits, timeout, 429/503, stop and private/external target rejection. Existing
   email/people behavior must not regress.
2. **Structured extruct adapter:** fixtures for explicit organization/contact-point
   fields, @graph references, multiple organizations and unrelated authors; sources
   retained, ambiguous records never silently merged.
3. **Validator consistency/cache:** repeated same-domain checks reuse DNS results;
   temporary failure stays unknown; syntax and transport eligibility stay distinct.
4. **Trafilatura extraction pilot:** compare a small consented/public HTML fixture
   corpus across corporate home, service, contact and imprint pages. Preserve raw
   contact extraction, handle empty output and measure clean-text usefulness before
   wiring it into AI prompts.

All four can run as local Python libraries. None requires another hosted service.
No automatic contact acceptance, delivery approval, identity merge or new model host
capabilities are part of these recommendations.

## Implementation follow-up

The bounded shared reader and initial structured company-field review are now
implemented; see [web extraction](modules/web-extraction.md). Original proposed
scope above is research history: generalized retries, complex Person relationships,
DNS cache changes and Trafilatura are not included in that first delivery.

The subsequent validator slice now adds a bounded DNS resolver cache and shared
syntax/transport checks. Original proposal items about changing normalization case or
fixture policy remain deferred; Trafilatura remains uninstalled.
