"""Validated rich-text documents and immutable local campaign attachments."""
import copy
import html
import json
import re
import uuid
from urllib.parse import urlsplit

from harvey.contacts import ContactError

MAX_FILE=10*1024*1024
MAX_TOTAL=20*1024*1024
MAX_ATTACHMENTS=5
TAGS={'doc':None,'paragraph':'p','hardBreak':'br','bulletList':'ul','orderedList':'ol','listItem':'li','blockquote':'blockquote'}
MARKS={'bold':'strong','italic':'em','underline':'u','strike':'s','link':'a'}
URL=re.compile(r'https?://\S+',re.I)
MERGE=re.compile(r'\{\{\s*(first_name|last_name|company|title|personalization)\s*\}\}')


def safe_link(value):
    if not isinstance(value,str) or len(value)>2000 or any(ord(c)<33 for c in value):
        raise ContactError('Invalid link. Use an https://, http:// or mailto: address.')
    try:parsed=urlsplit(value)
    except ValueError:raise ContactError('Invalid link. Use an https://, http:// or mailto: address.')
    if parsed.scheme.lower() not in ('https','http','mailto') or (parsed.scheme.lower()!='mailto' and (not parsed.hostname or parsed.username or parsed.password)):
        raise ContactError('Invalid link. Use an https://, http:// or mailto: address.')
    if '{{' in value or '}}' in value:
        raise ContactError('Links cannot contain placeholders.')
    return value


def rich_content(document, values=None):
    """Return normalized JSON, canonical plain text and HTML from a strict schema.

    Personalization occurs only in text nodes, never HTML or link attributes.
    No user supplied HTML, CSS, images, scripts, or arbitrary attributes survive.
    """
    if not isinstance(document,dict) or document.get('type')!='doc':
        raise ContactError('Invalid formatted message.')
    if len(json.dumps(document,ensure_ascii=False))>100000:
        raise ContactError('Formatted message is too large.')
    document=copy.deepcopy(document)
    count=0
    def visit(node,parent='',depth=0):
        nonlocal count
        count+=1
        if count>3000 or depth>25 or not isinstance(node,dict):
            raise ContactError('Formatted message is too complex.')
        kind=node.get('type')
        if not isinstance(kind,str):raise ContactError('Invalid formatted message.')
        if set(node)-{'type','attrs','content','marks','text'}:
            raise ContactError('Invalid formatted message.')
        allowed={'doc':{'paragraph','bulletList','orderedList','blockquote'},'paragraph':{'text','hardBreak'},'bulletList':{'listItem'},'orderedList':{'listItem'},'listItem':{'paragraph','bulletList','orderedList','blockquote'},'blockquote':{'paragraph','bulletList','orderedList','blockquote'}}
        if parent and kind not in allowed.get(parent,set()):
            raise ContactError('Invalid formatted message structure.')
        if kind=='text':
            text=node.get('text')
            if not isinstance(text,str) or len(text)>15000:
                raise ContactError('Invalid message text.')
            if values is not None:text=MERGE.sub(lambda m:str(values.get(m[1],'')),text)
            result={'type':'text','text':text}; output=html.escape(text).replace('\n','<br>'); links=[]
            marks=node.get('marks',[])
            if not isinstance(marks,list) or len(marks)>5:
                raise ContactError('Invalid text formatting.')
            clean=[]; seen=set(); linked=False
            for mark in marks:
                if not isinstance(mark,dict) or not isinstance(mark.get('type'),str) or mark.get('type') not in MARKS or mark['type'] in seen:
                    raise ContactError('Unsupported text formatting.')
                name=mark['type'];seen.add(name)
                if name=='link':
                    attrs=mark.get('attrs') or {}
                    if not isinstance(attrs,dict):raise ContactError('Invalid link.')
                    href=safe_link(attrs.get('href'))
                    clean.append({'type':'link','attrs':{'href':href,'target':None,'rel':'noopener noreferrer'}})
                    output='<a href="'+html.escape(href,quote=True)+'" rel="noopener noreferrer">'+output+'</a>'
                    links.append((href,text));linked=True
                else:
                    clean.append({'type':name});tag=MARKS[name];output='<'+tag+'>'+output+'</'+tag+'>'
            if clean:result['marks']=clean
            if not linked:links.append((None,text))
            return result,text,output,links
        if kind not in TAGS:
            raise ContactError('Unsupported message element.')
        if kind=='hardBreak':return {'type':'hardBreak'},'\n','<br>',[(None,'\n')]
        children=node.get('content',[])
        if not isinstance(children,list):raise ContactError('Invalid message structure.')
        if kind in ('bulletList','orderedList','listItem') and not children:raise ContactError('Empty list element.')
        parts=[visit(child,kind,depth+1) for child in children]
        clean={'type':kind}
        if parts:clean['content']=[part[0] for part in parts]
        separator='' if kind=='paragraph' else '\n'
        plain=separator.join(part[1] for part in parts)
        output=''.join(part[2] for part in parts)
        tag=TAGS[kind]
        if tag:output='<'+tag+'>'+output+'</'+tag+'>'
        runs=[]
        for index,part in enumerate(parts):
            if index and separator:runs.append((None,separator))
            runs.extend(part[3])
        return clean,plain,output,runs
    clean,plain,output,links=visit(document)
    if len(plain)>15000:raise ContactError('Message is too long.')
    outside=[];anchors=0;previous=None
    for href,text in links:
        if href:
            if href!=previous:anchors+=1
            previous=href;outside.append(' ')
        else:
            previous=None;outside.append(text)
    if anchors+len(URL.findall(''.join(outside)))>1:raise ContactError('A message can contain at most one web link.')
    return clean,plain,output


def attachment_ids(value):
    if value is None:return []
    if not isinstance(value,list) or len(value)>MAX_ATTACHMENTS or any(not isinstance(i,str) or not re.fullmatch('[a-f0-9]{32}',i) for i in value) or len(set(value))!=len(value):
        raise ContactError('Choose at most 5 different attachments.')
    return value


async def load_attachments(db, ids, include_content=False):
    ids=attachment_ids(ids);out=[]
    for aid in ids:
        row=await (await db.execute('SELECT id,filename,mime,size'+(',content' if include_content else '')+' FROM campaign_attachments WHERE id=?',(aid,))).fetchone()
        if not row:raise ContactError('An attachment is missing. Remove it and upload it again.')
        data=dict(zip(['id','filename','mime','size']+(['content'] if include_content else []),row))
        out.append(data)
    if sum(item['size'] for item in out)>MAX_TOTAL:raise ContactError('Attachments may total at most 20 MB per message.')
    return out


def file_type(filename,content):
    import io
    import zipfile
    if not isinstance(filename,str) or not 1<=len(filename)<=200 or filename in ('.','..') or any(c in filename for c in '/\\\r\n\x00') or any(ord(c)<32 or ord(c)==127 for c in filename):
        raise ContactError('Invalid filename.')
    ext=filename.rsplit('.',1)[-1].lower()
    if ext=='pdf' and content.startswith(b'%PDF-'):return 'application/pdf'
    if ext=='png' and content.startswith(b'\x89PNG\r\n\x1a\n'):return 'image/png'
    if ext in ('jpg','jpeg') and content.startswith(b'\xff\xd8\xff'):return 'image/jpeg'
    if ext in ('txt','csv'):
        try:content.decode('utf-8')
        except UnicodeDecodeError:raise ContactError('Text attachments must use UTF-8.')
        return 'text/plain' if ext=='txt' else 'text/csv'
    if ext in ('docx','xlsx'):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names=set(archive.namelist())
                if '[Content_Types].xml' in names and ('word/document.xml' if ext=='docx' else 'xl/workbook.xml') in names:
                    return 'application/vnd.openxmlformats-officedocument.'+('wordprocessingml.document' if ext=='docx' else 'spreadsheetml.sheet')
        except (zipfile.BadZipFile,OSError):pass
    raise ContactError('Supported attachments: PDF, PNG, JPG, UTF-8 TXT/CSV, DOCX and XLSX.')
