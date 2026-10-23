# Ansprechpersonen und Kontakte

Stand der Bedienergänzung: 18.10.2026. Technischer Einstieg:
[Kontakte](modules/contacts.md), [Unternehmen](modules/companies.md).

Die Sammelsuche ist jetzt unter **Unternehmen → Aktionen → Ansprechpersonen für
Auswahl suchen** erreichbar. Die Zeilenauswahl erfolgt über Kontrollkästchen;
eine separate Auswahlleiste wird nicht mehr angezeigt. Ergebnisse und Prüfung
liegen in einem bei Bedarf geöffneten Dialog. Eine gefundene Person wird erst nach
Prüfung und ausdrücklichem Speichern als Kontakt übernommen.

Kontaktaktionen sind in einer Auswahlliste mit Icons gebündelt. Zusätzlich zu
Notizen, Bearbeiten und Kontaktsperre gibt es **Löschen** mit wiederherstellbarem
Papierkorb. Wiederherstellung hebt Sperren nicht auf und startet abgebrochene
Nachrichten nicht erneut. Firmenkontakte bleiben als solche erkennbar; sie
werden nicht ohne Beleg in eine benannte Person umgewandelt.

## Bedienung

Unter **Unternehmen** eine oder mehrere Zeilen auswählen und
**Ansprechpersonen für Auswahl suchen** drücken. Auswahl über mehrere Seiten
wird unterstützt. Der Fortschritt zählt bearbeitete Unternehmen; die Zahl der
Personenvorschläge kann davon abweichen. **Suche anhalten** lässt die aktuell
laufenden Website-Prüfungen auslaufen. Nach einem Neuladen wird der gespeicherte
Auftrag wieder angezeigt und bei Bedarf fortgesetzt.

Unter **Ansprechpersonen prüfen** erscheinen offene Vorschläge aus bisherigen
Suchen, mit Unternehmen, Position, veröffentlichten Kontaktdaten, Quelle und
Funddatum. Die Liste zeigt 20 Vorschläge pro Seite. **Prüfen und übernehmen**
öffnet ein vorausgefülltes Formular. Erst **Kontakt speichern** legt den Kontakt
an. **Verwerfen** blendet einen Vorschlag dauerhaft aus; eine erneute Suche
übernimmt ihn nicht automatisch. Personen können auch ohne veröffentlichte
E-Mail übernommen werden.

**Kontakt hinzufügen** steht in der Kontaktübersicht, an jeder Unternehmenszeile
und in der Unternehmensdetailansicht bereit. Kontaktart **Person** benötigt
Vor- und Nachname; Position, E-Mail und Telefon sind optional. Ein vorhandenes
Unternehmen kann gesucht und zugeordnet oder ein neues Unternehmen mit Name
und optionaler Website angelegt werden. Eine Person ohne Unternehmen ist ebenfalls
möglich.

In einer Unternehmensdetailansicht öffnet **Als Firmenkontakt übernehmen** das
Formular mit Firmennamen, bekanntem Firmenpostfach und Telefonnummer. Firmenkontakte
haben keine fingierten Personennamen. Das Unternehmen und seine Historie bleiben
bestehen. Derselbe Kontakt wird bei wiederholter Anlage wiederverwendet. Konflikte
mit einer bereits anderweitig zugeordneten E-Mail werden vor dem Speichern gemeldet.

## Technischer Umfang

- Die Personensuche liest die offizielle Startseite und bis zu vier verlinkte
  Team-, Über-uns-, Kontakt- oder Impressumsseiten; fehlende Links werden durch
  Standardpfade ergänzt. Requests bleiben auf der Unternehmensdomain und ihrer
  www-Variante. Pro Antwort maximal 1 MB, begrenzte Redirects, öffentliche
  Netzwerkadressen und Zeitlimits. Keine Suchmaschinen- oder LinkedIn-Abfragen.
- Das bereits vorhandene **extruct** liest explizite schema.org-Personen aus
  JSON-LD und Microdata. Ein konservativer Parser ergänzt sichtbare Name/Rollen-
  Blöcke, auch mit deutschen Rollen und Umlauten. Personen-E-Mails und Telefonnummern
  werden ausschließlich aus expliziten Personeneigenschaften oder einem einzelnen
  Personenblock übernommen. Keine geratenen E-Mail-Muster.
- Es werden Vorschläge erzeugt: Ein Name auf einer Website belegt nicht automatisch
  eine aktuelle Beschäftigung oder die Zuständigkeit für einen bestimmten Einkauf.
  Ungewöhnliche, ausschließlich dynamische oder unstrukturierte Teamseiten können
  ohne Treffer bleiben. Crawl4AI und ein LLM-Fallback sind nicht erforderlich und
  wurden in diesem Schritt nicht zusätzlich installiert.
- Dauerhafte SQLite-Warteschlange mit zwei Arbeitern; Wiederaufnahme nach
  Serverneustart beim Öffnen der Unternehmensansicht. Bereits bearbeitete Firmen
  werden nicht erneut abgearbeitet. Eine beim Prozessabbruch unterbrochene Firma
  wird erneut gelesen. Aufträge bleiben von der öffentlichen E-Mail-Suche getrennt.
- Manuelle und übernommene Kontakte erhalten keine E-Mail-Verifizierung. Firmenkontakte
  haben den eigenen Status `company_contact` und werden nicht als neue Personen in
  den bestehenden Agentenablauf eingeordnet. Für eine bestehende Person werden
  vorhandene Daten beim Dublettenfund nicht überschrieben.
- Bestehende Datensätze werden als `person` migriert. Der CSV-Gesamtexport enthält
  zusätzlich `contact_type`, `source_url` und `source_found_at`.

## Open-Source-Grundlagen

Die vorhandenen Bibliotheken extruct, BeautifulSoup und python-email-validator
werden wiederverwendet. Der Ablauf für manuelle Anlage und Dublettenprüfung
orientiert sich an [Frappe CRM](https://github.com/frappe/crm/blob/develop/crm/fcrm/doctype/crm_deal/crm_deal.py).
Die Trennung von Person und Firmenkontakt orientiert sich an
[Odoo Community](https://github.com/odoo/odoo/blob/19.0/odoo/addons/base/models/res_partner.py).
Es wurde kein Quellcode dieser CRM-Anwendungen übernommen und kein vollständiges
CRM installiert.

## Prüfung

`tests/test_people_contacts.py` prüft strukturierte und deutsche Personenerkennung,
Quellenzuordnung, begrenzte Website-Zugriffe, manuelle Anlage, Firmenkontakte,
Dubletten, explizite Übernahme, Verwerfen sowie Abbruch und Wiederaufnahme.
Browserprüfung erfolgt mit einer getrennten temporären Datenbank und Demo-Daten.
Die neutralen Versand- und Freigabeeinstellungen bleiben erhalten.

## Ergebnisfenster statt dauerhafter Statusbereiche

Die Personenprüfung öffnet sich beim Start einer Suche in einem Dialog. Mit
**Schließen** oder Escape lässt er sich ausblenden; der Serverauftrag läuft
weiter. **Personenvorschläge ansehen** öffnet die Prüfung erneut, solange eine
Suche läuft oder offene Vorschläge vorhanden sind. Abgeschlossene Suchen ohne
offene Vorschläge belegen keinen Platz mehr in der Unternehmensliste. Der Dialog
öffnet sich nicht nach jedem Hintergrundupdate erneut.

Die öffentliche E-Mail-Suche verwendet ebenfalls einen schließbaren Dialog.
Das letzte Ergebnis ist über **E-Mail-Suchergebnis ansehen** erreichbar; bei
laufenden Aufträgen zeigt der Knopf den Fortschrittszugang an. Schließen hält
keine Suche an; dafür gibt es im Dialog weiterhin **Suche anhalten**.
