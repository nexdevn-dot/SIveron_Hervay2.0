
The local Tiptap 3.31.3 bundle additionally includes the MIT-licensed Bold,
Italic, Underline, Strike, Link, BulletList, OrderedList, ListItem and Blockquote
extensions. Source imports and pinned versions live in `tools/campaign-editor/`;
`npm run build` regenerates the bundle and complete license notices. Recipient
chips and the bounded upload UI use existing application components and native
browser controls; no additional uploader or newsletter service is required.

## Local Google Maps discovery

The native Python implementation in `harvey/collectors/google_maps.py` and
search planning/checkpoints were informed by these MIT-licensed projects:
- https://github.com/zimkk/Lead-Scraper-Google-Maps (search units, stable listing links, resume concepts)
- https://github.com/sonagara-vashram/google-maps-scraper (overlapping search areas)

No upstream runtime, extension, remote service or anti-detection code is bundled.
Gosom and gmapsscraper were evaluated as architectural/UI references only.
The collector and SQLite integration are independently written for Siveron.

The public-email search additionally adapts contact-page prioritisation,
extraction-noise filtering and explicit social-profile-link concepts evaluated
in zimkk and sonagara-vashram. These are independently implemented in the
existing company_contacts collector; no second scraping runtime is bundled.

## Company filtering

Tom Select 2.6.2 is vendored locally under Apache-2.0 with its bundled
@orchidjs/sifter and @orchidjs/unicode-variants dependencies. Complete notices
are in `harvey/web/vendor/tom-select-LICENSE.txt`. Rebuild instructions and
exact npm lockfile are in `tools/company-filters`.

OpenStatus data-table-filters was evaluated for UI concepts only. The SQL
facets, removable filter chips and stored views are native Siveron code;
no React, jQuery, OpenStatus runtime or external filtering service is used.

## Deep Chat 2.5.1 — local assistant UI

Source: https://github.com/OvidijusParsiunas/deep-chat (MIT).
Pinned package/lock and reproducible copy tool: `tools/assistant-chat`.
Shipped assets: `harvey/web/vendor/deep-chat-2.5.1.js`, with upstream and dependency
notices in `deep-chat-LICENSE.txt`. No CDN, browser-model, direct model API, camera,
microphone or persistent chat storage is configured. TypeChat is an architectural
reference only (https://github.com/microsoft/TypeChat); its code is not copied.

The registry audit on 2026-10-20 reports a moderate transitive `sprintf-js` precision
DoS advisory (GHSA-hp3w-g68c-fv3c) through Remarkable's CLI dependencies. The shipped
prebuilt browser module contains Remarkable's parser, not the argparse/sprintf CLI;
the application never exposes sprintf formatting. The pinned package tree retains
the upstream dependency advisory; no blanket clean-audit claim is made.
