"""Curated aliases improve selection; provider support remains authoritative."""
ALIASES = {
    'Arztpraxis': 'Arzt Ärzte Mediziner Praxis doctor physician medical',
    'Hausarztpraxis': 'Hausarzt Allgemeinmedizin Familienarzt general practitioner family doctor',
    'Zahnarzt': 'Zahnarztpraxis Zahnärzte dentist dental',
    'Elektriker': 'Elektro Elektrotechnik Elektroinstallation electrician',
    'Dachdecker': 'Dach Dachdeckerei roofer roofing',
    'Klempner': 'Sanitär Installateur plumber plumbing',
    'Heizungsbauer': 'Heizung Klimatechnik Wärmepumpe HVAC',
    'Gemeinschaftsverpflegung': 'Kantine Großküche Betriebsverpflegung catering',
    'Menühersteller': 'Menümanufaktur Menue Lebensmittel Fertiggerichte Hersteller Produktion',
    'Tiefkühlmenüs': 'Tiefkühlkost Frozen Food Cook Freeze Menüservice',
    'Schulverpflegung': 'Schulcatering Kita Essen Schulküche',
    'Seniorenverpflegung': 'Pflegeheim Klinikverpflegung Essen auf Rädern',
    'Parkplatzbetreiber': 'Parkraumbewirtschaftung Parkraummanagement Parkplatzmanagement Parkservice parking operator',
    'Parkhausbetreiber': 'Parkhaus Tiefgarage Parkhäuser parking garage operator',
    'Parkplatz': 'Parkplätze Parkplaetze parking car park parking lot',
    'Parkhaus': 'Parkhäuser Parkhaeuser Tiefgarage parking garage',
    'Flughafenparken': 'Flughafen Parkplatz Airport Parking',
    'Valet Parking': 'Valet Parkservice',
    'Lkw-Parkplatzbetreiber': 'Lkw Truck Parking',
}


def term_catalog(provider, supported):
    from harvey.collectors.discover import OpenStreetMap
    terms = list(dict.fromkeys([*ALIASES, *OpenStreetMap.SUGGESTED_TERMS]))
    return [{'value': term, 'searchBy': ALIASES.get(term, term),
             'supported': supported(provider, term)} for term in terms]
