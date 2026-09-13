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

## Ligen ändern

`ligen.json` bearbeiten – Name und Quell-URL pro Liga. Die URLs stammen von
`wa-mediengruppe.de/tabellen-wa/fussball/`; dort gibt es alles von der
Bundesliga bis zur Kreisliga D sowie Frauen- und Jugendligen.

## Hervorhebung

In `index.html` steuert die Zeile `const EIGENE = /rhynern/i;`, welche
Mannschaften farblich markiert werden.

## Archiv

Jeder Lauf schreibt zusätzlich `data/archiv/JJJJ-MM-TT.json`. Daraus lassen sich
später Spieltags-PDFs oder Saisonauswertungen bauen.

## Wenn etwas nicht erkannt wird

Kann eine Seite gelesen, aber nicht ausgewertet werden, legt das Skript die
Rohseite unter `debug/` ab. Diese Datei genügt, um den Parser nachzuziehen.
