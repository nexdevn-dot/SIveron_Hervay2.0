"""Explicit parking intents; no substring guesses about unrelated businesses.

OSM: https://wiki.openstreetmap.org/wiki/Tag:amenity=parking
Geoapify: https://apidocs.geoapify.com/docs/places/#categories
Operator searches require operator evidence, not just a parking facility name.
"""
from dataclasses import dataclass
import unicodedata


@dataclass(frozen=True)
class ParkingIntent:
    operators: bool = False
    garages: bool = False


def parking_intent(term: str) -> ParkingIntent | None:
    key = ' '.join(unicodedata.normalize('NFKC', term).casefold().split())
    if key in {'parkplatzbetreiber', 'parkraumbewirtschaftung', 'parkraummanagement',
               'parkplatzmanagement', 'parkservice', 'parking operator', 'parking operators'}:
        return ParkingIntent(operators=True)
    if key in {'parkhausbetreiber', 'parking garage operator'}:
        return ParkingIntent(operators=True, garages=True)
    if key in {'parkhaus', 'parkhäuser', 'parkhaeuser', 'tiefgarage', 'tiefgaragen',
               'parking garage', 'parking garages'}:
        return ParkingIntent(garages=True)
    if key in {'parkplatz', 'parkplätze', 'parkplaetze', 'parkplätze und parkhäuser',
               'parking', 'car park', 'car parks', 'parking lot', 'parking lots'}:
        return ParkingIntent()
    return None


def parking_operator(raw: dict) -> str:
    """Only an explicit, usable operator name establishes an operator record."""
    value = str(raw.get('operator') or '').strip()
    return '' if value.casefold() in {'', 'yes', 'no', 'unknown', 'none', 'unbekannt', 'private', 'privat'} else value
