"""Rich text validation, upload limits and MIME parity. No real network or mail."""
import copy
from email.message import EmailMessage

import pytest

from harvey.campaign_content import rich_content, safe_link, file_type, ContactError, attachment_ids
from harvey.integrations.mail_provider import set_message_content


def document(*nodes):
    return {'type':'doc','content':[{'type':'paragraph','content':list(nodes)}]}


def test_rich_text_personalization_is_escaped_and_has_plain_alternative():
    doc=document({'type':'text','text':'Guten Tag {{first_name}} & {{company}}','marks':[{'type':'bold'},{'type':'underline'}]})
    clean,plain,html=rich_content(doc,{'first_name':'Alex','company':'<img src=x onerror=alert(1)>'})
    assert plain=='Guten Tag Alex & <img src=x onerror=alert(1)>'
    assert '<strong>' in html and '<u>' in html
    assert '&lt;img' in html and '<img' not in html
    assert '{{company}}' in doc['content'][0]['content'][0]['text']


@pytest.mark.parametrize('url',['javascript:alert(1)','data:text/html,a','https://example.test/\nfoo','https://user:secret@example.test/','https://example.test/{{company}}','http://[invalid'])
def test_unsafe_links_rejected(url):
    with pytest.raises(ContactError):safe_link(url)


def test_links_are_counted_even_when_their_urls_are_not_visible():
    node={'type':'text','text':'Website','marks':[{'type':'link','attrs':{'href':'https://example.test','onclick':'evil()'}}]}
    clean,plain,html=rich_content(document(node))
    assert plain=='Website' and 'onclick' not in html and 'https://example.test' in html
    with pytest.raises(ContactError):rich_content(document(node,{'type':'text','text':' '},copy.deepcopy(node)))


@pytest.mark.parametrize('node',[{'type':'image','attrs':{'src':'x'}},{'type':'script','text':'evil'}, {'type':['bad']}, {'type':'text','text':'a','marks':[{'type':'link','attrs':'bad'}]}])
def test_unknown_or_malformed_nodes_rejected(node):
    with pytest.raises(ContactError):rich_content(document(node))


def test_lists_and_quotes_keep_structure_and_plain_text():
    doc={'type':'doc','content':[{'type':'bulletList','content':[{'type':'listItem','content':[{'type':'paragraph','content':[{'type':'text','text':'Punkt 1'}]}]},{'type':'listItem','content':[{'type':'paragraph','content':[{'type':'text','text':'Punkt 2'}]}]}]},{'type':'blockquote','content':[{'type':'paragraph','content':[{'type':'text','text':'Zitat'}]}]}]}
    _,plain,html=rich_content(doc)
    assert plain=='Punkt 1\nPunkt 2\nZitat'
    assert '<ul><li>' in html and '<blockquote>' in html


def test_attachment_types_and_ids_are_validated():
    assert file_type('Dokument.pdf',b'%PDF-1.4\n')=='application/pdf'
    assert file_type('Notiz.txt','Grüße'.encode())=='text/plain'
    for name,data in [('fake.pdf',b'not a PDF'),('../x.txt',b'x'),('x.exe',b'MZ'),('x.txt',b'\xff')]:
        with pytest.raises(ContactError):file_type(name,data)
    with pytest.raises(ContactError):attachment_ids(['a'*32]*2)
    with pytest.raises(ContactError):attachment_ids(['not-an-id'])


def test_mime_has_plain_html_and_intact_attachment():
    msg=EmailMessage();set_message_content(msg,'Guten Tag','<p><strong>Guten Tag</strong></p>',[{'mime':'application/pdf','filename':'Angebot.pdf','content':b'%PDF-1.4\nexample'}])
    assert msg.get_content_type()=='multipart/mixed'
    assert msg.get_body(preferencelist=('plain',)).get_content().strip()=='Guten Tag'
    assert '<strong>' in msg.get_body(preferencelist=('html',)).get_content()
    attachment=list(msg.iter_attachments())[0]
    assert attachment.get_filename()=='Angebot.pdf'
    assert attachment.get_payload(decode=True)==b'%PDF-1.4\nexample'


def test_link_runs_split_by_formatting_are_one_link_and_cannot_hide_another_url():
    link={'type':'link','attrs':{'href':'https://one.test'}}
    doc=document({'type':'text','text':'Company ','marks':[link]}, {'type':'text','text':'website','marks':[link,{'type':'bold'}]})
    from bs4 import BeautifulSoup
    assert BeautifulSoup(rich_content(doc)[2],'html.parser').find('strong').get_text()=='website'
    doc['content'][0]['content'].extend([{'type':'text','text':' https://two.'},{'type':'text','text':'test','marks':[{'type':'italic'}]}])
    with pytest.raises(ContactError):rich_content(doc)


def test_literal_newlines_are_preserved_in_html():
    _,plain,html=rich_content(document({'type':'text','text':'One\n\nTwo'}))
    assert plain=='One\n\nTwo' and html=='<p>One<br><br>Two</p>'
