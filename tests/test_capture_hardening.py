import json

import httpx
import pytest
from sqlalchemy import select

from crm.db import Config, Lead
from crm.domain import Campaign
from crm.providers import Apify, ProviderError, classify_place
from crm.streamlit_bridge import LocalAPI, APIError


def place(**changes):
    return {'title': 'Empresa Elegível', 'countryCode': 'BR', 'reviewsCount': 150,
            'emails': ['contato@example.invalid'], 'placeId': 'eligible-place', **changes}


def test_email_is_mandatory_and_first_bad_optional_contact_does_not_discard_valid_lead():
    assert classify_place(place(emails=[]), 'Campinas', 'Oficinas')[1] == 'sem_email'
    assert classify_place(place(emails=['invalid']), 'Campinas', 'Oficinas')[1] == 'sem_email'
    lead, reason, warnings = classify_place(place(emails=['invalid', 'REAL@EXAMPLE.INVALID'], phone='bad-phone', instagram='not-a-url'), 'Campinas', 'Oficinas')
    assert reason is None and lead.email == 'real@example.invalid'
    assert lead.phone is None and lead.instagram == '' and warnings
    assert classify_place(place(countryCode=None, country='Brasil'), 'SP', 'Oficinas')[0]
    assert classify_place(place(website='https://website.example'), 'SP', 'Oficinas')[1] == 'com_site'


def test_bridge_campaign_errors_explain_period_and_approval_without_losing_existing_save(app):
    api = LocalAPI(app)
    # A fixture sem senha permite apenas chamadas locais de desenvolvimento.
    good = Campaign(name='Campanha que deve permanecer').model_dump()
    api.request('PUT', '/api/campaign', json=good)
    with pytest.raises(APIError, match='7 dias'):
        api.request('PUT', '/api/campaign', json={**good, 'start_date': '2026-11-01', 'end_date': '2026-12-01'})
    with pytest.raises(APIError, match='aprove'):
        api.request('PUT', '/api/campaign', json={**good, 'start_date': '2026-11-01', 'end_date': '2026-11-07', 'enabled': True})
    assert api.request('GET', '/api/campaign')['name'] == good['name']


def test_recovery_uses_existing_run_and_resumes_transient_state(client, monkeypatch):
    class Source:
        polls = 0
        def start(self, *args): raise AssertionError('Recuperação não deve iniciar busca')
        def poll(self, run_id):
            assert run_id == 'external-run'
            Source.polls += 1
            return ('ABORTING', []) if Source.polls == 1 else ('ABORTED', [place(), place(emails=[])])
        def close(self): pass
    monkeypatch.setattr('crm.service.Apify', Source)
    args = {'run_id': 'external-run', 'city': 'Campinas', 'niche': 'Oficinas'}
    assert client.post('/api/capture/recover', json=args).json()['status'] == 'ABORTING'
    result = client.post('/api/capture/poll').json()
    assert result['partial'] and result['imported']
    assert (result['added'], result['rejected']) == (1, 1)
    assert client.post('/api/capture/poll').json() == result
    assert client.get('/api/leads').json()['total'] == 1


def test_force_reevaluation_reads_same_run_without_duplicate_or_new_charge(client, monkeypatch):
    class Source:
        def start(self, *args): raise AssertionError('Não criar uma nova busca')
        def poll(self, run_id): return 'SUCCEEDED', [place()]
        def close(self): pass
    monkeypatch.setattr('crm.service.Apify', Source)
    args = {'run_id': 're-evaluate-run', 'city': 'Campinas', 'niche': 'Oficinas'}
    first = client.post('/api/capture/recover', json=args).json()
    second = client.post('/api/capture/recover', json={**args, 'force_refresh': True}).json()
    assert first['added'] == 1
    assert second['added'] == 0 and second['duplicates'] == 1
    assert second['previous_import']['added'] == 1
    assert client.get('/api/leads').json()['total'] == 1


def test_failed_import_keeps_run_recoverable_and_rolls_back_then_succeeds(app, client, monkeypatch):
    class Source:
        def poll(self, run_id): return 'SUCCEEDED', [place(), place(placeId='other', emails=['other@example.invalid'])]
        def close(self): pass
    from crm import service
    original = service.add_lead
    calls = []
    def fail_second(s, item):
        calls.append(item)
        if len(calls) == 2: raise RuntimeError('simulated interruption')
        return original(s, item)
    monkeypatch.setattr(service, 'Apify', Source)
    monkeypatch.setattr(service, 'add_lead', fail_second)
    args = {'run_id': 'recover-after-failure', 'city': 'Campinas', 'niche': 'Oficinas'}
    # A exceção é esperada; o estado da execução é salvo antes de importar.
    with pytest.raises(RuntimeError):
        service.recover_capture(app.state.sessions, **args)
    with app.state.sessions() as s:
        assert s.scalar(select(Lead)) is None
        assert json.loads(s.get(Config, 'capture').value)['run_id'] == args['run_id']
    monkeypatch.setattr(service, 'add_lead', original)
    result = client.post('/api/capture/poll').json()
    assert result['added'] == 2


def test_apify_retries_only_reads_and_never_repeats_chargeable_start(monkeypatch):
    monkeypatch.setenv('CRM_APIFY_TOKEN', 'fake-only')
    monkeypatch.setattr('crm.providers.time.sleep', lambda _: None)
    calls = []
    def handler(req):
        calls.append(req.method)
        if req.method == 'POST': raise httpx.ReadTimeout('not confirmed')
        return httpx.Response(503 if calls.count('GET') < 3 else 200, json={'ok': True})
    client = httpx.Client(base_url='https://api.apify.com/v2/', transport=httpx.MockTransport(handler))
    monkeypatch.setattr('crm.providers.httpx.Client', lambda **_: client)
    provider = Apify()
    try:
        assert provider.api('GET', 'actor-runs/id') == {'ok': True}
        with pytest.raises(ProviderError, match='Run ID'):
            provider.start('Campinas', 'Oficinas', 25)
        assert calls == ['GET', 'GET', 'GET', 'POST']
    finally:
        provider.close()
