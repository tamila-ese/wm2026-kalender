#!/usr/bin/env python3
"""
WM 2026 -> Google-abonnierbarer Kalender (wm2026.ics)
Gratis-Variante via GitHub (kein eigenes Hosting noetig).

Datenquelle: API-Football (api-sports.io)
  Kostenloser Account -> API-Key. Gratis-Tarif: 100 Anfragen pro Tag.
  WM 2026: league=1, season=2026  (alle 104 Spiele in einem Aufruf).

Der API-Key wird aus der Umgebungsvariable API_FOOTBALL_KEY gelesen
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
API_KEY  = os.environ.get("API_FOOTBALL_KEY", "")
LEAGUE   = 1       # 1 = FIFA World Cup
SEASON   = 2026
OUTPUT   = "wm2026.ics"
CAL_NAME = "FIFA WM 2026"
DURATION = 120     # Minuten pro Spiel-Event

# Schweizer Spiele speziell kennzeichnen.
HIGHLIGHT_NEEDLES = ["switzerland", "schweiz", "suisse", "svizzera"]
HIGHLIGHT_EMOJI   = "\U0001F1E8\U0001F1ED"  # 🇨🇭


# ---------------------------------------------------------------------------
# Daten holen
# ---------------------------------------------------------------------------
def fetch_fixtures():
    if not API_KEY:
        print("FEHLER: Umgebungsvariable API_FOOTBALL_KEY ist leer.",
              file=sys.stderr)
        sys.exit(1)

    url = (f"https://v3.football.api-sports.io/fixtures"
           f"?league={LEAGUE}&season={SEASON}")
    req = Request(url, headers={
        "x-apisports-key": API_KEY,
        "User-Agent": "wm2026-cal/1.0",
    })
    try:
        with urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (URLError, HTTPError) as e:
        print(f"FEHLER beim API-Abruf: {e}", file=sys.stderr)
        sys.exit(1)

    if data.get("errors"):
        print(f"API meldet Fehler: {data['errors']}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(data.get("response"), list):
        print("Unerwartetes JSON-Format (kein 'response'-Array).", file=sys.stderr)
        sys.exit(1)
    return data["response"]


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


def safe(v, fallback="TBD"):
    v = (v or "").strip()
    return v if v else fallback


# ---------------------------------------------------------------------------
# Bauen
# ---------------------------------------------------------------------------
def build_ics(fixtures):
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
    for f in fixtures:
        fixture = f.get("fixture", {})
        teams   = f.get("teams", {})
        league  = f.get("league", {})

        iso = fixture.get("date")
        if not iso:
            continue

        start = to_utc_stamp(iso)
        end   = start + dt.timedelta(minutes=DURATION)

        home  = safe((teams.get("home") or {}).get("name"))
        away  = safe((teams.get("away") or {}).get("name"))
        rnd   = (league.get("round") or "").strip()

        venue = fixture.get("venue") or {}
        vname = (venue.get("name") or "").strip()
        vcity = (venue.get("city") or "").strip()
        loc   = ", ".join([p for p in (vname, vcity) if p])

        title = f"{home} vs {away}"
        if rnd:
            title += f" ({rnd})"

        is_swiss = any(n in (home + " " + away).lower()
                       for n in HIGHLIGHT_NEEDLES)
        if is_swiss:
            title = f"{HIGHLIGHT_EMOJI} {title}"

        fid = fixture.get("id") or f"{iso}{home}{away}"
        uid = f"wm2026-{fid}@wm-cal"

        desc = " | ".join([p for p in (rnd, loc) if p])

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"DTSTART:{fmt(start)}",
            f"DTEND:{fmt(end)}",
            fold(f"SUMMARY:{ics_escape(title)}"),
        ]
        if loc:
            lines.append(fold(f"LOCATION:{ics_escape(loc)}"))
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
    fixtures = fetch_fixtures()
    ics, count = build_ics(fixtures)
    with open(OUTPUT, "w", encoding="utf-8", newline="") as fh:
        fh.write(ics)
    print(f"OK: {OUTPUT} geschrieben ({count} Spiele).")


if __name__ == "__main__":
    main()
