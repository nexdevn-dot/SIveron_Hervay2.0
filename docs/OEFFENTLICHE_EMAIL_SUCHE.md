# Öffentliche Firmen-E-Mails suchen

Stand der Bedienergänzung: 18.10.2026. Technischer Einstieg:
[Unternehmen](modules/companies.md), [Entdecken](modules/discovery.md).

## Aktueller Zugang

Unter **Unternehmen** Zeilen über die Kontrollkästchen markieren und das links
angeordnete Menü **Aktionen** öffnen. Dort liegen Suchmodus, Sammelsuche und
vorhandene Suchergebnisse. Die zusätzliche Auswahlleiste und deren Hinweistext
sind ausgeblendet. Einzelabfragen bleiben am jeweiligen Unternehmen möglich.
Fortschritt und Ergebnis erscheinen in einem schließbaren Fenster; Schließen
stoppt den Auftrag nicht. Anhalten erfolgt über die entsprechende Dialogaktion.

Unter **Entdecken** steht die optionale E-Mail-Suche direkt nach dem Quellenbereich
und den gegebenenfalls sichtbaren Maps-Optionen. Sie ist standardmäßig ausgeschaltet
und betrifft nur Unternehmen des aktuellen Suchlaufs. Das Finden einer öffentlichen
Adresse erzeugt keinen Kontakt und keine Versandfreigabe.

Die Einzel- und Sammelsuche verwenden dieselbe Erkennung. Sie lesen die
Unternehmenswebsite und im Modus Schnell bei Bedarf bis zu zwei Kontakt-/Impressumsseiten.
Im Modus Gründlich werden bis zu sechs Unterseiten inklusive Über-uns/Team geprüft.
Schnell beendet die Seitensuche nach einem passenden Fund. Interne Links werden
anhand von URL und Linktext priorisiert; fehlende Links werden durch
`/kontakt` und `/impressum` ergänzt. Scheitert die Startadresse, wird die
HTTPS-Variante mit beziehungsweise ohne `www` versucht.

## Erkennung und Prüfung

- Sichtbarer Text, `mailto:` und explizite Schreibweisen wie `[at]`, `(at)`,
  `[dot]` und `(punkt)` werden ausgewertet.
- **extruct 0.18** extrahiert JSON-LD und Microdata. Nur explizite
  `email`-Eigenschaften werden berücksichtigt; beliebige Skriptzeichenketten
  werden ignoriert. Extruct lädt keine weiteren Websites nach.
- **email-validator 2.3** prüft und normalisiert Schreibweise einschließlich
  Unicode. Lesezugriffe auf Firmenlisten führen keine DNS-Abfragen durch.
- Bei einer ausdrücklich gestarteten Suche wird die Mail-Domain über DNS
  geprüft. Das gemeinsame zusätzliche Wartebudget beträgt drei Sekunden.
  Zeitüberschreitungen werden als unbekannt gespeichert, Adressen bleiben
  erhalten. Es gibt keine SMTP-Verbindung und keine Postfachbestätigung.
- `info`, `kontakt`, `office`, `sales` und ähnliche bekannte Rollen werden als
  allgemeines Firmenpostfach gekennzeichnet. Andere Adressen bleiben
  unklassifiziert; es wird keine Personenzuordnung geraten.
- Firmendomain/Subdomains und die bestehende Liste gängiger Webmailanbieter
  bleiben zulässig. Fremde Agentur-Domains werden ausgefiltert.

Wenn keine passende Adresse im HTML gefunden wurde, rendert Playwright genau
eine erreichbare Kontaktseite beziehungsweise die Startseite. Dieser zweite
Versuch ist auf sechs Sekunden und 20 HTTP-Anfragen begrenzt. Ressourcen
bleiben auf der geprüften öffentlichen Firmendomain; private Ziele,
Fremddomains, WebSockets und Service Worker sind gesperrt. Jede Antwort ist
auf 1 MB begrenzt. Fehlendes Chromium beeinträchtigt die HTML-Suche nicht.

In der E-Mail-Spalte stehen Prüfmerkmale und Prüfdatum. Alle neu gefundenen
Adressen bleiben **ungeprüft** im Sinne einer tatsächlichen Postfachprüfung.
Quelle, erster Fundzeitpunkt, DNS-Ergebnis und letzter Prüfzeitpunkt werden
getrennt gespeichert. Bestehende Adressen erhalten zusätzliche Merkmale bei
der nächsten expliziten Suche. Es entstehen keine Personen oder Versandfreigaben.

## Sammelsuche

Auswahl und Ergebnisse werden in SQLite als Auftrag gespeichert. Zwei
Abfragen laufen gleichzeitig. Neuladen oder Schließen des Browser-Tabs
unterbricht den Auftrag nicht, solange das Dashboard läuft. Nach einem
Dashboard-Neustart wird ein unterbrochener Auftrag beim nächsten Öffnen der
Unternehmensansicht wiederaufgenommen; ein laufender Eintrag wird erneut
geprüft. Stoppen lässt bereits laufende Abfragen auslaufen. Einzelne Fehler
brechen den übrigen Auftrag nicht ab.

Die Warteschlange ist für den lokalen Dashboardprozess ausgelegt, nicht
für mehrere Serverprozesse. Maximal ein Sammelauftrag mit bis zu 1000 Firmen
ist gleichzeitig aktiv. Die bestehenden Versand- und Freigabeschalter werden
nicht verändert.

## Installation und Prüfung

`bash scripts/setup.sh` installiert die festgehaltenen Bibliotheken und
Chromium im Projektcache (`.cache/ms-playwright`). Die globale Installation
und Benutzerkonfiguration bleiben unverändert.

Tests: `bash scripts/test.sh -q`. Die automatisierten Tests verwenden
kontrollierte HTML-/DNS-Antworten und temporäre Datenbanken. Der echte Chromium-Pfad lässt sich mit
`HARVEY_BROWSER_TESTS=1 bash scripts/test.sh tests/test_company_contacts_browser.py -q`
prüfen; auch dabei werden alle HTTP-Antworten lokal simuliert. Eine gemessene
Trefferquote für echte Firmenwebsites ergibt sich daraus noch nicht.

Quellen: [extruct](https://github.com/scrapinghub/extruct),
[email-validator](https://github.com/JoshData/python-email-validator),
[Playwright](https://github.com/microsoft/playwright-python).

## Datensätze bereinigen

Der Button neben der Sammelsuche entfernt Unternehmen aus der aktiven Liste,
wenn gleichzeitig keine gültige bekannte E-Mail, keine Telefonnummer und
keine Website oder Domain vorliegen. Auch E-Mails und Telefonnummern von
Ansprechpersonen schützen das Unternehmen vor der Bereinigung. Die Prüfung
betrifft den gesamten Bestand, unabhängig von Seiten, Auswahl und Filtern.
Nach dem Bereinigen werden Filter und Auswahl zurückgesetzt.

Die Entfernung ist wiederherstellbar: Unternehmen werden in SQLite mit
`removed_at` und einer Bereinigungskennung markiert. Historie, Ansprechpersonen
und Suchaufträge bleiben erhalten. Firmenlisten, Bestandszähler und aktive
Zielgruppen berücksichtigen diese Markierung. „Bereinigung rückgängig machen“
stellt den letzten Vorgang wieder her; die Kennung bleibt im Browser-Tab auch
nach Neuladen verfügbar. Während einer E-Mail-Suche ist die Bereinigung gesperrt.
Es erfolgen keine Website- oder DNS-Abfragen bei dieser Funktion.

## Abweichende E-Mail-Domain im offiziellen Kontaktbereich

Die explizite Unternehmenssuche berücksichtigt auch Adressen mit anderer
Mail-Domain, wenn sie auf der offiziellen Website in einem kleinen sichtbaren
Kontakt- oder Impressumsblock stehen und dort ein Bestandteil des Firmennamens
außerhalb der E-Mail-Adresse genannt wird. Agentur-, Webdesign- und externe
Datenschutz-Hinweise zählen nicht als Firmenkontakt. Ohne diesen Nachweis gilt
weiter die bisherige Domain-Zuordnung. Es werden keine ähnlich klingenden Domains
erraten und keine fremden Websites nachgeladen. Die gespeicherten Adressen bleiben
ungeprüft; Quellen-URL und Zuordnungsnachweis (`official_contact_block`) bleiben
erhalten. Die strengere Zuordnung in der Personensuche bleibt unverändert.

## Kompakte Anzeige mehrerer Adressen

Die Unternehmensliste zeigt zunächst eine Adresse. Weitere Adressen lassen sich
über **Weitere E-Mail-Adressen** aufklappen; bei vielen Einträgen ist dieser
Bereich in der Höhe begrenzt und scrollbar. **Prüfdetails** öffnet die technischen
Hinweise je Adresse. Quelle und Prüfstatus bleiben sichtbar, sämtliche Adressen
bleiben gespeichert. Die Darstellung verändert weder Auswahl noch Versandregeln.


## Erweiterte Suche und Verknüpfung mit Entdecken

Der Suchmodus unter Unternehmen gilt für Einzel- und Sammelsuche. Sammelaufträge
speichern ihn für eine Wiederaufnahme. Gründlich priorisiert zusätzlich verlinkte
Über-uns- und Teamseiten sowie deutsche und englische Ersatzpfade. Ohne Fund
werden höchstens zwei Seiten im Browser dargestellt; Schnell verwendet höchstens
eine. Gesamtzeitlimits je Unternehmen: 25 beziehungsweise 80 Sekunden.

Die Extraktion filtert technische Domains, Dateiendungen und hashartige Treffer;
diese Zusatzregeln verändern nicht die manuelle Adressvalidierung. Explizit
verlinkte Social-Profile werden mit Quellseite gespeichert und unter Telefon /
Website als Verlinkte Profile angezeigt. Teilen-/Login-Links und erkannte
Beitragslinks werden verworfen. Plattformen werden nicht durchsucht.

Unter Entdecken ist Nach der Unternehmenssuche öffentliche E-Mails suchen
standardmäßig ausgeschaltet. Bei Aktivierung folgt eine eigene Fortschrittsphase
für höchstens 1000 unterschiedliche Unternehmen aus genau diesem Suchlauf,
einschließlich bereits bekannter Treffer. Einträge über der Grenze werden
ausgewiesen. Anhalten wirkt zwischen Einzelprüfungen. Suchergebnisse bleiben
ungeprüft; Personen, Kampagnen und Versandfreigaben werden nicht angelegt.
