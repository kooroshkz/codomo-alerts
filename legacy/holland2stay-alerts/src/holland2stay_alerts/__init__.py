"""holland2stay-alerts is now codomo-alerts. This package only installs it."""

import sys

NOTE = ("holland2stay-alerts is now codomo-alerts: run `codomo-alerts` instead, and rename H2S_ "
        "settings to CODOMO_. https://github.com/kooroshkz/codomo-alerts#moving-from-holland2stay-alerts")


def main() -> int:
    print(NOTE, file=sys.stderr)
    from codomo_alerts.cli import main as run
    return run()
