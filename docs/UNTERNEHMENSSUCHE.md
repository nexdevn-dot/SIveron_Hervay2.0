# Unternehmenssuche: Eingabe und Fortschritt

Stand der Ergänzung: 18.10.2026. Technische Zuständigkeiten und Tests:
[Modul Entdecken](modules/discovery.md); offene Erweiterungen: [Roadmap](ROADMAP.md).

## Aktuelle Gliederung und Suchablauf

Die Ansicht beginnt mit **Quelle**. Direkt danach stehen bei Google Maps die
**Google-Maps-Suchoptionen**, anschließend die optionale öffentliche E-Mail-Suche.
Die eigene Rubrik **Suchkriterien** gruppiert Branchenbegriffe, Standort und Radius.
Weitere Suchoptionen, Vorschau und Start/Stop folgen darunter.

Google Maps verwendet einen lokalen Browser mit Schnell-/Teilgebietssuche und
wiederverwendbaren Suchabschnitten. Es wird kein separater Scrapingdienst angebunden.
Die Radiusprüfung benötigt genaue Koordinaten; unbekannte Koordinaten werden
übersprungen. Höchstens 100 Abschnitte mit jeweils bis zu 200 Einträgen bedeuten
keine zugesicherte Vollständigkeit. Einträge lassen sich vor dem Import nach
gelistetem Website-/Telefonvorkommen filtern.

Aktivierte Signale bestimmen, welche unterstützten Beobachtungen gespeichert werden.
Sie erzwingen derzeit keine Aufnahme nur solcher Unternehmen, die alle Signale erfüllen.
Ohne bestätigtes Signal stoppt die eigentliche Suche. Die optionale E-Mail-Phase
prüft maximal 1000 Unternehmen dieses Suchlaufs; sie erstellt keine Kontakte und
versendet keine Nachrichten. Die Websiteprofilierung kann zusätzlich ältere,
noch nicht oder nicht kürzlich geprüfte Unternehmen bearbeiten.

## Eingabe

Die Brancheneingabe verwendet Tagify 4.39.0. Begriffe lassen sich mit Enter,
per Vorschlagsliste und als kommagetrennte Liste hinzufügen, einzeln entfernen
oder bearbeiten. Ein lokaler Katalog ergänzt Synonyme; die bestehende
serverseitige Quellenprüfung bleibt maßgeblich. Nicht unterstützte Begriffe
werden kenntlich gemacht. Die Bibliothek erweitert nicht die Kategorien von
OSM oder Geoapify. Für freie Hersteller-/Nischenbegriffe kann eine konfigurierte
Websuchquelle nötig sein.

Ortsvorschläge verwenden Geoapify Geocoder Autocomplete 3.1.0 mit einer eigenen
Backend-Anfragefunktion. Der Browser bekommt keinen API-Schlüssel. Ab drei
Zeichen und nach 450 ms Eingabepause fragt er `/api/discover/locations` ab.
Antworten werden für einen Tag zwischengespeichert; neue externe Anfragen
reservieren eine Einheit im vorhandenen Geoapify-Kontingent. Es wird kein
Nominatim-Autocomplete eingesetzt. Ohne Schlüssel, bei fehlendem Kontingent
oder Ausfall bleibt manuelle Ortseingabe möglich.

Mehrere ausgewählte Orte bleiben als Chips sichtbar. Ausgewählte Koordinaten
werden serverseitig validiert und können erneute Geokodierung vermeiden. Der
Radius (1–200 km im API; vorgegebene Auswahl im UI) gilt für Kartenquellen.
Die Vorschau aktualisiert sich automatisch. Ein unbestätigter Branchenentwurf
blockiert den Start, damit keine getippten Begriffe unbemerkt fehlen.

Die JS-/CSS-Dateien liegen lokal unter `harvey/web/vendor/`; Versionen und
MIT-Lizenztexte bleiben erhalten. Laufzeit-CDNs und ein Frontend-Build sind
nicht erforderlich.

## Fortschritt

`run_discovery`, Ortsauflösung und Website-Prüfung liefern optionale
Fortschrittsereignisse. Das Dashboard speichert den aktuellen Stand unter
`discovery_progress` in SQLite und stellt ihn über `/api/discover/progress`
bereit. Während eines Laufs fragt das UI ungefähr jede Sekunde ab.

Die drei Phasen haben jeweils eigene, echte Zähler:

1. Orte vorbereiten: noch benötigte Ortsauflösungen.
2. Unternehmen suchen: abgearbeitete Suchabfragen, auch fehlgeschlagene.
3. Websites prüfen: abgearbeitete Unternehmen.

Eine Phase mit 100 % bedeutet nicht, dass spätere Phasen abgeschlossen sind.
Aktueller Begriff/Ort beziehungsweise Firmenname, neue und bekannte Unternehmen,
Fehler sowie gesamte Laufzeit werden angezeigt. Wiederholungen und Wartezeiten
bleiben Teil der gemessenen Zeit; währenddessen wird kein Fortschritt erfunden.

Die geschätzte Restzeit gilt ausdrücklich **für die aktuelle Phase**. Sie nutzt
die Dauer der letzten bis zu acht abgeschlossenen Einträge und erscheint erst
ab zwei Messwerten als Zeitspanne. Bei ungewöhnlich langer Wartezeit wird die
Schätzung ausgeblendet und eine Warteanzeige eingeblendet. Neue Phasen beginnen
mit einer neuen Messreihe.

Neuladen zeigt den gespeicherten Fortschritt und die laufende Suchauswahl wieder.
Nach einem Server-Neustart wird ein abgebrochener Lauf als unterbrochen angezeigt;
er wird nicht automatisch erneut gestartet. „Anhalten“ lässt den laufenden
Arbeitsschritt auslaufen und verhindert weitere Abfragen/Website-Prüfungen.
Bestandsdaten, Versandfreigaben und Modellkonfiguration werden nicht verändert.

## Parkplatzbetreiber finden

Seit dem 18. Oktober 2026 erkennt die Suchzuordnung auch Parkplatz-Begriffe:

- **Parkplatzbetreiber**, **Parkraumbewirtschaftung**, **Parkraummanagement**,
  **Parkplatzmanagement** und **Parkservice** suchen bei OpenStreetMap und
  Geoapify nach Parkstandorten mit ausdrücklich hinterlegtem Betreiber.
- **Parkhausbetreiber** beschränkt die Suche auf Parkhäuser und Tiefgaragen
  mit Betreiberangabe.
- **Parkplatz** und **Parkplätze** liefern Parkflächen; **Parkhaus** und
  **Tiefgarage** liefern die entsprechenden Standorte. Diese Treffer sind
  nicht automatisch eigenständige Betreiberfirmen.

Ein Begriff und ein separat gewählter Ort reichen zum Einstieg aus. Mehrere
Synonyme verbreitern die Kartensuche nicht: Sie können dieselben Standorte
erneut abfragen. Der Suchradius bezieht sich auf die Parkstandorte, nicht auf
die Firmenzentrale eines Betreibers.

Betreibername und Betreiber-Kontaktdaten werden nur aus ausdrücklich dafür
vorgesehenen Angaben übernommen. Kontaktdaten einer einzelnen Parkfläche
werden nicht als Betreiber-Kontaktdaten ausgegeben. Eine fehlende
Betreiber-Website bleibt unbekannt und belegt nicht, dass die Firma keine
Website hat. Bei bekannter Domain greift die bestehende Dublettenprüfung;
ohne Domain können mehrere Standorte desselben Betreibers getrennt erscheinen.

Die Abdeckung hängt von den hinterlegten Kartendaten ab. Geoapify kann nur
Betreiber übernehmen, deren Angabe in seiner Antwort enthalten ist. Eine
Websuchquelle wie SerpApi kann ergänzend Firmen finden, die nicht als Betreiber
an einem Kartenstandort erfasst sind. **Flughafenparken**, **Valet Parking** und
**Lkw-Parkplatzbetreiber** werden nicht pauschal auf normale Pkw-Parkflächen
umgedeutet; dafür eine Websuchquelle verwenden. Schlüssel, Kontingente und
Versandfreigaben werden durch diese Erweiterung nicht verändert.

Quellen für die Zuordnung: [OSM-Parkplätze](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dparking)
und [Geoapify-Kategorien](https://apidocs.geoapify.com/docs/places/#categories).

## Prüfung

`bash scripts/test.sh -q` prüft die bestehende Suite sowie Messwerte, Phasenwechsel,
Fehler/Stoppen, Koordinatenvalidierung, Proxy-Cache und Kontingentgrenzen.
Die Browserprüfung verwendet ein eigenes lokales Dashboard mit temporärer
Datenbank und simulierten Antworten; sie startet keine echte Unternehmenssuche.

## Ergebnislimit erkennen

Neue OpenStreetMap-Suchläufe erfassen je Suchanfrage das eingestellte Limit,
die tatsächlich gelieferten Rohdatensätze und die nutzbaren Treffer nach dem
Entfernen namenloser Einträge. Die Abschlussanzeige zeigt **Ergebnislimit
erreicht**, wenn die Quelle mindestens so viele Rohdatensätze wie angefordert
liefert. Weitere Treffer sind dann möglich, aber nicht garantiert. Andernfalls
zeigt sie an, dass die abgeschlossenen Anfragen unter dem Limit blieben.
Dubletten und bereits bekannte Unternehmen reduzieren die Zahl neuer Unternehmen
zusätzlich. Auch unterhalb des Limits ist das Ergebnis keine vollständige
Marktübersicht. Bei älteren Läufen oder Quellen ohne Rohdatenmessung wird das
Erreichen des Limits als nicht erfasst ausgewiesen; es wird nicht aus der Zahl
neuer Unternehmen geschätzt. Die Messwerte bleiben beim Neuladen erhalten.
