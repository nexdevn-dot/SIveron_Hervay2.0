---
name: Siveron Kontakte
description: Bestehende Dashboard-Gestaltung für Personensuche, Kontaktverwaltung und gehaltene Kampagnenentwürfe.
colors:
  accent: "#3269E8"
  bg: "#F5F8FC"
  panel: "#FFFFFF"
  border: "#E0E8F2"
  border-strong: "#C8D5E6"
  text: "#15243B"
  text-2: "#53647D"
  text-3: "#7889A1"
  error: "#b42318"
typography:
  body:
    fontFamily: "Geist, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "14px"
    lineHeight: 1.55
  label:
    fontSize: "11.5px"
    fontWeight: 500
rounded:
  sm: "5px"
  md: "8px"
  dialog: "12px"
spacing:
  field-columns: "16px"
  actions: "12px"
  dialog: "24px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.panel}"
    rounded: "{rounded.sm}"
    padding: "7px 14px"
  input:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "8px 11px"
  dialog:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.dialog}"
    padding: "{spacing.dialog}"
---

# Design System: Siveron Kontakte

## Overview

Lokale Bestandsaufnahme der Kontakt- und CRM-Erweiterung im Operate-Modus. Sie bewahrt die vorhandene Siveron-Identität: klare blaue Aktionen, helle Flächen, kompakte Formulare und sichtbare Quellen. Dies ist keine neue Produktidentität und kein globales Dashboard-Designsystem; ein PRODUCT.md oder ein neuer Comp wurde nicht vorausgesetzt.

Quelle der Implementierung: `harvey/web/app.css`, `index.html`, `contacts.js`, `crm.js` und die Kontaktansichten in `app.js`. Die Frontmatter beschreibt den hellen Standard. Die Komponenten erben die vorhandenen CSS-Variablen einschließlich des dunklen Themes; deren Werte bleiben im Stylesheet maßgeblich.

## Colors

Blau kennzeichnet primäre Aktionen und den Suchfortschritt. Neutrale Flächen und Konturen trennen Eingaben, Dialog und Vorschläge. Sekundärer Text trägt Erläuterungen und Herkunft; Fehlermeldungen verwenden den lokalen Fehler-Fallback. Das dunkle Theme verwendet dieselben Rollen, keine zusätzliche Palette für Kontakte.

## Typography

Geist trägt Text, Labels und Aktionen. Eingaben und normale Buttons verwenden (13px), kleine Buttons (12px). Native Formularbeschriftungen bleiben sichtbar und zugeordnet; versteckte Eingaben ziehen ihre Labels mit zurück. Quellen und lange Kontaktdaten dürfen umbrechen.

## Layout

Der zentrierte native Dialog ist höchstens (620px) breit, hält (16px) Abstand zu den Viewportkanten und ist auf die dynamische Viewporthöhe abzüglich (32px) begrenzt. Überlanger Inhalt scrollt im Dialog. Personen- und Kanalgruppen bilden zwei gleiche Spalten mit dem dokumentierten Spaltenabstand; Position füllt beide Spalten.

Bei höchstens (600px) werden diese Gruppen einspaltig und der Dialog erhält (18px) Innenabstand. Die Dashboard-Regeln bei höchstens (700px) vergrößern Eingaben auf mindestens (44px) Höhe und (16px) Schrift; Buttons erreichen (44px), kleine Buttons (40px). Aktionsgruppen und Vorschlags-Pagination umbrechen mit Flex-Wrap. Vorschläge sind durch horizontale Linien getrennt, mit (18px) vertikalem Innenabstand; Seiten zeigen maximal 20 Vorschläge.

Die Kontaktliste zeigt (30) Kontakte pro Seite. Suche und Sperrfilter stehen oberhalb der umbrechenden Auswahlleiste; die Filterspalten sind flexibel beziehungsweise höchstens (260px) breit. Bei höchstens (700px) wird die Tabelle zur vertikalen Liste: jede Zelle trägt ihre sichtbare Datenbeschriftung, die Tabellenkopfzeile entfällt. Kontaktaktionen bleiben mindestens (44px) hoch.

Notiz-, Sperr- und Kampagnenauswahldialoge sind höchstens (640px) breit; Viewportabstände und Höhenbegrenzung entsprechen dem Kontaktdialog. Ihr Innenabstand sinkt bei höchstens (700px) von (24px) auf (18px). Der Notizverlauf scrollt separat bis (35dvh).

Der Kampagneneditor ist auf (1000px) begrenzt. Das Briefing hat zwei Spalten mit (20px) Abstand, bei höchstens (700px) eine Spalte. Nachrichten stehen untereinander in Fieldsets mit (20px), mobil (16px) Innenabstand. Kontaktzeilen und Vorschau verwenden Trennlinien; lange Inhalte und erhaltene Textumbrüche bleiben lesbar.

## Elevation & Depth

Der Dialog liegt auf der Panel-Fläche mit einer einfachen Kontur. Ein dunkelblauer halbtransparenter Backdrop (`rgba(9,23,45,.55)`) trennt ihn vom Dashboard; die Erweiterung fügt keinen eigenen Schatten hinzu.

## Shapes

Eingaben und Buttons übernehmen die kleinen Dashboard-Radien, die Prüfung liegt in einer bestehenden Karte mit mittlerem Radius. Nur der Dialog besitzt den größeren Dialogradius. Flächen bleiben funktional und ohne dekorative Bildwelt.

## Components

- **Suchprüfung:** Auswahl von Unternehmen startet die Suche. Statussatz, nativer Fortschrittsbalken, Aktualisieren und Anhalten bilden laufende, abgeschlossene, angehaltene und unterbrochene Zustände ab. Bei unterbrochener Verbindung erklärt der Text, dass die Serversuche weiterlaufen kann. Reduzierte Bewegung verhindert den sanften Sprung zur Prüfung.
- **Personenvorschlag:** Name, Position, Unternehmen, verfügbare Kanäle, Quelle und Funddatum stehen vor „Prüfen und übernehmen“ und „Verwerfen“. Fehlende persönliche E-Mail wird ausdrücklich benannt. Vorschläge sind noch keine Kontakte.
- **Übernahmedialog:** Originalquelle prüfen, Daten ergänzen, dann ausdrücklich speichern. Kontaktart und Unternehmenszuordnung sind bei Vorschlägen gesperrt; die Unternehmenssuche samt Label ist verborgen. Quellenlinks öffnen separat mit `noopener noreferrer`; nur HTTP(S)-Quellen werden verlinkt.
- **Manuelle Anlage:** Person oder Firmenkontakt, optional bestehendes oder neues Unternehmen. Personen benötigen Vor- und Nachnamen; ein Firmenkontakt ohne Zuordnung benötigt einen Unternehmensnamen. Position, Website und Kanäle bleiben optional. Die UI ersetzt keine serverseitige Namens- oder Dublettenprüfung.
- **Formularzustände:** Speichern ist während der Anfrage gesperrt; ein Fehler bleibt im offenen Dialog als `role="alert"` sichtbar und erlaubt einen erneuten Versuch. Erfolg schließt den Dialog. Bei einer Dublette erklärt der Hinweis, dass Ergänzungen nicht gespeichert und bestehende Daten erhalten wurden. E-Mail bleibt nach dem Speichern ungeprüft.
- **Kontaktliste:** Suche nach Name, Unternehmen, E-Mail oder Telefon reagiert nach (300ms); Filterwechsel setzt Seite und Auswahl zurück. Mehrfachauswahl bleibt beim Seitenwechsel erhalten. „Diese Seite auswählen“ überspringt gesperrte Kontakte; diese haben deaktivierte Checkboxen. Auswahlzähler ist ein Status, der Ladebereich verwendet `aria-busy`. Leere Ergebnisse und Ladefehler erhalten Klartext.
- **Notizverlauf:** Nativer Dialog mit Datum, erhaltenen Zeilenumbrüchen und neuer Pflichtnotiz. Speichern sperrt den Button während der Anfrage, aktualisiert Verlauf und Zähler; Fehler bleiben als Alert im Dialog.
- **Kontaktbearbeitung:** Verwendet den bestehenden Anlagedialog mit gesperrter Kontaktart. Der Einführungstext erklärt erneute Prüfung bei geänderter E-Mail und Abbruch wartender Nachrichten bei Änderungen.
- **Nicht kontaktieren:** Eigener Dialog mit Pflichtgrund für eine neue Sperre. Bestehender Grund ist schreibgeschützt. Manuelle Sperren lassen sich ausdrücklich aufheben; Abmeldungen nicht. Unbestätigte externe Kampagnenpause bleibt als Warnung sichtbar, auch nach lokal gespeicherter Sperre. Die Kontaktübersicht bietet „Externe Pause erneut versuchen“.
- **Kampagnenauswahl und Entwurf:** Ausgewählte Kontakte öffnen einen neuen oder vorhandenen `manual_draft`. Der Editor trennt Name, Briefing (Zielgruppe, Angebot, Ziel, geplanter Absender, Signatur als Planungsnotiz), Kontaktstatus, Nachrichtenfolge und Vorschau. Kontakte können hinzugefügt und entfernt werden; fehlende, gesperrte und nicht verifizierte Kontakte bleiben ausdrücklich erkennbar. Speichern bestätigt einen gehaltenen Entwurf ohne Kampagnenstart; bereits übergebene Kampagnen sind schreibgeschützt. Ungespeicherte Änderungen verlangen vor dem Verwerfen eine Bestätigung.
- **Nachrichtenfolge und Vorschau:** Höchstens zehn Nachrichten mit Betreff, Text und Verzögerung (0–365 Tage); Nachricht eins bleibt bei null, weitere starten mit drei Tagen. Die kontaktbezogene Vorschau ersetzt `first_name`, `last_name`, `company`, `title` und `personalization` in doppelten geschweiften Klammern. Unbekannte Platzhalter erhalten eine sichtbare Warnung. Vorschau ist `aria-live="polite"`; die Signaturnotiz wird nicht automatisch angehängt.
- **Gemeinsame Primitive:** Primärbutton blau mit weißer Schrift, Hover-Deckkraft (.86); Sekundärbutton transparent mit Kontur. Gesperrte Buttons verwenden Deckkraft (.45). Tastaturfokus verwendet die globale blaue Kontur (2px); Eingaben ändern bei Fokus ihre Kontur. Kontaktlisten zeigen Herkunft und gegebenenfalls Quellenlink und Funddatum.

## Do's and Don'ts

- **Do** vorhandene Dashboard-Variablen und native Dialog-/Formularsemantik weiterverwenden.
- **Do** Quelle, fehlende Daten, laufende Suche und speicherbare Fehler ausdrücklich zeigen.
- **Don't** einen Personenvorschlag ohne ausdrückliches Speichern als Kontakt darstellen.
- **Don't** aus gespeichertem Kontakt eine geprüfte E-Mail oder Versandfreigabe ableiten; Entwicklungs-Sperren bleiben außerhalb dieser UI-Erweiterung erhalten.

Dokumentationsgrenze: Dieses Dokument hält implementierte UI-Regeln fest. Lokale Demo-Aufnahmen (`.impeccable/review/contacts-{desktop,mobile}.png` und `contact-manual-error-{desktop,mobile}.png`) und der bestätigte Finish-Review belegen die Darstellung; sie beweisen weder Live-Personensuche noch Mailzustellung. Der Finish-Fix-Batch umfasste Nichtnamenprüfung, verborgene Labels, Dublettenhinweis und den Fehlerzustand.

Die CRM-Erweiterung wurde im Finish-Review für diesen Umfang mit „ship“ bestätigt; zwölf neue CRM-Tests wurden geprüft. Finale lokale Demo-Aufnahmen: `.impeccable/review/crm-contacts-desktop.png`, `crm-contacts-user478.png`, `crm-campaign-desktop.png` und `crm-campaign-mobile.png` (jeweils im selben Review-Verzeichnis). Technische Bedienung: `docs/KONTAKTE_UND_KAMPAGNEN.md`. Die Demo und Mock-Tests belegen keine Live-Zustellung oder bestätigte externe Pause.
