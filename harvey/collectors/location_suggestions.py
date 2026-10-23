"""Geoapify city suggestions via a server-side key and shared free quota."""
import hashlib
import json
import math
import time

import httpx

from harvey.collectors.discovery_quota import reserve_quota


async def suggest_locations(state, text, language, api_key):
    empty = {'type': 'FeatureCollection', 'features': []}
    if len(text.strip()) < 3 or not api_key:
        return {**empty, 'available': bool(api_key)}
    key = 'location_suggestions:' + hashlib.sha256((language + ':' + text.casefold().strip()).encode()).hexdigest()
    cached = await state.get_setting(key)
    if cached:
        entry = json.loads(cached)
        if time.time() - entry['at'] < 86400:
            return entry['data']
    if not await reserve_quota(state, 'geoapify', 1):
        return {**empty, 'available': True, 'reason': 'quota'}
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
            response = await client.get('https://api.geoapify.com/v1/geocode/autocomplete',
                params={'text': text, 'type': 'city', 'lang': language, 'limit': 5, 'apiKey': api_key})
            response.raise_for_status()
            payload = response.json()
        features = []
        for feature in payload.get('features', [])[:5]:
            props = feature.get('properties', {})
            lat, lon = float(props['lat']), float(props['lon'])
            if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            properties = {key: str(props.get(key, '')) for key in ('formatted', 'city', 'state', 'country', 'country_code')}
            properties.update(lat=lat, lon=lon)
            features.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
                             'properties': properties})
        data = {**empty, 'features': features, 'available': True}
        await state.set_setting(key, json.dumps({'at': time.time(), 'data': data}))
        return data
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        # Never expose URLs, credentials or vendor error bodies in the UI.
        return {**empty, 'available': True, 'reason': 'unavailable'}
