#!/usr/bin/env python3
"""
WM 2026 -> Google-abonnierbarer Kalender (wm2026.ics)
Gratis-Variante via GitHub (kein eigenes Hosting noetig).

Datenquelle: football-data.org
  Kostenloser Account -> API-Key (kostenlos, "Free. Forever." fuer Top-Wettbewerbe).
  WM 2026 ist im Gratis-Tarif enthalten. Wettbewerbscode: WC.
  Rate-Limit Gratis: 10 Anfragen pro Minute (kein Tageslimit) -> mehr als genug.

Der API-Key wird aus der Umgebungsvariable FOOTBALL_DATA_KEY gelesen
(in GitHub als "Secret" hinterlegt, damit er nicht oeffentlich im Code steht).

Lauf:  python wm2026_calendar.py
Out:   wm2026.ics
"""

import os
import sys
import json
import datetime as dt
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
API_KEY  = os.environ.get("FOOTBALL_DATA_KEY", "")
COMP     = "WC"     # WC = FIFA World Cup
OUTPUT   = "wm2026.ics"
CAL_NAME = "FIFA WM 2026"
DURATION = 120      # Minuten pro Spiel-Event

# Schweizer Spiele speziell kennzeichnen.
HIGHLIGHT_NEEDLES = ["switzerland", "schweiz", "suisse", "svizzera"]
HIGHLIGHT_EMOJI   = "\U0001F1E8\U0001F1ED"  # 🇨🇭


# ---------------------------------------------------------------------------
# Daten holen
# ---------------------------------------------------------------------------
def fetch_matches():
    if not API_KEY:
        print("FEHLER: Umgebungsvariable FOOTBALL_DATA_KEY ist leer.",
              file=sys.stderr)
        sys.exit(1)

    url = f"https://api.football-data.org/v4/competitions/{COMP}/matches"
    req = Request(url, headers={
        "X-Auth-Token": API_KEY,
        "User-Agent": "wm2026-cal/1.0",
    })
    try:
        with urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"FEHLER beim API-Abruf (HTTP {e.code}): {body}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"FEHLER beim API-Abruf: {e}", file=sys.stderr)
        sys.exit(1)

    if "matches" not in data:
        print(f"Unerwartetes JSON-Format. Antwort: {json.dumps(data)[:400]}",
              file=sys.stderr)
        sys.exit(1)
    return data["matches"]


# ---------------------------------------------------------------------------
# ICS-Helfer
# ---------------------------------------------------------------------------
def ics_escape(text):
    return (text.replace("\\", "\\\\")
                .replace(";", "\\;")
                .replace(",", "\\,")
                .replace("\n", "\\n"))


def fold(line):
    out, b = [], line.encode("utf-8")
    while len(b) > 73:
        cut = 73
        while (b[cut] & 0xC0) == 0x80:  # nicht mitten in UTF-8-Zeichen schneiden
            cut -= 1
        out.append(b[:cut].decode("utf-8"))
        b = b" " + b[cut:]
    out.append(b.decode("utf-8"))
    return "\r\n".join(out)


def to_utc_stamp(iso):
    d = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)


def fmt(d):
    return d.strftime("%Y%m%dT%H%M%SZ")


def team_name(side):
    if not isinstance(side, dict):
        return "TBD"
    for key in ("name", "shortName", "tla"):
        v = (side.get(key) or "").strip()
        if v:
            return v
    return "TBD"


def nice(text):
    # GROUP_STAGE -> Group Stage, GROUP_A -> Group A
    return " ".join(w.capitalize() for w in str(text).replace("_", " ").split())


# ---------------------------------------------------------------------------
# Bauen
# ---------------------------------------------------------------------------
def build_ics(matches):
    now = fmt(dt.datetime.now(dt.timezone.utc))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//wm2026-cal//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{CAL_NAME}",
        "X-WR-TIMEZONE:UTC",
    ]

    count = 0
    for m in matches:
        iso = m.get("utcDate")
        if not iso:
            continue

        start = to_utc_stamp(iso)
        end   = start + dt.timedelta(minutes=DURATION)

        home  = team_name(m.get("homeTeam"))
        away  = team_name(m.get("awayTeam"))
        stage = nice(m.get("stage", ""))
        group = nice(m.get("group", "")) if m.get("group") else ""
        venue = (m.get("venue") or "").strip()

        title = f"{home} vs {away}"
        tag   = group or stage
        if tag:
            title += f" ({tag})"

        is_swiss = any(n in (home + " " + away).lower()
                       for n in HIGHLIGHT_NEEDLES)
        if is_swiss:
            title = f"{HIGHLIGHT_EMOJI} {title}"

        mid = m.get("id") or f"{iso}{home}{away}"
        uid = f"wm2026-{mid}@wm-cal"

        desc = " | ".join([p for p in (stage, group, venue) if p])

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"DTSTART:{fmt(start)}",
            f"DTEND:{fmt(end)}",
            fold(f"SUMMARY:{ics_escape(title)}"),
        ]
        if venue:
            lines.append(fold(f"LOCATION:{ics_escape(venue)}"))
        if desc:
            lines.append(fold(f"DESCRIPTION:{ics_escape(desc)}"))
        lines.append("CATEGORIES:" +
                     ("WM 2026,Schweiz" if is_swiss else "WM 2026"))
        lines += [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "DESCRIPTION:Anpfiff in 30 Minuten",
            "TRIGGER:-PT30M",
            "END:VALARM",
            "END:VEVENT",
        ]
        count += 1

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n", count


def main():
    matches = fetch_matches()
    ics, count = build_ics(matches)
    with open(OUTPUT, "w", encoding="utf-8", newline="") as fh:
        fh.write(ics)
    print(f"OK: {OUTPUT} geschrieben ({count} Spiele).")


if __name__ == "__main__":
    main()
