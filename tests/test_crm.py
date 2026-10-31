import csv
import io
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from crm.db import Dispatch, Lead, Suppression
from crm.domain import Campaign, LeadInput, add_lead, campaign, render_message, set_config
from crm.providers import ProviderError, map_place
from crm.service import Busy, daily_counts, exclusive, execute

AT = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)


class FakeGmail:
    replies = set()
    sent = []
    fail = False

    def verify_sender(self, sender):
        assert sender == "maxvirelli@gmail.com"

    def has_reply(self, lead):
        return lead.email in self.replies

    def send(self, c, lead, stage, attachments):
        if self.fail:
            raise TimeoutError("Ambiguous timeout")
        self.sent.append((lead.id, stage))
        return {"id": str(len(self.sent)), "threadId": f"thread-{lead.id}"}

    def close(self):
        pass


@pytest.fixture(autouse=True)
def reset_fake():
    FakeGmail.replies = set()
    FakeGmail.sent = []
    FakeGmail.fail = False


def setup_campaign(sessions, n=1, **kwargs):
    with sessions.begin() as s:
        data = dict(enabled=True, approved=True, start_date="2026-11-02", end_date="2026-11-08")
        data.update(kwargs)
        set_config(s, "campaign", Campaign(**data).model_dump())
        for i in range(n):
            add_lead(s, LeadInput(name=f"Empresa {i}", email=f"contato{i}@empresa.com.br"))


def test_crud_normalization_duplicates_bulk_and_csv(client):
    item = {"name": "Clínica Teste", "email": "CONTATO@EMPRESA.COM.BR", "phone": "(11) 99999-0000", "reviews": 120}
    r = client.post("/api/leads", json=item)
    assert r.status_code == 200
    lead = r.json()
    assert lead["phone"] == "5511999990000"
    assert lead["email"] == "contato@empresa.com.br"
    assert client.post("/api/leads", json=item).status_code == 409
    assert client.get("/api/leads?q=clínica").json()["total"] == 1
    assert client.get("/api/leads?q=inexistente").json()["total"] == 0
    item["name"] = "Clínica Atualizada"
    assert client.put(f'/api/leads/{lead["id"]}', json=item).json()["name"] == item["name"]
    assert client.post("/api/leads/bulk", json={"ids": [lead["id"]], "action": "status", "status": "sem_interesse"}).status_code == 200
    assert client.post("/api/leads/bulk", json={"ids": [lead["id"]], "action": "delete"}).status_code == 200
    assert client.get("/api/leads").json()["total"] == 0
    assert client.post("/api/leads", json=item).status_code == 409
    data = "name,email,phone\nLoja Nova,nova@loja.com.br,\nDuplicada,nova@loja.com.br,\nInválida,invalid,\n"
    r = client.post("/api/import", files={"file": ("leads.csv", data, "text/csv")}).json()
    assert (r["added"], r["duplicates"], len(r["errors"])) == (1, 1, 1)
    assert "Loja Nova" in client.get("/api/export").text


def test_csv_formula_escape(client):
    client.post("/api/leads", json={"name": "=FORMULA", "notes": "  +TEST"})
    rows = list(csv.DictReader(io.StringIO(client.get("/api/export").text.lstrip("\ufeff"))))
    assert rows[0]["name"] == "'=FORMULA"
    assert rows[0]["notes"].startswith("'")


def test_capture_filters_and_real_contacts():
    place = {"title": "Clínica Brasil", "countryCode": "BR", "reviewsCount": 50, "phone": "+55 11 99999-0000", "placeId": "123", "url": "https://maps.google.com/test"}
    lead = map_place(place, "São Paulo", "Clínicas")
    assert lead.email is None and lead.phone == "5511999990000"
    for extra in [{"countryCode": "US"}, {"countryCode": ""}, {"reviewsCount": 49}, {"reviewsCount": 401}, {"website": "https://example.com"}, {"permanentlyClosed": True}]:
        assert map_place({**place, **extra}, "SP", "Clínicas") is None
    assert map_place({**place, "reviewsCount": 400, "emails": ["REAL@EMPRESA.COM.BR"]}, "SP", "Clínicas").email == "real@empresa.com.br"


def test_limits_shared_across_runs_and_categories(app):
    sessions = app.state.sessions
    setup_campaign(sessions, 80)
    with sessions.begin() as s:
        for lead in list(s.scalars(select(Lead).order_by(Lead.id)))[40:]:
            lead.status, lead.stage = "em_cadencia", 0
            lead.first_sent, lead.next_send = (AT-timedelta(days=3)).isoformat(), (AT-timedelta(days=1)).isoformat()
    r = execute(sessions, gmail_factory=FakeGmail, clock=AT)
    assert r["sent"] == 60
    with sessions() as s:
        assert daily_counts(s, "2026-11-02") == {"initial": 30, "followup": 30, "total": 60}
    assert execute(sessions, gmail_factory=FakeGmail, clock=AT)["sent"] == 0
    assert len(set(FakeGmail.sent)) == 60


def test_three_followups_then_archive_and_no_repeats(app):
    sessions = app.state.sessions
    setup_campaign(sessions)
    for day in [0, 2, 4, 6]:
        assert execute(sessions, gmail_factory=FakeGmail, clock=AT+timedelta(days=day))["sent"] == 1
        assert execute(sessions, gmail_factory=FakeGmail, clock=AT+timedelta(days=day))["sent"] == 0
    assert [stage for _, stage in FakeGmail.sent] == [0, 1, 2, 3]
    with sessions() as s:
        lead = s.get(Lead, 1)
        assert lead.status == "arquivado" and lead.next_send is None


def test_reply_and_optout_stop_every_followup(app):
    sessions = app.state.sessions
    setup_campaign(sessions, 2)
    execute(sessions, gmail_factory=FakeGmail, clock=AT)
    FakeGmail.replies = {"contato0@empresa.com.br"}
    with sessions.begin() as s:
        s.add(Suppression(email="contato1@empresa.com.br", reason="optout"))
    r = execute(sessions, gmail_factory=FakeGmail, clock=AT+timedelta(days=2))
    assert r["sent"] == 0 and r["replies"] == 1
    with sessions() as s:
        assert s.get(Lead, 1).status == "respondeu"
        assert s.get(Suppression, "contato0@empresa.com.br")


def test_failed_inbox_is_fail_closed(app):
    class BrokenInbox(FakeGmail):
        def has_reply(self, lead):
            raise ProviderError("Inbox unavailable")
    sessions = app.state.sessions
    setup_campaign(sessions, 2)
    execute(sessions, gmail_factory=FakeGmail, clock=AT)
    with pytest.raises(ProviderError):
        execute(sessions, gmail_factory=BrokenInbox, clock=AT+timedelta(days=2))
    assert len(FakeGmail.sent) == 2


def test_ambiguous_send_pauses_without_releasing_quota(app):
    sessions = app.state.sessions
    setup_campaign(sessions)
    FakeGmail.fail = True
    with pytest.raises(ProviderError):
        execute(sessions, gmail_factory=FakeGmail, clock=AT)
    with sessions() as s:
        assert s.get(Lead, 1).status == "pausado"
        assert s.scalar(select(Dispatch)).state == "incerto"
        assert daily_counts(s, "2026-11-02")["total"] == 1
    FakeGmail.fail = False
    assert execute(sessions, gmail_factory=FakeGmail, clock=AT)["sent"] == 0


def test_window_expiration_and_pause(app):
    sessions = app.state.sessions
    setup_campaign(sessions)
    assert execute(sessions, scheduled=True, clock=AT-timedelta(hours=1), gmail_factory=FakeGmail)["sent"] == 0
    assert execute(sessions, clock=AT+timedelta(days=7), gmail_factory=FakeGmail)["sent"] == 0
    assert execute(sessions, scheduled=True, clock=AT, gmail_factory=FakeGmail)["sent"] == 1


def test_global_execution_lease(app):
    with exclusive(app.state.sessions):
        with pytest.raises(Busy):
            with exclusive(app.state.sessions):
                pass
    with exclusive(app.state.sessions):
        pass


def test_campaign_and_templates_validation(client):
    assert client.get("/api/campaign").json()["enabled"] is False
    assert client.put("/api/campaign", json={"enabled": True}).status_code == 422
    assert client.put("/api/campaign", json={"daily_followup": 31}).status_code == 422
    assert client.put("/api/campaign", json={"start_date": "2026-11-01", "end_date": "2026-11-08"}).status_code == 422
    c = Campaign()
    c.templates[0].body = '<script>alert(1)</script> https://site.com/proposta?x=1&y=2'
    subject, plain, content = render_message(c, Lead(name="Empresa <b>Brasil</b>", city="São Paulo"), 0)
    assert '<script>' not in content
    assert 'href="https://site.com/proposta?x=1&amp;y=2"' in content
    assert 'basta responder' in plain
    assert "voltarei" not in render_message(c, Lead(name="Empresa", city="SP"), 3)[1]
    assert 'html' in client.get('/api/preview/0').json()


def test_attachments_and_status(client):
    r = client.post('/api/attachments?inline=true', files={'file':('image.png',b'example-image','image/png')})
    assert r.status_code == 200 and r.json()['inline']
    assert 'data' not in r.json()
    assert client.post('/api/attachments',files={'file':('evil.html',b'<script>','text/html')}).status_code == 422
    assert len(client.get('/api/attachments').json()) == 1
    assert client.delete('/api/attachments/'+str(r.json()['id'])).status_code == 200
    settings = client.get('/api/settings').json()
    assert all(isinstance(v,bool) for v in settings['variables'].values())
    assert client.post('/api/automation/run').status_code == 401
    assert client.get('/healthz').json()['status'] == 'ok'


def test_authentication_and_csrf(tmp_path, monkeypatch):
    from crm.main import create_app
    from fastapi.testclient import TestClient
    monkeypatch.setenv('CRM_ADMIN_PASSWORD','a-long-test-password')
    app = create_app('sqlite:///'+str(tmp_path/'auth.db'))
    with TestClient(app) as c:
        assert c.get('/api/leads').status_code == 401
        assert c.post('/auth/login',json={'password':'wrong'}).status_code == 401
        assert c.post('/auth/login',json={'password':'a-long-test-password'}).status_code == 200
        assert c.get('/api/leads').status_code == 200
        assert c.post('/api/leads',json={'name':'Test lead'}).status_code == 403
        assert c.post('/api/leads',headers={'Origin':'http://evil.com'},json={'name':'Test lead'}).status_code == 403
        assert c.post('/api/leads',headers={'Origin':'http://testserver'},json={'name':'Test lead'}).status_code == 200
        assert c.post('/api/logout',headers={'Origin':'http://testserver'}).status_code == 200
        assert c.get('/api/leads').status_code == 401


def test_capture_pipeline_idempotent_and_filtered(app, client, monkeypatch):
    class FakeApify:
        def start(self, city, niche, limit):
            assert city=='Campinas, SP' and limit==25
            return 'run-123'

        def poll(self, run_id):
            assert run_id=='run-123'
            place={'title':'Empresa Captada','countryCode':'BR','reviewsCount':120,'placeId':'place-1','phone':'11999999999'}
            return 'SUCCEEDED',[place,place,{**place,'website':'https://site.com'},{**place,'placeId':'place-2','emails':['invalid']}]

        def close(self):
            pass
    monkeypatch.setattr('crm.service.Apify',FakeApify)
    assert client.post('/api/capture',json={'city':'Campinas, SP','niche':'Oficinas','limit':25}).json()['status']=='RUNNING'
    assert client.post('/api/capture',json={'city':'Campinas, SP','niche':'Oficinas','limit':25}).status_code==409
    result=client.post('/api/capture/poll').json()
    assert (result['added'],result['duplicates'],result['rejected'])==(1,1,2)
    assert client.post('/api/capture/poll').json()==result
    assert client.get('/api/leads').json()['total']==1


def test_production_rejects_local_database(monkeypatch,tmp_path):
    from crm.main import create_app
    monkeypatch.setenv('CRM_ENV','production')
    with pytest.raises(RuntimeError,match='PostgreSQL'):
        create_app('sqlite:///'+str(tmp_path/'production.db'))


def test_manual_reply_also_prevents_reactivation(app,client):
    setup_campaign(app.state.sessions)
    with app.state.sessions.begin() as s:
        lead=s.get(Lead,1)
        lead.status='em_cadencia'
        lead.stage=0
        lead.first_sent=AT.isoformat()
        lead.next_send=AT.isoformat()
    assert client.post('/api/leads/bulk',json={'ids':[1],'action':'status','status':'respondeu'}).status_code==200
    assert client.post('/api/leads/bulk',json={'ids':[1],'action':'status','status':'em_cadencia'}).status_code==409
    assert execute(app.state.sessions,clock=AT,gmail_factory=FakeGmail)['sent']==0
