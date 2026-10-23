# Kampagnen: Reifegrad und Sollablauf

## Historische Bewertung – Nachtrag vom 18.10.2026

Der folgende ursprüngliche Befund beschreibt den Stand vom **16.10.2026**.
Seine Reifegrade und damaligen Lücken sind keine aktuelle Bewertung.
Seitdem wurden unter anderem manuelle Kampagnenvorbereitung mit Übergabe in den
Postausgang, Firmenkontakt-Unterstützung, vereinfachte manuelle E-Mail-Eignung,
Kontaktaktionen/Papierkorb, Composer/Anhänge, Kampagnen-Unterhaltungen sowie
Such-, Filter- und Fortschrittsfunktionen ergänzt beziehungsweise erweitert.

Den aktuellen implementierten Umfang dokumentieren [Modulübersichten](INDEX.md).
Noch nicht umgesetzte Vorschläge stehen separat in der [Roadmap](ROADMAP.md).
Dieser Nachtrag vergibt keinen neuen Gesamtreifegrad und behauptet keinen neuen
Live-Nachweis. Die ursprüngliche Bewertung bleibt zur Nachvollziehbarkeit erhalten.

---

Stand: 16.10.2026. Bewertung durch Quellprüfung, 24 gezielte bestehende Tests und
zwei isolierte Laufzeitprüfungen. Keine produktiven Kampagnen oder Nachrichten
gestartet; keine Änderung des Anwendungscodes oder der Konfiguration.

## Urteil

Qualitativer Gesamtreifegrad **2 von 5: funktionsfähiger Prototyp**. Der manuelle
Entwurfseditor erreicht **3 von 5: nutzbares MVP**. Der durchgängige Weg vom
manuellen Entwurf zum kontrollierten Versand ist noch unvollständig.

Skala: 1 Teilansätze, 2 Prototyp mit wesentlichen Lücken, 3 nutzbares MVP,
4 produktionsreif mit kontrolliertem Betrieb, 5 belastbar optimiert und überwacht.
Die Werte sind eine fachliche Einordnung, keine automatisch gemessenen Prozente.

| Bereich | Reifegrad | Befund |
|---|---|---|
| Entwurf, Nachrichtenfolge, Wiederöffnen | 3/5 | Speicherung, bis zehn Schritte, Vorschau, Versionsprüfung vorhanden |
| Kontaktzuordnung | 3/5 | Auswahl, Dublettenvermeidung über IDs und Sperrprüfung vorhanden; Auswahl ist noch keine Versandbereitschaft |
| Kontaktsperren und lokale Schutzprüfungen | 3/5 | Sperren, Abbruch wartender Nachrichten, frische Prüfung vor Providerübergabe; kein Nachweis echten Providerbetriebs |
| Briefing und KI-Unterstützung im Editor | 2/5 | Briefing gespeichert; kein damit verbundener Textgenerierungsablauf |
| Manueller Entwurf bis Versandfreigabe | 1/5 | Veröffentlichungs-/Prüf-/Übergabeschritt fehlt |
| Zeitplanung und Lebenszyklus | 2/5 | Grundlegende Verzögerungen und Status vorhanden; Zustände und tatsächliche Versandzeiten unzureichend verbunden |
| Kampagnenauswertung | 2/5 | Backend-Grundlagen vorhanden, editornahe Kennzahlen und korrekte Versandbasis fehlen |

## Was heute funktioniert

Kontakte auswählen, neue oder vorhandene manuelle Entwürfe öffnen, Briefing und
Nachrichten bearbeiten, Kontakte und Schritte entfernen oder ergänzen, Platzhalter
in der Vorschau einsetzen und dauerhaft speichern. Gesperrte Empfänger werden
serverseitig abgewiesen; ungeprüfte E-Mails können Teil eines Entwurfs sein.
Bereits übergebene Kampagnen sind schreibgeschützt. Manuelle Kampagnen erhalten
`manual_draft` und werden vom bestehenden Sender bewusst nicht abgearbeitet.

Daneben existiert der ältere Agentenablauf: Writer erstellt `draft`-Kampagnen;
der native Sender bereitet pro Kontakt Nachrichten im Postausgang vor und sendet
freigegebene fällige Einträge unter den konfigurierten Schutzbedingungen.
Der alternative Instantly-Pfad übergibt Sequenzen an einen externen Anbieter.
Diese vorhandenen Bausteine ergeben noch keinen vollständigen manuellen Ablauf.

## Priorisierte Befunde

### A1 – Übergang vom manuellen Entwurf fehlt (hoch)

`harvey/crm.py:120` speichert `manual_draft`; `harvey/agents/sender.py:381`
überspringt diesen Status. Die Entwurfsrouten in `harvey/crm_routes.py:112`
bieten Anlegen, Laden und Bearbeiten. Ein expliziter veröffentlichender Übergang
mit finaler Empfängerprüfung und Outbox-Erstellung fehlt.

### A2 – Firmenkontakte können nicht regulär übernommen werden (hoch; inzwischen behoben)

`SENDABLE_STATUSES` in `harvey/agents/sender.py:43` erlaubt `new` und `queued`.
Firmenkontakte haben `company_contact`. Selbst eine verifizierte Adresse wird
bei der Vorbereitung deshalb ausgelassen. Firmenkontaktart und Bearbeitungsstatus
müssen voneinander getrennt oder ausdrücklich im Freigabeablauf behandelt werden.

Nachtrag zur Umsetzung: `has_sendable_status()` berücksichtigt jetzt ausdrücklich
Firmenkontakte mit Kontaktart `company` und dem bisherigen Status
`company_contact`, sowohl nativ als auch bei Instantly. Die bisherigen
Adress-, Sperr-, Freigabe- und Limitprüfungen bleiben erhalten. Kontaktart und
leere Personennamen bleiben beim Wechsel zu `queued`/`contacted` unverändert.
Manuelle Entwürfe werden dadurch nicht veröffentlicht. Regressionen stehen in
`tests/test_company_contact_sender.py`. Die ursprüngliche isolierte Beobachtung
oben beschreibt den Stand vor dieser Korrektur.

### A3 – Aktivstatus ohne vorbereitete Nachricht (hoch)

Die native Vorbereitung setzt in `harvey/agents/sender.py:435` `active`, auch
wenn kein Empfänger die Prüfungen bestanden hat. Isoliert bestätigt: ein
verifizierter Firmenkontakt, null Postausgangseinträge, trotzdem eine aktive
Kampagne. Erforderlich sind eindeutige Zustände für Prüfbedarf, Freigabewarteschlange,
Zeitplanung, laufenden Versand, Pause und Abschluss.

### A4 – Vorschau und Versand rendern unterschiedlich (mittel)

`harvey/web/crm.js:142` toleriert beliebige Leerzeichen in bekannten Platzhaltern.
`harvey/agents/sender.py:375` ersetzt nur zwei konkrete Schreibweisen. Isoliert
bestätigt: `{{  first_name  }}` bleibt im Versand-Renderer erhalten, obwohl die
Vorschau es ersetzen kann. Gemeinsame serverseitige Renderfunktion verwenden.

### A5 – Briefing steuert den Editorinhalt noch nicht (mittel)

Zielgruppe, Angebot, Ziel, geplanter Absender und Signatur werden in `brief_json`
gespeichert. Der Editor löst damit keine KI-Texterstellung aus. Der vorhandene
Writer arbeitet separat mit seiner Konfiguration. Ein eingetragener Absender
ändert kein Versandkonto; die Signatur ist derzeit ausdrücklich eine Planungsnotiz.

### A6 – Zentrale Versandbereitschaft fehlt (hoch vor Veröffentlichung)

Die Entwurfsvalidierung erlaubt leere Nachrichten und null Kontakte; das ist für
Zwischenstände sinnvoll. Vor einer Veröffentlichung braucht es einen eigenen
Prüfbericht für Empfängerstatus, Adressverifizierung, Sperren, Kontaktdaten,
Dubletten, Inhalte, Platzhalter, Konto und Zeitplan. Die heutige Anzeige
„verifizierte E-Mail“ berücksichtigt beispielsweise nicht alle Senderstatusregeln.
Die Inhaltsgrenzen von Editor und abschließendem Versand-Gate unterscheiden sich.

### A7 – Verzögerungen beziehen sich auf die Vorbereitung (mittel)

`harvey/agents/sender.py:416` berechnet alle Fälligkeiten aus dem Zeitpunkt der
Vorbereitung. Werden einzelne Nachrichten erst Tage später freigegeben oder
durch ein Limit verzögert, ist das nicht gleichbedeutend mit einer Wartezeit nach
dem tatsächlich versandten vorherigen Schritt. Folgeschritte sollten von dessen
bestätigtem Versandzeitpunkt abhängen. Versandfenster, Zeitzone und Werktage
gehören in einen expliziten manuellen Zeitplan.

### A8 – Auswertung ist noch keine belastbare Kampagnensteuerung (mittel)

`harvey/state.py:1772` liefert erste Kampagnenstatistiken. Die Antwortquote
verwendet zugeordnete Kontakte als Nenner; für eine echte Versandquote sind
mindestens tatsächlich angeschriebene eindeutige Empfänger nötig. Im neuen
Kampagneneditor fehlen die konsolidierte Sicht auf geplant, freigegeben,
gesendet, fehlgeschlagen, beantwortet, pausiert und abgeschlossen sowie passende
Bedienaktionen. Eine Antwort- oder Öffnungsstatistik allein belegt keinen Erfolg.

## Empfohlener Sollablauf

1. **Briefing:** Zielgruppe, Angebot, Ziel und tatsächlichen Absender festlegen.
2. **Empfänger prüfen:** geeignete, gesperrte, ungeprüfte und unvollständige
   Datensätze unterscheiden; ausgeschlossene Empfänger mit Grund anzeigen.
3. **Nachrichten erstellen:** manuell oder über eine ausdrücklich ausgelöste,
   briefinggestützte KI-Hilfe. Personen und Firmenpostfächer passend ansprechen.
4. **Verbindliche Vorschau:** dieselbe serverseitige Renderfunktion wie für den
   späteren Versand verwenden. Alle Nachrichten je Empfänger prüfbar machen.
5. **Versandbereitschaft prüfen:** Konto, Empfänger, Texte, Platzhalter, Limits,
   Sperren, Dubletten und Zeitplan in einem verständlichen Prüfbericht bewerten.
6. **In den Postausgang übergeben:** ausdrückliche Aktion; freigegebene Version
   von Nachricht, Empfänger und Adresse festhalten. Änderungen widerrufen die
   betroffene Freigabe und benötigen erneute Prüfung.
7. **Freigeben und planen:** Empfänger-/Nachrichtenfreigabe, Startzeit, Zeitzone,
   Versandfenster und Tageslimit. Eine Veröffentlichung ist keine globale
   Aufhebung sämtlicher Versandsperren.
8. **Versenden und überwachen:** letzte Sperrprüfung direkt vor der Übergabe;
   Folgeschritte anhand des tatsächlichen Versands planen. Bei Antwort oder
   Abmeldung Nachfassnachrichten stoppen; Kampagnen pausieren oder beenden können.
9. **Auswerten:** tatsächliche Versandereignisse, Antworten, Fehler und
   Abmeldungen nachvollziehbar auf Kampagne und Empfänger beziehen.

Empfohlene Reihenfolge: zuerst A1/A2/A3/A6 zusammen lösen, anschließend A4/A5,
danach Zeitplanung und Auswertung. Zusätzliche Analysefunktionen bringen erst
Nutzen, wenn der grundlegende Zustands- und Freigabeablauf verlässlich arbeitet.

## Nachweise und Grenzen

- `tests/test_crm_actions.py` und `tests/test_outbox_native.py`: erneut ausgeführt,
  **24 bestanden**; eine vorhandene Abhängigkeitswarnung.
- Zusätzliche isolierte Prüfungen mit temporärer Datenbank und FakeProvider:
  Aktivstatus ohne Outbox bei Firmenkontakt und Leerzeichenabweichung im Renderer.
  Ausgehende Testnachrichten: **0**.
- Die zuletzt zuvor ausgeführte Gesamtsuite hatte 540 bestandene und 22
  übersprungene Tests. Sie ersetzt keinen echten Provider- oder Betriebstest.
- Diese Bewertung ist keine Freigabe für Liveversand. Die bestehenden lokalen
  Entwicklungsstandards wurden nicht verändert.


## Nachtrag 17. Oktober 2026: manueller Ablauf vereinfacht

A1 ist für den nativen SMTP/Gmail-Ablauf behoben: `manual_draft` lässt sich
atomar als `awaiting_review` in den Postausgang mit `pending_review`-Nachrichten
übergeben. Technische E-Mail-Verifizierung ist dort optional; Kontakt- und
Adresssperren, Inhaltsprüfung, Versandpause, Tageslimit und ausdrückliche
Outbox-Freigabe bleiben wirksam. Der Kontaktprüfstatus wird nicht verfälscht.
A4 ist durch denselben Renderer für die Übergabe und den Sender behoben.
Für A5 ist eine optionale, ausdrücklich ausgelöste KI-Texthilfe mit validierter
Ausgabe hinzugekommen. Versandhindernisse werden im Editor angezeigt.
Der Bericht oben bleibt als historischer Bewertungsstand erhalten.
