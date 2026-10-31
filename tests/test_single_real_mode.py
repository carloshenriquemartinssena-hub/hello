from datetime import timedelta

import pytest
from sqlalchemy import select

from crm.db import Dispatch, Lead
from crm.domain import campaign
from crm.service import daily_counts, execute
from test_crm import AT, FakeGmail, setup_campaign


@pytest.fixture(autouse=True)
def reset_gmail():
    FakeGmail.replies, FakeGmail.sent, FakeGmail.fail = set(), [], False


def test_single_test_sends_only_initial_and_pauses_without_enabling_campaign(app):
    setup_campaign(app.state.sessions, 3, enabled=False, approved=False)
    result = execute(app.state.sessions, selected=[1], single_test=True, gmail_factory=FakeGmail, clock=AT)
    assert result['sent'] == 1
    with app.state.sessions() as s:
        lead = s.get(Lead, 1)
        assert lead.stage == 0 and lead.status == 'pausado' and lead.next_send is None
        assert s.get(Lead, 2).stage == -1 and s.get(Lead, 3).stage == -1
        assert not campaign(s).enabled and not campaign(s).approved
        assert daily_counts(s, '2026-11-02')['initial'] == 1
    assert execute(app.state.sessions, selected=[1], single_test=True, gmail_factory=FakeGmail, clock=AT+timedelta(days=2))['sent'] == 0


def test_single_test_refuses_bulk_scheduled_expired_or_missing_email(app):
    setup_campaign(app.state.sessions, 2)
    for kwargs in [{'selected': [1, 2]}, {'selected': [1], 'scheduled': True}, {}]:
        with pytest.raises(ValueError):
            execute(app.state.sessions, single_test=True, gmail_factory=FakeGmail, clock=AT, **kwargs)
    assert execute(app.state.sessions, selected=[1], single_test=True, gmail_factory=FakeGmail, clock=AT+timedelta(days=8))['sent'] == 0
    with app.state.sessions.begin() as s:
        s.get(Lead, 1).email = None
    assert execute(app.state.sessions, selected=[1], single_test=True, gmail_factory=FakeGmail, clock=AT)['sent'] == 0
    with app.state.sessions() as s:
        assert s.scalar(select(Dispatch)) is None


def test_single_test_endpoint_requires_confirmation_and_exact_one(client, monkeypatch):
    import importlib
    module = importlib.import_module('crm.main')
    calls = []
    monkeypatch.setattr(module, 'execute', lambda sessions, **kwargs: calls.append(kwargs) or {'sent': 1})
    assert client.post('/api/send/test-one', json={'lead_id': 1}).status_code == 422
    assert client.post('/api/send/test-one', json={'lead_id': 1, 'confirmed': True}).status_code == 200
    assert calls == [{'selected': [1], 'single_test': True}]


def test_single_test_preview_uses_actual_selected_lead(client):
    lead = client.post('/api/leads', json={'name': 'Empresa Captada', 'city': 'Campinas', 'email': 'real-test@example.invalid'}).json()
    response = client.get('/api/preview/0', params={'lead_id': lead['id']}).json()
    assert 'Empresa Captada' in response['subject']
    assert 'Campinas' in response['plain'] and 'Empresa Exemplo' not in response['plain']


def test_single_test_uncertain_send_is_not_retried(app):
    from crm.providers import ProviderError
    setup_campaign(app.state.sessions, enabled=False, approved=False)
    FakeGmail.fail = True
    with pytest.raises(ProviderError):
        execute(app.state.sessions, selected=[1], single_test=True, gmail_factory=FakeGmail, clock=AT)
    FakeGmail.fail = False
    assert execute(app.state.sessions, selected=[1], single_test=True, gmail_factory=FakeGmail, clock=AT)['sent'] == 0
    with app.state.sessions() as s:
        assert s.get(Lead, 1).status == 'pausado'
        assert s.scalar(select(Dispatch)).state == 'incerto'
