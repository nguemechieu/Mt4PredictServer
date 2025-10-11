import requests
import datetime
from dateutil import parser as date_parser
from typing import List, Dict, Any

NEWS_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


class NewsCalendar:
    """Efficient, rate-limited fetcher for FairEconomy / ForexFactory economic events."""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.last_fetch: datetime.datetime | None = None
        self.cache_ttl = datetime.timedelta(minutes=5)  # wait at least 5min before refetch

    # ------------------------------------------------------------
    def fetch(self, force: bool = False):
        """Fetch current week's news with rate-limit protection."""
        try:
            now = datetime.datetime.utcnow()
            if (
                    self.last_fetch
                    and not force
                    and now - self.last_fetch < self.cache_ttl
                    and self.events
            ):
                # 🧠 Use cached data — avoid hitting rate limit
                return

            resp = requests.get(NEWS_URL, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                self.events = self._parse(data)
                self.last_fetch = now
            else:
                print(f"⚠️ News fetch failed: {resp.status_code} {resp.text[:200]}")
        except requests.exceptions.RequestException as e:
            print(f"🌐 Network error fetching news: {e}")
        except Exception as e:
            print(f"⚠️ Unexpected error fetching news: {e}")

    # ------------------------------------------------------------
    def _parse(self, data):
     """Convert raw JSON list into internal dicts with UTC-naive datetimes."""
     events = []
     for e in data:
        try:
            dt = date_parser.parse(e.get("date")) if e.get("date") else None
            if dt and dt.tzinfo is not None:
                # Convert aware → naive UTC
                dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        except Exception:
            dt = None

        events.append({
            "title": e.get("title", ""),
            "country": e.get("country", ""),
            "impact": e.get("impact", "Unknown"),
            "datetime": dt,
            "forecast": e.get("forecast", ""),
            "previous": e.get("previous", ""),
            "actual": e.get("actual", ""),
        })
     return events

    # ------------------------------------------------------------
    def upcoming(self, max_events: int = 5) -> List[Dict[str, Any]]:
        """Return a list of upcoming events (UTC future only)."""
        now = datetime.datetime.utcnow()
        up = [e for e in self.events if e["datetime"] and e["datetime"] >= now]

        up.sort(key=lambda e: e["datetime"])
        return up[:max_events]

    # ------------------------------------------------------------
    def high_impact_for_currency(self, symbol: str | None = None) -> List[Dict[str, Any]]:
        """
        Return upcoming high-impact events for a given currency or country.
        Example: symbol='EURUSD' → look for 'EUR' and 'USD' events.
        """
        now = datetime.datetime.utcnow()
        if not symbol:
            return []

        currencies = {symbol[:3], symbol[3:]} if len(symbol) >= 6 else {symbol}
        return [
            e
            for e in self.events
            if e["country"].upper() in currencies
               and e["impact"].lower() in ("high", "medium")
               and e["datetime"]
               and e["datetime"] >= now
        ]

    # ------------------------------------------------------------
    def summarize(self, symbol: str | None = None, limit: int = 5) -> str:
        """
        Return a short formatted summary string for GPT context.
        """
        self.fetch()  # Safe — rate-limited
        events = self.high_impact_for_currency(symbol)
        if not events:
            return "No high-impact events upcoming."

        lines = []
        for e in events[:limit]:
            t = e["datetime"].strftime("%b %d %H:%M UTC") if e["datetime"] else "?"
            lines.append(
                f"{t} — {e['country']} {e['title']} "
                f"(Impact: {e['impact']}, Forecast: {e['forecast']}, Prev: {e['previous']})"
            )
        return "\n".join(lines)
