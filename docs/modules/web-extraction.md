# Public page reader and structured company review

Code checked: 2026-10-20. [Index](../INDEX.md) · [Companies](companies.md)

## Shared reader (implemented)

[public_pages.py](../../harvey/collectors/public_pages.py) serves public email,
people and ProfileCollector reads using an injected HTTPX client and async URL guard.
It validates every redirect target, permits at most three HTTP hops, streams at most
1 MB of decoded data and enforces a 15-second whole-read timeout in addition to
client timeouts. Cancellation propagates. Contact/people readers allow HTML;
ProfileCollector also allows text/XML for existing robots/sitemap functionality.
The existing official-host/public-address guard remains the policy; this does not
introduce a new DNS-pinning transport or authenticated API client.

Each reader caches at most 16 URL results for 60 seconds, scoped to its job/collector
and domain. HTML is shared between email/people's existing extraction and structured
field extraction within that job. Independent email and people jobs do not share a
cross-job cache or an HTTP client. ProfileCollector switches cache on company domain
changes. There is no persistent HTML cache and no new cache of credentials/content
in the database. No Trafilatura integration is included.

Timeout, network, HTTP, guard, content-format, size and redirect-limit failures are
stable diagnostics without raw exception strings. Email jobs retain their durable
reason display/retry behavior; ProfileCollector keeps a bounded diagnostic list for
its reader. People lookup retains its current summary status. No extra automatic
retry layer is added: existing bounded job retry remains authoritative. HTTP 429/5xx
can be reported retryable but do not cause immediate retry amplification. Stopping a
job still takes effect between work units; reads have a bounded duration.

## Structured suggestions (implemented)

[structured_company.py](../../harvey/collectors/structured_company.py) uses the
already installed extruct JSON-LD/Microdata extractors. Bounded traversal discovers
recognized Organization/LocalBusiness types. Entity selection requires an exact
normalized company name or an explicit URL at the company's official host. This is
a candidate-association heuristic, not verified organization identity. Multiple
branches/entities can yield separate review suggestions. Unrelated Person/agency
records do not become generic company contact details.

Bounded in-document @id resolution supports ContactPoint and PostalAddress objects;
conflicting declarations at the same identifier are skipped, and no remote reference
or context is fetched by this adapter. It proposes phone, formatted postal location
and explicitly published email, preserving entity/contact label, sanitized source URL,
method and checked time. It does not invent missing values or add new Person matching.
Original HTML-based email/person extraction remains in place.

Explicit email and people lookups store suggestions from checked pages. Website
profiling adds homepage suggestions only when CONTACT_FOUND is confirmed. A new
append-only migration creates company_field_candidates. Repeated identical evidence
updates checked_at without reopening reviewed records. No contacts are created and
no existing company values are changed by extraction.

## Review and adoption

Company profile GET includes pending suggestions (up to 100), with existing value;
exactly identical stored phone/location values are hidden. The dialog shows source,
collection date, entity/contact label, proposed value and Adopt/Dismiss controls.
Replacing an existing nonempty value requires UI confirmation. POST
`/api/company-field-candidates/{id}/review` requires action and expected_value.

A transaction checks that the company is active, candidate pending and current
phone/location still equals the reviewed value. Conflicts or repeated review return
409. Accepting phone/location updates only that company field and updated_at.
Accepting email adds known public email without verification, contact creation or
scheduling. Dismiss changes the candidate status only. Accepted/dismissed source
records remain stored. Contacts, suppressions, approvals and sent history are untouched.

This first slice is phone/address/contact-point evidence. Complex Person-employer
relationships, additional metadata formats and cross-job fetch reuse remain proposals.
Source text is untrusted; suggestions require operator review.

## Verification

`test_public_pages.py`: cache, redirects/guard, decoded-size cap, status/format errors,
whole-read timeout and cancellation. `test_structured_company.py`: graph references,
Microdata, wrong entities, malformed/ambiguous data, repeated evidence, stale adoption,
explicit accept/dismiss, unverified email and no contact/outbox creation. Existing
contact/people/profile/migration suites cover compatibility.

## DNS cache and common email checks (2026-10-20)

[email_checks.py](../../harvey/email_checks.py) centralizes syntax normalization and
transport support. Manual contacts/public extraction retain the previous normalized
lowercase storage, fixture .test compatibility and public placeholder exclusions.
This slice does not migrate stored addresses or change dedup/suppression keys.
`email_checks` distinguishes syntax_valid, send_supported and stable reasons:
empty/syntax_invalid/transport_unsupported/ready. Ready means syntax and the existing
ASCII transport policy only, never DNS verification, mailbox existence or approval.
Gate and Sender share that policy, additionally rejecting syntactically invalid
legacy addresses that the old loose regex accepted. No SMTPUTF8 expansion occurs.
Contact and campaign reads expose the same flags without DNS; frontend selection
uses them when present, with a provisional fallback for unsaved/legacy payloads.

Explicit domain checks reuse a process-local dnspython resolver with a thread-safe
1024-entry LRU cache and DNS TTL/negative-answer expiry. Resolver lifetime is two
seconds; the outer async operation remains bounded to three seconds. The validator
receives the resolver without a separate timeout argument (the library forbids
combining them). Temporary timeouts/unknown results remain unknown; only explicit
domain-level undeliverability yields no_mail_domain. No SMTP probe or test message
is sent. Lookup already groups addresses by domain; caching now also benefits
sequential checks across jobs. Concurrent cache misses are not promised to coalesce.

Tests: `test_email_checks.py` mocks DNS transport to prove reuse, expiry and unknown
recovery; checks independent syntax/transport policy and no DNS during contact or
campaign reads. Existing lookup, CRM, gate and sender tests cover compatibility.

## Reuse contract

Reuse interfaces inspected: 2026-10-23. See the
[detailed reuse guide](../reuse/web-extraction.md) for inputs/outputs,
transitive dependencies, data and side effects, failure semantics, extraction steps,
examples and relevant tests. The [catalog](../REUSABLE_COMPONENTS.md) distinguishes
small logic, adapter seams and application-coupled workflows; these modules are
not a separately versioned public SDK.
