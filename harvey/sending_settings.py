"""Focused, atomic edits of the active YAML; keep unrelated data and comments."""
import hashlib
import os
from pathlib import Path
import tempfile

import yaml


class SendingSettingsError(ValueError):
    pass


def _mapping_child(node, key):
    if isinstance(node, yaml.MappingNode):
        return next((v for k,v in node.value if k.value==key), None)
    return None


def read_sending_settings(path):
    raw=Path(path).read_bytes()
    text=raw.decode('utf-8')
    config=yaml.safe_load(text)
    email=((config or {}).get('channels') or {}).get('email') or {}
    return {'enabled':email.get('enabled',True), 'max_daily_sends':email.get('max_daily_sends',50),
            'revision':hashlib.sha256(raw).hexdigest()}


def save_sending_settings(path, payload):
    if not isinstance(payload,dict) or type(payload.get('enabled')) is not bool or type(payload.get('max_daily_sends')) is not int or not 0<=payload['max_daily_sends']<=100000:
        raise SendingSettingsError('Bitte einen Versandstatus und ein ganzzahliges Tageslimit zwischen 0 und 100000 eingeben.')
    path=Path(path)
    raw=path.read_bytes()
    text=raw.decode('utf-8')
    if payload.get('revision')!=hashlib.sha256(raw).hexdigest():
        raise SendingSettingsError('Die Einstellungen wurden inzwischen geändert. Bitte neu laden.')
    root=yaml.compose(text)
    email=_mapping_child(_mapping_child(root,'channels'),'email')
    if not isinstance(email,yaml.MappingNode) or email.flow_style or not email.value:
        raise SendingSettingsError('Die E-Mail-Konfiguration kann in diesem Format nicht bearbeitet werden.')
    newline='\r\n' if '\r\n' in text else '\n'
    updates={'enabled':'true' if payload['enabled'] else 'false','max_daily_sends':str(payload['max_daily_sends'])}
    edits=[]
    for key,value in updates.items():
        node=_mapping_child(email,key)
        if node is not None:
            if not isinstance(node,yaml.ScalarNode):
                raise SendingSettingsError('Ungültige E-Mail-Konfiguration.')
            edits.append((node.start_mark.index,node.end_mark.index,value))
        else:
            first=email.value[0][0].start_mark
            start=text.rfind('\n',0,first.index)+1
            edits.append((start,start,' '*first.column+key+': '+value+newline))
    for start,end,replacement in sorted(edits,reverse=True):
        text=text[:start]+replacement+text[end:]
    # Validate before replacing any configuration. Nothing else is rewritten.
    expected=yaml.safe_load(path.read_text(encoding='utf-8'))
    expected['channels']['email'].update(enabled=payload['enabled'],max_daily_sends=payload['max_daily_sends'])
    if yaml.safe_load(text)!=expected:
        raise SendingSettingsError('Die Konfiguration konnte nicht sicher aktualisiert werden.')
    mode=path.stat().st_mode & 0o777
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',newline='',dir=path.parent,prefix='.'+path.name+'.',delete=False) as stream:
            temporary=Path(stream.name)
            os.chmod(temporary,mode)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if hashlib.sha256(path.read_bytes()).hexdigest()!=payload['revision']:
            raise SendingSettingsError('Die Konfiguration wurde inzwischen geändert. Bitte neu laden.')
        os.replace(temporary,path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return read_sending_settings(path)
