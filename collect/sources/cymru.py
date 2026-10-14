"""Team Cymru's full IPv6 bogon list: address space that should not appear in the routing table."""
import ipaddress
import re
from datetime import datetime, timedelta, timezone

from collect.registry import MONTH, Context, source

URL = "https://team-cymru.org/Services/Bogons/fullbogons-ipv6.txt"
HOME = "https://www.team-cymru.com/bogon-reference"
UPDATED = re.compile(r"#\s*last updated (\d+)")
MIN_PREFIXES = 1000
MAX_AGE = timedelta(days=3)


def parse(text: str, now: datetime | None = None, min_prefixes: int = MIN_PREFIXES) -> dict:
    stamp = UPDATED.search(text)
    if not stamp:
        raise ValueError("Cymru bogon list format changed: no 'last updated' line")
    updated = datetime.fromtimestamp(int(stamp.group(1)), timezone.utc)
    if now is not None and now - updated > MAX_AGE:
        raise ValueError(f"Cymru bogon list stopped updating: last updated {updated.date()}")
    prefixes = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            ipaddress.IPv6Network(line, strict=False)
        except ValueError as exc:
            raise ValueError(f"Cymru bogon list format changed: not a prefix: {line[:60]!r}") from exc
        prefixes += 1
    if prefixes < min_prefixes:
        raise ValueError(f"Cymru bogon list format changed: only {prefixes} prefixes")
    return {"prefixes": prefixes, "updated": updated.date().isoformat(), "url": HOME}


@source("cymru_bogons", MONTH, title="Team Cymru IPv6 full bogons", url=HOME)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=60)
    response.raise_for_status()
    return parse(response.text, now=ctx.now)
