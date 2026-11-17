<div align="center">

# codomo-alerts

**Know the moment a Codomo home (formerly Holland2Stay) matching your search is listed.**

Self-hosted. One command. Alerts on Telegram, Discord, ntfy, Slack, email and 100+ other apps.

[![CI](https://github.com/kooroshkz/codomo-alerts/actions/workflows/ci.yml/badge.svg)](https://github.com/kooroshkz/codomo-alerts/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-black)](https://github.com/kooroshkz/codomo-alerts/blob/main/LICENSE)
![Python](https://img.shields.io/badge/python-3.11%2B-black)
![Docker](https://img.shields.io/badge/docker-amd64%20%7C%20arm64-black)

[Website](https://kooroshkz.github.io/codomo-alerts) · [Live demo](https://kooroshkz.github.io/codomo-alerts/demo/) · [Quick start](#quick-start)

<img src="https://raw.githubusercontent.com/kooroshkz/codomo-alerts/main/docs/assets/dashboard.png" alt="Dashboard" width="820">

</div>

## Why

Good homes on Codomo are gone within minutes, and refreshing the site all day is no way to
live. This checks the listings for you and messages you when something matches your cities,
size and budget, so you can book it before everyone else.

Holland2Stay became Codomo on 15 November 2026 and holland2stay.com now redirects to
[codomo.eu](https://codomo.eu). This project was called holland2stay-alerts until then; see
[Moving from holland2stay-alerts](#moving-from-holland2stay-alerts).

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

Check them with `codomo-alerts test`. A new home looks like this:

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
cities = ["Eindhoven", "Rotterdam"]   # empty = all of the Netherlands
bedrooms = ["studio", "1"]            # or "2+", "1-3"
price_max = 1600                      # per month, service costs included
contract = ["long"]                   # long or short stay

[notify]
urls = ["tgram://BOT_TOKEN/CHAT_ID"]
```

Every setting also works as an environment variable, which is handy for Docker:

| Variable | Example | |
|---|---|---|
| `CODOMO_CITIES` | `Eindhoven, The Hague` | `codomo-alerts cities` lists names. Linz, Granada and Carcavelos only when you name them |
| `CODOMO_EXCLUDE_CITIES` | `Maastricht` | everywhere except these |
| `CODOMO_BEDROOMS` | `studio, 2+` | studio, 1, 2, 3, 4 |
| `CODOMO_PRICE_MIN` / `CODOMO_PRICE_MAX` | `1600` | euro per month, service costs included |
| `CODOMO_CONTRACT` | `long` | long, short, or a maximum: indefinite, 2y, 1y, 6m, 4m |
| `CODOMO_FURNISHING` | `furnished` | fully-furnished, furnished, semi-furnished, unfurnished |
| `CODOMO_PERSONS` | `2` | the home must fit this many people |
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

## Commands

| | |
|---|---|
| `codomo-alerts init` | set up your search and notifications |
| `codomo-alerts watch` | keep checking and send alerts (the default) |
| `codomo-alerts list` | what matches right now (`--interest`, `--city`, `--json`) |
| `codomo-alerts test` | send a test message to every app |
| `codomo-alerts doctor` | check your setup |
| `codomo-alerts stats` | what the watcher has seen so far |
| `codomo-alerts cities` | city names you can use |
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

codomo.eu has no public API. The list of homes at `codomo.eu/homes/nl/en` is rendered on
Codomo's server with your filters in the address, and the data of each home card is inside
the page. A check reads one list page per bedroom count you want (one more page for every
25 homes), decodes the cards, and checks that what it read adds up to the page's own counts.
When it doesn't, the check fails instead of reporting homes as taken.

The maximum stay (long or short stay) is only on each home's own page, so with a contract
filter it reads that page once for every new home and remembers the answer. A home whose page
can't be read waits for the next check, so a short stay is never announced to someone who
wants a long one. Photos come from Codomo's image server.

## Ask an AI assistant

`codomo-alerts mcp` runs an [MCP](https://modelcontextprotocol.io) server, so Claude, Cursor and
others can answer "any studios in Eindhoven under €1,300?". Install the extra first:

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

## Moving from holland2stay-alerts

- Install the new package: `pipx uninstall holland2stay-alerts && pipx install codomo-alerts`,
  or use the image `ghcr.io/kooroshkz/codomo-alerts`.
- Rename `H2S_` variables to `CODOMO_`. In the config, `lottery` is now `interest` (the old
  key still works) and `occupants` is now `persons`, a number of people.
- City names, bedrooms like `2+`, `contract = ["long"]` and furnishing names keep working.
- The data folder is now `codomo-alerts`, so the first run starts fresh, quietly.

## FAQ

**Does it book for me?** No, and it never will. Booking with automated tools is against
Codomo's terms. It tells you, you book.

**Is this allowed?** It reads public listing pages at a slow pace and identifies itself in the
user agent. Codomo's robots.txt asks bots to stay away from `/api/` and from addresses with a
`?`, which includes the filtered list this tool reads; the sitemap and the home pages are
allowed. Read [Codomo's terms](https://codomo.eu/en/terms-and-conditions) and decide for
yourself. You're responsible for how you use it.

**What happened to Holland2Stay?** It became Codomo on 15 November 2026. Every
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
