# holland2stay-alerts is now codomo-alerts

Holland2Stay became [Codomo](https://codomo.eu) on 16 November 2026, and this project moved
with it. The tool is now **[codomo-alerts](https://pypi.org/project/codomo-alerts/)**:
self-hosted alerts for new Codomo homes in the Netherlands, Spain (Granada), Portugal
(Carcavelos, near Lisbon) and Austria (Linz), sent to Telegram, Discord, ntfy, Slack, email
and 100+ other apps.

Installing `holland2stay-alerts` installs `codomo-alerts`, and the old `holland2stay-alerts`
and `h2s-alerts` commands start it. For a new install, use the new name:

```bash
pipx install codomo-alerts
codomo-alerts init
codomo-alerts watch
```

Or with Docker: `ghcr.io/kooroshkz/codomo-alerts`.

Coming from holland2stay-alerts 0.1: settings start with `CODOMO_` instead of `H2S_`, and
`lottery` is now `interest` (Codomo replaced the lottery with a shortlist). The full list is in
[Moving from holland2stay-alerts](https://github.com/kooroshkz/codomo-alerts#moving-from-holland2stay-alerts).

- Website: https://kooroshkz.github.io/codomo-alerts/
- Source and docs: https://github.com/kooroshkz/codomo-alerts

Unofficial, not made by or connected to Codomo or Holland2Stay.
