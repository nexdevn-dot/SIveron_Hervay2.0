# Siveron – Produktbrief für kritische Weiterentwicklung mit ChatGPT

**Stand: 20. Oktober 2026 · lokale Projektvariante**

**Lokale Produktverantwortung und Weiterentwicklung: Bao Dang.** Ausgangspunkt ist
Harvey von Ethan Rogers, v0.3.0, Commit `e2632eb`. Die Anwendung und lokalen Änderungen
bleiben MIT-lizenziert; ursprüngliche Urheberhinweise und gesonderte
Drittanbieter-Lizenzen bleiben erhalten. Der Vergleich bezieht sich auf diese
Startbasis, nicht auf die erste jemals veröffentlichte Harvey-Version.
[Ausführlicher Entwicklungsvergleich](DEVELOPMENT_STATUS_2026-10-20.md).

Dieses Dokument kann allein in ChatGPT hochgeladen oder vollständig eingefügt werden.
Es beschreibt den dokumentierten Funktionsstand dieser lokalen Anwendung, nicht alle
Funktionen des ursprünglichen Open-Source-Projekts. Es enthält keine Zugangsdaten,
Kundendaten oder private Betriebskonfiguration. Eine implementierte Funktion ist
nicht automatisch ein Nachweis für produktionsreifen Betrieb oder erfolgreiche
Live-Anbindung an einen externen Anbieter.

## 1. Wofür die Lösung gedacht ist

Siveron unterstützt den Weg von der Unternehmensrecherche über die Kontaktpflege
und Kampagnenvorbereitung bis zu kontrolliertem E-Mail-Versand, Antwortbearbeitung
und ausdrücklich angelegten Verkaufschancen.

Der Schwerpunkt liegt auf einem überschaubaren lokalen Vertriebsarbeitsplatz.
Ein konkretes Geschäftsmodell, Produkt, Kundensegment, Budget und Teamgröße sind
hier bewusst nicht festgelegt. Vorschläge sollen diese Angaben erfragen oder ihre
Annahmen deutlich kennzeichnen.

**Produktprinzipien:**

- Möglichst einfache Bedienung; erweiterte Aktionen kompakt in Menüs bündeln.
- Bestehende Funktionen verbinden, statt parallele Werkzeuge für dieselbe Aufgabe einzuführen.
- Vorhandene Open-Source-Bausteine sinnvoll wiederverwenden; Lizenz und Integrationsaufwand prüfen.
- Erweiterungen möglichst direkt integrieren, ohne einen zusätzlichen separaten Dienst betreiben zu müssen.
- Oberfläche und Hilfe in Deutsch und Englisch, auch auf kleinen Bildschirmen nutzbar.
- Unbekannte oder unsichere Daten sichtbar lassen; keine Sicherheit vortäuschen.
- Recherche, Kontaktübernahme, Entwurf, Freigabe und Versand als getrennte Entscheidungen behandeln.

## 2. Die wichtigsten Objekte

| Objekt | Bedeutung |
| --- | --- |
| Unternehmen | Rechercheeintrag einer Organisation mit bekannten Angaben und Quellen. |
| Kontakt | Benannte Person oder allgemeiner Firmenkontakt; kann einem Unternehmen zugeordnet sein. |
| Signal | Aktivierbares Recherchemerkmal; eine Beobachtung speichert den gefundenen Nachweis. |
| Zielkundenprofil | Gespeicherte erforderliche/ausgeschlossene Signale und zulässiges Nachweisalter. |
| Kampagne | Empfängerauswahl, Planungsangaben und Nachrichtenfolge. |
| Postausgangsnachricht | Einzelne Nachricht mit eigenem Prüf-, Freigabe-, Termin- und Versandstatus. |
| Unterhaltung | Gespeicherter Austausch mit einem Kontakt und Kampagnenbezug, soweit vorhanden. |
| Verkaufschance | Explizit erfasster Vertriebsfall mit Phase, Zuständigkeit und nächster Aufgabe. |
| Vorlage | Wiederverwendbarer Nachrichtenablauf mit optionalen Suchkriterien und Zielprofil-Verweis. |

Ein Unternehmen mit gefundener E-Mail ist noch kein übernommener Kontakt. Ein
Firmenkontakt ist keine automatisch erfundene Person. Eine Antwort ist noch keine
Qualifizierung, Terminvereinbarung oder Verkaufschance.

## 3. Vorhandene Funktionen

### Heute – zentrale Aufgabenübersicht

- Überblick über Unternehmen, Kontakte, Signale und Aktivitäten.
- Handlungsbedarf für ungeprüfte Antworten, Nachrichten zur Freigabe und blockierten oder unklaren Versand.
- Fällige Aufgaben offener Verkaufschancen.
- Direkter Einstieg in den betroffenen Datensatz.
- Aufgaben leiten sich aus dem aktuellen Zustand ab; gewöhnliches terminbedingtes Warten wird nicht als Fehler dargestellt.

### Signale und Zielkundenprofile

- Recherchemerkmale bestätigen oder ablehnen.
- Zielgruppen aus vorhandenen Signalbeobachtungen bilden: erforderliche und ausgeschlossene Merkmale kombinieren.
- Zielkundenprofile speichern und Nachweisalter festlegen.
- Ergebnisse als passend, nicht passend oder unbekannt mit Belegen und Gründen prüfen.
- Unternehmensnamen in Ergebnislisten öffnen ein Profil-Pop-up.
- Ein aktiviertes Signal steuert die Erfassung unterstützter Merkmale; es ist kein automatischer Importfilter.
- Das optionale Zielprofil bewertet importierte Ergebnisse nach der Recherche. Auch unbekannte oder nicht passende Unternehmen bleiben erhalten.

### Entdecken – Unternehmen recherchieren

- Datenquelle, Branchenbegriffe, Orte, Radius und Suchumfang auswählen.
- Vorschau vor dem Start; Fortschritt, Dauer und Ergebnisse eines Suchlaufs anzeigen.
- Quellen umfassen OpenStreetMap/Overpass, Geoapify, SerpApi, lokale Google-Maps-Browsersuche sowie DataForSEO-/Serper-Adapter. Verfügbarkeit hängt von Einrichtung und Anbieter ab.
- Lokale Maps-Suche mit schneller oder gebietsweise gründlicher Suche, Ergebnisfiltern und gespeicherten Suchabschnitten.
- Doppelte Rechercheeinträge möglichst vermeiden.
- Optional anschließend öffentliche E-Mails für Unternehmen dieses Suchlaufs suchen.
- Recherche stoppen und Ergebnisse später weiterbearbeiten.
- Die lokale Maps-Suche ist experimentell und verspricht keine vollständige Abdeckung. Anbieter-, Radius-, Mengen- und Budgetgrenzen bleiben relevant.

### Unternehmen – Daten prüfen und ergänzen

- Suche, Mehrfachfilter, weitere Merkmale, gespeicherte Ansichten und Seitenwechsel.
- Bekannte E-Mails, Telefonnummern, Websites, Quellen und verlinkte Social-Profile anzeigen.
- Kompakte E-Mail-Anzeige mit aufklappbaren zusätzlichen Adressen und Prüfdetails.
- Unternehmensprofil mit Stammdaten und verknüpften Kontakten als Pop-up öffnen.
- Strukturierte Website-Angaben zu Telefon, Adresse und Kontaktstellen mit Quelle als Vorschläge prüfen, übernehmen oder verwerfen; bestehende Werte bleiben bis zur ausdrücklichen Übernahme erhalten.
- Unternehmen auswählen und Aktionen gesammelt ausführen.
- Öffentliche E-Mails schnell oder gründlich auf Unternehmensseiten suchen.
- Ergebnisse, Teilerfolge, Fehlergründe und Quellen prüfen; geeignete vorübergehende Fehler begrenzt erneut versuchen.
- Öffentliche Ansprechpersonen suchen und Vorschläge gesondert prüfen.
- Kontakt manuell ergänzen oder Unternehmen als Firmenkontakt übernehmen.
- Kontaktlose Datensätze bereinigen oder ausdrücklich ausgewählte Unternehmen reversibel aus der aktiven Liste entfernen.
- Unternehmensentfernung löscht keine verknüpften Kontakte/Kampagnen und stoppt keinen Versand.

### Kontakte – Empfänger verwalten

- Bekannte Personen und Firmenkontakte manuell erfassen oder geprüfte Vorschläge übernehmen.
- Suche, Filter, Mehrfachauswahl und CSV-Export.
- Notizen, Bearbeiten, Kontaktsperre und wiederherstellbares Löschen über Aktionen.
- Kontakte mit gültiger E-Mail für manuelle Kampagnen auswählen; technische Verifizierung ist in diesem Ablauf optional.
- Sperren und Abmeldungen bleiben Versandhindernisse. Eine gültige Schreibweise oder vorhandene Mail-Domain beweist keine Zustellbarkeit.
- Öffentlich verlinkte Profile sind Quellenhinweise, keine bestätigte Identität.

### Kampagnen – Nachrichten gestalten

- Manuellen Entwurf mit Empfängern und Planungsangaben anlegen, speichern und später fortsetzen.
- Nachrichtenfolge aus Erstkontakt und zeitversetzten Folgeschritten bearbeiten.
- Rich-Text-Editor, Formatierung, Links, Platzhalter, Anhänge und personalisierte Vorschau.
- Schritte hinzufügen, duplizieren und umordnen; Abstände festlegen.
- Optional einen KI-Textvorschlag auf Basis von Angebot und Kampagnenziel erzeugen und selbst bearbeiten.
- Verbundene Icon-Schritte: Kontakte → Entwurf → Vorschau → Vorbereiten → Freigabe.
- Vorbereitung und tatsächlichen Nachrichtenversand getrennt darstellen.
- Vorherige Kontaktierung und Überschneidungen über Kontakte, Adressen und zugeordnete Unternehmen vor Vorbereitung prüfen.
- Entwürfe als Vorlagen speichern; daraus neue Entwürfe ohne Empfänger oder bisherige Freigaben erstellen.
- Vorlagen können Suchkriterien und Zielprofil-Verweise enthalten; deren Übernahme startet keine Suche.
- Vorlagen übernehmen keine Anhänge oder privaten Absenderfelder. Im Nachrichtentext selbst enthaltene persönliche Angaben müssen dennoch geprüft werden.

### Postausgang – prüfen, freigeben und Versand verstehen

- Einzelne vorbereitete Nachrichten prüfen, freigeben oder ablehnen.
- Kampagnenbezogene Ansicht und getrennte Status für Prüfung, Freigabe, Planung, Versand und Probleme.
- Gründe für blockierten, unklaren oder wartenden Versand mit nächstem Handlungsschritt anzeigen.
- Versandpause, Tageslimit, Mailkonfiguration, Empfängersperren und weitere Versandregeln berücksichtigen.
- Folgeschritte warten auf erfolgreichen Versand des unmittelbaren Vorgängers und den festgelegten Abstand.
- „Versendet“ bedeutet dokumentierte Annahme durch den Versanddienst; kein Nachweis für Posteingang oder Lesen beim Empfänger.

### Unterhaltungen, Ergebnisse und Verkaufschancen

- Unterhaltungen nach Kampagne gruppieren und Nachrichten in einem Dialog öffnen.
- Antworten als geprüft markieren; neue Antworten erzeugen erneut Prüfbedarf.
- Qualifizierung und Terminstatus ausdrücklich manuell bewerten und korrigieren.
- Kampagnenergebnisse mit getrennten Nachrichten-/Kontaktzahlen und Zeitraum betrachten.
- Fehlende Zuordnung oder historische Datierung als unbekannt behandeln, statt Zahlen zu erfinden.
- Aus einer eingegangenen Antwort nach bestätigtem Interesse eine Verkaufschance anlegen oder verknüpfen.
- Phasen: neu, qualifiziert, Angebot, Verhandlung, gewonnen, verloren.
- Zuständigkeit, nächste Aufgabe, Datum und Notiz pflegen; offene Phasen benötigen Aufgabe und Datum.
- Mehrere Unterhaltungen desselben exakten Kontakts verknüpfen und Quellen erhalten.
- Eine Verkaufschance erzeugt keine automatische Nachricht, Termineinladung oder Qualifizierungsbewertung.

### Einstellungen, Betrieb, Nutzung und Hilfe

- Seitennavigation, Darstellung, DE/EN und responsive Ansichten.
- Agent starten/stoppen, Versand getrennt pausieren und Aktivitäten/Protokolle einsehen.
- Mailanbieter, Integrationen und Versandwerte über Einstellungen konfigurieren.
- Modellnutzung nach Zeitraum, Anbieter, Agent und Aufgabe betrachten.
- Anbieter-Kontingent mit Abfragezeitpunkt anzeigen; gezielter Aktualisierungsbutton umgeht den automatischen Cache.
- Kontingent des Kontos und ausschließlich von Siveron protokollierte Aufrufe unterscheiden.
- Ausführliche zweisprachige Hilfe mit Ablaufdarstellungen.

## 4. Typische durchgehende Workflows

### A. Neue Zielunternehmen bis zur ersten Nachricht

1. Angebot und Zielgruppe außerhalb oder innerhalb der vorhandenen Planungsfelder klären.
2. Unterstützte Signale bestätigen und optional ein Zielkundenprofil speichern.
3. Quelle, Begriffe und Region in Entdecken festlegen; Vorschau prüfen, dann Recherche starten.
4. Ergebnisse filtern, Quellen ansehen und öffentliche E-Mail-/Personensuche durchführen.
5. Passende Firmenkontakte oder Personen ausdrücklich übernehmen.
6. Kontakte mit E-Mail auswählen und Kampagnenentwurf erstellen.
7. Text, Platzhalter, Anhänge und Folgeschritte prüfen; Überschneidungen kontrollieren.
8. Personalisierte Vorschau ansehen und zur Freigabe vorbereiten.
9. Nachrichten im Postausgang ausdrücklich freigeben.
10. Versandvoraussetzungen und tatsächlichen Status prüfen; Antworten bearbeiten.

### B. Bekannter Kontakt ohne Recherche

Kontakt manuell hinzufügen → Kampagne entwerfen → Vorschau → vorbereiten →
Postausgang prüfen und freigeben. Unternehmensrecherche ist dafür keine Voraussetzung.

### C. Interessierte Antwort weiterführen

Unterhaltung öffnen → Antwort und Quellen prüfen → Ergebnis bei Bedarf manuell
bewerten → Interesse bestätigen und Verkaufschance anlegen → nächste Aufgabe mit
Datum/Zuständigkeit setzen → unter Heute nachhalten → Phase später korrigieren.

### D. Erfolgreichen Ablauf wiederverwenden

Gespeicherten Entwurf als Vorlage sichern → persönlichen Text prüfen → neuen leeren
Entwurf daraus erstellen → neue Empfänger wählen → Vorschau und Freigabe erneut
durchlaufen. Suchkriterien bei Bedarf separat übernehmen und prüfen.

## 5. Wo KI eine Rolle spielt – und wo nicht

**Vorhanden:** optionaler Textvorschlag im Kampagneneditor und modellgestützte
Agentenfunktionen für Schreiben, Analyse und Antwortbearbeitung, abhängig vom
jeweiligen Betriebsweg und der Konfiguration. Der manuelle Vorschlagsweg fordert
derzeit einen kurzen deutschen Text an; eine englische Oberfläche garantiert keine
englische KI-Ausgabe.

**Nicht pauschal KI-gesteuert:** Quellenimport, Filter, Statusprüfung, Versandregeln,
Vorlagenkopie, manuelle Ergebnisbewertung und Aufgabenableitung. Diese Abläufe
brauchen keine erfundene Modellentscheidung.

Die Anwendung besitzt neben dem manuellen Ablauf eigenständige Agentenpfade.
Vorschläge dürfen deshalb nicht unterstellen, dass jede Antwort ausschließlich
manuell bearbeitet wird oder jeder Betriebsweg identische Kontaktkriterien hat.
Modellzugang und Sicherheitsprüfungen dürfen für Komfortfunktionen nicht umgangen werden.

## 6. Bekannte Grenzen und bereits vorgesehene Erweiterungen

**Grenzen des aktuellen Standes:**

- Kein vollständiges Mehrbenutzer-CRM mit Rollen-/Rechtesystem; Zuständigkeit ist zunächst Freitext.
- Keine garantierte Suchvollständigkeit, Identitätsprüfung oder E-Mail-Zustellbarkeit.
- Keine bereits belegte automatische Kontaktanreicherung über beliebige Facebook-, TikTok- oder LinkedIn-Profile.
- Keine vollständige Umsatz-, Kosten- oder ROI-Zuordnung pro Kampagne.
- Kein automatisch gebuchter Kalendertermin allein durch manuelle Terminbewertung.
- Keine numerischen Zielprofil-Regeln für beliebige Kennzahlen; der erste Ausbau bewertet Signalpräsenz und Nachweisqualität.
- Tests mit Mocks und Demodaten beweisen keine zuverlässige Live-Zustellung oder Anbieterabdeckung.

**Roadmap: Grundlagen bereits geliefert, Ausbau teilweise offen:**

| Referenz | Stand / nächster Fokus |
| --- | --- |
| R01–R02 | Geführter Kampagnenablauf, Folgeschritt-Abstände und Versanddiagnose vorhanden. Bedienbarkeit und Randfälle weiter prüfen. |
| R03–R04 | Zielprofile und Prüfung vorheriger Kontaktierung vorhanden; weitergehende Regeln/Identitätsklärung offen. |
| R05–R06 | Aufgabenübersicht, lokale Ergebnisse und manuelle Bewertungen vorhanden; keine vollständige Umsatzanalyse. |
| R07 | E-Mail-Fehlerdiagnose und begrenzte Wiederholungen vorhanden; andere Recherchepfade ausbaufähig. |
| R08–R09 | Erste Vorlagen- und Verkaufschancenfunktion vorhanden; keine vollständige CRM-Suite. |
| R10 | Aufwand, Kosten und Ergebniszuordnung pro Kampagne verbessern. |
| R11 | Identität und unsichere Profilzuordnungen anhand öffentlicher Belege prüfen. |
| R12 | Optionale, beleggestützte KI-Eignungsbewertung und bearbeitbare Antwortentwürfe. |
| R13 | Maps-Parser, Anbieterdiagnosen und Wiederaufnahme robuster absichern. |
| R14 | Durchgehende Regressionstests für DE/EN, mobile Nutzung und wichtige Workflows. |
| R15 | Große Module schrittweise aufteilen, ohne vorab einen Frameworkwechsel zu verlangen. |

Diese Liste ist eine Momentaufnahme. Ideen bleiben Vorschläge, bis ihre Umsetzung
nachgewiesen ist. Open-Source-Kandidaten sind noch keine eingebauten Funktionen.

## 7. Rahmen für realistische technische Vorschläge

Lokale Python-Anwendung mit FastAPI, SQLite und separatem Hintergrundagenten.
Frontend: HTML, CSS und gewöhnliches JavaScript mit lokal eingebundenen Widgets.
Vorhandene Daten und Statusgrenzen sollen erhalten bleiben. Kein zusätzlicher
Cloud-Dienst, Frameworkwechsel oder komplettes Neuschreiben als Standardantwort.

Bei einer Open-Source-Empfehlung bitte unterscheiden:

1. Konkreter Code-/Komponentenimport.
2. Kleine anpassbare Bibliothek.
3. Rein konzeptionelle Workflow-/Designreferenz.

Lizenz, Wartung, Abhängigkeiten, lokale Nutzbarkeit und Integrationsaufwand müssen
an Primärquellen geprüft werden. Vermutete Fähigkeiten und nicht geprüfte Aussagen
sind als solche zu kennzeichnen.

## 8. Kopierbarer Auftrag an ChatGPT

> Du bist ein kritischer Produkt-, UX- und Vertriebsworkflow-Berater für ein kleines
> Softwareteam. Nutze den obigen Funktionsstand als Ausgangspunkt. Challenge die
> Lösung: Welche Arbeitsschritte sind unnötig kompliziert, welche Funktionen fehlen,
> und wo wären weniger Funktionen oder bessere Verknüpfungen sinnvoller?
>
> Behaupte keine eigene Codeprüfung. Trenne belegte Dokumentangaben, deine Annahmen
> und offene Fragen. Berücksichtige bereits implementierte Funktionen und die
> bestehende Roadmap, statt sie als neue Ideen zu verkaufen.
>
> Stelle zuerst höchstens fünf Fragen, deren Antworten die Priorisierung wesentlich
> verändern würden. Falls Angaben fehlen, liefere zusätzlich eine vorläufige
> Einschätzung mit ausdrücklich genannten Annahmen. Erfinde keine Zielgruppe,
> Produktleistung, Umsätze oder rechtliche Zulässigkeit der Kontaktaufnahme.
>
> Liefere danach:
>
> 1. Die fünf größten Brüche im End-to-End-Workflow, mit konkretem Nutzerszenario.
> 2. Eine priorisierte Tabelle mit höchstens zehn Verbesserungen: Problem, betroffener
>    Workflow, vorhandene Grundlage/Roadmap-ID, Änderung, Nutzen, Aufwand S/M/L,
>    Risiko, messbares Erfolgskriterium und kleinster sinnvoller erster Ausbau.
> 3. Kennzeichne jeden Vorschlag als Vereinfachung, Verbesserung einer vorhandenen
>    Funktion oder neue Funktion. Sage auch, welche Idee du vorerst streichen würdest.
> 4. Beschreibe für die drei wichtigsten Vorschläge den Ablauf vorher/nachher,
>    einschließlich Leerzustand, Fehlerfall, Rückgängigmachen sowie DE/EN und Mobil.
> 5. Falls KI sinnvoll ist: Welche Eingabedaten braucht sie, welchen belegbaren Mehrwert
>    liefert sie, wie wird Unsicherheit sichtbar, und wie funktioniert der Ablauf ohne KI?
> 6. Falls Open Source sinnvoll ist: Recherchiere aktuelle GitHub-Primärquellen und nenne
>    konkrete Komponenten/Funktionen, Lizenz, Integrationsart und Zusatzabhängigkeiten.
>    Wenn du nicht recherchieren kannst, kennzeichne Kandidaten als ungeprüft.
> 7. Schlage eine kurze Umsetzungsreihenfolge mit Abhängigkeiten und prüfbaren
>    Abnahmekriterien vor. Keine automatischen Freigaben, erfundene Identitätszuordnungen
>    oder Umgehung von Sperren als Abkürzung.
>
> Bewerte Nutzen anhand von Zeit bis zur ersten geprüften Kampagne, manuellen Schritten,
> Qualität belegter Kontakte, Verständnis des Versandstatus und tatsächlich bewerteten
> Ergebnissen. Mehr gefundene Datensätze allein sind kein Erfolg. Gib keine willkürlichen
> Nutzen-Prozentzahlen an. Antworte auf Deutsch, konkret und auch dann kritisch, wenn
> die beste Lösung darin besteht, eine Funktion wegzulassen.

## 9. Optionale Angaben vor dem Hochladen ergänzen

- Mein Angebot / Geschäftsmodell: …
- Zielgruppe und Region: …
- Teamgröße und Rollen: …
- Wichtigster wiederkehrender Anwendungsfall: …
- Aktuell größter Zeitverlust oder häufigster Fehler: …
- Gewünschtes messbares Ergebnis: …
- Monatliches Budget für externe Dienste: …
- Was ausdrücklich nicht verändert werden soll: …

Keine Passwörter, Tokens, privaten Kundenlisten oder Mailinhalte ergänzen.

## 10. Interne Vertiefung im Projekt

Diese Links helfen bei späterer Umsetzung; für die ChatGPT-Besprechung ist das
Dokument ohne die verlinkten Dateien nutzbar.

- [Aktuelle Roadmap](ROADMAP.md)
- [Modulübersicht](INDEX.md)
- [Architektur](ARCHITECTURE.md)
- [Open-Source-Kandidaten](OPEN_SOURCE_CANDIDATES.md)
- [Benutzerhandbuch Deutsch](HANDBUCH_DE.md)

Grundlage: vorhandene Modulunterlagen und die zuletzt im Projekt umgesetzten
Funktionsänderungen. Dies ist ein Produktbrief zur Diskussion, kein vollständiges
API-Verzeichnis, kein Sicherheits-/Rechtsaudit und kein Live-Betriebsbericht.
