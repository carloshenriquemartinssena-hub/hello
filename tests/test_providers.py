import base64
import json
from email import policy
from email.parser import BytesParser

import httpx
import pytest

from crm.db import Attachment, Lead
from crm.domain import Campaign
from crm.providers import Gmail, ProviderError


def gmail_mock(monkeypatch, handler):
    for key in ['CRM_GMAIL_CLIENT_ID','CRM_GMAIL_CLIENT_SECRET','CRM_GMAIL_REFRESH_TOKEN']:
        monkeypatch.setenv(key, 'test-only')
    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr('crm.providers.httpx.Client', lambda **_: client)
    return Gmail()


def test_gmail_reply_in_previous_thread_from_different_address(monkeypatch):
    def handler(request):
        path = request.url.path
        if path.endswith('/token'):
            return httpx.Response(200,json={'access_token':'fake-token'})
        if path.endswith('/profile'):
            return httpx.Response(200,json={'emailAddress':'maxvirelli@gmail.com'})
        if path.endswith('/threads/older'):
            return httpx.Response(200,json={'messages':[{'internalDate':'1793620801000','payload':{'headers':[{'name':'From','value':'Outra pessoa <diretoria@empresa.com.br>'}]}}]})
        raise AssertionError(str(request.url))
    gmail = gmail_mock(monkeypatch,handler)
    try:
        gmail.verify_sender('maxvirelli@gmail.com')
        lead=Lead(name='Empresa',email='contato@empresa.com.br',first_sent='2026-11-02T12:00:00+00:00',thread_id='latest')
        lead.history_threads=['older','latest']
        assert gmail.has_reply(lead)
    finally:
        gmail.close()


def test_gmail_mime_inline_image_pdf_and_subject_threads(monkeypatch):
    payloads=[]
    def handler(request):
        if request.url.path.endswith('/token'):
            return httpx.Response(200,json={'access_token':'fake-token'})
        if request.url.path.endswith('/threads/old-thread'):
            return httpx.Response(200,json={'messages':[{'payload':{'headers':[{'name':'Message-ID','value':'<old@example.com>'},{'name':'Subject','value':'Outro assunto'}]}}]})
        if request.url.path.endswith('/messages/send'):
            payloads.append(json.loads(request.content))
            return httpx.Response(200,json={'id':'msg-1','threadId':'new-thread'})
        raise AssertionError(str(request.url))
    gmail=gmail_mock(monkeypatch,handler)
    c=Campaign()
    lead=Lead(name='Clínica de Exemplo',email='contato@empresa.com.br',city='Campinas',thread_id='old-thread')
    attachments=[Attachment(id=1,name='foto.png',data=b'image-data',content_type='image/png',inline=True),Attachment(id=2,name='proposta.pdf',data=b'pdf-data',content_type='application/pdf',inline=False)]
    try:
        gmail.send(c,lead,1,attachments)
        assert 'threadId' not in payloads[0]  # Assunto diferente não força uma thread incompatível no Gmail.
        msg=BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(payloads[0]['raw']))
        assert msg['To']=='contato@empresa.com.br'
        assert msg['In-Reply-To']=='<old@example.com>'
        assert 'basta responder' in msg.get_body(preferencelist=('plain',)).get_content()
        assert 'cid:crm2-1' in msg.get_body(preferencelist=('html',)).get_content()
        assert {part.get_filename() for part in msg.walk() if part.get_filename()} == {'foto.png','proposta.pdf'}
    finally:
        gmail.close()


def test_oauth_failure_does_not_expose_provider_secret(monkeypatch):
    def handler(request):
        return httpx.Response(400,json={'error':'bad_credentials','secret':'never-display'})
    with pytest.raises(ProviderError) as e:
        gmail_mock(monkeypatch,handler)
    assert 'never-display' not in str(e.value)
