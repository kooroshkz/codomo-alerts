# Contributing

Thanks for helping. Small fixes, new ideas and bug reports are all welcome.

## Setup

```bash
git clone https://github.com/kooroshkz/codomo-alerts
cd codomo-alerts
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check src tests
```

`codomo-alerts demo` shows the dashboard with sample data, so you can work on the UI without
touching codomo.eu.

## A few rules

- Tests never call codomo.eu. Use the fake in `tests/conftest.py`, or the saved real pages in
  `tests/data` when you change how pages are read.
- Be polite to their site: as few requests per check as the search allows, no lower minimum
  interval, no pretending to be a browser, no booking. Pull requests that change this won't
  be merged.
- Keep messages and UI text short and plain.

## How pages are read

codomo.eu has no public API. The list of homes is rendered on their server, and the data is
in the page itself (Next.js React Server Components data). `src/codomo_alerts/codomo.py`
decodes it into home cards, and every answer is checked against the page's own numbers, so
a page the code misreads becomes an error instead of "these homes are gone". When the layout
changes, save a fresh page, add it to `tests/data`, and fix the decoder until the tests pass.

Codomo runs the same site in every country (`/homes/nl/en`, `/homes/es/en`, `/homes/pt/en`,
`/homes/at/en`), but the homes differ: rooms in Spain and Austria can be female only or male
only, and homes in Portugal and Austria have no bedroom count. Check a change against more
than one country.

## The website

`docs/` is the GitHub Pages site, in English with Dutch, Spanish, Portuguese and German pages
in `docs/nl`, `docs/es`, `docs/pt` and `docs/de`. When you change one page, change the others
too, and keep `docs/sitemap.xml` and the `hreflang` links in sync.

## When the site changes

Most breakage looks like `doctor` failing or "Alerts may be broken". Please open an issue
with the `doctor` output (without your notification links) and the log lines around it.

## Daily upstream check

`.github/workflows/upstream.yml` runs `codomo-alerts upstream` every morning. When codomo.eu
stops answering the way the code expects, the run fails and an issue labeled `upstream` is
opened; it closes itself once things work again. New cities open a separate issue without
failing the run.

GitHub pauses scheduled workflows in public repos after 60 days without commits. Merging the
monthly Dependabot updates keeps it running.
