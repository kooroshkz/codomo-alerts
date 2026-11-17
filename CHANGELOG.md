# Changelog

## 0.2.2

- First release on PyPI under the new name (0.2.0 and 0.2.1 are on GitHub and ghcr.io only).
- A release run can be re-run without failing on the GitHub release it already made.

## 0.2.1

- A message with several homes now says "Female only" or "Male only" on each room Codomo
  keeps for one gender, like single alerts already did.

## 0.2.0

Holland2Stay became Codomo on 2026-11-16. Every holland2stay.com address now redirects to
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
- Every country Codomo rents in: the Netherlands, Spain (Granada), Portugal (Carcavelos,
  near Lisbon) and Austria (Linz). New setting `countries` (`CODOMO_COUNTRIES`): codes like
  `nl` or `es`, names like `Spain` or `Österreich`, or `all`. Empty means every country Codomo
  lists, and a country Codomo opens later is read without an update. With no cities and no
  countries it now reads every country; set `countries = ["nl"]` to keep only the
  Netherlands. A city outside the named countries is a config error.
- New setting `gender` (`CODOMO_GENDER`): `female` or `male` skips rooms Codomo marks for the
  other gender only. Alerts show "Female only" or "Male only" when Codomo marks a home.
- Homes without a bedroom count (Portugal and Austria today) count as studios for the
  `bedrooms` filter.
- `codomo-alerts init` asks for countries when no cities are given, and for gender when the
  search reaches Spain, Portugal or Austria. `codomo-alerts cities` lists every city with its
  country, and the MCP search tool takes a `country`.
- Website in English, Dutch, Spanish, Portuguese and German.

## 0.1.0

First release.

- Alerts for new homes, homes back on the market, lottery homes, lottery homes that become
  bookable, price drops and new buildings
- Filters for city, bedrooms, price, contract, furnishing, occupants and move-in date
- Notifications through Apprise, with digests and quiet hours
- Release-hour schedule with three presets and automatic backoff
- Dashboard with activity, time on market and a release-time heatmap
- `upstream` command and a daily workflow that opens an issue when Holland2Stay changes
