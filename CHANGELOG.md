# Changelog

## 0.2.0

Holland2Stay became Codomo on 2026-11-15. Every holland2stay.com address now redirects to
codomo.eu, and the REST API this tool used is gone, so this release reads codomo.eu instead.
It is a breaking release.

- New name: the package, the command and the repository are now `codomo-alerts`
  (`pipx install codomo-alerts`, `codomo-alerts watch`). The Docker image is
  `ghcr.io/kooroshkz/codomo-alerts`.
- Environment variables start with `CODOMO_` instead of `H2S_`.
- The config uses names, not Holland2Stay ids: cities by name (slugs like `den-haag` work
  too), bedrooms as `studio`, `2`, `2+` or `1-3`, contract as `long`, `short` or a maximum.
  `occupants` is replaced by `persons`, the number of people the home must fit.
- The lottery is gone on Codomo. Homes with a lot of demand are "Register interest" homes:
  you sign up and Codomo picks someone from the shortlist. `lottery = true` is now
  `interest = true` (the old key still works, with a warning). Alerts show how many people
  already registered.
- The maximum stay is only on each home's own page, so with a contract filter the tool reads
  that page once for every new home. A home whose page can't be read waits for the next
  check, so a short stay is never announced to someone who wants a long one.
- New buildings come from the building pages in codomo.eu's sitemap. The old "new building
  weeks before sale" check relied on Holland2Stay's product ids and is gone.
- The data folder is now `codomo-alerts`, so the first run starts fresh (quietly, like any
  first run). The old `holland2stay-alerts` folder can be deleted.
- Codomo's maintenance page is recognised: a short pause, not "the site changed".
- `codomo-alerts upstream` checks the list page, a home page, photos and new cities.

## 0.1.0

First release.

- Alerts for new homes, homes back on the market, lottery homes, lottery homes that become
  bookable, price drops and new buildings
- Filters for city, bedrooms, price, contract, furnishing, occupants and move-in date
- Notifications through Apprise, with digests and quiet hours
- Release-hour schedule with three presets and automatic backoff
- Dashboard with activity, time on market and a release-time heatmap
- `upstream` command and a daily workflow that opens an issue when Holland2Stay changes
