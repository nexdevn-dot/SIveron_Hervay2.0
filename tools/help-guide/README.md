# Dashboard manual

`harvey/web/help-content.js` contains the paired German/English source for all
chapters, diagram labels, statuses, instructions and troubleshooting answers.
The help renderer owns localization inside `data-help-localized`; the general
DOM string translator deliberately skips that subtree. Search indexes both
editions, so queries continue to work when changing language.

When changing behaviour, update the corresponding chapter in both languages.
Keep claims tied to implemented behaviour; never add account data or credentials.
The AI draft endpoint currently produces German copy independently of UI locale;
the manual explicitly documents this limitation.

- Validate content: `node --test tools/help-guide/content.test.cjs`
- Regenerate Markdown editions: `node tools/help-guide/export.cjs`
- Check syntax: `node --check harvey/web/help.js`

Browser checks: desktop/mobile, DE/EN, search and empty results, chapter links,
FAQ disclosure, keyboard focus. Print uses the browser dialog, includes filtered
out chapters, expands FAQ answers for printing and restores them afterwards.
The help page makes no API requests, starts no job and sends no messages.
