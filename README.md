# Scorer

Fußballergebnisse der eigenen Ligen, automatisch aktualisiert.

Ein GitHub-Actions-Workflow liest jeden Abend die Spiel- und Tabellenseiten des
Tabellendienstes der WA Mediengruppe, legt das Ergebnis als `data/daten.json` im
Repo ab und committet es. `index.html` zeigt diese Datei an – ohne Wartezeit und
ohne API-Schlüssel.

## Einrichten

1. Dateien in dieses Repo übernehmen (Struktur beibehalten).
2. **Settings → Actions → General → Workflow permissions**: „Read and write
   permissions" aktivieren. Ohne das kann der Workflow nicht committen.
3. **Settings → Pages**: Source „Deploy from a branch", Branch `main`, Ordner
   `/ (root)`. Die App liegt dann unter
   `https://granny1990.github.io/Scorer/`.
4. **Actions → Ergebnisse aktualisieren → Run workflow** einmal manuell starten.
   Danach läuft es von allein.

## Zeitplan

`cron: "5 16,17,18,19 * * *"` – GitHub plant in UTC. Die vier Läufe decken
18, 19 und 20 Uhr deutscher Zeit in Sommer- und Winterzeit ab. GitHub startet
geplante Läufe unter Last mitunter einige Minuten später.

## Ligen und Markierungen ändern

Alles steht in `ligen.json`:

```json
{
  "markiert": ["Rhynern", "Hammer SpVg"],
  "ligen": [
    { "name": "Regionalliga West", "url": "https://wa-mediengruppe.de/..." }
  ]
}
```

`ligen` bestimmt, was geholt und in welcher Reihenfolge angezeigt wird.
`markiert` enthält Textbausteine – jede Mannschaft, in deren Namen einer davon
vorkommt, wird in Spielen und Tabelle hervorgehoben. "Rhynern" trifft also auch
"SV Westfalia Rhynern II".

Die Quell-URLs findet man auf `wa-mediengruppe.de/tabellen-wa/fussball/`: dort
die Liga aufrufen und die Adresse aus der Adresszeile kopieren, ohne den
Saison-Zusatz wie `/v:2026_27` – dann bleibt sie auch nächste Saison richtig.
Verfügbar ist alles von der Bundesliga bis zur Kreisliga D, dazu Frauen- und
Jugendligen.

## Archiv

Jeder Lauf schreibt zusätzlich `data/archiv/JJJJ-MM-TT.json`. Daraus lassen sich
später Spieltags-PDFs oder Saisonauswertungen bauen.

## Wenn etwas nicht erkannt wird

Kann eine Seite gelesen, aber nicht ausgewertet werden, legt das Skript die
Rohseite unter `debug/` ab. Diese Datei genügt, um den Parser nachzuziehen.
