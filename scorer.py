#!/usr/bin/env python3
"""Holt Spiele und Tabellen der in ligen.json konfigurierten Ligen.

Schreibt:
  data/daten.json            aktueller Stand samt Markierungen, den die App liest
  data/archiv/JJJJ-MM-TT.json  Tageskopie als Archiv
  debug/<liga>.html          Rohseite, nur wenn das Parsen misslingt

Laeuft ohne API-Schluessel: die Seiten werden direkt gelesen.
"""

import json
import pathlib
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup, NavigableString

WURZEL = pathlib.Path(__file__).resolve().parent.parent
DATEN = WURZEL / "data"
ARCHIV = DATEN / "archiv"
DEBUG = WURZEL / "debug"

KOPF = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9",
}

ERGEBNIS = re.compile(r"^(\d{1,3})\s*:\s*(\d{1,3})$")
PLATZ = re.compile(r"^(\d{1,2})\.$")
GANZZAHL = re.compile(r"^[-+]?\d+$")
DATUM = re.compile(r"\d{1,2}\.\s*\w+\s*\d{4}")
AUSFALL = re.compile(r"abgesagt|ausgefallen|abgebrochen|verlegt|gewertet|spielfrei", re.I)


def hole(url: str) -> str:
    anfrage = urllib.request.Request(url, headers=KOPF)
    with urllib.request.urlopen(anfrage, timeout=40) as antwort:
        return antwort.read().decode("utf-8", "replace")


def saeubere(text: str) -> str:
    return " ".join(text.split())


ZAHL_TOKEN = re.compile(r"^(?::?[-+]?\d+|:)$")
RANG_TOKEN = re.compile(r"^\d{1,2}\.$")


def entdoppele(name: str) -> str:
    """wa.de gibt Teamnamen doppelt aus: 'VfL Mark VfL Mark'."""
    teile = saeubere(name).split()
    if len(teile) >= 2 and len(teile) % 2 == 0:
        haelfte = len(teile) // 2
        if teile[:haelfte] == teile[haelfte:]:
            return " ".join(teile[:haelfte])
    return " ".join(teile)


def saeubere_name(rohtext: str) -> str:
    """Aus dem Zeilentext den reinen Mannschaftsnamen herausloesen.

    Die Tabellenzeile liegt auf wa.de zusaetzlich als ein Textblock vor, etwa
    '1. Hammer SportClub Hammer SportClub 6 5 0 1 32 :8 24 15': vorn der
    Tabellenplatz, dann der doppelte Name, dahinter die Statistik.

    Gesucht wird die Verdopplung, nicht der Zahlenschwanz - sonst verliert
    'SuS Ruenthe 08' seine 08 und '1. FC Nuernberg' seine Eins.
    """
    teile = saeubere(rohtext).split()
    if teile and RANG_TOKEN.match(teile[0]):
        teile = teile[1:]
    if not teile:
        return ""

    for laenge in range(len(teile) // 2, 0, -1):
        if teile[:laenge] == teile[laenge:2 * laenge]:
            return " ".join(teile[:laenge])

    # Keine Verdopplung: Zahlen nur abschneiden, wenn hinten eine vollstaendige
    # Statistik steht (Sp G U V Tore :Gegentore TD Pkt).
    schwanz = 0
    while schwanz < len(teile) and ZAHL_TOKEN.match(teile[len(teile) - 1 - schwanz]):
        schwanz += 1
    if schwanz >= 6:
        teile = teile[:len(teile) - schwanz]
    return " ".join(teile)


# --------------------------------------------------------------- Tabelle
def lies_tabelle(suppe: BeautifulSoup):
    """Erste Tabelle, die wie eine Gesamttabelle aussieht."""
    for tabelle in suppe.find_all("table"):
        reihen = []
        for tr in tabelle.find_all("tr"):
            zellen = [saeubere(z.get_text(" ", strip=True))
                      for z in tr.find_all(["td", "th"])]
            zellen = [z for z in zellen if z]
            if len(zellen) < 4:
                continue

            platz = None
            for z in zellen:
                treffer = PLATZ.match(z)
                if treffer:
                    platz = int(treffer.group(1))
                    break
            if platz is None:
                continue

            namen = [z for z in zellen
                     if not GANZZAHL.match(z) and not PLATZ.match(z)
                     and not z.startswith(":")]
            zahlen = [int(z) for z in zellen if GANZZAHL.match(z)]
            if not namen or len(zahlen) < 3:
                continue

            name = saeubere_name(max(namen, key=len))
            if not name:
                continue
            reihen.append([name, zahlen[0], zahlen[-2], zahlen[-1]])

        if len(reihen) >= 4:
            reihen.sort(key=lambda r: (-r[3], -r[2], r[0]))
            return reihen
    return []


# --------------------------------------------------------------- Spiele
def zeichenkette_tokens(suppe: BeautifulSoup):
    """Dokumentreihenfolge aus Mannschaftslinks, Ergebnissen und Daten."""
    tokens = []
    for knoten in suppe.descendants:
        if getattr(knoten, "name", None) == "a":
            href = knoten.get("href") or ""
            if "/spiele/mannschaft:" in href:
                name = entdoppele(knoten.get_text(" ", strip=True))
                if name:
                    tokens.append(("team", name))
            continue
        if isinstance(knoten, NavigableString):
            text = saeubere(str(knoten))
            if not text:
                continue
            if ERGEBNIS.match(text):
                treffer = ERGEBNIS.match(text)
                tokens.append(("ergebnis", (int(treffer.group(1)), int(treffer.group(2)))))
            elif AUSFALL.search(text) and len(text) < 40:
                tokens.append(("status", text))
            elif DATUM.search(text) and len(text) < 60:
                tokens.append(("datum", text))
    return tokens


def lies_spiele(suppe: BeautifulSoup):
    tokens = zeichenkette_tokens(suppe)
    spiele, daten_texte, puffer = [], [], []

    for art, wert in tokens:
        if art == "datum":
            if not spiele:
                daten_texte.append(wert)
            continue
        if art == "team":
            if len(puffer) == 2:
                spiele.append([puffer[0], puffer[1], None, None, "offen"])
                puffer = []
            puffer.append(wert)
            continue
        if len(puffer) == 2:
            if art == "ergebnis":
                spiele.append([puffer[0], puffer[1], wert[0], wert[1], "gespielt"])
            else:
                spiele.append([puffer[0], puffer[1], None, None, saeubere(wert)])
            puffer = []

    if len(puffer) == 2:
        spiele.append([puffer[0], puffer[1], None, None, "offen"])

    zeitraum = ""
    if daten_texte:
        erste = DATUM.search(daten_texte[0])
        letzte = DATUM.search(daten_texte[-1])
        if erste and letzte:
            zeitraum = erste.group(0) if erste.group(0) == letzte.group(0) \
                else f"{erste.group(0)} bis {letzte.group(0)}"

    return spiele, zeitraum


# --------------------------------------------------------------- Liga
def hole_liga(liga: dict) -> dict:
    name, url = liga["name"], liga["url"]
    ergebnis = {"liga": name, "url": url, "zeitraum": "", "spiele": [],
                "tabelle": [], "fehler": None}
    try:
        seite = hole(url)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as fehler:
        ergebnis["fehler"] = f"Seite nicht erreichbar: {fehler}"
        print(f"  ! {name}: {ergebnis['fehler']}")
        return ergebnis

    suppe = BeautifulSoup(seite, "html.parser")
    spiele, zeitraum = lies_spiele(suppe)
    tabelle = lies_tabelle(suppe)

    ergebnis["spiele"] = spiele
    ergebnis["zeitraum"] = zeitraum
    ergebnis["tabelle"] = tabelle

    if not spiele and not tabelle:
        ergebnis["fehler"] = "Seite gelesen, aber nichts erkannt."
        DEBUG.mkdir(exist_ok=True)
        pfad = DEBUG / (re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") + ".html")
        pfad.write_text(seite[:400000], encoding="utf-8")
        print(f"  ! {name}: nichts erkannt, Rohseite in {pfad.name}")
    else:
        print(f"  + {name}: {len(spiele)} Spiele, {len(tabelle)} Tabellenplaetze")

    return ergebnis


def main() -> int:
    konfig = json.loads((WURZEL / "ligen.json").read_text(encoding="utf-8"))
    if isinstance(konfig, list):          # altes Format: nur eine Liste von Ligen
        ligen, markiert = konfig, []
    else:
        ligen = konfig.get("ligen", [])
        markiert = [m for m in konfig.get("markiert", []) if str(m).strip()]

    jetzt = datetime.now(timezone(timedelta(hours=2)))  # deutsche Zeit, grob
    print(f"Lauf um {jetzt:%d.%m.%Y %H:%M}")

    eintraege = [hole_liga(liga) for liga in ligen]

    inhalt = {
        "stand": jetzt.isoformat(timespec="minutes"),
        "quelle": "wa-mediengruppe.de (Tabellendienst der WA Mediengruppe)",
        "markiert": markiert,
        "ligen": eintraege,
    }

    DATEN.mkdir(exist_ok=True)
    ARCHIV.mkdir(exist_ok=True)
    text = json.dumps(inhalt, ensure_ascii=False, indent=1)
    (DATEN / "daten.json").write_text(text, encoding="utf-8")
    (ARCHIV / f"{jetzt:%Y-%m-%d}.json").write_text(text, encoding="utf-8")

    erfolgreich = sum(1 for e in eintraege if not e["fehler"])
    print(f"Fertig: {erfolgreich} von {len(eintraege)} Ligen gelesen.")
    return 0 if erfolgreich else 1


if __name__ == "__main__":
    sys.exit(main())
