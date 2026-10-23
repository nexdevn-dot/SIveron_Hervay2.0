# Local company filter assets

Tom Select 2.6.2 is pinned in package-lock.json. In this directory run:

```sh
npm ci --ignore-scripts
npm run build
```

The build copies the published JavaScript/CSS and license notices into
web/vendor; no CDN is used at runtime. company-filters.js is native application
code. Installed node_modules stay out of Git.

No OpenStatus, jQuery or React runtime is installed; faceted filtering and
saved views are implemented against the existing SQLite backend.
