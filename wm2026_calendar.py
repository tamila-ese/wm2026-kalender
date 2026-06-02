#!/usr/bin/env python3
"""
WM 2026 -> Google-abonnierbarer Kalender (wm2026.ics)
Gratis-Variante via GitHub (kein eigenes Hosting noetig).

Datenquelle: football-data.org (kostenloser API-Key, WM gratis, Code: WC).
Der API-Key kommt aus der Umgebungsvariable FOOTBALL_DATA_KEY (GitHub Secret).

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

# Englisch (football-data.org) -> Deutsch. Deckt alle 48 Teilnehmer ab.
# Was hier nicht drin steht (z.B. neue Platzhalter), bleibt unveraendert.
DE_NAMES = {
    "Mexico": "Mexiko",
    "South Africa": "Suedafrika",
    "South Korea": "Suedkorea",
    "Czechia": "Tschechien",
    "Canada": "Kanada",
    "Bosnia-Herzegovina": "Bosnien-Herzegowina",
    "United States": "USA",
    "Paraguay": "Paraguay",
    "Qatar": "Katar",
    "Switzerland": "Schweiz",
    "Brazil": "Brasilien",
    "Morocco": "Marokko",
    "Haiti": "Haiti",
    "Scotland": "Schottland",
    "Australia": "Australien",
    "Turkey": "Tuerkei",
    "Germany": "Deutschland",
    "Curaçao": "Curacao",
    "Netherlands": "Niederlande",
    "Japan": "Japan",
    "Ivory Coast": "Elfenbeinkueste",
    "Ecuador": "Ecuador",
    "Sweden": "Schweden",
    "Tunisia": "Tunesien",
    "Spain": "Spanien",
    "Cape Verde Islands": "Kap Verde",
    "Belgium": "Belgien",
    "Egypt": "Aegypten",
    "Saudi Arabia": "Saudi-Arabien",
    "Uruguay": "Uruguay",
    "Iran": "Iran",
    "New Zealand": "Neuseeland",
    "France": "Frankreich",
    "Senegal": "Senegal",
    "Iraq": "Irak",
    "Norway": "Norwegen",
    "Argentina": "Argentinien",
    "Algeria": "Algerien",
    "Austria": "Oesterreich",
    "Jordan": "Jordanien",
    "Portugal": "Portugal",
    "Congo DR": "DR Kongo",
    "England": "England",
    "Croatia": "Kroatien",
    "Ghana": "Ghana",
    "Panama": "Panama",
    "Uzbekistan": "Usbekistan",
    "Colombia": "Kolumbien",
    "Italy": "Italien",
    "Nigeria": "Nigeria",
    "Denmark": "Daenemark",
    "Poland": "Polen",
    "Wales": "Wales",
    "Cameroon": "Kamerun",
    "Serbia": "Serbien",
    "Ukraine": "Ukraine",
}

# Stage/Group auf Deutsch
DE_STAGE = {
    "GROUP_STAGE": "Gruppenphase",
    "LAST_32": "Sechzehntelfinale",
    "LAST_16": "Achtelfinale",
    "ROUND_OF_16": "Achtelfinale",
    "QUARTER_FINALS": "Viertelfinale",
    "SEMI_FINALS": "Halbfinale",
    "THIRD_PLACE": "Spiel um Platz 3",
    "FINAL": "Final",
}

# Flaggen-Emoji pro Team (deutscher Name -> Flagge).
DE_FLAGS = {
    "Mexiko": "🇲🇽", "Suedafrika": "🇿🇦", "Suedkorea": "🇰🇷", "Tschechien": "🇨🇿",
    "Kanada": "🇨🇦", "Bosnien-Herzegowina": "🇧🇦", "USA": "🇺🇸", "Paraguay": "🇵🇾",
    "Katar": "🇶🇦", "Schweiz": "🇨🇭", "Brasilien": "🇧🇷", "Marokko": "🇲🇦",
    "Haiti": "🇭🇹", "Schottland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Australien": "🇦🇺", "Tuerkei": "🇹🇷",
    "Deutschland": "🇩🇪", "Curacao": "🇨🇼", "Niederlande": "🇳🇱", "Japan": "🇯🇵",
    "Elfenbeinkueste": "🇨🇮", "Ecuador": "🇪🇨", "Schweden": "🇸🇪", "Tunesien": "🇹🇳",
    "Spanien": "🇪🇸", "Kap Verde": "🇨🇻", "Belgien": "🇧🇪", "Aegypten": "🇪🇬",
    "Saudi-Arabien": "🇸🇦", "Uruguay": "🇺🇾", "Iran": "🇮🇷", "Neuseeland": "🇳🇿",
    "Frankreich": "🇫🇷", "Senegal": "🇸🇳", "Irak": "🇮🇶", "Norwegen": "🇳🇴",
    "Argentinien": "🇦🇷", "Algerien": "🇩🇿", "Oesterreich": "🇦🇹", "Jordanien": "🇯🇴",
    "Portugal": "🇵🇹", "DR Kongo": "🇨🇩", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Kroatien": "🇭🇷",
    "Ghana": "🇬🇭", "Panama": "🇵🇦", "Usbekistan": "🇺🇿", "Kolumbien": "🇨🇴",
    "Italien": "🇮🇹", "Nigeria": "🇳🇬", "Daenemark": "🇩🇰", "Polen": "🇵🇱",
    "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "Kamerun": "🇨🇲", "Serbien": "🇷🇸", "Ukraine": "🇺🇦",
}


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
            de = DE_NAMES.get(v, v)        # uebersetzen, sonst Original
            flag = DE_FLAGS.get(de, "")    # Flagge davor, falls bekannt
            return f"{flag} {de}".strip()
    return "TBD"


def stage_de(raw):
    return DE_STAGE.get(str(raw), str(raw).replace("_", " ").title())


def group_de(raw):
    if not raw:
        return ""
    # GROUP_A -> Gruppe A
    parts = str(raw).split("_")
    if len(parts) == 2 and parts[0] == "GROUP":
        return f"Gruppe {parts[1]}"
    return str(raw).replace("_", " ").title()


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
        stage = stage_de(m.get("stage", ""))
        group = group_de(m.get("group", ""))

        title = f"{home} - {away}"
        tag   = group or stage
        if tag:
            title += f" ({tag})"

        mid = m.get("id") or f"{iso}{home}{away}"
        uid = f"wm2026-{mid}@wm-cal"

        desc = " | ".join([p for p in (stage, group) if p])

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"DTSTART:{fmt(start)}",
            f"DTEND:{fmt(end)}",
            fold(f"SUMMARY:{ics_escape(title)}"),
        ]
        if desc:
            lines.append(fold(f"DESCRIPTION:{ics_escape(desc)}"))
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
