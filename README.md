<div align="center">

# Codomo alerts (formerly Holland2Stay alerts)

**Get a message the moment a new Codomo home that fits your search is listed.**

Codomo alerts is a free, open source notifier for new listings on [codomo.eu](https://codomo.eu),
the student and expat housing site that was called Holland2Stay. It works in every country
Codomo rents in: the Netherlands (Eindhoven, Rotterdam, Amsterdam, The Hague, Utrecht and
more), Spain (Granada), Portugal (Carcavelos, near Lisbon) and Austria (Linz).
Alerts arrive on Telegram, Discord, ntfy, Slack, email and 100+ other apps.

[![CI](https://github.com/kooroshkz/codomo-alerts/actions/workflows/ci.yml/badge.svg)](https://github.com/kooroshkz/codomo-alerts/actions/workflows/ci.yml)
[![GitHub stars](https://img.shields.io/github/stars/kooroshkz/codomo-alerts?style=flat&color=black)](https://github.com/kooroshkz/codomo-alerts/stargazers)
[![License: MIT](https://img.shields.io/badge/license-MIT-black)](https://github.com/kooroshkz/codomo-alerts/blob/main/LICENSE)
![Python](https://img.shields.io/badge/python-3.11%2B-black)
![Docker](https://img.shields.io/badge/docker-amd64%20%7C%20arm64-black)

[Website](https://kooroshkz.github.io/codomo-alerts/) · [Live demo](https://kooroshkz.github.io/codomo-alerts/demo/) · [Quick start](#quick-start) · [Where it works](#where-it-works) · [FAQ](#faq)

Nederlands: [Codomo meldingen](https://kooroshkz.github.io/codomo-alerts/nl/) · Español: [alertas Codomo Granada](https://kooroshkz.github.io/codomo-alerts/es/) · Português: [alertas Codomo Lisboa](https://kooroshkz.github.io/codomo-alerts/pt/) · Deutsch: [Codomo Benachrichtigung Linz](https://kooroshkz.github.io/codomo-alerts/de/)

<img src="https://raw.githubusercontent.com/kooroshkz/codomo-alerts/main/docs/assets/dashboard.png" alt="Codomo alerts dashboard with matching homes, activity and release hours" width="820">

</div>

## Why

Good homes on Codomo are gone within minutes, and refreshing the site all day is no way to
live. This checks the listings for you and messages you when something matches your cities,
size and budget, so you can book it before everyone else.

Holland2Stay became Codomo on 16 November 2026 and holland2stay.com now redirects to
[codomo.eu](https://codomo.eu). This project was called holland2stay-alerts until then and
moved with it; see [Moving from holland2stay-alerts](#moving-from-holland2stay-alerts).

If it helps you find a home, a ⭐ on GitHub helps the next person find this tool.

## Where it works

Every country and city Codomo lists. When Codomo opens a new country, it is picked up without
an update. On 17 November 2026:

| Country | Cities | What you find there |
|---|---|---|
| Netherlands | Amersfoort, Amsterdam, Arnhem, Capelle aan den IJssel, Delft, Den Bosch, Diemen, Dordrecht, Eindhoven, Groningen, Haarlem, Helmond, Leiden, Maarssen, Maastricht, Nieuwegein, Nijmegen, Rijswijk, Rotterdam, Sittard, The Hague, Tilburg, Utrecht, Velp, Zeist, Zoetermeer | Studios and apartments to book directly, plus register-interest homes |
| Spain | Granada (Codomo Granada) | Rooms from about €395 a month. Some rooms are shared with another tenant, some are female only or male only |
| Portugal | Carcavelos, near Lisbon (Codomo Lombos) | Student rooms from about €869 a month |
| Austria | Linz (Codomo Linz) | Student rooms from about €709 a month. Some rooms are shared, some are female only or male only |

Prices include service costs. `codomo-alerts cities` shows the cities listed right now, with
their country.

## Quick start

### Docker

```bash
docker run -d --name codomo-alerts --restart unless-stopped \
  -e CODOMO_CITIES="Eindhoven, Rotterdam" \
  -e CODOMO_BEDROOMS="studio, 1" \
  -e CODOMO_PRICE_MAX=1600 \
  -e CODOMO_NOTIFY="tgram://BOT_TOKEN/CHAT_ID" \
  -v codomo-data:/data -p 127.0.0.1:8080:8080 \
  ghcr.io/kooroshkz/codomo-alerts
```

The dashboard is on [localhost:8080](http://localhost:8080). To open it to other devices, publish
the port without `127.0.0.1:` and set `CODOMO_DASHBOARD_PASSWORD`. Works on a Raspberry Pi or a NAS too.
Prefer Compose? See [docker-compose.yml](https://github.com/kooroshkz/codomo-alerts/blob/main/docker-compose.yml).

### Looking in Granada, Lisbon or Linz?

Same command, other city. `Lisbon` and `Lisboa` work as names for Carcavelos.

```bash
docker run -d --name codomo-alerts --restart unless-stopped \
  -e CODOMO_CITIES="Granada" \
  -e CODOMO_GENDER=female \
  -e CODOMO_NOTIFY="tgram://BOT_TOKEN/CHAT_ID" \
  -v codomo-data:/data -p 127.0.0.1:8080:8080 \
  ghcr.io/kooroshkz/codomo-alerts
```

| You want | Set |
|---|---|
| Granada | `CODOMO_CITIES=Granada` |
| Lisbon (Carcavelos) | `CODOMO_CITIES=Lisbon` |
| Linz | `CODOMO_CITIES=Linz` |
| Every home in Spain and Portugal | `CODOMO_COUNTRIES="es, pt"` |
| Only the Netherlands | `CODOMO_COUNTRIES=nl` |
| Everything Codomo lists | leave `CODOMO_CITIES` and `CODOMO_COUNTRIES` empty |

`CODOMO_GENDER` is optional: it skips rooms Codomo marks for the other gender only.

### Python

```bash
pipx install codomo-alerts
codomo-alerts init     # a few questions, then a test message
codomo-alerts watch
```

Needs Python 3.11 or newer. Keep it running on any computer that stays on.

## What you get

- **New homes** matching your search, once each, with city, size, price and contract
- **Back on the market**: homes that come back after someone didn't pay
- **Register interest**: homes where Codomo picks someone from a shortlist (it replaced the
  Holland2Stay lottery), with how many people already signed up, and a message when such a
  home becomes directly bookable
- **Price drops** on homes you're already watching
- **New buildings** when a new building page shows up on codomo.eu
- **Female only and male only rooms** are marked in the alert, or skipped with `gender`
- **A dashboard** with what's available, what got taken and how fast, and the hours new homes
  usually show up
- **Many at once** come as one message, not twenty
- **Quiet hours**: alerts wait, and you only get the ones that are still available
- **Health notices** if Codomo blocks requests or changes something

## Notifications

Alerts go through [Apprise](https://github.com/caronc/apprise/wiki), so almost any app works.
Add one link per app:

| App | Link |
|---|---|
| Telegram | `tgram://BOT_TOKEN/CHAT_ID` ([make a bot](https://core.telegram.org/bots#how-do-i-create-a-bot)) |
| Discord | `discord://WEBHOOK_ID/WEBHOOK_TOKEN` |
| ntfy | `ntfy://a-long-secret-topic` (free push to your phone, no account) |
| Slack | `slack://TOKEN_A/TOKEN_B/TOKEN_C/#channel` |
| Email | `mailtos://you:app-password@gmail.com` |
| Signal, Matrix, Pushover, Gotify, Home Assistant, webhooks… | [all options](https://github.com/caronc/apprise/wiki) |

Check them with `codomo-alerts test`. Alerts are in English. A new home looks like this:

```
Engelandlaan 300-C
Zoetermeer · 2 bedrooms · €1,688
Indefinite · Semi-furnished
https://codomo.eu/homes/nl/en/zoetermeer/sea-tower/engelandlaan-300-c
```

## Configuration

Run `codomo-alerts init`, or copy [config.example.toml](https://github.com/kooroshkz/codomo-alerts/blob/main/config.example.toml) to `config.toml`:

```toml
[search]
cities = ["Eindhoven", "Rotterdam"]   # empty = every city
countries = []                        # empty = every country; or ["nl"], ["es", "pt"]
bedrooms = ["studio", "1"]            # or "2+", "1-3"
price_max = 1600                      # per month, service costs included
contract = ["long"]                   # long or short stay
gender = ""                           # "female" or "male" skips rooms for the other gender only

[notify]
urls = ["tgram://BOT_TOKEN/CHAT_ID"]
```

`init` asks for countries when you don't name cities, and for gender when your search
reaches Spain, Portugal or Austria.

Every setting also works as an environment variable, which is handy for Docker:

| Variable | Example | |
|---|---|---|
| `CODOMO_CITIES` | `Eindhoven, The Hague` | only these cities. `codomo-alerts cities` lists names with their country. `Lisbon` works for Carcavelos |
| `CODOMO_COUNTRIES` | `nl, es` | `nl`, `es`, `pt`, `at`, names like `Spain` or `Österreich`, or `all`. Empty means every country Codomo lists, new ones included. A city outside these countries is a config error |
| `CODOMO_EXCLUDE_CITIES` | `Maastricht` | everywhere except these |
| `CODOMO_BEDROOMS` | `studio, 2+` | studio, 1, 2, 3, 4. Homes without a bedroom count (Portugal, Austria) count as studios |
| `CODOMO_PRICE_MIN` / `CODOMO_PRICE_MAX` | `1600` | euro per month, service costs included |
| `CODOMO_CONTRACT` | `long` | long, short, or a maximum: indefinite, 2y, 1y, 6m, 4m |
| `CODOMO_FURNISHING` | `furnished` | fully-furnished, furnished, semi-furnished, unfurnished |
| `CODOMO_PERSONS` | `2` | the home must fit this many people |
| `CODOMO_GENDER` | `female` | `female` or `male`: skips rooms Codomo marks for the other gender only. Empty shows all |
| `CODOMO_MOVE_IN_BEFORE` | `2027-02-01` | |
| `CODOMO_INTEREST` | `true` | register-interest homes too |
| `CODOMO_NOTIFY` | `tgram://… ntfy://…` | separate links with a space |
| `CODOMO_NOTIFY_FILE` | `/run/secrets/codomo` | read the links from a file |
| `CODOMO_QUIET_HOURS` | `23:00-07:00` | |
| `CODOMO_SCHEDULE` | `normal` | relaxed, normal or eager |
| `CODOMO_DASHBOARD` / `CODOMO_PORT` / `CODOMO_HOST` | `on` / `8080` / `0.0.0.0` | |
| `CODOMO_DASHBOARD_PASSWORD` | | when it's reachable from other devices |
| `CODOMO_DATA_DIR` | `/data` | |
| `CODOMO_CONFIG` | `/config/config.toml` | |

Country names that work: Netherlands, Holland, Nederland; Spain, España, Spanje; Portugal;
Austria, Österreich, Oostenrijk.

## Commands

| | |
|---|---|
| `codomo-alerts init` | set up your search and notifications |
| `codomo-alerts watch` | keep checking and send alerts (the default) |
| `codomo-alerts list` | what matches right now (`--interest`, `--city`, `--json`) |
| `codomo-alerts test` | send a test message to every app |
| `codomo-alerts doctor` | check your setup |
| `codomo-alerts stats` | what the watcher has seen so far |
| `codomo-alerts cities` | every city Codomo lists, with its country |
| `codomo-alerts demo` | try the dashboard with sample data |
| `codomo-alerts mcp` | MCP server for AI assistants |
| `codomo-alerts upstream` | check that codomo.eu still works the way this tool expects |

## How often it checks

Most homes are released on weekdays during office hours, plus a small batch just after
midnight when unpaid reservations go back on sale. So it checks more often then and less
at night:

| | relaxed | normal | eager |
|---|---|---|---|
| Weekdays 08:30 to 18:00, and 00:05 to 00:45 | 5 min | 2 min | 1 min |
| Rest of the day | 10 min | 5 min | 3 min |
| Night | 30 min | 15 min | 10 min |

Register-interest homes have no deadline to race, so they are checked every 10 minutes.
It never goes below one minute, adds a bit of randomness, says who it is in the user agent,
and backs off when Codomo asks it to.

## How it reads Codomo

codomo.eu has no public API. The list of homes for each country, like `codomo.eu/homes/nl/en`
or `codomo.eu/homes/es/en`, is rendered on Codomo's server with your filters in the address,
and the data of each home card is inside the page. A check reads one list page per country
and bedroom count you want (one more page for every 25 homes), decodes the cards, and checks
that what it read adds up to the page's own counts. When it doesn't, the check fails instead
of reporting homes as taken.

The maximum stay (long or short stay) is only on each home's own page, so with a contract
filter it reads that page once for every new home and remembers the answer. A home whose page
can't be read waits for the next check, so a short stay is never announced to someone who
wants a long one. Photos come from Codomo's image server.

## Ask an AI assistant

`codomo-alerts mcp` runs an [MCP](https://modelcontextprotocol.io) server, so Claude, Cursor and
others can answer "any studios in Eindhoven under €1,300?" or "which rooms in Granada are free
in February?". The search tool takes a city or a country. Install the extra first:

```bash
pipx install "codomo-alerts[mcp]"
```

```json
{ "mcpServers": { "codomo": { "command": "codomo-alerts", "args": ["mcp"] } } }
```

## Home Assistant

Send alerts to Home Assistant with an Apprise link (`hassio://…`), or read the dashboard's
JSON from `http://HOST:8080/api/overview` with a REST sensor.

## Tips for actually getting a home

- Create your Codomo account before you start looking.
- Fill in your home search in the Codomo tenant portal: Codomo uses it when it picks someone
  for a register-interest home, and it tells you itself when a home fits.
- Have your documents ready. After booking you have about a day to pay.
- Keep a browser tab open and stay logged in, so an alert is one tap away from booking.
- In Granada and Linz, check whether a room is shared and whether it is female only or male
  only before you book. The alert says so when Codomo marks it.

## Moving from holland2stay-alerts

- Install the new package: `pipx uninstall holland2stay-alerts && pipx install codomo-alerts`,
  or use the image `ghcr.io/kooroshkz/codomo-alerts`.
  `pipx upgrade holland2stay-alerts` works too: that package now only installs codomo-alerts,
  and the old commands start it.
- Rename `H2S_` variables to `CODOMO_`. In the config, `lottery` is now `interest` (the old
  key still works) and `occupants` is now `persons`, a number of people.
- City names, bedrooms like `2+`, `contract = ["long"]` and furnishing names keep working.
- With no cities and no countries set, it now reads every country Codomo lists. To keep only
  the Netherlands, set `countries = ["nl"]` (or `CODOMO_COUNTRIES=nl`).
- The data folder is now `codomo-alerts`, so the first run starts fresh, quietly.

## FAQ

**Is there a Codomo app that notifies me about new homes?** Codomo uses the home search in
your tenant portal for register-interest homes. For a message about every new listing,
filtered your way and sent to the app you already use, run this tool. It is free and
unofficial.

**How do I get Holland2Stay notifications now?** Holland2Stay is now Codomo, and tools that
used the old Holland2Stay API stopped working when it closed. This project was
holland2stay-alerts and reads codomo.eu since version 0.2.0. Install `codomo-alerts` and your
city names still work.

**Does it work for Codomo Granada, Lisbon or Linz?** Yes. Set `CODOMO_CITIES` to `Granada`,
`Lisbon` (Carcavelos) or `Linz`, or set `CODOMO_COUNTRIES` to `es`, `pt` or `at`. Rooms there
have their own rules: some are shared and some are female only or male only. Set
`CODOMO_GENDER` to skip the rooms that aren't open to you.

**Why don't homes in Portugal and Austria show a bedroom count?** Codomo doesn't give one.
They are rooms in student residences, so the `bedrooms` filter counts them as studios: `studio` includes
them, `2+` skips them.

**Which countries does it cover?** Every country Codomo lists: today the Netherlands, Spain,
Portugal and Austria. When Codomo opens a new country, it is included without an update,
unless you limit `countries`.

**Does it book for me?** No, and it never will. Booking with automated tools is against
Codomo's terms. It tells you, you book.

**Is this allowed?** It reads public listing pages at a slow pace and identifies itself in the
user agent. Codomo's robots.txt asks bots to stay away from `/api/` and from addresses with a
`?`, which includes the filtered list this tool reads; the sitemap and the home pages are
allowed. Read [Codomo's terms](https://codomo.eu/en/terms-and-conditions) and decide for
yourself. You're responsible for how you use it.

**Do I need a server?** No. Any computer that stays on works: a laptop on power, a Raspberry
Pi, a NAS or a small VPS.

**What happened to Holland2Stay?** It became Codomo on 16 November 2026. Every
holland2stay.com address redirects to codomo.eu, and version 0.2.0 reads codomo.eu.

**Alerts stopped.** Run `codomo-alerts doctor`, and `codomo-alerts upstream` to see whether
Codomo changed something. Codomo sometimes shows a maintenance page for half an hour; the tool
recognises it and keeps trying. A daily check runs the same test here and opens an
[issue](https://github.com/kooroshkz/codomo-alerts/issues?q=label%3Aupstream) when it fails,
so look there first.

## Contributing

Ideas, fixes and other landlords are welcome. If it helped you find a home, a ⭐ helps
other people find it too. See [CONTRIBUTING.md](https://github.com/kooroshkz/codomo-alerts/blob/main/CONTRIBUTING.md).

## Disclaimer

This is an unofficial, independent project. It is not affiliated with, endorsed by or
connected to Codomo or Holland2Stay B.V. Their names are only used to describe what this
works with. It never books, pays, fills in forms or logs in. There's no guarantee you'll get
a home, and it can stop working whenever the site changes. Provided as is, under the
[MIT license](https://github.com/kooroshkz/codomo-alerts/blob/main/LICENSE).
