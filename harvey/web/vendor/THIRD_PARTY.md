# Local browser dependencies

- Tagify 4.39.0 — MIT — https://github.com/yairEO/tagify
- Geoapify Geocoder Autocomplete 3.1.0 — MIT — https://github.com/geoapify/geocoder-autocomplete

Browser JS and CSS are copied unchanged from the corresponding npm tarballs.
License notices are preserved next to the assets. No CDN is used at runtime.
Geoapify requests are proxied through the backend; no API key is embedded in
these assets. Setup does not require Node/npm for these vendored files.

## Campaign composer

- Tiptap core and plain-text extensions: 3.31.3, MIT, https://github.com/ueberdosis/tiptap
- SortableJS: 1.15.7, MIT, https://github.com/SortableJS/Sortable
- Local bundle: `campaign-editor-deps.js`; full dependency license notices: `campaign-editor-LICENSES.txt`.
- Rebuild from `tools/campaign-editor` with `npm ci --ignore-scripts`, `npm run build`, and `node licenses.mjs`. Exact dependencies and integrity hashes are in package-lock.json. No CDN is used by the dashboard.

## Tom Select 2.6.2

Apache-2.0, https://github.com/orchidjs/tom-select . The local complete bundle
includes @orchidjs/sifter and @orchidjs/unicode-variants (Apache-2.0).
Full license and dependency notices: `tom-select-LICENSE.txt`.
Pinned package lock and reproducible copy step: `tools/company-filters`.
