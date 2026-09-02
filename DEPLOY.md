# Publishing the site

`site/index.html` is fully self-contained — inline CSS, inline SVG, inline JS, no
external requests, no build step. Any static host serves it as-is.

## Vercel

The CLI is not installed here and there is no authenticated session, so the
login step has to be yours — it opens a browser or emails a code.

```bash
cd /Users/Chris/Documents/situation-room-eval/site
npx vercel login      # once
npx vercel --prod     # deploys this directory
```

Accept the defaults when prompted; the project root is `site/`, there is no
build command, and the output directory is `.`. `vercel.json` in that directory
already sets `cleanUrls` and no-cache headers, so a redeploy is visible
immediately rather than being served stale.

To redeploy after regenerating the report:

```bash
python -m trackii.report && (cd site && npx vercel --prod)
```

## Anything else

Because the file is self-contained, all of these work with no configuration:

- **GitHub Pages** — commit `site/` and enable Pages on that directory
- **Netlify** — drag `site/` onto the dashboard
- **Cloudflare Pages** — same, no build command
- **`python -m http.server`** — from `site/`, for local review

## Before publishing

Regenerate and re-verify, because the report is built from whatever is in
`results/` at the time:

```bash
python research/backfill_surplus.py     # if a sweep began before a scoring change
python -m trackii.report
python research/audit_docs.py
python research/audit_leakage.py
```
