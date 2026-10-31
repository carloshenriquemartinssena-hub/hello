import importlib

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from crm.db import Activity, Dispatch, Lead


def test_preparation_is_authenticated_repeatable_and_never_sends(tmp_path, monkeypatch):
    module = importlib.import_module('crm.main')
    monkeypatch.delenv('CRM_ENV', raising=False)
    token = 'test-worker-token-' + 'x' * 32
    monkeypatch.setenv('CRM_WORKER_TOKEN', token)

    def forbidden(*args, **kwargs):
        raise AssertionError('Preparação não pode enviar, captar nem consultar a caixa')

    monkeypatch.setattr(module, 'execute', forbidden)
    monkeypatch.setattr(module, 'start_capture', forbidden)
    monkeypatch.setattr(module, 'synchronize', forbidden)
    app = module.create_app('sqlite:///' + str(tmp_path / 'prepare.db'))
    with TestClient(app) as client:
        assert client.post('/api/automation/prepare').status_code == 401
        assert client.post('/api/automation/prepare', headers={'Authorization': 'Bearer wrong'}).status_code == 401
        for _ in range(2):
            response = client.post('/api/automation/prepare', headers={'Authorization': 'Bearer ' + token})
            assert response.status_code == 200
            assert response.json()['emails_sent'] == 0
            assert response.json()['capture_started'] is False
        with app.state.sessions() as s:
            for model in [Lead, Dispatch, Activity]:
                assert s.scalar(select(func.count()).select_from(model)) == 0


def test_manual_buttons_do_not_wait_for_preparation(client, monkeypatch):
    module = importlib.import_module('crm.main')
    calls = []
    monkeypatch.setattr(module, 'start_capture', lambda sessions, city, niche, limit: calls.append('capture') or {'status': 'RUNNING'})
    monkeypatch.setattr(module, 'execute', lambda sessions, **kwargs: calls.append(kwargs) or {'sent': 0})
    assert client.post('/api/capture', json={'city': 'Campinas', 'niche': 'Oficinas', 'limit': 25}).status_code == 200
    assert client.post('/api/send', json={'ids': [1]}).status_code == 200
    assert calls == ['capture', {'selected': [1]}]
