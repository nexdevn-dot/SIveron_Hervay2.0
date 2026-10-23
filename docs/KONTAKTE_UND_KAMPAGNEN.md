# Kontaktnotizen, Kontaktsperren und Kampagnenentwürfe

Stand der Ergänzung: 18.10.2026. Zuständigkeiten und Tests:
[Kontakte](modules/contacts.md), [Kampagnen](modules/campaigns.md),
[Postausgang und Unterhaltungen](modules/delivery.md).

## Durchgängiger aktueller Ablauf

**Kontakte auswählen → Kampagne erstellen → Nachricht gestalten und Vorschau prüfen
→ Entwurf speichern → Zur Freigabe vorbereiten → Postausgang prüfen und freigeben
→ geplanter Versand bei erfüllten Voraussetzungen.**

Der Composer bietet Formatierung, Platzhalter und Anhänge. Der KI-Vorschlag ist
optional und nutzt Angebot/Ziel; der aktuelle Vorschlagsendpunkt fordert einen
kurzen deutschen Text an. Die DE/EN-Oberfläche bestimmt nicht automatisch die
Sprache der generierten Nachricht. KI-Vorschläge speichern oder versenden nichts.

Eine Freigabe ist noch keine Versandbestätigung. Agent, Versandfreigabe,
Mailanbindung, Versandzeit, Tageslimit, Sperren und weitere Senderprüfungen wirken
unabhängig. Grün kennzeichnet versendete Nachrichten, Gelb wartende/geplante.
Unterhaltungen sind nach gespeicherter Kampagnenzuordnung gruppiert; die Nachricht
öffnet sich separat. Nicht zugeordnete Unterhaltungen erhalten eine eigene Gruppe.

## Kontakte bearbeiten

Im Reiter **Kontakte** stehen pro Datensatz die Aktionen in einer Auswahlliste mit Icons zur Verfügung:

- **Notizen:** bisherigen Verlauf lesen und eine neue Notiz speichern. Frühere
  Rückmeldungen bleiben erhalten. Gespeicherte Kommentare werden als Notizen
  behandelt; es wird keine automatische Auswertung durch die KI behauptet.
- **Bearbeiten:** Name, Position, Unternehmenszuordnung, E-Mail und Telefon
  korrigieren. Ein neues Unternehmen kann mit angelegt werden. Die Kontaktart
  bleibt erhalten. Eine geänderte E-Mail verliert ihre frühere Verifizierung;
  eine geänderte Telefonnummer ihre frühere Telefonverifizierung.
- **Nicht kontaktieren / Sperre ansehen:** Sperre mit Grund setzen oder eine
  manuelle Sperre ausdrücklich aufheben. Eine Abmeldung durch den Empfänger
  kann hier nicht aufgehoben werden.

- **Löschen:** Kontakt aus dem aktiven Bestand in den Papierkorb verschieben.
  Wartende Nachrichten werden abgebrochen. Wiederherstellung erhält bestehende
  Sperren und startet keine abgebrochenen Nachrichten neu.

Kontaktkorrekturen und Sperren erscheinen zusätzlich im Notizverlauf. Bereits
wartende Nachrichten werden bei Kontaktkorrekturen abgebrochen, damit alte
Adressen oder veraltete personalisierte Texte nicht weiterverwendet werden.
Eine konkurrierende Bearbeitung wird anhand einer Versionsnummer erkannt.

Die Liste bietet Suche, einen Sperrfilter und 30 Kontakte je Seite. Die Auswahl
bleibt beim Seitenwechsel erhalten und wird bei Filteränderungen aufgehoben.
Gesperrte Kontakte können nicht ausgewählt werden. Auf schmalen Bildschirmen
stehen Angaben und Aktionen eines Kontakts untereinander.

## Kampagne vorbereiten

1. Gewünschte Kontakte markieren und **Kampagne erstellen** wählen.
2. Einen vorhandenen manuellen Entwurf auswählen oder einen neuen anlegen.
3. Im Editor einen Kampagnennamen eintragen. Zielgruppe, Angebot, Ziel und
   geplanter Absender sind optionale Planungsangaben. Die Signatur ist eine Planungsnotiz; für eine vollständige
   Nachricht die gewünschte Signatur auch in den Nachrichtentext schreiben.
4. Bis zu zehn Nachrichten gestalten. Optional erstellt **Text mit KI vorschlagen**
   aus Angebot und Ziel einen Vorschlag über die vorhandene, eingeschränkte
   Brain-Anbindung. Die KI erhält die Planungsangaben, keine Kontaktliste,
   und speichert oder versendet nichts. Vorhandene Nachrichten werden erst
   nach Bestätigung ersetzt. Die Erreichbarkeit des Live-Modells ist durch
   Mock-Tests nicht belegt.

   Für manuelle Nachrichten gilt: Für Folgeschritte kann die Wartezeit
   nach der vorherigen Nachricht angegeben werden (0–365 Tage). Nachricht 1
   hat immer die Wartezeit 0.
5. Über die Vorschau einen Kontakt auswählen und die eingesetzten Platzhalter
   prüfen. Firmenkontakte benötigen eine allgemeine Anrede, weil sie keine
   erfundenen Personennamen besitzen.
6. **Entwurf speichern** drücken. Der Entwurf lässt sich unter Kampagnen erneut
   öffnen. Kontakte und Nachrichten können hinzugefügt oder entfernt werden.

Unterstützte Platzhalter sind `{{first_name}}`, `{{last_name}}`, `{{company}}`,
`{{title}}` und `{{personalization}}`. Unbekannte Platzhalter werden in der Vorschau
gekennzeichnet. Planungsangaben ändern weder die konfigurierte Absenderidentität
noch die Mailkonto-Einstellungen.

Eine syntaktisch gültige E-Mail genügt für die manuelle Kampagne. Technische
Verifizierung ist optional; der Prüfstatus wird nicht verändert. Personen und
Firmenkontakte folgen demselben Ablauf. Sperren und Abmeldungen bleiben wirksam.

7. **Zur Freigabe vorbereiten** speichert den Entwurf und prüft alle Kontakte
   und gerenderten Nachrichten. Fehlende E-Mails, bereits kontaktierte Empfänger,
   unvollständige Texte und unbekannte Platzhalter müssen zuerst korrigiert werden.
8. Die Nachrichten stehen anschließend als `pending_review` im **Postausgang**.
   Dort ausdrücklich freigeben oder ablehnen. Wiederholtes Vorbereiten erzeugt
   keine Duplikate. Die Kampagne wird schreibgeschützt (`awaiting_review`).

**Speichern und Vorbereiten versenden nichts.** Der manuelle Ablauf verwendet
SMTP/Gmail. Versandweg, deaktivierter Kanal, Tageslimit und Versandpause werden
im Editor angezeigt und bleiben unverändert. Ein optionaler Verifizierungsdienst
ist keine Pflicht zur Einrichtung. Automatisch erzeugte Kampagnen behalten ihre
bisherigen Prüfregeln. Nur ausdrücklich zur Freigabe vorbereitete manuelle
Kampagnen dürfen nach Outbox-Freigabe ohne technische Verifizierung versenden.

Seit 19.10.2026 wartet jeder native Folgeschritt auf den erfolgreichen Versand
seines unmittelbaren Vorgängers an denselben Kontakt in derselben Kampagne und
auf den gespeicherten Abstand. Verspätete Freigabe oder Tageslimit verkürzen ihn
nicht. Nach Erfolg wird der nächste wartende Termin nötigenfalls nach hinten
verschoben; ein bereits späterer Termin bleibt bestehen. Fehlgeschlagene oder
abgelehnte Vorgänger geben den Folgeschritt nicht frei. Bei 0 Tagen ist ebenfalls
zuerst Vorgängererfolg erforderlich. Erfolg bezeichnet die Annahme durch den
Versanddienst, nicht nachgewiesenen Postfacheingang. Bereits versendete Nachrichten
bleiben unverändert; Freigaben werden nicht automatisch erteilt.

Für bestehende Warteschlangen übernimmt eine Migration eindeutige ganzzahlige
Tagesabstände aus benachbarten gespeicherten Terminen. Fehlende oder unlesbare
Abstände werden nicht geschätzt: Solche Folgeschritte bleiben zurückgehalten.
Diese Änderung gilt nach Neustart der jeweiligen laufenden Prozesse und
Datenbankinitialisierung; sie startet den Agenten nicht.


## Durchsetzung der Kontaktsperre

Die Sperre besteht aus einem eigenen Kontaktmerkmal und einer gespeicherten
Adresssperre. Sie ist vom Bearbeitungsstatus des Kontakts unabhängig. Eine alte
abgemeldete Adresse bleibt auch nach einem Adresswechsel gesperrt. Frühere
Datensätze mit Status `opted_out` werden bei der Migration übernommen.

Eine Sperre beendet wartende Sequenzen und Antworten. Neue Outbox-Einträge und
Freigaben werden für gesperrte Kontakte verhindert. Der native Sender prüft den
aktuellen Datenbankstand unmittelbar vor der Übergabe an den Mailanbieter.
Auch der automatische Antwortpfad und die Übergabe an Instantly prüfen die
Sperre. Der normale Export geprüfter Kontakte schließt gesperrte Empfänger aus;
der Gesamtexport enthält Sperrkennzeichen und Grund.

Bei bereits extern in Instantly liegenden Kampagnen kann Siveron nicht jeden
späteren externen Einzelversand lokal kontrollieren. Deshalb wird bei einer
Kontaktsperre die gesamte betroffene externe Kampagne pausiert. Die Pause wird
als offener Auftrag gespeichert und nur bei bestätigter Anbieterantwort als
abgeschlossen behandelt. Bei einer fehlenden Bestätigung zeigt die Oberfläche
eine Warnung. Die Pause kann ausdrücklich erneut versucht werden; der Sender
versucht ausstehende Pausen ebenfalls erneut. Bis zur Bestätigung muss der
Anbieter direkt geprüft werden. Bereits übergebene oder gesendete Nachrichten
lassen sich durch die lokale Sperre nicht zurückholen.

Das Aufheben einer manuellen Sperre reaktiviert weder abgebrochene Nachrichten
noch pausierte Kampagnen.

## Verifizierte Firmenkontakte im Sender

Ein verifizierter Firmenkontakt mit dem bisherigen Status `company_contact`
ist im vorhandenen Versandablauf nun ebenso auswählbar wie neue Personen.
Die Prüfung verlangt dabei die Kontaktart `company`. Bei der nativen
Vorbereitung wechselt der Status zu `queued`, nach erfolgreichem Versand zu
`contacted`. Die Kontaktart bleibt `company`; Personennamen werden nicht ergänzt.
Dies gilt auch für die Empfängerauswahl bei Instantly. Adressverifizierung,
Kontaktsperren, Freigabe, Kanalaktivierung, Versandpause und Limits gelten weiter.
Die bestehende optionale Behandlung riskanter Adressen wurde nicht geändert.
Der gehaltene Status `manual_draft` bleibt vom automatischen Versand ausgeschlossen.

## Implementierung und Prüfung

Die Umsetzung verwendet den bestehenden Python-/SQLite-/JavaScript-Aufbau.
Frappe CRM, Mautic und EspoCRM dienten als Vorbilder für die recherchierten
Abläufe; es wurde kein vollständiges CRM zusätzlich installiert und kein
Quellcode aus diesen Projekten übernommen.

- `harvey/crm.py`: transaktionale Sperren, gehaltene Entwürfe und externe Pause.
- `harvey/crm_routes.py`: Kontakt-, Notiz-, Status- und Entwurfsendpunkte.
- `harvey/contacts.py`: explizite Kontaktanlage und Korrekturen mit Versionstest.
- `harvey/web/crm.js`: Kontaktaktionen, Auswahl und Kampagneneditor.
- `tests/test_crm_actions.py`: Notizen, Migration, Korrekturen, Auswahl,
  Sperrdurchsetzung, Entwurfsstatus, Export und externe Pausen mit Mocks.

Die Browserprüfung verwendet eine getrennte temporäre Datenbank mit Demo-Daten.
Mocks und Browser-Demodaten beweisen keine echte Mailzustellung.

## Versand im Dashboard einstellen

Unter **Einstellungen → E-Mail-Versand** lassen sich der Versand aktivieren oder
abschalten und die maximale Anzahl versendeter E-Mails pro Tag einstellen.
**Versandeinstellungen speichern** ändert nur diese beiden Werte in der aktiven
Konfiguration; Freigabepflicht, Mailkonto und Versandpause bleiben erhalten.
Ein Tageslimit von 0 hält den Versand an. Der Agent muss für Änderungen gestoppt
sein; die Werte gelten beim nächsten Start unter **Steuerung**. Speichern startet
den Agenten nicht und versendet keine Nachricht. Nach einem ausdrücklichen Start
können bereits freigegebene Nachrichten versendet werden.

## Freigegebene Nachrichten bei erreichtem KI-Budget

Ein erreichtes KI-Nutzungslimit pausiert die Texterstellung und andere
KI-Aufgaben. Bereits freigegebene Nachrichten im nativen SMTP/Gmail-Postausgang
werden weiterhin im normalen Heartbeat geprüft. Dafür liest Siveron vorher
Antworten und Rückläufer ohne KI: Antworten stoppen ausstehende Folgenachrichten,
Abmeldungen setzen die Kontaktsperre, Rückläufer werden wie bisher behandelt.
Die Antworten bleiben für eine spätere vollständige KI-Bearbeitung erhalten.
Scheitert die Postfachprüfung, wird nichts versendet. Es werden in diesem Modus
keine neuen Kampagnen an den Versand übergeben und keine Nachrichten freigegeben.
Versandpause, deaktivierter Kanal, Ruhezeiten, Tageslimit und Inhaltsprüfungen
bleiben wirksam. Codex-Anmelde-, Versions- und Isolationsprüfungen bleiben
unverändert; ein Sicherheits- oder Anmeldefehler hält den Zyklus weiterhin an.

## Ampel im Postausgang

Jede Nachricht zeigt neben der Farbe einen lesbaren Status:
- Grün: **Versendet** – der Versanddienst hat die Nachricht erfolgreich angenommen.
- Gelb: **In Warteschlange** oder **Wartet auf Freigabe** – noch nicht versendet.
- Rot: **Versand fehlgeschlagen** – Fehlergrund steht in der Übersicht.
- Grau: **Abgelehnt** oder **Abgebrochen** – kein erfolgreicher Versand.

Ohne offene Freigabeentscheidungen aktualisiert sich der Postausgang alle
15 Sekunden. Grün bestätigt den erfolgreichen Versandaufruf, nicht die
Zustellung im Posteingang oder das Lesen durch den Empfänger.

## Nachrichten komfortabel bearbeiten

Der Kampagneneditor zeigt die Nachrichtenfolge als kompakte Auswahlliste. Nur
die gewählte Nachricht ist geöffnet. Tiptap 3.31.3 stellt lokal einen Editor mit Formatierungen,
Klartextalternative und Rückgängig/Wiederholen bereit. Vorname, Nachname,
Unternehmen, Position und Personalisierung lassen sich über Knöpfe in Betreff
oder Nachricht einfügen (je nach zuletzt bearbeitetem Feld). Über **Vorschau**
werden bekannte Kontaktdaten eingesetzt; **Bearbeiten** wechselt zurück.

**Duplizieren** erstellt eine unabhängig bearbeitbare Kopie. Die Reihenfolge
lässt sich über den Ziehgriff mit SortableJS 1.15.7 oder per **Nach oben / Nach
unten** ändern. Die Nachrichten werden dabei neu nummeriert. Nachricht 1 hat
keine Wartezeit; wird der bisherige Erstkontakt zu einer Folgenachricht,
erhält er zunächst drei Tage Wartezeit. Folgenachrichten können 0–365 Tage
Wartezeit haben. Mindestens eine und höchstens zehn Nachrichten bleiben im
Editor. Entfernen einer gefüllten Nachricht verlangt eine Bestätigung.

Speicherung, Vorschau und nativer Versand unterstützen die beschriebenen
Textformatierungen und Anhänge; eine Klartextalternative bleibt erhalten.
Komplexe Newsletter-Layouts und eingebettete Bilder werden nicht angeboten. Zeilenumbrüche und Platzhalter bleiben
beim Speichern/Neuladen erhalten. Bereits zur Freigabe übergebene Kampagnen
bleiben schreibgeschützt, lassen sich aber Nachricht für Nachricht ansehen.
Die vorhandene optionale KI-Texthilfe bleibt separat, ohne neue KI-Dienste oder
kostenpflichtige Editor-Erweiterungen. Der Frontend-Build ist optional für die
Entwicklung; die fertigen Assets werden lokal mitgeliefert. Build und zehn
Editor-Tests: `cd tools/campaign-editor && npm ci --ignore-scripts && npm run build && npm test`.
Die vorhandene Terminierung von Folgeschritten relativ zur Vorbereitung bleibt
unverändert; der Editor allein ändert diese Versandlogik nicht.

## Kontaktaktionen als Menü und wiederherstellbares Löschen

Jede Kontaktzeile bietet **Aktionen** als aufklappbare Liste mit SVG-Icons.
Notizen, Bearbeiten und Nicht kontaktieren/Sperre ansehen bleiben verfügbar;
**Löschen** öffnet eine Bestätigung mit dem konkreten Kontaktnamen.
Das Menü liegt über der Tabelle und wird beim Scrollen nicht abgeschnitten.
Pfeiltasten, Pos1/Ende und Escape unterstützen die Tastaturbedienung. Die
periodische Kontaktaktualisierung pausiert bei geöffnetem Menü oder Dialog.

Löschen entfernt den Kontakt aus aktiven Übersichten, der Firmenkontaktanzahl,
Kampagnenauswahl und beiden CSV-Exporten. Der Datensatz und die Historie bleiben
für die Wiederherstellung erhalten. Eine Transaktion markiert den Kontakt als
gelöscht und gesperrt, bricht wartende Nachrichten ab und merkt nötige externe
Kampagnenpausen vor. Eine fehlende Anbieterbestätigung wird ausdrücklich gemeldet.
Bestehende Adresssperren und Abmeldungen bleiben erhalten.

**Gelöschte Kontakte → Aktionen → Wiederherstellen** bringt den Kontakt zurück.
Vorherige Kontaktsperren bleiben bestehen; abgebrochene Nachrichten und pausierte
Kampagnen werden nicht reaktiviert. Versionsprüfungen verhindern das Löschen oder
Wiederherstellen anhand veralteter Daten. Wiederanlage einer gelöschten Identität
verweist auf die Wiederherstellung, statt eine neue ungesperrte Kopie anzulegen.

## Formatierte Kampagnen und Dateianhänge (18.10.2026)

Der Editor unterstützt nun Fett, Kursiv, Unterstrichen, Durchgestrichen,
Aufzählungen, nummerierte Listen, Zitate, Links und das Einfügen von Emoji-Text.
Formatierungen werden als validiertes Dokument gespeichert; der Server leitet
Klartext und HTML daraus ab. Kontakt-Platzhalter werden ausschließlich in Text
ersetzt und für HTML maskiert. Die bestehenden Text-, Link- und Versandgrenzen
bleiben aktiv. Der Klartext-Modus früherer Kampagnen bleibt kompatibel.

**Empfänger hinzufügen** sucht direkt im Editor nach verfügbaren Kontakten mit
E-Mail. Die Auswahl erscheint als entfernbare Chips. **Kontaktliste öffnen**
erlaubt weiterhin die umfangreichere Auswahl. Die neuen Beschriftungen und
Bedienhinweise sind auf Deutsch und Englisch vorhanden; die Sprachumschaltung
übersetzt keine vom Nutzer geschriebenen Nachrichtentexte oder Dateinamen.

Pro Nachricht können fünf Dateien mit jeweils höchstens 10 MB und zusammen
höchstens 20 MB hochgeladen werden: PDF, PNG/JPG, UTF-8-TXT/CSV und DOCX/XLSX.
Der Server validiert Format und Größe. Zuordnungen werden im Entwurf gespeichert;
Entfernen löst die Zuordnung, löscht aber keine historischen Dateiinhalte.
Dateien werden lokal als unveränderliche Uploads gespeichert. Beim Duplizieren
sind Textdokument und Dateiauswahl unabhängig bearbeitbar. Anbieter können wegen
MIME-Kodierung oder eigener Limits kleinere maximale Nachrichtengrößen erlauben.

Zur Freigabe werden personalisierter Klartext, HTML und Anhangsreferenzen samt
Dateinamen im Postausgang festgehalten. Dort sind Formatierung und Downloads
vor der Freigabe sichtbar. SMTP und Gmail erzeugen MIME-Nachrichten mit
Klartextalternative, HTML-Teil und den gespeicherten Dateiinhalten. Fehlende
Anhänge verhindern den Versand. Der externe Instantly-Ablauf übernimmt diese
Erweiterung nicht. Es wurden keine Umfrage-Erfassung oder Newsletter-Layouts
mit eingebetteten Bildern hinzugefügt.

Prüfung: vollständige Python-Suite, ergänzte Dokument-/Upload-/MIME- und
Sender-Tests sowie Node-Tests für unabhängige Duplikate. Browserprüfung mit
isolierter Datenbank: Empfängersuche, Formatierung, Upload, Speichern/Neuladen,
Vorschau, DE/EN, Mobilansicht und Vorbereitung im Test-Postausgang. Kein echter
Mailversand und keine Live-KI-Abfrage wurden als Test ausgelöst.

## Versandbereitschaft je Nachricht (19.10.2026)

Im Postausgang ergänzt **Versandbereitschaft** den gespeicherten Nachrichtenstatus.
**Bereit**, **Wartet**, **Blockiert**, **Ungeklärt** und **Fehlgeschlagen** erklären
mit nächster Aktion, was nach der letzten Prüfung bekannt ist. **Weitere Ursachen**
zeigt zusätzliche Hindernisse. Änderungen an Freigaben, Pausen, Sperren oder
Einstellungen werden dadurch nicht automatisch ausgeführt. Fehlende oder veraltete
Laufzeitdaten bleiben ungeklärt; Bereit ist keine Versandbestätigung. Anzeige und
nativer Sender verwenden gemeinsame fachliche Prüfungen. Details und Grenzen:
[Versandmodul](modules/delivery.md).
