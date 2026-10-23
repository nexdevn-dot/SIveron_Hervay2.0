# Siveron lokal entwickeln

Lokale Produktverantwortung und Weiterentwicklung: **Bao Dang**. Grundlage ist
**Harvey von Ethan Rogers**, Startbasis v0.3.0 (`e2632eb`). Die Anwendung und die
lokalen Änderungen stehen weiterhin unter **MIT**; ursprüngliche Urheberhinweise
bleiben erhalten. [Namensnennung](AUTHORS.md) ·
[Vergleich Ausgangsversion / aktueller Stand](docs/DEVELOPMENT_STATUS_2026-10-20.md).

Für die Weiterentwicklung: [Technischer Dokumentationsindex](docs/INDEX.md).
Er verweist gezielt auf Architektur, Module, Entwicklungsablauf und Roadmap.


Das Projekt ist eine neutrale Entwicklungsumgebung ohne Unternehmen,
Zielgruppe, Mailkonto oder freigegebene Kampagnen. Geschäftliche Einrichtung
und Produkttraining sind absichtlich offen.

## In Codex hinzufügen

Füge `/Users/tanjahamacher-dang/Documents/Codex/Siveron` über die
Projektverwaltung als lokalen Projektordner hinzu. Die direkte Registrierung
konnte aus diesem Chat nicht vorgenommen werden: Es gibt dafür kein
verfügbares Projekt-Anlegewerkzeug und die UI-Steuerung der Codex-App ist
gesperrt. Öffne anschließend einen Chat in diesem Projekt.

`AGENTS.md` beschreibt die Arbeitsregeln. Unter `.codex/environments/` sind
Setup und Aktionen für Dashboard, Tests und Umgebungsprüfung vorbereitet.
Falls die App sie nicht automatisch auswählt, wähle die Umgebung
„Siveron lokal“ in den Projekteinstellungen. Die Einbindung in die App muss
nach dem Hinzufügen geprüft werden.

## Starten

```bash
cd /Users/tanjahamacher-dang/Documents/Codex/Siveron
bash scripts/dashboard.sh
```

Dashboard: http://127.0.0.1:5555. Beenden mit Ctrl+C. Der Dashboardprozess
startet nicht automatisch den Vertriebsagenten. Mit `HARVEY_PORT=5556 bash
scripts/dashboard.sh` kannst du einen anderen Port verwenden.

```bash
bash scripts/doctor.sh
bash scripts/test.sh -q
scripts/harvey --help
```

Der Ordner enthält Python 3.12.15, eine virtuelle Umgebung mit bearbeitbar
installiertem Siveron und Codex CLI 0.159.3. Die globale Codex-Installation
bleibt unverändert. Nutze für Siveron immer `scripts/harvey` bzw.
`scripts/codex`, damit die richtige CLI-Version verwendet wird.

## Aufbau

- `harvey/`: Upstream-Anwendung mit lokaler Anpassung der Codex-Anbindung.
- `tests/`: Upstream-Tests und zusätzliche Tests für das alternative Modell.
- `harvey.local.yaml`: aktive private Konfiguration.
- `config/development.yaml`: versionierbare neutrale Vorlage.
- `.env`: leere Zugangsdaten-Vorlage; nicht veröffentlichen.
- `data/harvey.db`: lokale SQLite-Datenbank.
- `scripts/`: reproduzierbare Installation und Startbefehle.
- `requirements-dev.lock`: festgehaltene Python-Abhängigkeiten.
- `.tools/`, `.python/`, `.venv/`, `.cache/`: lokale Werkzeuge und Laufzeiten.

Die Dateien mit Zugangsdaten, Datenbank, Laufzeiten und persönlichen
Produktinformationen sind von Git ausgeschlossen. Keine Zugangsdaten in
Codex-Nachrichten einfügen. Keine globalen Modelleinstellungen wurden gesetzt.

## Reproduzierbare Installation

```bash
bash scripts/setup.sh
```

Benötigt auf einem neuen Mac Git, Node/npm und ein Python mit pip für die
kleine uv-Installation. Danach lädt das Skript die eigene Python-Laufzeit.
Beim ersten Einrichten ist Internet nötig. Bestehende `.env`, lokale
Konfiguration und Datenbank werden nicht überschrieben. Ein Umzug des
Projektordners erfordert eine neu erstellte `.venv`, da sie absolute Pfade
enthält. Die Browserinstallation für LinkedIn ist nicht erforderlich,
solange dieser Kanal deaktiviert bleibt.

## Später einen echten Anwendungsfall einrichten

**Stand vom 15. Oktober 2026:** Die lokale Anbindung verwendet jetzt
`gpt-6-luna` mit `codex_restricted_text: true` und niedriger Denktiefe.
Der Codex-Vorabcheck hat das Modell und seine Werkzeugklassen im Konto
bestätigt, ohne einen Modellprompt zu senden. Ein separater API-Schlüssel
oder API-Vertrag wurde nicht eingerichtet.

Die Originalversion von Siveron akzeptiert ausschließlich Modelle ohne
angebotene Werkzeuge und empfiehlt `gpt-5.5`, das in diesem Konto fehlt.
Auf Wunsch des Nutzers wurde eine lokale, eng begrenzte Alternative ergänzt:
`gpt-6-luna` und `gpt-6.1-sol` dürfen mit der geprüften Codex CLI 0.159.3 in
diesem Modus laufen. Luna ist die sparsamere Wahl für klar umrissene,
wiederkehrende Vertriebsaufgaben. Unter Siverons Isolation verbleiben interne
V8-Rechenwerkzeuge, Warten, Nutzereingabe und Uhr. Es gibt keinen Datei-,
Shell-, Netzwerk-, Mail- oder MCP-Zugriff durch das Modell. Jeder Versuch
eines Werkzeugaufrufs bricht die Modellantwort weiterhin ab. Eine komplette
Werkzeugfreiheit wird für diesen Modus ausdrücklich nicht behauptet.

Die Werkzeugoberfläche wurde mit der echten CLI an einem lokalen
Testserver geprüft, einschließlich eines absichtlich eingeschleusten
MCP-Servers (startet nicht) und einer verbotenen Werkzeuganforderung
(wird abgebrochen). Version, Kontotyp, Anmeldungsisolation, erlaubte
Netzwerkziele, deaktivierte Features, leere Ausführungsumgebungen und Hooks
werden weiterhin geprüft. Neue Modelle oder Werkzeuge sind nicht pauschal
zugelassen. Die ursprüngliche Prüfung für werkzeugfreie Modelle bleibt
als Standard ohne diesen lokalen Zusatzmodus erhalten.

1. KI-Anbindung prüfen: `scripts/harvey status --check`. Der Check sendet
   keinen Modellprompt. Falls ein Login fehlt, `scripts/codex login` im
   eigenen Terminal ausführen und mit ChatGPT anmelden. Siveron benötigt
   weiterhin eine dateibasierte Codex-Anmeldung. Diese lokale Version nutzt
   `gpt-6-luna`; `codex_restricted_text: true` muss dabei gesetzt bleiben.
   Eine Anmeldung in der Desktop-App allein garantiert diesen CLI-Login
   nicht. Keine Zugangsdaten automatisch kopieren oder umstellen.
2. Firma, Absender, Angebot, Branche und Region in `harvey.local.yaml`
   eintragen oder `scripts/harvey train https://DEINE-WEBSITE.example`
   nutzen. Training lädt Website-Inhalte und verbraucht KI-Kontingent.
3. Suchsignale im Dashboard auswählen. Es sind zunächst keine bestätigt.
   Danach lässt sich die Recherche mit `scripts/harvey discover` starten.
4. Für tatsächlichen E-Mail-Betrieb Mailanbieter und gegebenenfalls
   Adressprüfung in `.env` einrichten. Gmail benötigt eigene Google-OAuth-
   Daten und `scripts/harvey gmail auth`.
5. Versand erst gezielt aktivieren: E-Mail-Kanal einschalten, ein positives
   Tageslimit wählen und `scripts/harvey sending resume` ausführen.
   `require_approval: true` zunächst beibehalten.

Im neutralen Zustand sind E-Mail und LinkedIn deaktiviert, Versandlimit 0
und die Datenbank-Versandsperre aktiv. `scripts/harvey run` kann mit den
neutralen Platzhaltern den interaktiven Geschäftseinrichtungsassistenten
öffnen; das ist erwartetes Verhalten. Der Vertriebsagent läuft nicht im
Hintergrund und es gibt keinen Autostart.

## Git und weitere Entwicklung

Quelle: https://github.com/ethanplusai/harvey

Der Checkout verwendet den Branch `local/development`. `origin` zeigt
weiter auf das öffentliche Upstream-Projekt; es wurde nichts gepusht und
kein eigenes GitHub-Repository erstellt. Lokale Ergänzungen kannst du
prüfen und bei Bedarf committen. Für eine Veröffentlichung zuerst ein
eigenes Repository/Fork und dessen Remote einrichten.

Die technische Einrichtung ist unabhängig von der Eignung einer konkreten
Akquisekampagne. Kalenderbuchung bleibt im übernommenen Code ein Platzhalter.

## Geprüfter Stand

- Upstream: `e2632eb20ee2d4fb6fe04ae715a52f578acf9a37`, Siveron 0.3.0.
- Python 3.12.15 und projektlokale Codex CLI 0.159.3 installiert.
- Gesamtlauf nach Modellanpassung einschließlich echter CLI-Tests mit
  lokalen Mocks: 455 bestanden, 1 optionaler Pakettest übersprungen.
- Anschließend 64 gezielte Tests für Modellmodus, Provider, Plattform und
  den Erhalt der Einstellungen beim Training und Setup: alle bestanden.
- Modellwechsel: Codex-Vorabcheck für `gpt-6-luna` erfolgreich; dabei wurde
  kein Modellprompt gesendet. Die Konfiguration steht in der aktiven Datei
  `harvey.local.yaml` und in `config/development.yaml` für neue Installationen.
- Training und interaktiver Einrichtungsassistent behalten die gewählte
  Modellkonfiguration einschließlich des eingeschränkten Textmodus bei.
- Zweiter Aufruf von `scripts/setup.sh` erfolgreich, bestehende Konfiguration
  und Datenbank erhalten.
- Shell-Syntax, TOML-Struktur und Dateirechte geprüft. Das Codex-
  Umgebungsschema wurde mit dem installierten App-Code abgeglichen;
  die Auswahl in der Projektverwaltung ist noch nicht verifiziert.
- Dashboard im Browser geladen: Agent gestoppt, 0 Firmen/Kontakte,
  0 bestätigte Signale, Versand pausiert.
- Geschäftliche Einrichtung bleibt bei 33 Prozent im Dashboard stehen,
  weil Mailkonto, Angebot und Produktwissen absichtlich fehlen. Das ist
  für diese neutrale Umgebung erwartetes Verhalten.
- Kein Versand, keine Recherche, kein Produkttraining, kein Autostart,
  kein Push und keine Änderung der globalen Codex-Konfiguration.

Die Standardsuite meldet Warnungen aus Upstream-Abhängigkeiten bzw. zur
veralteten Nutzung von `datetime.utcnow()`. Sie führt zu keinen Testfehlern.

Codex-Umgebungen: https://learn.chatgpt.com/docs/environments/local-environment
